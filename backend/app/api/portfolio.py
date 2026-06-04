from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.database import db
from app.models.schemas import AssetType, PaperTrade, PnLDataPoint, PortfolioPosition, TradeStatus, TradeType
from app.services.paper_trading import paper_trading as engine
from app.services.telegram_bot import telegram

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=list[PortfolioPosition])
async def get_portfolio():
    return engine.get_positions()


@router.get("/pnl", response_model=list[PnLDataPoint])
async def get_pnl_chart():
    return [PnLDataPoint(**p) for p in await db.call(db.get_pnl_history)]


@router.get("/history", response_model=list[PaperTrade])
async def get_trade_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return [_row_to_trade(t) for t in await db.call(db.get_trades, limit=limit, offset=offset)]


@router.get("/stats", response_model=dict)
async def portfolio_stats():
    return {
        "total_value": engine.get_portfolio_value(),
        "pnl": engine.get_pnl(),
        "capital": engine.capital,
        "trade_count": len(engine.trades),
    }


@router.post("/trade", response_model=PaperTrade)
async def execute_trade(
    trade_type: TradeType,
    asset: AssetType,
    amount: str,
):
    try:
        parsed_amount = Decimal(amount)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid amount")

    trade = engine.execute_trade(trade_type, asset, parsed_amount)
    await db.call(db.save_trade, trade)
    await telegram.notify_trade(trade.model_dump(mode="json"))
    return trade


def _row_to_trade(row: dict) -> PaperTrade:
    return PaperTrade(
        id=row["id"],
        type=TradeType(row["type"]),
        asset=AssetType(row["asset"]),
        amount=Decimal(row["amount"]),
        price=row["price"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
        status=TradeStatus(row["status"]),
        txHash=row.get("tx_hash"),
    )
