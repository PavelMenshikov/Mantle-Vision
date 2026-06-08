from __future__ import annotations

import logging

from fastapi import APIRouter

from app.database import db
from app.models.schemas import MantleTx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/txs", tags=["txs"])


@router.get("/recent", response_model=list[MantleTx])
async def recent_transactions(limit: int = 20):
    """Return recent transactions from the latest Mantle blocks."""
    from web3 import Web3
    from app.services.mantle_scanner import mantle_scanner

    w3 = mantle_scanner.w3
    if not w3:
        return []

    latest = mantle_scanner.get_latest_block()
    if not latest:
        return []

    from_block = max(0, latest - 5)
    txs = []

    for block_num in range(from_block, latest + 1):
        try:
            raw = w3.eth.get_block(block_num, full_transactions=True)
            ts = raw.get("timestamp", 0)
            for tx in raw.get("transactions", []):
                value_eth = round(float(Web3.from_wei(tx.get("value", 0) or 0, "ether")), 6)
                txs.append(MantleTx(
                    hash=tx["hash"].hex(),
                    from_=tx["from"],
                    to=(tx.get("to") or ""),
                    value_eth=value_eth,
                    block=block_num,
                    timestamp=ts,
                    method="transfer" if value_eth > 0 else "contract",
                ))
        except Exception as e:
            logger.debug(f"recent_transactions block {block_num}: {e}")

    txs.sort(key=lambda t: (t.block, t.hash), reverse=True)
    return txs[:limit]
