from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from app.config import settings

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, token: str = "") -> None:
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self._initialized = False

        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not set — telegram notifier disabled")
            return

        self.bot = Bot(
            token=self.token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self.dp = Dispatcher()
        self._register_handlers()
        self._initialized = True
        logger.info("Telegram notifier initialized")

    def _register_handlers(self) -> None:
        if not self.dp:
            return

        @self.dp.message(Command("start"))
        async def cmd_start(message: Message) -> None:
            await message.answer(
                "🤖 <b>Mantle Vision</b>\n\n"
                "AI-powered on-chain intelligence platform.\n"
                "Я присылаю уведомления о:\n"
                "• Новых Alpha-сигналах\n"
                "• Сделках Paper Trading\n"
                "• Whale-активности\n"
                "• Изменениях портфеля\n\n"
                "Команды:\n"
                "/help — справка\n"
                "/status — статус агента",
            )

        @self.dp.message(Command("help"))
        async def cmd_help(message: Message) -> None:
            await message.answer(
                "<b>Mantle Vision — Telegram Bot</b>\n\n"
                "Бот автоматически присылает уведомления.\n"
                "Ничего настраивать не нужно — просто добавь бота в чат.\n\n"
                "Команды:\n"
                "/start — приветствие\n"
                "/status — статус агента\n"
                "/help — эта справка",
            )

        @self.dp.message(Command("status"))
        async def cmd_status(message: Message) -> None:
            from app.blockchain.client import mantle_client
            block = await mantle_client.get_block_number()
            signals_count = len(__import__("app.api.signals", fromlist=["_signal_store"])._signal_store) if hasattr(__import__("app.api.signals", fromlist=["_signal_store"]), "_signal_store") else 0
            await message.answer(
                f"<b>🔌 Статус Mantle Vision</b>\n\n"
                f"🟢 Бот: активен\n"
                f"⛓️ Сеть: Mantle{'' if settings.MANTLE_CHAIN_ID == 5000 else ' Sepolia'}\n"
                f"📦 Блок: {block}\n"
                f"📊 Сигналов: {signals_count}\n"
                f"🎮 Режим: {'DEMO' if settings.DEMO_MODE else 'LIVE'}",
            )

    async def start(self) -> None:
        if not self._initialized or not self.dp or not self.bot:
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
        if not self._initialized or not self.bot:
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

    async def notify_trade(self, trade_data: dict[str, Any]) -> None:
        direction_emoji = "🟢" if trade_data["type"] == "buy" else "🔴"
        status_emoji = "✅" if trade_data["status"] == "executed" else "❌"

        text = (
            f"{direction_emoji} {status_emoji} <b>Paper Trade</b>\n"
            f"└ Тип: {trade_data['type'].upper()}\n"
            f"└ Актив: {trade_data['asset']}\n"
            f"└ Кол-во: {trade_data['amount']}\n"
            f"└ Цена: ${trade_data['price']:.2f}\n"
            f"└ Статус: <b>{trade_data['status'].upper()}</b>\n"
            f"└ ID: <code>{trade_data['id'][:12]}...</code>"
        )
        await self.send_message(text)

    async def notify_signal(self, signal: dict[str, Any]) -> None:
        direction_emoji = "🟢" if signal["direction"] == "buy" else "🔴" if signal["direction"] == "sell" else "🟡"
        conf_stars = "🔥" * int(signal["confidence"] * 5) if signal["confidence"] > 0 else "⚪"

        text = (
            f"{direction_emoji} <b>Alpha Signal</b>\n"
            f"└ Тип: {signal['type']}\n"
            f"└ Актив: {signal['asset']}\n"
            f"└ Направление: {signal['direction'].upper()}\n"
            f"└ Уверенность: {signal['confidence']:.0%} {conf_stars}\n"
            f"└ Источник: {signal['source']}\n"
            f"└ {signal['reasoning'][:200]}"
        )
        await self.send_message(text)

    async def notify_whale_alert(self, whale: dict[str, Any]) -> None:
        text = (
            f"🐋 <b>Whale Alert</b>\n"
            f"└ Адрес: <code>{whale['address'][:10]}...</code>\n"
            f"└ Сумма: ${whale.get('totalValue', 0):,.0f}\n"
            f"└ Риск: {'🔴' if whale.get('riskScore', 0) > 0.7 else '🟡' if whale.get('riskScore', 0) > 0.4 else '🟢'} {whale.get('riskScore', 0):.0%}"
        )
        await self.send_message(text)

    async def notify_portfolio_summary(self, pnl: float, value: float) -> None:
        emoji = "🟢" if pnl >= 0 else "🔴"
        text = (
            f"{emoji} <b>Portfolio Summary</b>\n"
            f"└ Value: ${value:,.2f}\n"
            f"└ P&L: <b>{'+' if pnl >= 0 else ''}{pnl:,.2f}</b>\n"
            f"└ Return: {'+' if pnl >= 0 else ''}{(pnl / 10000 * 100):.2f}%"
        )
        await self.send_message(text)


telegram = TelegramNotifier()
