from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from app.config import settings
from app.models.schemas import Signal, SignalDirection, SignalSource

logger = logging.getLogger(__name__)

DIRECTION_MAP = {
    "bullish": "buy", "bearish": "sell",
    "neutral": "hold", "buy": "buy", "sell": "sell", "hold": "hold",
}


def _normalize_direction(raw: str) -> str:
    return DIRECTION_MAP.get(raw.lower(), "hold")

SYSTEM_PROMPT = """You are Mantle Vision AI, an on-chain intelligence and investigation agent for the Mantle Network.
You analyze blockchain data to detect:
1. Insider wallet clusters — groups of wallets funded from the same source acting in coordination
2. Anomalous behavior — wallets waking up after long inactivity, unusual transaction patterns
3. Whale exit traps — accumulation followed by distribution phases
4. Smart money reputation — wallets with consistently profitable historical patterns
5. Liquidity concentration risk — TVL dominated by few addresses

Your responses must be JSON with: signal_type (anomaly/insider/whale/risk), asset, direction (bullish/bearish/neutral),
confidence (0-1), reasoning with specific on-chain evidence, and relevant addresses/hashes.
Focus on Mantle ecosystem: MNT, mETH, USDC, USDY, fBTC, and protocols like
Cleopatra DEX, Methamorphosis LRT, Lendle lending, Merchant Moe, Agni Finance, Fluxion, etc."""


def _fallback_whale_analysis(data: dict[str, Any]) -> dict[str, Any]:
    total_value = data.get("totalValue") or data.get("total_value", 0)
    wallet_type = data.get("wallet_type", "unknown")
    tags = data.get("tags", [])
    score = data.get("sentinel_score", data.get("anomaly_score", 0))
    tag_str = ", ".join(tags[:5]) if tags else "no tags"
    reasoning_parts = [f"Address moved {total_value:.1f} MNT"]
    if wallet_type and wallet_type != "unknown":
        reasoning_parts.append(f"classified as {wallet_type}")
    if score:
        reasoning_parts.append(f"risk score {score:.0%}")
    reasoning_parts.append(f"tags: {tag_str}")
    reasoning_parts.append("Deep investigation: check funding sources and tx history on mantlescan.xyz")
    return {
        "type": "whale_movement",
        "asset": "MNT",
        "direction": "hold",
        "confidence": 0.0,
        "reasoning": ". ".join(reasoning_parts) + ".",
        "source": "on_chain_facts",
    }


def _fallback_market_trend(data: dict[str, Any]) -> dict[str, Any]:
    """Детерминированный fallback без random."""
    return {
        "type": "market_trend",
        "asset": "MNT",
        "direction": "hold",
        "confidence": 0.0,
        "reasoning": "Market trend analysis unavailable — AI providers offline.",
        "source": "no_data",
    }


def _fallback_signal(asset: str = "MNT") -> Optional[dict[str, Any]]:
    """
    Возвращает None когда AI недоступен.
    Никогда не генерирует случайные направления — это вводит пользователя в заблуждение.
    Вызывающий код должен обработать None и показать 'Insufficient data'.
    """
    logger.warning(f"All AI providers unavailable for {asset} — returning no signal")
    return None


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
        import asyncio

        def _call_altllm() -> Optional[str]:
            altllm = self._get_altllm()
            if not altllm:
                return None
            resp = altllm.chat.completions.create(
                model="altllm-standard",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
                max_tokens=500,
            )
            logger.info("Using AltLLM Standard for analysis (crypto-native AI)")
            return resp.choices[0].message.content

        def _call_openai() -> Optional[str]:
            client = self._get_openai()
            if not client:
                return None
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

        def _call_groq() -> Optional[str]:
            groq = self._get_groq()
            if not groq:
                return None
            resp = groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            logger.info("Using Groq for analysis")
            return resp.choices[0].message.content

        try:
            result = await asyncio.to_thread(_call_altllm)
            if result:
                return result
        except Exception as e:
            logger.warning(f"AltLLM call failed: {e}")

        try:
            result = await asyncio.to_thread(_call_openai)
            if result:
                return result
        except Exception as e:
            logger.warning(f"OpenAI call failed: {e}")

        try:
            result = await asyncio.to_thread(_call_groq)
            if result:
                return result
        except Exception as e:
            logger.warning(f"Groq call failed: {e}")

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
            direction=SignalDirection(_normalize_direction(data.get("direction", "hold"))),
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
            direction=SignalDirection(_normalize_direction(data.get("direction", "hold"))),
            confidence=data.get("confidence", 0.5),
            reasoning=data.get("reasoning", "No reasoning provided"),
            timestamp=datetime.now(timezone.utc),
            source=SignalSource.ANALYZER,
        )

    async def generate_signal(self, asset: str = "MNT") -> Optional[Signal]:
        ai_result = await self._call_ai(
            f"Generate a trading signal for {asset} on Mantle Network. "
            "Consider on-chain volume, whale activity, and market sentiment. Return JSON."
        )

        if not ai_result:
            return None

        try:
            data = json.loads(ai_result)
        except json.JSONDecodeError:
            return None

        return Signal(
            id=str(uuid4()),
            type=data.get("type", "combined_signal"),
            asset=data.get("asset", asset),
            direction=SignalDirection(_normalize_direction(data.get("direction", "hold"))),
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
            if signal:
                signals.append(signal)
        return signals


analyzer = AIAnalyzer()
