from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from app.config import settings
from app.models.schemas import (
    AssetType,
    PaperTrade,
    PortfolioPosition,
    PnLDataPoint,
    TradeStatus,
    TradeType,
)

logger = logging.getLogger(__name__)

PERSIST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "portfolio_state.json")

INITIAL_CAPITAL = 10_000.0

TOKEN_PRICES: dict[str, float] = {
    "MNT": 0.82,
    "USDC": 1.00,
    "mETH": 3200.0,
    "USDY": 1.05,
    "fBTC": 85000.0,
}


class PaperTradingEngine:
    def __init__(self) -> None:
        self.capital: float = INITIAL_CAPITAL
        self.positions: dict[str, Decimal] = {a: Decimal("0") for a in AssetType}
        self.trades: list[PaperTrade] = []
        self.pnl_history: list[PnLDataPoint] = []
        self._load_state()

    def _load_state(self) -> None:
        if not os.path.exists(PERSIST_PATH):
            return
        try:
            with open(PERSIST_PATH) as f:
                data = json.load(f)
            self.capital = data.get("capital", INITIAL_CAPITAL)
            for k, v in data.get("positions", {}).items():
                if k in self.positions:
                    self.positions[k] = Decimal(str(v))
            self.trades = [PaperTrade(**t) for t in data.get("trades", [])]
            self.pnl_history = [PnLDataPoint(**p) for p in data.get("pnl_history", [])]
            logger.info(f"Portfolio state loaded: ${self.capital:.2f} cash")
        except Exception as e:
            logger.warning(f"Failed to load portfolio state: {e}")

    def _save_state(self) -> None:
        try:
            data = {
                "capital": self.capital,
                "positions": {k: str(v) for k, v in self.positions.items()},
                "trades": [t.model_dump(mode="json") for t in self.trades],
                "pnl_history": [p.model_dump(mode="json") for p in self.pnl_history],
            }
            with open(PERSIST_PATH, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save portfolio state: {e}")

    def _get_price(self, asset: str) -> float:
        return TOKEN_PRICES.get(asset, 1.0)

    def execute_trade(self, trade_type: TradeType, asset: AssetType, amount: Decimal) -> PaperTrade:
        price = self._get_price(asset.value)
        cost = float(amount) * price
        trade_id = str(uuid4())

        if trade_type == TradeType.BUY:
            if cost > self.capital:
                trade = PaperTrade(
                    id=trade_id,
                    type=TradeType.BUY,
                    asset=asset,
                    amount=amount,
                    price=price,
                    status=TradeStatus.FAILED,
                    timestamp=datetime.now(timezone.utc),
                )
                logger.warning(f"Trade {trade_id}: insufficient funds (need ${cost:.2f}, have ${self.capital:.2f})")
                return trade

            self.capital -= cost
            self.positions[asset.value] += amount
            logger.info(f"BUY {amount} {asset.value} @ ${price:.2f} | Remaining: ${self.capital:.2f}")

        elif trade_type == TradeType.SELL:
            current = self.positions.get(asset.value, Decimal("0"))
            if amount > current:
                trade = PaperTrade(
                    id=trade_id,
                    type=TradeType.SELL,
                    asset=asset,
                    amount=amount,
                    price=price,
                    status=TradeStatus.FAILED,
                    timestamp=datetime.now(timezone.utc),
                )
                logger.warning(f"Trade {trade_id}: insufficient {asset.value} balance (have {current})")
                return trade

            self.capital += cost
            self.positions[asset.value] -= amount
            logger.info(f"SELL {amount} {asset.value} @ ${price:.2f} | Capital: ${self.capital:.2f}")

        trade = PaperTrade(
            id=trade_id,
            type=trade_type,
            asset=asset,
            amount=amount,
            price=price,
            status=TradeStatus.EXECUTED,
            timestamp=datetime.now(timezone.utc),
        )
        self.trades.append(trade)
        self._record_pnl()
        self._save_state()
        return trade

    def get_positions(self) -> list[PortfolioPosition]:
        positions: list[PortfolioPosition] = []
        total_cost = INITIAL_CAPITAL - self.capital

        for asset_type in AssetType:
            amount = self.positions[asset_type.value]
            if amount == Decimal("0"):
                continue
            price = self._get_price(asset_type.value)
            value = float(amount) * price

            cost_basis = 0.0
            asset_trades = [t for t in self.trades if t.asset == asset_type and t.status == TradeStatus.EXECUTED]
            for t in asset_trades:
                if t.type == TradeType.BUY:
                    cost_basis += float(t.amount) * t.price
                else:
                    cost_basis -= float(t.amount) * t.price

            pnl = value - cost_basis
            pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0.0

            positions.append(PortfolioPosition(
                asset=asset_type,
                amount=amount,
                value=round(value, 2),
                pnl=round(pnl, 2),
                pnlPercent=round(pnl_pct, 2),
            ))

        return positions

    def get_portfolio_value(self) -> float:
        pos_value = sum(
            float(self.positions[at.value]) * self._get_price(at.value)
            for at in AssetType
        )
        return round(self.capital + pos_value, 2)

    def get_pnl(self) -> float:
        return round(self.get_portfolio_value() - INITIAL_CAPITAL, 2)

    def get_trades(self, limit: int = 50) -> list[PaperTrade]:
        return sorted(self.trades, key=lambda t: t.timestamp, reverse=True)[:limit]

    def get_pnl_chart(self) -> list[PnLDataPoint]:
        return self.pnl_history[-100:]

    def _record_pnl(self) -> None:
        self.pnl_history.append(PnLDataPoint(
            timestamp=datetime.now(timezone.utc),
            pnl=self.get_pnl(),
            portfolioValue=self.get_portfolio_value(),
        ))

    def reset(self) -> None:
        self.capital = INITIAL_CAPITAL
        self.positions = {a: Decimal("0") for a in AssetType}
        self.trades.clear()
        self.pnl_history.clear()
        self._save_state()
        logger.info("Portfolio reset to initial state")


paper_trading = PaperTradingEngine()
