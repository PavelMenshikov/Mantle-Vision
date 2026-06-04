from __future__ import annotations

import asyncio
import logging
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
            mode = "TRADE RECOMMENDATIONS" if self.auto_trade else "ANALYTICS"
            await message.answer(
                "🤖 <b>Mantle Vision</b>\n\n"
                "AI cyber-intelligence agent for Mantle Network.\n"
                "Monitoring:\n"
                "\u2022 Insider wallet clusters\n"
                "\u2022 Whale behavior anomalies\n"
                "\u2022 Reputation and link graphs\n"
                "\u2022 Liquidity trap risks\n\n"
                f"Mode: {mode}\n"
                "Commands:\n"
                "/help \u2014 help\n"
                "/status \u2014 agent status\n"
                "/autotrade \u2014 toggle trade recommendations",
            )

        @self.dp.message(Command("help"))
        async def cmd_help(message: Message) -> None:
            await message.answer(
                "<b>Mantle Vision \u2014 Telegram Bot</b>\n\n"
                "Bot sends automatic notifications.\n\n"
                "<b>Modes:</b>\n"
                "\u2022 Analytics (OFF) \u2014 alerts only for anomalies and risks\n"
                "\u2022 Recommendations (ON) \u2014 +trade suggestions\n\n"
                "Commands:\n"
                "/start \u2014 welcome\n"
                "/help \u2014 help\n"
                "/status \u2014 current mode & status\n"
                "/autotrade \u2014 toggle auto-trade mode\n"
                "/connect \u2014 link your MetaMask\n\n"
                "Bot monitors MNT, mETH, USDC pairs.",
            )

        @self.dp.message(Command("status"))
        async def cmd_status(message: Message) -> None:
            m = "Recommendations" if self.auto_trade else "Analytics"
            await message.answer(f"<b>Mode:</b> {m}\n<b>Auto trade:</b> {'ON' if self.auto_trade else 'OFF'}")

        @self.dp.message(Command("autotrade"))
        async def cmd_autotrade(message: Message) -> None:
            self.auto_trade = not self.auto_trade
            m = "ON" if self.auto_trade else "OFF"
            await message.answer(f"Auto trade: <b>{m}</b>")

        @self.dp.message(Command("connect"))
        async def cmd_connect(message: Message) -> None:
            if not message.from_user:
                return
            code = await verify_connection_code(str(message.from_user.id))
            if code:
                await message.answer(
                    f"To link your wallet, visit:\n"
                    f"http://localhost:3000/telegram?code={code}\n\n"
                    f"Code: <code>{code}</code>\n"
                    f"Valid for 5 minutes."
                )
            else:
                await message.answer("Error generating code. Try again later.")

        self._initialized = True
        logger.info("Telegram notifier initialized")

    async def start(self) -> None:
        if not self.token:
            return
        self._ensure_init()
        if not self.dp or not self.bot:
            return
        logger.info("Starting Telegram bot polling...")
        try:
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Telegram polling error: {e}")

    async def stop(self) -> None:
        if self.bot:
            await self.bot.session.close()
            logger.info("Telegram bot stopped")

    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        if not self.token:
            return False
        self._ensure_init()
        if not self.bot:
            return False

        chat_id = self.chat_id
        if not chat_id:
            return False

        try:
            await asyncio.wait_for(
                self.bot.send_message(chat_id, text, parse_mode=parse_mode),
                timeout=5,
            )
            return True
        except asyncio.TimeoutError:
            logger.warning("Telegram send_message timed out (blocked?)")
            return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def notify_signal(self, signal: dict[str, Any]) -> None:
        direction_emoji = "\U0001f7e2" if signal["direction"] == "buy" else "\U0001f534" if signal["direction"] == "sell" else "\U0001f7e1"
        conf_stars = "\U0001f525" * int(signal["confidence"] * 5) if signal["confidence"] > 0 else "\u26aa"
        text = (
            f"{direction_emoji} <b>Signal: {signal['direction'].upper()}</b> {signal['asset']}\n"
            f"Confidence: {signal['confidence']:.0%} {conf_stars}\n"
            f"{signal.get('reasoning', '')}\n"
            f"#{signal['asset']} #{signal['direction']}"
        )
        await self.send_message(text)

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
        await self.send_message(text)

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
        await self.send_message(text)


telegram = TelegramNotifier()
