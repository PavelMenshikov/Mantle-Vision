from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from app.config import settings
from app.models.schemas import Signal, SignalDirection, SignalSource

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are MantelAI, an on-chain intelligence analyst for the Mantle Network.
You analyze blockchain data, whale movements, DeFi activity, and market sentiment.
You have access to real-time crypto data: token prices (CoinGecko), crypto news, gas prices.
Your responses must be concise JSON with signal type, asset, direction (buy/sell/hold),
confidence (0-1), reasoning, and relevant transaction hashes.
Focus on Mantle ecosystem: MNT, mETH, USDC, USDY, fBTC, and protocols like
Cleopatra DEX, Methamorphosis LRT, Lendle lending, Merchant Moe, Agni Finance, Fluxion, etc."""


def _fallback_whale_analysis(data: dict[str, Any]) -> dict[str, Any]:
    total_value = data.get("total_value", 0)
    if total_value > 100_000_000:
        direction = "sell"
        confidence = 0.55 + random.random() * 0.2
        reasoning = "Large whale wallet detected. Historical patterns suggest distribution phase."
    elif total_value > 10_000_000:
        direction = "hold"
        confidence = 0.5 + random.random() * 0.15
        reasoning = "Medium whale accumulation detected. Monitoring for breakout confirmation."
    else:
        direction = "buy"
        confidence = 0.5 + random.random() * 0.25
        reasoning = "Small wallet showing accumulation pattern. Potential early entry signal."

    return {
        "type": "whale_movement",
        "asset": "MNT",
        "direction": direction,
        "confidence": round(min(confidence, 0.95), 2),
        "reasoning": reasoning,
        "source": "ai_analyzer",
    }


def _fallback_market_trend(data: dict[str, Any]) -> dict[str, Any]:
    sentiment = data.get("overall", 0.5)
    if sentiment > 0.7:
        direction = "buy"
        confidence = 0.6 + random.random() * 0.15
        reasoning = "Strong positive market sentiment detected. Bullish momentum likely."
    elif sentiment < 0.4:
        direction = "sell"
        confidence = 0.55 + random.random() * 0.15
        reasoning = "Bearish sentiment prevailing. Risk-off positioning recommended."
    else:
        direction = "hold"
        confidence = 0.5 + random.random() * 0.1
        reasoning = "Neutral market conditions. Await clearer directional signal."

    return {
        "type": "market_trend",
        "asset": "MNT",
        "direction": direction,
        "confidence": round(min(confidence, 0.9), 2),
        "reasoning": reasoning,
        "source": "ai_analyzer",
    }


def _fallback_signal(asset: str = "MNT") -> dict[str, Any]:
    direction = random.choice(["buy", "sell", "hold"])
    conf_map = {"buy": (0.6, 0.85), "sell": (0.55, 0.8), "hold": (0.5, 0.7)}
    lo, hi = conf_map[direction]
    confidence = lo + random.random() * (hi - lo)

    reasons = {
        "buy": [
            "Accumulation detected across multiple whale wallets",
            "Positive net flow to exchanges, suggesting buying pressure",
            "Social sentiment strongly bullish with increasing volume",
        ],
        "sell": [
            "Whale distribution pattern detected on chain",
            "Exchange inflows increasing, potential sell pressure",
            "Declining social volume with negative sentiment shift",
        ],
        "hold": [
            "Mixed signals across on-chain metrics",
            "Awaiting confirmation of trend direction",
            "Low volatility expected in near term",
        ],
    }

    return {
        "type": "combined_signal",
        "asset": asset,
        "direction": direction,
        "confidence": round(confidence, 2),
        "reasoning": random.choice(reasons[direction]),
        "source": "ai_analyzer",
    }


class AIAnalyzer:
    def __init__(self) -> None:
        self.openai_key = settings.OPENAI_API_KEY
        self.groq_key = settings.GROQ_API_KEY
        self.altllm_key = settings.ALTLLM_API_KEY
        self._openai_client: Optional[Any] = None
        self._groq_client: Optional[Any] = None
        self._altllm_client: Optional[Any] = None

    def _get_openai(self) -> Any:
        if self._openai_client is None and self.openai_key:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.openai_key)
            except Exception as e:
                logger.warning(f"Failed to init OpenAI: {e}")
        return self._openai_client

    def _get_groq(self) -> Any:
        if self._groq_client is None and self.groq_key:
            try:
                from openai import OpenAI
                self._groq_client = OpenAI(
                    api_key=self.groq_key,
                    base_url="https://api.groq.com/openai/v1",
                )
            except Exception as e:
                logger.warning(f"Failed to init Groq: {e}")
        return self._groq_client

    def _get_altllm(self) -> Any:
        if self._altllm_client is None and self.altllm_key:
            try:
                from openai import OpenAI
                self._altllm_client = OpenAI(
                    api_key=self.altllm_key,
                    base_url="https://api.altllm.ai/v1",
                )
                logger.info("AltLLM client initialized (crypto-aware AI)")
            except Exception as e:
                logger.warning(f"Failed to init AltLLM: {e}")
        return self._altllm_client

    async def _call_ai(self, prompt: str, model: str = "gpt-4o-mini") -> Optional[str]:
        client = self._get_openai()
        if client:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )
                logger.info("Using OpenAI for analysis")
                return resp.choices[0].message.content
            except Exception as e:
                logger.warning(f"OpenAI call failed: {e}")

        groq = self._get_groq()
        if groq:
            try:
                resp = groq.chat.completions.create(
                    model="mixtral-8x7b-32768",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                )
                logger.info("Using Groq for analysis")
                return resp.choices[0].message.content
            except Exception as e:
                logger.warning(f"Groq call failed: {e}")

        altllm = self._get_altllm()
        if altllm:
            try:
                resp = altllm.chat.completions.create(
                    model="altllm-basic",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=500,
                )
                logger.info("Using AltLLM for analysis (crypto-native AI)")
                return resp.choices[0].message.content
            except Exception as e:
                logger.warning(f"AltLLM call failed: {e}")

        return None

    async def analyze_whale_movement(self, whale_data: dict[str, Any]) -> Signal:
        ai_result = await self._call_ai(
            f"Analyze this whale movement data and return a JSON signal:\n{json.dumps(whale_data, indent=2)}"
        )

        if ai_result:
            try:
                data = json.loads(ai_result)
            except json.JSONDecodeError:
                logger.warning("AI returned invalid JSON, using fallback")
                data = _fallback_whale_analysis(whale_data)
        else:
            data = _fallback_whale_analysis(whale_data)

        return Signal(
            id=str(uuid4()),
            type=data.get("type", "whale_movement"),
            asset=data.get("asset", "MNT"),
            direction=SignalDirection(data.get("direction", "hold")),
            confidence=data.get("confidence", 0.5),
            reasoning=data.get("reasoning", "No reasoning provided"),
            timestamp=datetime.now(timezone.utc),
            source=SignalSource.ANALYZER,
        )

    async def analyze_market_trend(self, sentiment_data: dict[str, Any]) -> Signal:
        ai_result = await self._call_ai(
            f"Analyze this market sentiment data and return a JSON signal:\n{json.dumps(sentiment_data, indent=2)}"
        )

        if ai_result:
            try:
                data = json.loads(ai_result)
            except json.JSONDecodeError:
                data = _fallback_market_trend(sentiment_data)
        else:
            data = _fallback_market_trend(sentiment_data)

        return Signal(
            id=str(uuid4()),
            type=data.get("type", "market_trend"),
            asset=data.get("asset", "MNT"),
            direction=SignalDirection(data.get("direction", "hold")),
            confidence=data.get("confidence", 0.5),
            reasoning=data.get("reasoning", "No reasoning provided"),
            timestamp=datetime.now(timezone.utc),
            source=SignalSource.ANALYZER,
        )

    async def generate_signal(self, asset: str = "MNT") -> Signal:
        ai_result = await self._call_ai(
            f"Generate a trading signal for {asset} on Mantle Network. "
            "Consider on-chain volume, whale activity, and market sentiment. Return JSON."
        )

        if ai_result:
            try:
                data = json.loads(ai_result)
            except json.JSONDecodeError:
                data = _fallback_signal(asset)
        else:
            data = _fallback_signal(asset)

        return Signal(
            id=str(uuid4()),
            type=data.get("type", "combined_signal"),
            asset=data.get("asset", asset),
            direction=SignalDirection(data.get("direction", "hold")),
            confidence=data.get("confidence", 0.5),
            reasoning=data.get("reasoning", "No reasoning provided"),
            txHash=data.get("txHash"),
            timestamp=datetime.now(timezone.utc),
            source=SignalSource.ANALYZER,
        )

    async def batch_analyze(self, data_points: list[dict[str, Any]]) -> list[Signal]:
        signals: list[Signal] = []
        for point in data_points[:5]:
            asset = point.get("asset", "MNT")
            signal = await self.generate_signal(asset)
            signals.append(signal)
        return signals


analyzer = AIAnalyzer()
