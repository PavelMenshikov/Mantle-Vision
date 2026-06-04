from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from app.database import db
from app.services.mantle_scanner import mantle_scanner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scanner", tags=["scanner"])


@router.get("/status")
async def scanner_status():
    stats = db.get_stats()
    latest_block = mantle_scanner.get_latest_block()
    prices = db.get_cached_prices()

    # last signal time
    signals = db.get_signals(limit=1)
    last_signal_ts = signals[0]["timestamp"] if signals else None

    return {
        "latest_block": latest_block,
        "chain": "mantle",
        "mode": "demo",
        "total_signals": stats["total_signals"],
        "total_trades": stats["total_trades"],
        "last_signal_at": last_signal_ts,
        "prices_cached": list(prices.keys()) if prices else [],
        "scanner_interval_s": 120,
        "scanner_active": latest_block > 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
