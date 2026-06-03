from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import Signal, SignalDirection, SignalSource
from app.services.analyzer import analyzer
from app.services.elfa import elfa_client
from app.services.nansen import nansen_client
from app.services.telegram_bot import telegram

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/signals", tags=["signals"])

_signal_store: list[Signal] = []


@router.get("", response_model=list[Signal])
async def list_signals(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    source: Optional[str] = None,
    direction: Optional[str] = None,
):
    filtered = _signal_store
    if source:
        filtered = [s for s in filtered if s.source.value == source]
    if direction:
        filtered = [s for s in filtered if s.direction.value == direction]

    filtered.sort(key=lambda s: s.timestamp, reverse=True)
    start = (page - 1) * per_page
    return filtered[start:start + per_page]


@router.get("/{signal_id}", response_model=Signal)
async def get_signal(signal_id: str):
    for signal in _signal_store:
        if signal.id == signal_id:
            return signal
    raise HTTPException(status_code=404, detail="Signal not found")


@router.post("/generate", response_model=Signal)
async def generate_signal(asset: str = "MNT"):
    signal = await analyzer.generate_signal(asset)
    _signal_store.append(signal)
    return signal


async def push_signal(signal: Signal) -> None:
    _signal_store.append(signal)
    from app.api.ws import manager
    data = signal.model_dump(mode="json")
    await manager.broadcast(data)
    await telegram.notify_signal(data)
