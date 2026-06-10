from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import settings
from app.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scanner", tags=["scanner"])


@router.get("/status")
async def scanner_status():
    from app.services.mantle_scanner import mantle_scanner

    stats = await db.call(db.get_stats)
    latest_block = mantle_scanner.get_latest_block()
    prices = await db.call(db.get_cached_prices)

    # last signal time
    signals = await db.call(db.get_signals, limit=1)
    last_signal_ts = signals[0]["timestamp"] if signals else None

    is_sepolia = mantle_scanner.is_sepolia
    return {
        "latest_block": latest_block,
        "chain": "mantle-sepolia" if is_sepolia else "mantle",
        "mode": "live" if not settings.DEMO_MODE else "demo",
        "total_signals": stats["total_signals"],
        "total_trades": stats["total_trades"],
        "last_signal_at": last_signal_ts,
        "prices_cached": list(prices.keys()) if prices else [],
        "scanner_interval_s": 60 if is_sepolia else 180,
        "scanner_active": latest_block > 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
