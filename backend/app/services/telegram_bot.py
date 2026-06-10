from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.config import settings
from app.api.telegram_auth import verify_connection_code

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, token: str = "") -> None:
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.bot: Any = None
        self.dp: Any = None
        self._initialized = False
        self.auto_trade = False
        self.bot_username: str = ""

        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not set — telegram notifier disabled")

    def _ensure_init(self) -> None:
        if self._initialized or not self.token:
            return
        from aiogram import Bot, Dispatcher
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        from aiogram.filters import Command
        from aiogram.types import Message

        self.bot = Bot(
            token=self.token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self.dp = Dispatcher()

        @self.dp.message(Command("start"))
        async def cmd_start(message: Message) -> None:
            if not message.from_user:
                logger.warning("/start from anonymous user")
                return
            args = message.text.split(maxsplit=1)
            code = args[1].strip() if len(args) > 1 else ""
            log_extra = f"chat_id={message.from_user.id} username={message.from_user.username}"
            logger.info(f"/start received {log_extra} code={'...' + code[-4:] if code else 'none'}")

            if code:
                chat_id = str(message.from_user.id)
                username = message.from_user.username or ""
                ok = verify_connection_code(code, chat_id, username)
                if ok:
                    logger.info(f"Telegram auth SUCCESS: {log_extra} code={code[:4]}...")
                    await message.answer("✅ <b>Connected!</b>\nYour wallet is linked to Mantle Vision.")
                else:
                    logger.warning(f"Telegram auth FAILED: {log_extra} code={code[:4]}...")
                    await message.answer("❌ Invalid or expired code. Go to the web app and generate a new one.")
                return

            mode = "TRADE RECOMMENDATIONS" if self.auto_trade else "ANALYTICS"
            await message.answer(
                "🤖 <b>Mantle Vision</b>\n\n"
                "AI cyber-intelligence agent for Mantle Network.\n"
                "Monitoring:\n"
                "\u2022 Insider wallet clusters\n"
                "\u2022 Whale behavior anomalies\n"
                "\u2022 Reputation and link graphs\n"
                "\u2022 Liquidity trap risks\n\n"
                f"Mode: {mode}\n\n"
                "To link your wallet:\n"
                "1. Go to the Mantle Vision web app\n"
                "2. Click 'Sign In with Telegram'\n"
                "3. Click the bot link to send /start CODE\n\n"
                "Commands:\n"
                "/help \u2014 help\n"
                "/status \u2014 agent status\n"
                "/autotrade \u2014 toggle trade recommendations",
            )

        @self.dp.message(Command("connect"))
        async def cmd_connect(message: Message) -> None:
            if not message.from_user:
                logger.warning("/connect from anonymous user")
                return
            args = message.text.split(maxsplit=1)
            code = args[1].strip() if len(args) > 1 else ""
            log_extra = f"chat_id={message.from_user.id} username={message.from_user.username}"

            if not code:
                logger.info(f"/connect without code {log_extra}")
                await message.answer(
                    "Send /connect <code>CODE</code> with the code from the web app.\n\n"
                    "Example: /connect a1b2c3d4\n\n"
                    "Generate a new code at: https://mantle-vision.app"
                )
                return

            chat_id = str(message.from_user.id)
            username = message.from_user.username or ""
            ok = verify_connection_code(code, chat_id, username)
            if ok:
                logger.info(f"Telegram connect SUCCESS: {log_extra} code={code[:4]}...")
                await message.answer("✅ <b>Connected!</b>\nYour wallet is linked to Mantle Vision.")
            else:
                logger.warning(f"Telegram connect FAILED: {log_extra} code={code[:4]}...")
                await message.answer("❌ Invalid or expired code. Generate a new one from the web app.")

        @self.dp.message(Command("help"))
        async def cmd_help(message: Message) -> None:
            log_extra = f"chat_id={message.from_user.id}" if message.from_user else "unknown"
            logger.info(f"/help {log_extra}")
            await message.answer(
                "<b>Mantle Vision \u2014 Telegram Bot</b>\n\n"
                "AI-powered wallet intelligence for Mantle Network.\n\n"
                "<b>Connection:</b>\n"
                "Go to the web app \u2192 Sign In with Telegram \u2192 click the bot link\n\n"
                "<b>Commands:</b>\n"
                "/start \u2014 welcome & link wallet\n"
                "/connect CODE \u2014 connect using code from web app\n"
                "/status \u2014 current mode & status\n"
                "/autotrade \u2014 toggle auto-trade mode\n"
                "/help \u2014 this help\n\n"
                "Bot monitors MNT, mETH, USDC pairs.",
            )

        @self.dp.message(Command("status"))
        async def cmd_status(message: Message) -> None:
            m = "Recommendations" if self.auto_trade else "Analytics"
            logger.info(f"/status: mode={m} auto_trade={self.auto_trade}")
            await message.answer(f"<b>Mode:</b> {m}\n<b>Auto trade:</b> {'ON' if self.auto_trade else 'OFF'}")

        @self.dp.message(Command("autotrade"))
        async def cmd_autotrade(message: Message) -> None:
            self.auto_trade = not self.auto_trade
            m = "ON" if self.auto_trade else "OFF"
            logger.info(f"/autotrade toggled: {m}")
            await message.answer(f"Auto trade: <b>{m}</b>")

        self._initialized = True
        logger.info("Telegram bot handlers registered")

    async def start(self) -> None:
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not set — bot not started")
            return
        self._ensure_init()
        if not self.dp or not self.bot:
            logger.error("Telegram bot not initialized (dp or bot is None)")
            return
        if not self.bot_username:
            try:
                bot_user = await self.bot.me()
                self.bot_username = bot_user.username or ""
                logger.info(f"Bot username resolved: @{self.bot_username}")
            except Exception as e:
                logger.warning(f"Failed to get bot username via API: {e}")
        logger.info("Starting Telegram bot polling...")
        try:
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Telegram polling error: {e}")

    async def stop(self) -> None:
        if self.bot:
            await self.bot.session.close()
            logger.info("Telegram bot stopped")

    async def send_message(self, text: str, parse_mode: str = "HTML", chat_id: Optional[str] = None) -> bool:
        if not self.token:
            logger.debug("send_message skipped: TELEGRAM_BOT_TOKEN not set")
            return False
        self._ensure_init()
        if not self.bot:
            logger.warning("send_message skipped: bot not initialized")
            return False

        target = chat_id or self.chat_id
        if not target:
            logger.debug("send_message skipped: no chat_id")
            return False

        try:
            await asyncio.wait_for(
                self.bot.send_message(target, text, parse_mode=parse_mode),
                timeout=5,
            )
            logger.debug(f"Message sent to chat_id={target} ({len(text)} chars)")
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Telegram send_message timed out (chat_id={target})")
            return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message to {target}: {e}")
            return False

    async def broadcast(self, text: str, parse_mode: str = "HTML") -> int:
        from app.database import db
        sent = 0
        targets: set[str] = set()
        if self.chat_id:
            targets.add(self.chat_id)
        for user in db.get_all_verified_telegram_users():
            cid = user.get("chat_id")
            if cid:
                targets.add(cid)
        if not targets:
            logger.debug("broadcast skipped: no targets")
            return 0
        for cid in targets:
            ok = await self.send_message(text, parse_mode=parse_mode, chat_id=cid)
            if ok:
                sent += 1
        logger.info(f"broadcast: sent to {sent}/{len(targets)} targets")
        return sent

    async def notify_signal(self, signal: dict[str, Any]) -> None:
        direction_emoji = "\U0001f7e2" if signal["direction"] == "buy" else "\U0001f534" if signal["direction"] == "sell" else "\U0001f7e1"
        conf_stars = "\U0001f525" * int(signal["confidence"] * 5) if signal["confidence"] > 0 else "\u26aa"
        text = (
            f"{direction_emoji} <b>Signal: {signal['direction'].upper()}</b> {signal['asset']}\n"
            f"Confidence: {signal['confidence']:.0%} {conf_stars}\n"
            f"{signal.get('reasoning', '')}\n"
            f"#{signal['asset']} #{signal['direction']}"
        )
        logger.info(f"Broadcasting signal: {signal['direction']} {signal['asset']} confidence={signal['confidence']:.2f}")
        await self.broadcast(text)

    async def notify_whale_alert(self, data: dict[str, Any]) -> None:
        addr = data.get("address", "unknown")[:10]
        score = data.get("sentinel_score", 0)
        wtype = data.get("wallet_type", "unknown")
        vol = data.get("totalValue", 0)
        tags = data.get("tags", [])
        tag_str = " | ".join(tags[:3]) if tags else ""
        text = (
            f"\U0001f40b <b>Whale Alert</b>\n"
            f"Wallet: <code>{addr}...</code>\n"
            f"Type: {wtype}\n"
            f"Score: {score:.0%}\n"
            f"Volume: {vol:.2f} ETH\n"
            f"{tag_str}"
        )
        logger.info(f"Broadcasting whale alert: {addr} type={wtype} score={score:.2f}")
        await self.broadcast(text)

    async def notify_anomaly(self, anomaly: dict[str, Any]) -> None:
        addr = anomaly.get("address", "unknown")[:10]
        score = anomaly.get("anomaly_score", 0)
        tx_count = anomaly.get("tx_count", 0)
        value = anomaly.get("total_value", 0)
        details = anomaly.get("details", "")
        text = (
            f"\u26a0\ufe0f <b>Anomaly Detected</b>\n"
            f"Wallet: <code>{addr}...</code>\n"
            f"Anomaly Score: {score:.0%}\n"
            f"Txs: {tx_count}\n"
            f"Volume: ${value:,.0f}\n"
            f"{details}"
        )
        logger.info(f"Broadcasting anomaly: {addr} score={score:.2f}")
        await self.broadcast(text)


telegram = TelegramNotifier()
