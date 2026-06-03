from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

ELFA_BASE = "https://api.elfa.ai/v1"


def _mock_social_signals() -> list[dict[str, Any]]:
    return [
        {"topic": "Mantle Network", "sentiment": 0.72, "volume": 15_200, "mentions_24h": 3200, "trending": True},
        {"topic": "mETH", "sentiment": 0.65, "volume": 8_900, "mentions_24h": 1800, "trending": True},
        {"topic": "MNT Staking", "sentiment": 0.81, "volume": 5_400, "mentions_24h": 950, "trending": False},
    ]


def _mock_market_sentiment() -> dict[str, Any]:
    return {
        "overall": 0.68,
        "fear_greed_index": 62,
        "bullish_percentage": 54.2,
        "bearish_percentage": 21.8,
        "neutral_percentage": 24.0,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _mock_prediction_markets() -> list[dict[str, Any]]:
    return [
        {
            "id": "pm-001",
            "question": "Will MNT reach $5 by end of Q2 2026?",
            "probability": 0.63,
            "volume": 1_200_000.0,
            "liquidity": 450_000.0,
        },
        {
            "id": "pm-002",
            "question": "Will Mantle TVL exceed $2B in 2026?",
            "probability": 0.71,
            "volume": 890_000.0,
            "liquidity": 320_000.0,
        },
    ]


def _mock_trending_topics() -> list[dict[str, Any]]:
    return [
        {"topic": "Mantle L2", "score": 95, "change_24h": 12.5, "related": ["scaling", "eth"]},
        {"topic": "Methamorphosis", "score": 88, "change_24h": 8.3, "related": ["lst", "mETH", "restaking"]},
        {"topic": "Cleopatra", "score": 76, "change_24h": 15.1, "related": ["dex", "mantle"]},
    ]


class ElfaAIClient:
    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key or settings.ELFA_AI_API_KEY
        self.demo_mode = not self.api_key or settings.DEMO_MODE
        self._client: Optional[httpx.AsyncClient] = None

        if self.demo_mode:
            logger.info("Elfa AI client running in DEMO mode (no API key)")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=ELFA_BASE,
                headers={"X-API-Key": self.api_key} if self.api_key else {},
                timeout=30.0,
            )
        return self._client

    async def get_social_signals(self) -> list[dict[str, Any]]:
        if self.demo_mode:
            return _mock_social_signals()
        client = await self._get_client()
        try:
            resp = await client.get("/social/signals")
            resp.raise_for_status()
            return resp.json().get("data", [])
        except httpx.HTTPStatusError as e:
            logger.error(f"Elfa social signals error: {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Elfa request failed: {e}")
            raise

    async def get_market_sentiment(self) -> dict[str, Any]:
        if self.demo_mode:
            return _mock_market_sentiment()
        client = await self._get_client()
        try:
            resp = await client.get("/sentiment/market")
            resp.raise_for_status()
            return resp.json().get("data", {})
        except httpx.HTTPStatusError as e:
            logger.error(f"Elfa sentiment error: {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Elfa request failed: {e}")
            raise

    async def get_prediction_markets(self) -> list[dict[str, Any]]:
        if self.demo_mode:
            return _mock_prediction_markets()
        client = await self._get_client()
        try:
            resp = await client.get("/prediction-markets")
            resp.raise_for_status()
            return resp.json().get("data", [])
        except httpx.HTTPStatusError as e:
            logger.error(f"Elfa prediction markets error: {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Elfa request failed: {e}")
            raise

    async def get_trending_topics(self) -> list[dict[str, Any]]:
        if self.demo_mode:
            return _mock_trending_topics()
        client = await self._get_client()
        try:
            resp = await client.get("/trending")
            resp.raise_for_status()
            return resp.json().get("data", [])
        except httpx.HTTPStatusError as e:
            logger.error(f"Elfa trending error: {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Elfa request failed: {e}")
            raise

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


elfa_client = ElfaAIClient()
