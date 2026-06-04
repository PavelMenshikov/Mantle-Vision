from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from app.database import db
from app.models.schemas import Signal, SignalDirection, SignalSource
from app.services.analyzer import analyzer
from app.services.telegram_bot import telegram

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/signals", tags=["signals"])


@router.post("/generate")
async def generate_signal(asset: str = "MNT"):
    signal = await analyzer.generate_signal(asset)
    if not signal:
        raise HTTPException(status_code=503, detail="AI analysis unavailable — no signal generated")
    await db.call(db.save_signal, signal)
    await push_signal(signal)
    logger.info(f"Generated signal: {signal.id} {signal.direction.value} {signal.asset} ({signal.confidence:.0%})")
    return signal


@router.get("", response_model=list[Signal])
async def list_signals(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    source: Optional[str] = None,
    direction: Optional[str] = None,
):
    rows = await db.call(db.get_signals, limit=per_page, offset=(page - 1) * per_page, direction=direction, source=source)
    return [_row_to_signal(r) for r in rows]


@router.get("/{signal_id}", response_model=Signal)
async def get_signal(signal_id: str):
    row = await db.call(db.get_signal_by_id, signal_id)
    if not row:
        raise HTTPException(status_code=404, detail="Signal not found")
    return _row_to_signal(row)


@router.get("/stats", response_model=dict)
async def signal_stats():
    return await db.call(db.get_stats)


async def push_signal(signal: Signal) -> None:
    from app.api.ws import manager
    data = signal.model_dump(mode="json")
    await manager.broadcast(data)
    await telegram.notify_signal(data)


def _row_to_signal(row: dict) -> Signal:
    return Signal(
        id=row["id"],
        type=row["type"],
        asset=row["asset"],
        direction=SignalDirection(row["direction"]),
        confidence=row["confidence"],
        reasoning=row["reasoning"] or "",
        txHash=row.get("tx_hash"),
        timestamp=datetime.fromisoformat(row["timestamp"]),
        source=SignalSource(row["source"]),
    )
