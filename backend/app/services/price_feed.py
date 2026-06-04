"""Real-time price feed — CoinGecko via direct API (no key needed)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

REAL_PRICES: dict[str, float] = {
    "MNT": 0.85,
    "USDC": 1.00,
    "mETH": 3200.0,
    "USDY": 1.05,
    "fBTC": 85000.0,
}

MANTLE_ASSET_IDS = {
    "MNT": "mantle",
    "USDC": "usd-coin",
    "mETH": "mantle-staked-eth",
    "USDY": "ondo-us-dollar-yield",
    "fBTC": "fire-bitcoin",
}

_cache: dict[str, float] = {**REAL_PRICES}
_cache_time: float = 0
_cache_ttl = 60


async def _fetch_from_coingecko() -> dict[str, float]:
    ids = list(MANTLE_ASSET_IDS.values())
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{COINGECKO_BASE}/simple/price",
                params={"ids": ",".join(ids), "vs_currencies": "usd"},
            )
            if resp.status_code == 429:
                logger.warning("CoinGecko rate limited — using cached prices")
                return {}
            resp.raise_for_status()
            data = resp.json()
            prices: dict[str, float] = {}
            for symbol, cg_id in MANTLE_ASSET_IDS.items():
                if cg_id in data and "usd" in data[cg_id]:
                    prices[symbol] = data[cg_id]["usd"]
            return prices
    except Exception as e:
        logger.debug(f"CoinGecko fetch failed: {e}")
        return {}


async def get_price(symbol: str) -> float:
    global _cache, _cache_time
    now = datetime.now(timezone.utc).timestamp()
    if now - _cache_time > _cache_ttl:
        fresh = await _fetch_from_coingecko()
        if fresh:
            _cache.update(fresh)
            _cache_time = now
            logger.debug(f"Prices updated: {fresh}")
    return _cache.get(symbol.upper(), 1.0)


async def get_all_prices() -> dict[str, float]:
    global _cache, _cache_time
    now = datetime.now(timezone.utc).timestamp()
    if now - _cache_time > _cache_ttl:
        fresh = await _fetch_from_coingecko()
        if fresh:
            _cache.update(fresh)
            _cache_time = now
    return dict(_cache)


async def get_market_snapshot() -> dict[str, dict]:
    prices = await get_all_prices()
    snapshot = {}
    for symbol, price in prices.items():
        snapshot[symbol] = {
            "price_usd": price,
            "change_24h": 0.0,
            "volume_24h": 0.0,
        }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            cg_ids = list(MANTLE_ASSET_IDS.values())
            resp = await client.get(
                f"{COINGECKO_BASE}/simple/price",
                params={
                    "ids": ",".join(cg_ids),
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_24hr_vol": "true",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                for symbol, cg_id in MANTLE_ASSET_IDS.items():
                    if cg_id in data:
                        snapshot[symbol]["change_24h"] = data[cg_id].get("usd_24h_change", 0)
                        snapshot[symbol]["volume_24h"] = data[cg_id].get("usd_24h_vol", 0)
    except Exception as e:
        logger.debug(f"Market snapshot fetch failed: {e}")

    return snapshot
