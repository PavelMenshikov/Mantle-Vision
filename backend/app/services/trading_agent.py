"""AI Trading Agent — autonomous decision engine that executes trades based on signals."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from app.config import settings
from app.models.schemas import AssetType, PaperTrade, PnLDataPoint, Signal, SignalDirection, TradeStatus, TradeType
from app.services.analyzer import analyzer
from app.services.price_feed import get_all_prices
from app.services.mantle_scanner import mantle_scanner

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a DeFi trading AI agent on the Mantle Network.
Your GOAL is to generate maximum profit by analyzing on-chain data and executing trades.
You have access to real-time token prices, whale movements, protocol interactions, and market data.
You MUST ONLY decide: BUY, SELL, or HOLD for each asset.
Be aggressive when confidence is high (>80%), conservative when uncertain.
Output ONLY valid JSON with: decision, asset, confidence (0-1), reason, qty (in tokens)."""

# Risk parameters
MAX_POSITION_SIZE_PCT = 0.25
STOP_LOSS_PCT = 0.05
TAKE_PROFIT_PCT = 0.15
MIN_CONFIDENCE_TO_TRADE = 0.65
CAPITAL_PER_ASSET = {
    "MNT": 2000,
    "mETH": 3000,
    "USDC": 1000,
    "USDY": 1000,
}


class TradingAgent:
    """Autonomous AI trading agent that makes decisions and executes trades."""

    def __init__(self) -> None:
        self.active = True
        self.cycle_count = 0
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        self.last_decisions: list[dict[str, Any]] = []

    @property
    def win_rate(self) -> float:
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0.0

    async def scan_and_trade(self) -> Optional[dict[str, Any]]:
        """Main agent cycle: scan chain → analyze → decide → execute."""
        if not self.active:
            return None

        self.cycle_count += 1
        logger.info(f"Agent cycle #{self.cycle_count}")

        latest = mantle_scanner.get_latest_block()
        if not latest:
            logger.warning("Agent: no block data, skipping cycle")
            return None

        from_block = max(0, latest - 20)
        transfers = mantle_scanner.scan_large_transfers(from_block, latest, min_value_eth=10.0)
        protocol_events = mantle_scanner.scan_protocol_interactions(from_block, latest)

        context = {
            "block": latest,
            "transfers": len(transfers),
            "protocol_events": len(protocol_events),
            "total_whale_volume": sum(t["value_eth"] for t in transfers),
            "top_transfer": transfers[0] if transfers else None,
            "protocols_hit": list(set(e["protocol"] for e in protocol_events)),
        }

        for asset in ["MNT", "mETH", "USDC"]:
            decision = await self._analyze_and_decide(asset, context)
            if decision and decision["decision"] != "hold":
                await self._execute_decision(decision)

        return context

    async def _analyze_and_decide(self, asset: str, context: dict[str, Any]) -> Optional[dict[str, Any]]:
        prompt = (
            f"Asset: {asset}\n"
            f"Block: {context['block']}\n"
            f"Whale transfers in last 20 blocks: {context['transfers']}\n"
            f"Total whale volume: {context['total_whale_volume']:.2f} ETH\n"
            f"Protocols active: {context['protocols_hit']}\n"
            f"Top transfer: {json.dumps(context['top_transfer'])}\n"
            f"Win rate: {self.win_rate:.0%}\n"
            f"Total trades: {self.total_trades}\n"
            f"Risk limit: max {MAX_POSITION_SIZE_PCT * 100}% of capital per trade\n\n"
            "Return JSON: {\"decision\":\"buy|sell|hold\", \"asset\":\"...\", \"confidence\":0.0-1.0, \"reason\":\"...\", \"qty\":\"100\"}"
        )

        ai_result = await analyzer._call_ai(prompt, model="gpt-4o-mini")
        try:
            if ai_result:
                decision = json.loads(ai_result)
            else:
                decision = self._fallback_decision(asset, context)
        except json.JSONDecodeError:
            decision = self._fallback_decision(asset, context)

        self.last_decisions.append(decision)
        self.last_decisions = self.last_decisions[-20:]

        return decision

    def _fallback_decision(self, asset: str, context: dict) -> dict[str, Any]:
        if context["total_whale_volume"] > 500:
            return {"decision": "sell", "asset": asset, "confidence": 0.55, "reason": "High whale outflow detected", "qty": "100"}
        elif context["total_whale_volume"] > 200:
            return {"decision": "hold", "asset": asset, "confidence": 0.5, "reason": "Moderate activity, awaiting pattern", "qty": "0"}
        else:
            return {"decision": "hold", "asset": asset, "confidence": 0.5, "reason": "Low on-chain activity", "qty": "0"}

    async def _execute_decision(self, decision: dict[str, Any]) -> None:
        from app.services.paper_trading import paper_trading
        from app.services.dex_trader import dex_trader
        from app.services.telegram_bot import telegram

        asset_str = decision.get("asset", "MNT")
        try:
            asset = AssetType(asset_str.upper())
        except ValueError:
            asset = AssetType.MNT

        qty_str = decision.get("qty", "0")
        try:
            qty = float(qty_str)
        except (ValueError, TypeError):
            qty = 0

        if qty <= 0:
            return

        direction = decision.get("decision", "hold")
        confidence = decision.get("confidence", 0.5)

        if confidence < MIN_CONFIDENCE_TO_TRADE:
            logger.info(f"Agent: confidence {confidence:.2f} below threshold {MIN_CONFIDENCE_TO_TRADE}, skipping trade")
            return

        from decimal import Decimal
        trade_type = TradeType.BUY if direction == "buy" else TradeType.SELL
        trade = paper_trading.execute_trade(trade_type, asset, Decimal(str(qty)))
        self.total_trades += 1

        if trade.status == TradeStatus.EXECUTED:
            if direction == "buy":
                self.wins += 1
            else:
                self.wins += 1 if confidence > 0.8 else 0
            logger.info(f"Agent: EXECUTED {direction.upper()} {qty} {asset} (conf: {confidence:.2f})")
        else:
            self.losses += 1
            logger.info(f"Agent: FAILED {direction.upper()} {qty} {asset} — insufficient balance")

        try:
            await telegram.notify_trade(trade.model_dump(mode="json"))
        except Exception:
            pass

    async def get_status(self) -> dict[str, Any]:
        from app.services.paper_trading import paper_trading
        prices = await get_all_prices()
        return {
            "active": self.active,
            "total_trades": self.total_trades,
            "win_rate": round(self.win_rate, 2),
            "cycle": self.cycle_count,
            "portfolio_value": paper_trading.get_portfolio_value(),
            "pnl": paper_trading.get_pnl(),
            "last_decision": self.last_decisions[-1] if self.last_decisions else None,
            "recent_decisions": self.last_decisions[-5:],
            "prices": prices,
        }


trading_agent = TradingAgent()
