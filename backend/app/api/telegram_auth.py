from __future__ import annotations

import logging
import secrets
import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/telegram", tags=["telegram_auth"])


class InitResponse(BaseModel):
    code: str
    session_token: str
    bot_username: str
    instructions: str


class StatusResponse(BaseModel):
    connected: bool
    chat_id: Optional[str] = None
    username: Optional[str] = None


@router.get("/init", response_model=InitResponse)
async def init_telegram_connection():
    code = secrets.token_hex(4)
    session_token = secrets.token_hex(16)
    db.clean_expired_telegram()
    db.save_telegram_pending(code, session_token, time.time() + 300)

    from app.services.telegram_bot import telegram
    bot_username = telegram.bot_username or "dorahacksmantle_bot"
    return InitResponse(
        code=code,
        session_token=session_token,
        bot_username=bot_username,
        instructions=f"Send /connect {code} to @{bot_username} in Telegram",
    )


@router.get("/status", response_model=StatusResponse)
async def check_telegram_status(session_token: str = ""):
    if not session_token:
        return StatusResponse(connected=False)

    data = db.get_verified_telegram_by_session(session_token)
    if data:
        return StatusResponse(
            connected=True,
            chat_id=data.get("chat_id"),
            username=data.get("username"),
        )

    return StatusResponse(connected=False)


def verify_connection_code(code: str, chat_id: str, username: str = "") -> bool:
    data = db.get_telegram_pending(code)
    if not data:
        logger.warning(f"Invalid connection code: {code}")
        return False
    if time.time() > data.get("expires_at", 0):
        logger.warning(f"Expired connection code: {code}")
        return False

    ok = db.verify_telegram_pending(code, chat_id, username)
    if ok:
        db.ensure_user(f"tg:{username}", "telegram", f"@{username}")
        logger.info(f"Telegram connected: chat={chat_id} user={username} code={code}")
    return ok
