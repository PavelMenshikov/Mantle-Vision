from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, portfolio, signals, whales
from app.api.ws import manager
from app.config import settings
from app.services.telegram_bot import telegram

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def signal_scanner() -> None:
    from app.services.analyzer import analyzer
    from app.services.mantle_scanner import mantle_scanner
    from app.services.trading_agent import trading_agent

    while True:
        try:
            latest = mantle_scanner.get_latest_block()
            if not latest:
                await asyncio.sleep(30)
                continue

            from_block = max(0, latest - 20)
            transfers = mantle_scanner.scan_large_transfers(from_block, latest, min_value_eth=10.0)
            if transfers:
                whale = {"address": transfers[0]["from"], "total_value": transfers[0]["value_eth"], "risk_score": 0.5}
                signal = await analyzer.analyze_whale_movement(whale)
                from app.api.signals import push_signal
                await push_signal(signal)
                from app.services.telegram_bot import telegram
                await telegram.notify_whale_alert(whale)

            if trading_agent.active:
                await trading_agent.scan_and_trade()

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


app.include_router(signals.router, prefix="/api")
app.include_router(whales.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await manager.handler(ws)
