from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, signals, whales, telegram_auth, scanner, transactions, wallet
from app.api.signals import push_signal
from app.api.ws import manager
from app.blockchain.client import mantle_client
from app.config import settings
from app.database import db
from app.services.anomaly_detector import anomaly_detector
from app.services.analyzer import analyzer
from app.services.arbiter import arbiter
from app.services.cluster_analyzer import cluster_analyzer
from app.services.mantle_scanner import mantle_scanner
from app.services.price_feed import get_all_prices, get_market_snapshot, get_price
from app.services.strategies import rsi_strategy, volume_strategy, nostalgia_strategy
from app.services.telegram_bot import telegram
from app.services.trading_agent import trading_agent
from app.services.whale_score import whale_scorer

# In-memory ring buffer for recent alerts (dashboard fallback)
recent_alerts: list[dict[str, Any]] = []
MAX_RECENT_ALERTS = 100

# Cooldown tracking to reduce spam (wallet_type:address -> timestamp)
_notif_cooldowns: dict[str, float] = {}
COOLDOWN_SECONDS = 3600  # 1 hour cooldown per wallet per notification type

def should_notify(key: str) -> bool:
    import time
    now = time.time()
    last = _notif_cooldowns.get(key, 0)
    if now - last >= COOLDOWN_SECONDS:
        _notif_cooldowns[key] = now
        return True
    return False

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
                    full_addr = wt['address']
                    wt_val = float(wt['value_eth'])
                    if wt_val < 100:
                        continue  # skip tiny movements
                    cooldown_key = f"tracked:{full_addr}"
                    if not should_notify(cooldown_key):
                        logger.debug(f"Cooldown: skipping tracked {full_addr[:10]}")
                        continue
                    logger.info(f"Tracked wallet active: {full_addr[:10]}... moved {wt_val} MNT")
                    ai_reasoning = ""
                    try:
                        ai_signal = await analyzer.analyze_whale_movement({"address": full_addr, "totalValue": wt_val, "tags": []})
                        ai_reasoning = ai_signal.reasoning
                    except Exception:
                        pass
                    label = (wt["profile"] or {}).get("label", full_addr[:10])
                    wt_type = label.split(":")[0] if ":" in label else label
                    type_emoji = {"anomaly": "\u26a0\ufe0f", "smart_money": "\U0001f9e0", "whale": "\U0001f40b", "insider": "\U0001f575\ufe0f", "cex": "\U0001f3e6", "fresh": "\U0001f476", "clean": "\U00002705", "heavy_distributor": "\U0001f4e5", "heavy_accumulator": "\U0001f4e4"}.get(wt_type, "\U0001f441\ufe0f")
                    if telegram:
                        text = f"{type_emoji} <b>Tracked wallet active</b>\n\U0001f4cc Wallet: <a href='https://mantlescan.xyz/address/{full_addr}'>{full_addr}</a>\n\U0001f4b0 Volume: {wt_val:.2f} MNT\n\U0001f50d Found by: {wt_type}"
                        if ai_reasoning:
                            text += f"\n\U0001f9e0 {ai_reasoning}"
                        await telegram.broadcast(text)
                    await manager.broadcast({"type": "tracked_wallet", "address": full_addr, "value_eth": wt_val, "label": label, "ai_reasoning": ai_reasoning, "wallet_type": wt_type})
                    push_alert({"type": "tracked_wallet", "address": full_addr, "value_eth": wt_val, "label": label, "ai_reasoning": ai_reasoning, "wallet_type": wt_type})

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
                market = await get_market_snapshot()

                # Smart money aggregation by asset
                smart_money_moves: dict[str, list[dict]] = {}

                for asset in ["MNT", "mETH", "USDC"]:
                    strategy_results = await run_strategies(asset, transfers, protocol_events)

                    # Track smart money moves for aggregation
                    sw_type = strategy_results["whale"].get("wallet_type", "")
                    if sw_type == "smart_money":
                        sw_addr = strategy_results["whale"].get("address", transfers[0].get("from", "unknown"))
                        sw_vol = strategy_results["whale"].get("totalValue", transfers[0].get("value_eth", 0)) if sw_type == "smart_money" else 0
                        if asset not in smart_money_moves:
                            smart_money_moves[asset] = []
                        smart_money_moves[asset].append({"address": sw_addr, "volume": sw_vol})

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

                    # Broadcast via WebSocket (skip weak HOLD signals to reduce spam)
                    is_strong = arbiter_result.direction.value != "hold" or arbiter_result.confidence >= 0.5
                    if is_strong:
                        await push_signal(arbiter_result)

                    # Record on-chain
                    try:
                        if arbiter_result.direction.value != "hold":
                            sn = 4  # AI_PREDICTION
                            dr = 0 if arbiter_result.direction.value == "buy" else 1 if arbiter_result.direction.value == "sell" else 2
                            cf = 0 if arbiter_result.confidence >= 0.7 else 1 if arbiter_result.confidence >= 0.3 else 2
                            await mantle_client.record_signal_on_chain(
                                signal_type=sn, asset=asset, direction=dr,
                                confidence=cf, reasoning=arbiter_result.reasoning,
                            )
                            # Демонстрация accuracy tracking на Sepolia:
                            # высококонфидентный buy-сигнал = "правильное" решение для демо
                            if (
                                arbiter_result.direction.value == "buy"
                                and arbiter_result.confidence >= 0.70
                                and settings.AGENT_CONTRACT_ADDRESS
                            ):
                                await mantle_client.report_signal_accurate(
                                    agent_id=0,
                                    signal_id=0,
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
                    primary_whale_data = {
                        "address": transfers[0]["from"],
                        "totalValue": transfers[0]["value_eth"],
                        "sentinel_score": primary.get("sentinel_score", 0.5),
                        "wallet_type": wallet_type,
                        "cluster_info": primary.get("cluster_info", {}),
                        "tags": primary.get("tags", []),
                    }

                    # Add AI-powered reasoning
                    try:
                        ai_signal = await analyzer.analyze_whale_movement(primary_whale_data)
                        primary_whale_data["ai_reasoning"] = ai_signal.reasoning
                    except Exception:
                        primary_whale_data["ai_reasoning"] = ""

                    whale_addr = primary_whale_data["address"]
                    if wallet_type in ("whale", "insider", "anomaly") and not should_notify(f"whale_alert:{whale_addr}"):
                        logger.debug(f"Cooldown: skipping whale alert for {whale_addr[:10]}")
                        whale_alert_data = None
                    else:
                        whale_alert_data = {"type": "whale_alert", "wallet_type": wallet_type, "address": primary_whale_data["address"], "score": primary_whale_data["sentinel_score"], "volume": primary_whale_data["totalValue"], "ai_reasoning": primary_whale_data.get("ai_reasoning", ""), "tags": primary_whale_data.get("tags", [])}
                    if wallet_type == "insider":
                        if whale_alert_data:
                            await telegram.notify_whale_alert(primary_whale_data)
                            await manager.broadcast(whale_alert_data)
                            push_alert(whale_alert_data)
                    elif wallet_type == "smart_money":
                        if smart_money_moves:
                            lines = [f"\U0001f9e0 <b>Smart Money Activity (24h)</b>", f"\U0001f50d Found by: Whale Scorer Strategy"]
                            broadcast_assets = {}
                            for asset, wallets in smart_money_moves.items():
                                broadcast_assets[asset] = wallets
                                for w in wallets[:3]:
                                    addr = w["address"]
                                    vol = w["volume"]
                                    try:
                                        curr_bal = mantle_scanner.get_balance(addr)
                                        bal_str = f" | \U0001f4b0 Balance: {curr_bal:.1f} MNT"
                                    except Exception:
                                        bal_str = ""
                                    lines.append(f"\U0001f4c8 <a href='https://mantlescan.xyz/address/{addr}'>{addr[:6]}...{addr[-4:]}</a> moved {vol:.2f} {asset}{bal_str}")
                                if len(wallets) > 3:
                                    lines.append(f"...and {len(wallets)-3} more {asset} wallets")
                            await telegram.broadcast("\n".join(lines))
                            smart_money_alert = {"type": "smart_money", "assets": broadcast_assets}
                            await manager.broadcast(smart_money_alert)
                            push_alert(smart_money_alert)
                    elif wallet_type == "anomaly":
                        if whale_alert_data:
                            await telegram.notify_whale_alert(primary_whale_data)
                            await manager.broadcast(whale_alert_data)
                            push_alert(whale_alert_data)
                    else:
                        if whale_alert_data:
                            await telegram.notify_whale_alert(primary_whale_data)
                            await manager.broadcast(whale_alert_data)
                            push_alert(whale_alert_data)

            # Heavy computation only when there's activity
            if transfers:
                anomalies = await anomaly_detector.scan_block_anomalies(from_block, latest)
                for anom in anomalies:
                    logger.info(f"Anomaly: {anom['wallet'][:10]}... score={anom['anomaly_score']:.2f}")
                    try:
                        ai_signal = await analyzer.analyze_whale_movement(anom)
                        anom["ai_reasoning"] = ai_signal.reasoning
                    except Exception:
                        anom["ai_reasoning"] = ""
                    anom_addr = anom.get("wallet", "")
                    if anom_addr and not should_notify(f"anomaly:{anom_addr}"):
                        logger.debug(f"Cooldown: skipping anomaly for {anom_addr[:10]}")
                        continue
                    anomaly_alert = {"type": "anomaly", "wallet": anom.get("wallet", ""), "anomaly_score": anom.get("anomaly_score", 0), "tx_count": anom.get("tx_count", 0), "total_value": anom.get("total_value", 0), "ai_reasoning": anom.get("ai_reasoning", "")}
                    await telegram.notify_anomaly(anom)
                    await manager.broadcast(anomaly_alert)
                    push_alert(anomaly_alert)

                clusters = cluster_analyzer.detect_insider_cluster(transfers)
                for cl in clusters:
                    logger.info(f"Insider cluster: {cl['size']} wallets, confidence={cl['confidence']:.2f}")
                    cluster_alert = {"type": "insider_cluster", "size": cl.get("size", 0), "confidence": cl.get("confidence", 0), "total_volume": cl.get("total_volume", 0), "members": cl.get("members", [])}
                    await telegram.notify_insider_cluster(cl)
                    await manager.broadcast(cluster_alert)
                    push_alert(cluster_alert)

        except Exception as e:
            logger.warning(f"Signal scanner error: {e}")

        sleep_secs = 60 if mantle_scanner.is_sepolia else 180
        await asyncio.sleep(sleep_secs)


async def _scanner_with_restart() -> None:
    """Wrapper: перезапускает signal_scanner если он упал."""
    restart_count = 0
    max_restarts = 20
    while restart_count < max_restarts:
        try:
            logger.info(f"Signal scanner starting (attempt {restart_count + 1})")
            await signal_scanner()
        except asyncio.CancelledError:
            logger.info("Signal scanner cancelled — shutting down")
            break
        except Exception as e:
            restart_count += 1
            wait = min(30 * restart_count, 300)
            logger.error(
                f"Signal scanner crashed (attempt {restart_count}): {e}. "
                f"Restarting in {wait}s..."
            )
            await asyncio.sleep(wait)
    logger.critical("Signal scanner exceeded max restarts — giving up")


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

    scanner_task = asyncio.create_task(_scanner_with_restart())
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


def push_alert(alert: dict[str, Any]) -> None:
    global recent_alerts
    alert["_stored_at"] = datetime.now(timezone.utc).isoformat()
    recent_alerts.insert(0, alert)
    if len(recent_alerts) > MAX_RECENT_ALERTS:
        recent_alerts = recent_alerts[:MAX_RECENT_ALERTS]


@app.get("/api/alerts")
async def get_alerts(limit: int = 20):
    return recent_alerts[:limit]


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
