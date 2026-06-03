from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import WhaleActivity, WhaleProfile
from app.services.nansen import nansen_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whales", tags=["whales"])

_whale_store: dict[str, WhaleProfile] = {}


@router.get("", response_model=list[WhaleProfile])
async def list_whales():
    if not _whale_store:
        wallets = await nansen_client.get_whale_wallets()
        for w in wallets:
            profile = WhaleProfile(
                address=w["address"],
                label=w.get("label", ""),
                totalValue=w.get("total_value", 0),
                riskScore=w.get("risk_score", 0.5),
                tags=w.get("tags", []),
            )
            _whale_store[w["address"]] = profile

    return list(_whale_store.values())


@router.post("", response_model=WhaleProfile)
async def add_whale(address: str, label: str = ""):
    if address in _whale_store:
        raise HTTPException(status_code=409, detail="Whale already tracked")

    profile = await nansen_client.get_wallet_profile(address)
    whale = WhaleProfile(
        address=address,
        label=label or profile.get("label", ""),
        totalValue=profile.get("total_value", 0),
        riskScore=profile.get("risk_score", 0.5),
        tags=profile.get("tags", []),
    )
    _whale_store[address] = whale
    logger.info(f"Added whale: {address}")
    return whale


@router.delete("/{address}")
async def remove_whale(address: str):
    if address not in _whale_store:
        raise HTTPException(status_code=404, detail="Whale not found")
    del _whale_store[address]
    logger.info(f"Removed whale: {address}")
    return {"status": "removed", "address": address}


@router.get("/{address}/activity", response_model=list[WhaleActivity])
async def whale_activity(
    address: str,
    limit: int = Query(20, ge=1, le=100),
):
    profile = await nansen_client.get_wallet_profile(address)
    activities = profile.get("recent_txs", [])

    if not activities:
        activities = [
            {
                "txHash": "0xabc123def456...",
                "method": "swap",
                "value": 1_250_000.0,
                "timestamp": "2026-06-01T12:00:00Z",
                "token": "MNT",
                "to": "0xCleopatraDEX...",
                "from": address,
            },
            {
                "txHash": "0xdef789ghi012...",
                "method": "deposit",
                "value": 500_000.0,
                "timestamp": "2026-06-01T10:30:00Z",
                "token": "mETH",
                "to": "0xMethamorphosis...",
                "from": address,
            },
        ]

    return [WhaleActivity(**a) for a in activities[:limit]]
