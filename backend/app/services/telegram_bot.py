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
from app.api.telegram_auth import verify_connection_code

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, token: str = "") -> None:
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self._initialized = False
        self.auto_trade = False

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
            mode = "TRADE RECOMMENDATIONS" if self.auto_trade else "ANALYTICS"
            await message.answer(
                "🤖 <b>Mantle Vision</b>\n\n"
                "AI cyber-intelligence agent for Mantle Network.\n"
                "Monitoring:\n"
                "• Insider wallet clusters\n"
                "• Whale behavior anomalies\n"
                "• Reputation and link graphs\n"
                "• Liquidity trap risks\n\n"
                f"Mode: {mode}\n"
                "Commands:\n"
                "/help — help\n"
                "/status — agent status\n"
                "/autotrade — toggle trade recommendations",
            )

        @self.dp.message(Command("help"))
        async def cmd_help(message: Message) -> None:
            await message.answer(
                "<b>Mantle Vision — Telegram Bot</b>\n\n"
                "Bot sends automatic notifications.\n\n"
                "<b>Modes:</b>\n"
                "• Analytics (OFF) — alerts only for anomalies and risks\n"
                "• Recommendations (ON) — +trade suggestions\n\n"
                "Commands:\n"
                "/start — welcome\n"
                "/status — agent status\n"
                "/autotrade — toggle mode\n"
                "/help — this help",
            )

        @self.dp.message(Command("status"))
        async def cmd_status(message: Message) -> None:
            from app.blockchain.client import mantle_client
            block = await mantle_client.get_block_number()
            signals_count = 0
            try:
                from app.database import db
                stats = db.get_stats()
                signals_count = stats.get("total_signals", 0)
            except Exception:
                pass
            mode_text = "TRADE RECOMMENDATIONS" if self.auto_trade else "ANALYTICS"
            await message.answer(
                f"<b>🔌 Mantle Vision Status</b>\n\n"
                f"🟢 Bot: active\n"
                f"⛓️ Network: Mantle{'' if settings.MANTLE_CHAIN_ID == 5000 else ' Sepolia'}\n"
                f"📦 Block: {block}\n"
                f"📊 Signals: {signals_count}\n"
                f"🎮 Mode: {mode_text}\n"
                f"🤖 Auto-recommendations: {'ON' if self.auto_trade else 'OFF'}",
            )

        @self.dp.message(Command("autotrade"))
        async def cmd_autotrade(message: Message) -> None:
            self.auto_trade = not self.auto_trade
            mode = "TRADE RECOMMENDATIONS" if self.auto_trade else "ANALYTICS"
            await message.answer(
                f"{'✅' if self.auto_trade else '❌'} Auto-recommendations: {'ON' if self.auto_trade else 'OFF'}\n"
                f"Current mode: {mode}"
            )

        @self.dp.message(Command("connect"))
        async def cmd_connect(message: Message) -> None:
            args = message.text.split()
            if len(args) < 2:
                await message.answer(
                    "❌ Usage: /connect XXXX\n\n"
                    "Where XXXX is the code from Mantle Vision Web App (Settings → Telegram Connect)."
                )
                return

            code = args[1].strip()
            chat_id = str(message.chat.id)
            username = message.from_user.username or message.from_user.first_name or ""

            if verify_connection_code(code, chat_id, username):
                await message.answer(
                    "✅ <b>Connection successful!</b>\n\n"
                    "You are connected to Mantle Vision.\n"
                    "You will now receive:\n"
                    "• Sentinel alerts for anomalies\n"
                    "• Insider clusters\n"
                    "• Trade recommendations (if enabled)\n\n"
                    "Commands:\n"
                    "/status — agent status\n"
                    "/autotrade — toggle recommendations"
                )
            else:
                await message.answer(
                    "❌ <b>Invalid or expired code.</b>\n\n"
                    "Generate a new code in Settings → Telegram Connect in the web app."
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

    async def notify_signal(self, signal: dict[str, Any]) -> None:
        direction_emoji = "🟢" if signal["direction"] == "buy" else "🔴" if signal["direction"] == "sell" else "🟡"
        conf_stars = "🔥" * int(signal["confidence"] * 5) if signal["confidence"] > 0 else "⚪"

        text = (
            f"{direction_emoji} <b>Alpha Signal</b>\n"
            f"└ Type: {signal['type']}\n"
            f"└ Asset: {signal['asset']}\n"
            f"└ Direction: {signal['direction'].upper()}\n"
            f"└ Confidence: {signal['confidence']:.0%} {conf_stars}\n"
            f"└ Source: {signal['source']}\n"
            f"└ {signal['reasoning'][:200]}"
        )

        if self.auto_trade and signal["direction"] in ("buy", "sell"):
            trade_type = "buy" if signal["direction"] == "buy" else "sell"
            text += (
                f"\n\n💡 <b>Recommendation:</b>\n"
                f"└ Action: {trade_type.upper()}\n"
                f"└ Size: 5% of portfolio\n"
                f"└ TP: +15% | SL: -8%"
            )

        await self.send_message(text)

    async def notify_whale_alert(self, whale: dict[str, Any]) -> None:
        sentinel = whale.get("sentinel_score", whale.get("riskScore", 0))
        cluster = whale.get("cluster_info", {})
        wallet_type = whale.get("wallet_type", whale.get("tags", [""])[0])

        risk_icon = "🔴" if sentinel > 0.7 else "🟡" if sentinel > 0.4 else "🟢"

        type_icons = {
            "insider": "🕵️",
            "smart_money": "🧠",
            "whale": "🐋",
            "market_maker": "🔄",
            "anomaly": "⚠️",
        }
        type_icon = type_icons.get(wallet_type, "🐋")
        type_label = wallet_type.replace("_", " ").title()

        cluster_info = ""
        if cluster.get("size", 0) > 1:
            cluster_info = f"\n└ Cluster: {cluster['size']} wallets"

        text = (
            f"{type_icon} <b>{type_label} Alert</b>\n"
            f"└ Address: <code>{whale.get('address', '')[:10]}...</code>\n"
            f"└ Sentinel Score: {sentinel:.0%}\n"
            f"└ Volume: ${whale.get('totalValue', 0):,.0f}"
            f"{cluster_info}"
        )

        await self.send_message(text)

    async def notify_trade(self, trade_data: dict[str, Any]) -> None:
        direction_emoji = "🟢" if trade_data["type"] == "buy" else "🔴"
        status_emoji = "✅" if trade_data["status"] == "executed" else "❌"

        text = (
            f"{direction_emoji} {status_emoji} <b>Paper Trade</b>\n"
            f"└ Type: {trade_data['type'].upper()}\n"
            f"└ Asset: {trade_data['asset']}\n"
            f"└ Amount: {trade_data['amount']}\n"
            f"└ Price: ${trade_data['price']:.2f}\n"
            f"└ Status: <b>{trade_data['status'].upper()}</b>\n"
            f"└ ID: <code>{trade_data['id'][:12]}...</code>"
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

    async def notify_insider_cluster(self, cluster_data: dict[str, Any]) -> None:
        members = cluster_data.get("members", [])
        member_lines = "\n".join(
            f"  • <code>{m['address'][:10]}...</code> — ${m.get('total_in', 0) + m.get('total_out', 0):,.0f}"
            for m in members[:5]
        )

        text = (
            f"🕵️ <b>Insider Cluster Detected</b>\n"
            f"└ Size: {cluster_data.get('size', 0)} wallets\n"
            f"└ Total volume: ${cluster_data.get('total_volume', 0):,.0f}\n"
            f"└ Confidence: {cluster_data.get('confidence', 0):.0%}\n"
            f"\n{member_lines}"
        )

        if self.auto_trade:
            text += (
                f"\n\n💡 <b>Recommendation:</b>\n"
                f"└ Insider cluster activated\n"
                f"└ Confidence: {cluster_data.get('confidence', 0):.0%}\n"
                f"└ Action: monitor entry"
            )

        await self.send_message(text)

    async def notify_anomaly(self, anomaly: dict[str, Any]) -> None:
        text = (
            f"⚠️ <b>Anomaly Detected</b>\n"
            f"└ Wallet: <code>{anomaly.get('wallet', anomaly.get('address', 'unknown'))[:10]}...</code>\n"
            f"└ Anomaly Score: {anomaly.get('anomaly_score', 0):.0%}\n"
            f"└ Txs: {anomaly.get('tx_count', 0)}\n"
            f"└ Volume: ${anomaly.get('total_value', 0):,.0f}\n"
            f"└ {anomaly.get('details', '')}"
        )
        await self.send_message(text)


telegram = TelegramNotifier()
