"""Wallet-based authentication (Sign-In With Ethereum)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import settings
from app.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_nonces: dict[str, dict] = {}
_sessions: dict[str, dict] = {}

JWT_SECRET = settings.MANTLE_PRIVATE_KEY or secrets.token_hex(32)


class NonceResponse(BaseModel):
    nonce: str
    message: str


class VerifyRequest(BaseModel):
    address: str
    signature: str
    message: str


class VerifyResponse(BaseModel):
    token: str
    address: str
    expires_at: int


def _generate_nonce() -> str:
    return secrets.token_hex(16)


def _create_message(address: str, nonce: str) -> str:
    return (
        f"Mantle Vision - Sign-In With Ethereum\n\n"
        f"Address: {address}\n"
        f"Nonce: {nonce}\n"
        f"Time: {datetime.now(timezone.utc).isoformat()}\n\n"
        f"By signing, you authenticate with Mantle Vision AI Agent."
    )


def _create_token(address: str) -> str:
    payload = {
        "address": address,
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400 * 7,  # 7 days
    }
    payload_str = json.dumps(payload, separators=(",", ":"))
    sig = hmac.new(JWT_SECRET.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
    return f"{payload_str}.{sig}"


def _verify_token(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_str, sig = parts
        expected = hmac.new(JWT_SECRET.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(payload_str)
        if time.time() > payload.get("exp", 0):
            return None
        return payload
    except Exception:
        return None


@router.get("/nonce/{address}", response_model=NonceResponse)
async def get_nonce(address: str):
    nonce = _generate_nonce()
    message = _create_message(address, nonce)
    _nonces[address.lower()] = {
        "nonce": nonce,
        "message": message,
        "expires": time.time() + 300,
    }
    return NonceResponse(nonce=nonce, message=message)


@router.post("/verify")
async def verify(req: VerifyRequest):
    addr = req.address.lower()
    nonce_data = _nonces.pop(addr, None)

    if not nonce_data:
        raise HTTPException(400, "No nonce requested. Call /auth/nonce/{address} first.")
    if time.time() > nonce_data["expires"]:
        raise HTTPException(400, "Nonce expired. Request a new one.")

    expected_msg = _create_message(req.address, nonce_data["nonce"])
    if req.message != expected_msg:
        raise HTTPException(400, "Message mismatch. Use the exact message from /nonce.")

    try:
        from web3 import Web3
        recovered = Web3().eth.account.recover_message(
            Web3().keccak_text(req.message),
            signature=req.signature,
        )
        if recovered.lower() != addr:
            raise HTTPException(401, "Signature does not match address.")
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        raise HTTPException(401, "Invalid signature.")

    token = _create_token(req.address)
    _sessions[token] = {
        "address": req.address,
        "created": time.time(),
    }

    db.ensure_user(req.address.lower(), "metamask", req.address[:6] + "..." + req.address[-4:])

    exp = int(time.time()) + 86400 * 7
    return VerifyResponse(token=token, address=req.address, expires_at=exp)


@router.get("/session")
async def check_session(token: str):
    payload = _verify_token(token)
    if not payload:
        raise HTTPException(401, "Invalid or expired token.")
    return {
        "valid": True,
        "address": payload["address"],
        "expires_at": payload["exp"],
    }
