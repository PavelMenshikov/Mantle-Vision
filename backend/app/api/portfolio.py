from __future__ import annotations

import logging

from fastapi import APIRouter, Query

from app.models.schemas import AssetType, PaperTrade, PnLDataPoint, PortfolioPosition, TradeType
from app.services.paper_trading import paper_trading as engine
from app.services.telegram_bot import telegram

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=list[PortfolioPosition])
async def get_portfolio():
    return engine.get_positions()


@router.get("/pnl", response_model=list[PnLDataPoint])
async def get_pnl_chart():
    return engine.get_pnl_chart()


@router.get("/history", response_model=list[PaperTrade])
async def get_trade_history(
    limit: int = Query(50, ge=1, le=200),
):
    return engine.get_trades(limit=limit)


@router.post("/trade", response_model=PaperTrade)
async def execute_trade(
    trade_type: TradeType,
    asset: AssetType,
    amount: str,
):
    from decimal import Decimal
    try:
        parsed_amount = Decimal(amount)
    except Exception:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid amount")

    trade = engine.execute_trade(trade_type, asset, parsed_amount)
    await telegram.notify_trade(trade.model_dump(mode="json"))
    return trade
