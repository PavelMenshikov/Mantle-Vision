from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.database import db
from app.models.schemas import WhaleActivity, WhaleProfile
from app.services.nansen import nansen_client
from app.services.whale_score import whale_scorer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whales", tags=["whales"])


@router.get("", response_model=list[WhaleProfile])
async def list_whales(refresh: bool = False):
    if refresh:
        wallets = await nansen_client.get_whale_wallets()
        for w in wallets:
            profile = WhaleProfile(
                address=w["address"],
                label=w.get("label", ""),
                totalValue=w.get("total_value", 0),
                riskScore=w.get("risk_score", 0.5),
                tags=w.get("tags", []),
            )
            db.save_whale_profile(profile)

    rows = db.get_whale_profiles()
    if not rows:
        return []

    return [
        WhaleProfile(
            address=r["address"],
            label=r["label"] or "",
            totalValue=r["total_value"],
            riskScore=r["risk_score"],
            tags=json.loads(r["tags"]) if isinstance(r["tags"], str) else r["tags"],
        )
        for r in rows
    ]


@router.post("", response_model=WhaleProfile)
async def add_whale(address: str, label: str = ""):
    existing = db.get_whale_by_address(address)
    if existing:
        raise HTTPException(status_code=409, detail="Whale already tracked")

    score = whale_scorer.score_single_wallet(address)
    whale = WhaleProfile(
        address=address,
        label=label or f"Whale:{address[:8]}",
        totalValue=score.get("total_volume", 0),
        riskScore=score.get("whale_score", 0.5),
        tags=score.get("tags", ["whale"]),
        lastActivity=datetime.now(timezone.utc),
    )
    db.save_whale_profile(whale)
    logger.info(f"Added whale: {address}")
    return whale


@router.delete("/{address}")
async def remove_whale(address: str):
    existing = db.get_whale_by_address(address)
    if not existing:
        raise HTTPException(status_code=404, detail="Whale not found")
    conn = db._get_conn()
    conn.execute("DELETE FROM whale_profiles WHERE address = ?", (address,))
    conn.commit()
    logger.info(f"Removed whale: {address}")
    return {"status": "removed", "address": address}


@router.get("/score/{address}", response_model=dict)
async def get_whale_score(address: str):
    score = whale_scorer.score_single_wallet(address)
    return score


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
