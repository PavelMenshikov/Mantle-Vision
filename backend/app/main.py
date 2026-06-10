from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, signals, whales, telegram_auth, scanner, transactions, wallet
from app.api.ws import manager
from app.config import settings
from app.database import db

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    force=True,
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("watchfiles").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("aiogram").setLevel(logging.INFO)
logging.getLogger("aiohttp").setLevel(logging.WARNING)
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

    _db = db
    cycle_count = 0

    while True:
        try:
            latest = mantle_scanner.get_latest_block()
            if not latest:
                await asyncio.sleep(30)
                continue

            scan_window = 100 if not mantle_scanner.is_sepolia else 20
            from_block = max(0, latest - scan_window)
            to_block = latest

            threshold = mantle_scanner.whale_min_value if mantle_scanner.is_sepolia else 10.0
            transfers = mantle_scanner.scan_large_transfers(from_block, latest, min_value_eth=threshold)
            protocol_events = mantle_scanner.scan_protocol_interactions(from_block, latest)

            # Cache prices
            prices = await get_all_prices()
            _db.save_prices(prices)

            # ════════════════════════════════════════════
            # TRACKED WALLET MONITORING
            # ════════════════════════════════════════════
            tracked_addresses = _db.get_all_whale_addresses()
            if tracked_addresses:
                # Check if any tracked wallet appears in recent transfers
                active_tracked = []
                for tx in transfers:
                    frm = tx.get("from", "").lower()
                    to = tx.get("to", "").lower()
                    for addr in [frm, to]:
                        if addr in tracked_addresses and addr not in [a["address"] for a in active_tracked]:
                            profile = _db.get_whale_by_address(addr)
                            active_tracked.append({"address": addr, "value_eth": tx.get("value_eth", 0), "profile": profile})

                for wt in active_tracked:
                    logger.info(f"Tracked wallet active: {wt['address'][:10]}... moved {wt['value_eth']} MNT")
                    from app.services.telegram_bot import telegram
                    if telegram:
                        label = (wt["profile"] or {}).get("label", wt["address"][:10])
                        await telegram.send_message(
                            f"👁 <b>Tracked wallet active</b>\n"
                            f"└ {label}: {wt['address'][:10]}...\n"
                            f"└ Moved {wt['value_eth']} MNT\n"
                            f"└ /signals"
                        )

            # Also periodically re-check all tracked wallets (every ~30 min)
            cycle_count += 1
            if cycle_count >= 10 and tracked_addresses:
                cycle_count = 0
                logger.info(f"Re-checking {len(tracked_addresses)} tracked wallets...")
                for addr in tracked_addresses:
                    try:
                        balance = mantle_scanner.get_balance(addr)
                        profile = _db.get_whale_by_address(addr)
                        if profile and profile.get("total_value", 0) != balance:
                            logger.info(f"Tracked {addr[:10]}... balance changed: {profile['total_value']} -> {balance}")
                            _db.upsert_whale_from_scores(addr, {"total_volume": balance, "tags": ["active", "tracked"]})
                    except Exception:
                        continue

            # Trigger: whale movement or significant protocol event
            has_trigger = len(transfers) > 0 or len(protocol_events) > 0

            if has_trigger:
                logger.info(f"Trigger: {len(transfers)} whale tx, {len(protocol_events)} protocol events")

                # Gather wallet context for arbiter (cluster info, KB history)
                wallet_context = None
                wallet_type = ""
                from app.services.cluster_analyzer import cluster_analyzer
                from app.services.whale_score import whale_scorer

                whale_scores = {}
                if transfers:
                    top_addr = transfers[0].get("from", "")
                    if top_addr:
                        # Pre-compute whale scores once for wallet context
                        whale_scores = await whale_scorer.compute_from_transfers(transfers)
                        primary = whale_scores.get(top_addr, {})
                        wallet_type = primary.get("wallet_type", "")
                        cluster = _db.find_cluster_by_address(top_addr)
                        if cluster:
                            wallet_context = {"cluster": cluster}

                # ════════════════════════════════════════════
                # AUTO-SAVE CATEGORIZED WALLETS
                # ════════════════════════════════════════════
                now = datetime.now(timezone.utc).isoformat()
                for addr, score in whale_scores.items():
                    _db.upsert_whale_from_scores(addr, score, now)
                if whale_scores:
                    logger.info(f"Auto-saved {len(whale_scores)} categorized wallets to tracking DB")

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
                    _db.save_signal_with_scores(
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

                    # Record on-chain
                    from app.blockchain.client import mantle_client
                    try:
                        if arbiter_result.direction.value != "hold":
                            sn = 4  # AI_PREDICTION
                            dr = 0 if arbiter_result.direction.value == "buy" else 1 if arbiter_result.direction.value == "sell" else 2
                            cf = 0 if arbiter_result.confidence >= 0.7 else 1 if arbiter_result.confidence >= 0.3 else 2
                            await mantle_client.record_signal_on_chain(
                                signal_type=sn, asset=asset, direction=dr,
                                confidence=cf, reasoning=arbiter_result.reasoning,
                            )
                    except Exception as e:
                        logger.debug(f"On-chain record skipped: {e}")

                    # Execute if approved
                    if arbiter_result.direction.value != "hold" and trading_agent.active:
                        await trading_agent.execute_arbiter_decision(
                            arbiter_result, strategy_results
                        )

                # Notify Telegram (aggregated for smart money)
                if transfers:
                    from app.services.telegram_bot import telegram

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

            # Heavy computation only when there's activity
            if transfers:
                from app.services.anomaly_detector import anomaly_detector
                anomalies = await anomaly_detector.scan_block_anomalies(from_block, latest)
                for anom in anomalies:
                    logger.info(f"Anomaly: {anom['wallet'][:10]}... score={anom['anomaly_score']:.2f}")
                    await telegram.notify_anomaly(anom)

                from app.services.cluster_analyzer import cluster_analyzer
                clusters = cluster_analyzer.detect_insider_cluster(transfers)
                for cl in clusters:
                    logger.info(f"Insider cluster: {cl['size']} wallets, confidence={cl['confidence']:.2f}")
                    await telegram.notify_insider_cluster(cl)

        except Exception as e:
            logger.warning(f"Signal scanner error: {e}")

        sleep_secs = 60 if mantle_scanner.is_sepolia else 180
        await asyncio.sleep(sleep_secs)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("=" * 50)
    logger.info("Mantle Vision backend starting")
    logger.info(f"Mode: {'DEMO' if settings.DEMO_MODE else 'LIVE'}")
    logger.info(f"Telegram token: {'SET' if settings.TELEGRAM_BOT_TOKEN else 'NOT SET'}")
    logger.info(f"Telegram chat_id: {'SET' if settings.TELEGRAM_CHAT_ID else 'NOT SET'}")
    logger.info(f"OpenAI key: {'SET' if settings.OPENAI_API_KEY else 'NOT SET'}")
    logger.info(f"RPC URL: {settings.MANTLE_RPC_URL}")
    logger.info("=" * 50)

    from app.services.telegram_bot import telegram
    scanner_task = asyncio.create_task(signal_scanner())
    heartbeat_task = asyncio.create_task(manager.heartbeat())

    if settings.TELEGRAM_BOT_TOKEN:
        telegram_task = asyncio.create_task(telegram.start())
        asyncio.create_task(telegram.send_message("Mantle Vision agent started — scanning chain..."))
        logger.info("Telegram bot task created")
    else:
        telegram_task = None
        logger.warning("Telegram bot disabled — TELEGRAM_BOT_TOKEN not set")

    yield

    scanner_task.cancel()
    heartbeat_task.cancel()
    if telegram_task:
        telegram_task.cancel()
    try:
        await scanner_task
    except asyncio.CancelledError:
        pass
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass
    if telegram_task:
        try:
            await telegram_task
        except asyncio.CancelledError:
            pass

    if settings.TELEGRAM_BOT_TOKEN:
        await telegram.stop()
    logger.info("Mantle Vision backend stopped")


app = FastAPI(
    title="Mantle Vision — Wallet Intelligence",
    description="On-chain wallet analysis, anomaly detection, and funding tree visualization for Mantle Network",
    version="2.0.0",
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
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "blockchain": "mantle",
        "mode": "live" if not settings.DEMO_MODE else "demo",
    }


app.include_router(scanner.router, prefix="/api")
app.include_router(signals.router, prefix="/api")
app.include_router(whales.router, prefix="/api")
app.include_router(auth.router, prefix="/api")

app.include_router(telegram_auth.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(wallet.router, prefix="/api")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await manager.handler(ws)
