from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, portfolio, signals, whales, telegram_auth, scanner
from app.api.ws import manager
from app.config import settings
from app.database import db
from app.services.telegram_bot import telegram

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def run_strategies(
    asset: str,
    transfers: list[dict[str, Any]],
    protocol_events: list[dict[str, Any]],
) -> dict[str, Any]:
    from app.services.strategies import rsi_strategy, volume_strategy, nostalgia_strategy
    from app.services.price_feed import get_price
    from app.services.whale_score import whale_scorer

    price = await get_price(asset)

    rsi_result = rsi_strategy.compute(asset, current_price=price)
    rsi_strategy.record_price(asset, price)

    total_volume = sum(t.get("value_eth", 0) for t in transfers)
    volume_result = volume_strategy.compute(asset, current_volume=total_volume)
    volume_strategy.record_volume(asset, total_volume)

    nostalgia_result = nostalgia_strategy.compute(asset, current_price=price)
    nostalgia_strategy.record_price(asset, price)

    whale_scores = await whale_scorer.compute_from_transfers(transfers)
    primary_whale = transfers[0] if transfers else None
    whale_result = whale_scores.get(
        primary_whale.get("from", "") if primary_whale else "",
        {"whale_score": 0.5, "tags": [], "total_volume": 0},
    )

    return {
        "rsi": rsi_result,
        "volume": volume_result,
        "nostalgia": nostalgia_result,
        "whale": whale_result,
    }


async def signal_scanner() -> None:
    from app.services.arbiter import arbiter
    from app.services.mantle_scanner import mantle_scanner
    from app.services.price_feed import get_all_prices
    from app.services.trading_agent import trading_agent

    while True:
        try:
            latest = mantle_scanner.get_latest_block()
            if not latest:
                await asyncio.sleep(30)
                continue

            from_block = max(0, latest - 20)
            transfers = mantle_scanner.scan_large_transfers(from_block, latest, min_value_eth=10.0)
            protocol_events = mantle_scanner.scan_protocol_interactions(from_block, latest)

            # Cache prices
            prices = await get_all_prices()
            db.save_prices(prices)

            # Trigger: whale movement or significant protocol event
            has_trigger = len(transfers) > 0 or len(protocol_events) > 0

            if has_trigger:
                logger.info(f"Trigger: {len(transfers)} whale tx, {len(protocol_events)} protocol events")

                # Gather wallet context for arbiter (cluster info, KB history)
                wallet_context = None
                wallet_type = ""
                from app.services.cluster_analyzer import cluster_analyzer
                from app.services.whale_score import whale_scorer

                if transfers:
                    top_addr = transfers[0].get("from", "")
                    if top_addr:
                        # Pre-compute whale scores once for wallet context
                        whale_scores = await whale_scorer.compute_from_transfers(transfers)
                        primary = whale_scores.get(top_addr, {})
                        wallet_type = primary.get("wallet_type", "")
                        cluster = db.find_cluster_by_address(top_addr)
                        if cluster:
                            wallet_context = {"cluster": cluster}

                # Market snapshot for broader context
                from app.services.price_feed import get_market_snapshot
                market = await get_market_snapshot()

                # Smart money aggregation: don't spam per-tx
                smart_money_moves: dict[str, int] = {}

                for asset in ["MNT", "mETH", "USDC"]:
                    strategy_results = await run_strategies(asset, transfers, protocol_events)

                    # Track smart money moves for aggregation
                    sw_type = strategy_results["whale"].get("wallet_type", "")
                    if sw_type == "smart_money":
                        smart_money_moves[asset] = smart_money_moves.get(asset, 0) + 1

                    arbiter_result = await arbiter.decide(
                        asset=asset,
                        rsi_result=strategy_results["rsi"],
                        volume_result=strategy_results["volume"],
                        nostalgia_result=strategy_results["nostalgia"],
                        whale_result=strategy_results["whale"],
                        wallet_context=wallet_context,
                        market_snapshot=market.get(asset, {}),
                    )

                    # Persist to database with all scores
                    db.save_signal_with_scores(
                        signal=arbiter_result,
                        rsi_score=strategy_results["rsi"].get("score"),
                        volume_score=strategy_results["volume"].get("score"),
                        nostalgia_score=strategy_results["nostalgia"].get("score"),
                        whale_score=strategy_results["whale"].get("whale_score"),
                        ai_decision=arbiter_result.direction.value,
                        ai_confidence=arbiter_result.confidence,
                    )

                    # Broadcast via WebSocket
                    from app.api.signals import push_signal
                    await push_signal(arbiter_result)

                    # Execute if approved
                    if arbiter_result.direction.value != "hold" and trading_agent.active:
                        await trading_agent.execute_arbiter_decision(
                            arbiter_result, strategy_results
                        )

                # Notify Telegram (aggregated for smart money)
                if transfers:
                    from app.services.telegram_bot import telegram
                    from app.services.whale_score import whale_scorer

                    primary_whale_data = {
                        "address": transfers[0]["from"],
                        "totalValue": transfers[0]["value_eth"],
                        "sentinel_score": primary.get("sentinel_score", 0.5),
                        "wallet_type": wallet_type,
                        "cluster_info": primary.get("cluster_info", {}),
                        "tags": primary.get("tags", []),
                    }

                    if wallet_type == "insider":
                        await telegram.notify_whale_alert(primary_whale_data)
                    elif wallet_type == "smart_money":
                        if smart_money_moves:
                            counts = []
                            for asset, cnt in smart_money_moves.items():
                                counts.append(f"{cnt} Smart Money entered {asset}")
                            summary = "🧠 <b>Smart Money Activity (24h)</b>\n" + "\n".join(f"└ {c}" for c in counts)
                            summary += "\n\n└ Check dashboard: /signals"
                            await telegram.send_message(summary)
                    elif wallet_type == "anomaly":
                        await telegram.notify_whale_alert(primary_whale_data)
                    else:
                        await telegram.notify_whale_alert(primary_whale_data)

            # Anomaly detection on block data
            from app.services.anomaly_detector import anomaly_detector
            anomalies = await anomaly_detector.scan_block_anomalies(from_block, latest)
            for anom in anomalies:
                logger.info(f"Anomaly: {anom['wallet'][:10]}... score={anom['anomaly_score']:.2f}")
                await telegram.notify_anomaly(anom)

            # Insider cluster detection
            from app.services.cluster_analyzer import cluster_analyzer
            clusters = cluster_analyzer.detect_insider_cluster(transfers)
            for cl in clusters:
                logger.info(f"Insider cluster: {cl['size']} wallets, confidence={cl['confidence']:.2f}")
                await telegram.notify_insider_cluster(cl)

            # Record PnL snapshot every cycle
            from app.services.paper_trading import paper_trading as pt
            pnl = trading_agent.get_pnl()
            portfolio_val = trading_agent.get_portfolio_value()
            db.save_pnl_snapshot(pnl, portfolio_val, pt.capital)

        except Exception as e:
            logger.warning(f"Signal scanner error: {e}")

        await asyncio.sleep(120)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Mantle Vision backend starting")
    scanner_task = asyncio.create_task(signal_scanner())
    heartbeat_task = asyncio.create_task(manager.heartbeat())
    telegram_task = asyncio.create_task(telegram.start())

    try:
        await asyncio.wait_for(telegram.send_message("🔵 <b>Mantle Vision</b> agent started — scanning chain..."), timeout=5)
    except Exception:
        pass

    yield

    scanner_task.cancel()
    heartbeat_task.cancel()
    telegram_task.cancel()
    try:
        await scanner_task
    except asyncio.CancelledError:
        pass
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass
    try:
        await telegram_task
    except asyncio.CancelledError:
        pass

    await telegram.stop()
    logger.info("Mantle Vision backend stopped")


app = FastAPI(
    title="Mantle Vision",
    description="AI-powered on-chain intelligence platform for Mantle Network",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "blockchain": "mantle",
        "mode": "demo" if settings.DEMO_MODE else "live",
    }


app.include_router(scanner.router, prefix="/api")
app.include_router(signals.router, prefix="/api")
app.include_router(whales.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(telegram_auth.router, prefix="/api")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await manager.handler(ws)
