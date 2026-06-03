from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: Set[WebSocket] = set()
        self.heartbeat_interval = 30

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.connections.add(ws)
        logger.info(f"WebSocket connected ({len(self.connections)} total)")

    def disconnect(self, ws: WebSocket) -> None:
        self.connections.discard(ws)
        logger.info(f"WebSocket disconnected ({len(self.connections)} total)")

    async def broadcast(self, data: dict[str, Any]) -> None:
        message = json.dumps(data, default=str)
        stale: list[WebSocket] = []
        for ws in self.connections:
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(ws)

    async def heartbeat(self) -> None:
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            stale: list[WebSocket] = []
            for ws in self.connections:
                try:
                    await ws.send_json({"type": "heartbeat", "timestamp": __import__("datetime").datetime.utcnow().isoformat()})
                except Exception:
                    stale.append(ws)
            for ws in stale:
                self.disconnect(ws)

    async def handler(self, ws: WebSocket) -> None:
        await self.connect(ws)
        try:
            while True:
                data = await ws.receive_text()
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "ping":
                        await ws.send_json({"type": "pong"})
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            self.disconnect(ws)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            self.disconnect(ws)


manager = ConnectionManager()
