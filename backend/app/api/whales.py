from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from web3 import Web3

from app.database import db
from app.models.schemas import WhaleActivity, WhaleProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whales", tags=["whales"])


@router.get("", response_model=list[WhaleProfile])
async def list_whales(user_id: str = "", refresh: bool = False):
    if user_id:
        user_whales = await db.call(db.get_user_whales, user_id)
        result = []
        for uw in user_whales:
            row = await db.call(db.get_whale_by_address, uw["address"])
            if row:
                result.append(WhaleProfile(
                    address=row["address"],
                    label=uw["label"] or row["label"] or "",
                    totalValue=row["total_value"],
                    riskScore=row["risk_score"],
                    tags=json.loads(row["tags"]) if isinstance(row["tags"], str) else row["tags"],
                ))
            else:
                result.append(WhaleProfile(
                    address=uw["address"],
                    label=uw["label"] or f"Whale:{uw['address'][:8]}",
                ))
        return result

    rows = await db.call(db.get_whale_profiles)
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
async def add_whale(address: str, label: str = "", user_id: str = ""):
    from app.services.whale_score import whale_scorer
    score = whale_scorer.score_single_wallet(address)

    if user_id:
        added = await db.call(db.add_user_whale, user_id, address, label)
        if not added:
            raise HTTPException(status_code=409, detail="Whale already in your watchlist")
        whale = WhaleProfile(
            address=address,
            label=label or f"Whale:{address[:8]}",
            totalValue=score.get("total_volume", 0),
            riskScore=score.get("whale_score", 0.5),
            tags=score.get("tags", ["whale"]),
        )
        return whale

    existing = await db.call(db.get_whale_by_address, address)
    if existing:
        raise HTTPException(status_code=409, detail="Whale already tracked")

    whale = WhaleProfile(
        address=address,
        label=label or f"Whale:{address[:8]}",
        totalValue=score.get("total_volume", 0),
        riskScore=score.get("whale_score", 0.5),
        tags=score.get("tags", ["whale"]),
        lastActivity=datetime.now(timezone.utc),
    )
    await db.call(db.save_whale_profile, whale)
    logger.info(f"Added whale: {address}")
    return whale


@router.delete("/{address}")
async def remove_whale(address: str, user_id: str = ""):
    if user_id:
        removed = await db.call(db.remove_user_whale, user_id, address)
        if not removed:
            raise HTTPException(status_code=404, detail="Whale not found in your watchlist")
        return {"status": "removed", "address": address}

    existing = await db.call(db.get_whale_by_address, address)
    if not existing:
        raise HTTPException(status_code=404, detail="Whale not found")
    conn = db._get_conn()
    conn.execute("DELETE FROM whale_profiles WHERE address = ?", (address,))
    conn.commit()
    logger.info(f"Removed whale: {address}")
    return {"status": "removed", "address": address}


@router.get("/score/{address}", response_model=dict)
async def get_whale_score(address: str):
    from app.services.whale_score import whale_scorer
    score = whale_scorer.score_single_wallet(address)
    return score


@router.get("/{address}/activity", response_model=list[WhaleActivity])
async def whale_activity(
    address: str,
    limit: int = Query(20, ge=1, le=100),
):
    from app.services.mantle_scanner import mantle_scanner

    if not mantle_scanner.w3 or not mantle_scanner.is_connected:
        mantle_scanner._connect()
    if not mantle_scanner.w3:
        return []

    try:
        checksum = Web3.to_checksum_address(address)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid address")

    latest = mantle_scanner.get_latest_block()
    if not latest:
        return []

    activities = []
    from_block = max(0, latest - 200)
    for block_num in range(from_block, latest + 1):
        if len(activities) >= limit:
            break
        try:
            block = mantle_scanner.w3.eth.get_block(block_num, full_transactions=True)
            if not block or not block.get("transactions"):
                continue
            for tx in block.get("transactions", []):
                tx_from = (tx.get("from") or "").lower()
                tx_to = (tx.get("to") or "").lower()
                target = checksum.lower()
                if tx_from != target and tx_to != target:
                    continue
                value_eth = float(Web3.from_wei(tx.get("value", 0) or 0, "ether"))
                activities.append(WhaleActivity(
                    txHash=tx["hash"].hex(),
                    method="transfer",
                    value=value_eth,
                    timestamp=datetime.fromtimestamp(block.get("timestamp", 0), tz=timezone.utc),
                    token="MNT",
                    to=tx_to,
                    from_=tx_from,
                ))
                if len(activities) >= limit:
                    break
        except Exception:
            continue

    return activities
