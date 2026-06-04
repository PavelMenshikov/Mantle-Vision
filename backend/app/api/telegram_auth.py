from __future__ import annotations

import logging
import secrets
import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/telegram", tags=["telegram_auth"])

_pending_connections: dict[str, dict[str, Any]] = {}
_connected_chats: dict[str, str] = {}


class InitResponse(BaseModel):
    code: str
    bot_username: str
    instructions: str


class StatusResponse(BaseModel):
    connected: bool
    chat_id: Optional[str] = None
    username: Optional[str] = None


@router.get("/init", response_model=InitResponse)
async def init_telegram_connection(session_token: str = ""):
    code = secrets.token_hex(4)
    _pending_connections[code] = {
        "session_token": session_token,
        "created_at": time.time(),
        "expires_at": time.time() + 300,
        "verified": False,
        "chat_id": None,
        "username": None,
    }
    return InitResponse(
        code=code,
        bot_username="MantleVisionBot",
        instructions=f"Send /connect {code} to @MantleVisionBot in Telegram",
    )


@router.get("/status", response_model=StatusResponse)
async def check_telegram_status(session_token: str = ""):
    for code, data in _pending_connections.items():
        if data.get("session_token") == session_token and data.get("verified"):
            return StatusResponse(
                connected=True,
                chat_id=data.get("chat_id"),
                username=data.get("username"),
            )

    return StatusResponse(connected=False)


def verify_connection_code(code: str, chat_id: str, username: str = "") -> bool:
    data = _pending_connections.get(code)
    if not data:
        logger.warning(f"Invalid connection code: {code}")
        return False
    if time.time() > data.get("expires_at", 0):
        logger.warning(f"Expired connection code: {code}")
        _pending_connections.pop(code, None)
        return False

    data["verified"] = True
    data["chat_id"] = chat_id
    data["username"] = username
    _connected_chats[chat_id] = code
    logger.info(f"Telegram connected: chat={chat_id} user={username} code={code}")
    return True
