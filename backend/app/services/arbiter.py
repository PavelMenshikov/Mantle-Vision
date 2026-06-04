from __future__ import annotations

import json
import logging
import statistics
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from app.config import settings
from app.models.schemas import Signal, SignalDirection, SignalSource

logger = logging.getLogger(__name__)

ARBITER_SYSTEM_PROMPT = """You are a conservative risk arbiter for Mantle Vision, an on-chain intelligence platform.
Your ONLY job is to receive pre-computed multi-layer scores and recommend an action.

INPUT: 
- RSI strategy score (technical analysis)
- Volume strategy score (volume anomaly detection)
- Nostalgia strategy (pattern matching)
- Whale/Sentinel Score (wallet reputation + cluster + anomaly multi-factor scoring)
- Knowledge Base context (similar historical patterns)

OUTPUT rules:
- "approve": true only if at least 2 strategies agree AND average score > 0.6
- "approve": false if Sentinel Score > 0.8 (too risky)
- "decision": "buy" when opportunity is clear
- "decision": "sell" when risk is detected
- "decision": "hold" when no clear signal
- "confidence": output confidence 0.0-1.0
- "explanation": one sentence explaining the risk/reasoning

Output ONLY valid JSON with keys: approve, decision, confidence, explanation"""


class AIArbiter:
    """Refactored AI arbiter — receives strategy scores, returns YES/NO.

    This replaces the old approach of asking AI to generate signals from scratch.
    Now AI is just a gatekeeper: mathematically computed strategies propose trades,
    AI says yes/no (one cheap call instead of one per asset).
    """

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
                logger.warning(f"Arbiter: failed to init OpenAI: {e}")
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
                logger.warning(f"Arbiter: failed to init Groq: {e}")
        return self._groq_client

    def _get_altllm(self) -> Any:
        if self._altllm_client is None and self.altllm_key:
            try:
                from openai import OpenAI
                self._altllm_client = OpenAI(
                    api_key=self.altllm_key,
                    base_url="https://api.altllm.ai/v1",
                )
            except Exception as e:
                logger.warning(f"Arbiter: failed to init AltLLM: {e}")
        return self._altllm_client

    async def _call_ai(self, prompt: str) -> Optional[str]:
        altllm = self._get_altllm()
        if altllm:
            try:
                resp = altllm.chat.completions.create(
                    model="altllm-standard",
                    messages=[
                        {"role": "system", "content": ARBITER_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"},
                    max_tokens=200,
                )
                logger.info("Arbiter: using AltLLM Standard")
                return resp.choices[0].message.content
            except Exception as e:
                logger.warning(f"Arbiter: AltLLM call failed: {e}")

        client = self._get_openai()
        if client:
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": ARBITER_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"},
                    max_tokens=200,
                )
                return resp.choices[0].message.content
            except Exception as e:
                logger.warning(f"Arbiter: OpenAI call failed: {e}")

        groq = self._get_groq()
        if groq:
            try:
                resp = groq.chat.completions.create(
                    model="mixtral-8x7b-32768",
                    messages=[
                        {"role": "system", "content": ARBITER_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    max_tokens=200,
                )
                return resp.choices[0].message.content
            except Exception as e:
                logger.warning(f"Arbiter: Groq call failed: {e}")

        return None

    def _fallback_decision(
        self, strategy_results: dict[str, Any]
    ) -> dict[str, Any]:
        """Mathematical fallback when all AI providers fail."""
        scores = strategy_results.get("scores", {})
        whale = strategy_results.get("whale_score", {})

        whale_score_val = whale.get("whale_score", 0.0) if isinstance(whale, dict) else 0.0
        sentinel_val = whale.get("sentinel_score", whale_score_val) if isinstance(whale, dict) else 0.0
        top_risk = max(whale_score_val, sentinel_val)

        # Count strategy signals
        buy_count = sum(1 for s in scores.values() if s.get("signal") == "buy")
        sell_count = sum(1 for s in scores.values() if s.get("signal") == "sell")
        avg_score = statistics.mean([s.get("score", 0.5) for s in scores.values()]) if scores else 0.5

        if top_risk > 0.8:
            return {"approve": False, "decision": "hold", "confidence": 0.9, "explanation": f"Risk threshold exceeded (sentinel={sentinel_val:.2f})"}

        if buy_count >= 2 and avg_score > 0.6:
            return {"approve": True, "decision": "buy", "confidence": round(avg_score, 2), "explanation": "Majority buy with strong scores"}
        elif sell_count >= 2 and avg_score > 0.6:
            return {"approve": True, "decision": "sell", "confidence": round(avg_score, 2), "explanation": "Majority sell with strong scores"}
        else:
            return {"approve": False, "decision": "hold", "confidence": round(0.5 + avg_score * 0.3, 2), "explanation": "No strong consensus"}

    async def decide(
        self,
        asset: str,
        rsi_result: dict[str, Any],
        volume_result: dict[str, Any],
        nostalgia_result: dict[str, Any],
        whale_result: dict[str, Any],
        wallet_context: Optional[dict[str, Any]] = None,
        market_snapshot: Optional[dict[str, float]] = None,
    ) -> Signal:
        wallet_address = whale_result.get("address", "") if isinstance(whale_result, dict) else ""
        wallet_type = whale_result.get("wallet_type", "") if isinstance(whale_result, dict) else ""

        cluster_context = ""
        if wallet_context and wallet_context.get("cluster"):
            cl = wallet_context["cluster"]
            cluster_context = (
                f"\nWallet Investigation Context:\n"
                f"- Wallet {wallet_address[:10]}... is part of an insider cluster "
                f"({cl['total_members']} wallets, ${cl['total_volume']:,.0f} total volume)\n"
                f"- Cluster root funder: {cl.get('root_funder', 'unknown')[:10]}...\n"
            )

        market_context = ""
        if market_snapshot:
            market_context = (
                f"\nMarket Context for {asset}:\n"
                f"- Price: ${market_snapshot.get('price_usd', 'N/A')}\n"
                f"- 24h Change: {market_snapshot.get('change_24h', 0):.2f}%\n"
                f"- 24h Volume: ${market_snapshot.get('volume_24h', 0):,.0f}\n"
            )

        kb_context = ""
        try:
            from app.services.knowledge_base import knowledge_base
            kb_context = knowledge_base.get_context_for_ai(
                wallet_address,
                {
                    "whale_score": whale_result.get("whale_score", 0.0) if isinstance(whale_result, dict) else 0.0,
                    "sentinel_score": whale_result.get("sentinel_score", 0.0) if isinstance(whale_result, dict) else 0.0,
                },
            )
        except Exception:
            pass

        ai_prompt = json.dumps({
            "asset": asset,
            "rsi_strategy": rsi_result,
            "volume_strategy": volume_result,
            "nostalgia_strategy": nostalgia_result,
            "wallet_type": wallet_type,
            "wallet_analysis": whale_result,
        }, indent=2)

        extras = f"{market_context}{cluster_context}{kb_context}"
        if extras.strip():
            ai_prompt += f"\n\n{extras}"

        ai_response = await self._call_ai(ai_prompt)

        if ai_response:
            try:
                decision = json.loads(ai_response)
            except json.JSONDecodeError:
                decision = self._fallback_decision({
                    "scores": {"rsi": rsi_result, "volume": volume_result, "nostalgia": nostalgia_result},
                    "whale_score": whale_result,
                })
        else:
            decision = self._fallback_decision({
                "scores": {"rsi": rsi_result, "volume": volume_result, "nostalgia": nostalgia_result},
                "whale_score": whale_result,
            })

        approve = decision.get("approve", False)
        dir_val = decision.get("decision", "hold")
        confidence = decision.get("confidence", 0.5)
        explanation = decision.get("explanation", "No explanation")

        # Override: if sentinel_score or whale_score indicates extreme risk, always hold
        whale_score_val = whale_result.get("whale_score", 0.0) if isinstance(whale_result, dict) else 0.0
        sentinel_val = whale_result.get("sentinel_score", whale_score_val) if isinstance(whale_result, dict) else 0.0
        top_risk = max(whale_score_val, sentinel_val)
        if top_risk > 0.85:
            approve = False
            dir_val = "hold"
            confidence = 0.95
            explanation = f"Risk threshold exceeded (sentinel={sentinel_val:.2f})"

        # Map direction
        direction = SignalDirection.HOLD
        if approve and dir_val == "buy":
            direction = SignalDirection.BUY
        elif approve and dir_val == "sell":
            direction = SignalDirection.SELL

        return Signal(
            id=str(uuid4()),
            type="arbiter_decision",
            asset=asset,
            direction=direction,
            confidence=confidence,
            reasoning=f"RSI={rsi_result.get('score', 0.5):.2f}, Vol={volume_result.get('score', 0.5):.2f}, Nost={nostalgia_result.get('score', 0.5):.2f}, Whale={whale_score_val:.2f}, Sentinel={sentinel_val:.2f} | Arbiter: {explanation}",
            timestamp=datetime.now(timezone.utc),
            source=SignalSource.ANALYZER,
        )


arbiter = AIArbiter()
