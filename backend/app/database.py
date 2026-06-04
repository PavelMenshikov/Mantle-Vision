from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

from app.config import BACKEND_DIR
from app.models.schemas import (
    AssetType,
    PaperTrade,
    PnLDataPoint,
    Signal,
    SignalDirection,
    SignalSource,
    TradeStatus,
    TradeType,
    WhaleProfile,
)

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(BACKEND_DIR, "mantle_vision.db")

_loop_lock = threading.Lock()


def _run_sync(fn, *args, **kwargs):
    """Run a synchronous DB call off the event loop."""
    try:
        loop = asyncio.get_running_loop()
        return asyncio.run_coroutine_threadsafe(
            asyncio.to_thread(fn, *args, **kwargs), loop
        ).result()
    except RuntimeError:
        return fn(*args, **kwargs)


class Database:
    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, timeout=10)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn.execute("PRAGMA cache_size=-8000")
        return self._local.conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                auth_method TEXT NOT NULL,
                display_name TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                last_seen TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_whales (
                user_id TEXT NOT NULL,
                address TEXT NOT NULL,
                label TEXT DEFAULT '',
                added_at TEXT NOT NULL,
                PRIMARY KEY (user_id, address),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                asset TEXT NOT NULL,
                direction TEXT NOT NULL,
                confidence REAL NOT NULL,
                reasoning TEXT,
                tx_hash TEXT,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                rsi_score REAL,
                volume_score REAL,
                nostalgia_score REAL,
                whale_score REAL,
                ai_decision TEXT,
                ai_confidence REAL
            );

            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                asset TEXT NOT NULL,
                amount TEXT NOT NULL,
                price REAL NOT NULL,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                tx_hash TEXT,
                signal_id TEXT,
                strategy_scores TEXT
            );

            CREATE TABLE IF NOT EXISTS pnl_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                pnl REAL NOT NULL,
                portfolio_value REAL NOT NULL,
                capital REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS whale_profiles (
                address TEXT PRIMARY KEY,
                label TEXT,
                total_value REAL DEFAULT 0,
                risk_score REAL DEFAULT 0.5,
                tags TEXT DEFAULT '[]',
                last_active TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS price_cache (
                symbol TEXT PRIMARY KEY,
                price REAL NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS strategy_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT NOT NULL,
                strategy TEXT NOT NULL,
                score REAL NOT NULL,
                details TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (signal_id) REFERENCES signals(id)
            );

            CREATE TABLE IF NOT EXISTS wallet_clusters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                root_funder TEXT NOT NULL,
                total_members INTEGER DEFAULT 1,
                total_volume REAL DEFAULT 0,
                avg_success_rate REAL DEFAULT 0,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                tags TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS cluster_members (
                address TEXT PRIMARY KEY,
                cluster_id INTEGER NOT NULL,
                role TEXT DEFAULT 'member',
                total_in REAL DEFAULT 0,
                total_out REAL DEFAULT 0,
                tx_count INTEGER DEFAULT 0,
                first_seen TEXT,
                last_seen TEXT,
                FOREIGN KEY (cluster_id) REFERENCES wallet_clusters(id)
            );

            CREATE TABLE IF NOT EXISTS funding_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_address TEXT NOT NULL,
                to_address TEXT NOT NULL,
                value_eth REAL DEFAULT 0,
                tx_hash TEXT,
                block_number INTEGER,
                timestamp TEXT,
                FOREIGN KEY (from_address) REFERENCES cluster_members(address),
                FOREIGN KEY (to_address) REFERENCES cluster_members(address)
            );

            CREATE TABLE IF NOT EXISTS anomaly_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                feature_vector TEXT NOT NULL,
                wallet_addresses TEXT DEFAULT '[]',
                cluster_id INTEGER,
                confidence REAL DEFAULT 0,
                description TEXT,
                outcome TEXT,
                first_observed TEXT NOT NULL,
                last_observed TEXT NOT NULL,
                times_seen INTEGER DEFAULT 1,
                FOREIGN KEY (cluster_id) REFERENCES wallet_clusters(id)
            );

            CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_signals_direction ON signals(direction);
            CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source);
            CREATE INDEX IF NOT EXISTS idx_signals_confidence ON signals(confidence DESC);
            CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(type);
            CREATE INDEX IF NOT EXISTS idx_signals_asset ON signals(asset);
            CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_trades_asset ON trades(asset);
            CREATE INDEX IF NOT EXISTS idx_pnl_timestamp ON pnl_snapshots(timestamp);
            CREATE INDEX IF NOT EXISTS idx_strategy_scores_signal ON strategy_scores(signal_id);
            CREATE INDEX IF NOT EXISTS idx_cluster_members_cluster ON cluster_members(cluster_id);
            CREATE INDEX IF NOT EXISTS idx_funding_links_from ON funding_links(from_address);
            CREATE INDEX IF NOT EXISTS idx_funding_links_to ON funding_links(to_address);
            CREATE INDEX IF NOT EXISTS idx_anomaly_patterns_type ON anomaly_patterns(pattern_type);
            CREATE INDEX IF NOT EXISTS idx_whale_profiles_value ON whale_profiles(total_value DESC);
        """)
        conn.commit()
        logger.info(f"Database initialized: {self.db_path}")

    # --- Users ---

    def ensure_user(self, user_id: str, auth_method: str, display_name: str = "") -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT OR IGNORE INTO users (id, auth_method, display_name, created_at, last_seen)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, auth_method, display_name, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
        )
        conn.execute(
            "UPDATE users SET last_seen = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), user_id),
        )
        conn.commit()

    def get_user_whales(self, user_id: str) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT address, label FROM user_whales WHERE user_id = ? ORDER BY added_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def add_user_whale(self, user_id: str, address: str, label: str = "") -> bool:
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO user_whales (user_id, address, label, added_at) VALUES (?, ?, ?, ?)",
                (user_id, address.lower(), label, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            return True
        except Exception:
            return False

    def remove_user_whale(self, user_id: str, address: str) -> bool:
        conn = self._get_conn()
        conn.execute(
            "DELETE FROM user_whales WHERE user_id = ? AND address = ?",
            (user_id, address.lower()),
        )
        conn.commit()
        return conn.total_changes > 0

    # --- Signals ---

    def save_signal(self, signal: Signal) -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO signals
               (id, type, asset, direction, confidence, reasoning, tx_hash, timestamp, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                signal.id, signal.type, signal.asset, signal.direction.value,
                signal.confidence, signal.reasoning, signal.txHash,
                signal.timestamp.isoformat(), signal.source.value,
            ),
        )
        conn.commit()

    def save_signal_with_scores(
        self,
        signal: Signal,
        rsi_score: Optional[float] = None,
        volume_score: Optional[float] = None,
        nostalgia_score: Optional[float] = None,
        whale_score: Optional[float] = None,
        ai_decision: Optional[str] = None,
        ai_confidence: Optional[float] = None,
    ) -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO signals
               (id, type, asset, direction, confidence, reasoning, tx_hash,
                timestamp, source, rsi_score, volume_score, nostalgia_score,
                whale_score, ai_decision, ai_confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                signal.id, signal.type, signal.asset, signal.direction.value,
                signal.confidence, signal.reasoning, signal.txHash,
                signal.timestamp.isoformat(), signal.source.value,
                rsi_score, volume_score, nostalgia_score,
                whale_score, ai_decision, ai_confidence,
            ),
        )
        conn.commit()

    def get_signals(
        self,
        limit: int = 50,
        offset: int = 0,
        direction: Optional[str] = None,
        source: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        conn = self._get_conn()
        query = "SELECT * FROM signals WHERE 1=1"
        params: list[Any] = []
        if direction:
            query += " AND direction = ?"
            params.append(direction)
        if source:
            query += " AND source = ?"
            params.append(source)
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_signal_by_id(self, signal_id: str) -> Optional[dict[str, Any]]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM signals WHERE id = ?", (signal_id,)).fetchone()
        return dict(row) if row else None

    # --- Trades ---

    def save_trade(self, trade: PaperTrade, signal_id: Optional[str] = None, strategy_scores: Optional[dict] = None) -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO trades
               (id, type, asset, amount, price, timestamp, status, tx_hash, signal_id, strategy_scores)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trade.id, trade.type.value, trade.asset.value, str(trade.amount),
                trade.price, trade.timestamp.isoformat(), trade.status.value,
                trade.txHash, signal_id,
                json.dumps(strategy_scores) if strategy_scores else None,
            ),
        )
        conn.commit()

    def get_trades(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_trades_by_asset(self, asset: str, limit: int = 50) -> list[dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM trades WHERE asset = ? ORDER BY timestamp DESC LIMIT ?",
            (asset, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # --- PnL ---

    def save_pnl_snapshot(self, pnl: float, portfolio_value: float, capital: float) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO pnl_snapshots (timestamp, pnl, portfolio_value, capital) VALUES (?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), pnl, portfolio_value, capital),
        )
        conn.commit()

    def get_pnl_history(self, limit: int = 200) -> list[dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM pnl_snapshots ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    # --- Whale Profiles ---

    def save_whale_profile(self, profile: WhaleProfile) -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO whale_profiles
               (address, label, total_value, risk_score, tags, last_active, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                profile.address, profile.label, profile.totalValue,
                profile.riskScore, json.dumps(profile.tags),
                profile.lastActivity.isoformat() if profile.lastActivity else None,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()

    def get_whale_profiles(self) -> list[dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM whale_profiles ORDER BY total_value DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_whale_by_address(self, address: str) -> Optional[dict[str, Any]]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM whale_profiles WHERE address = ?", (address,)
        ).fetchone()
        return dict(row) if row else None

    # --- Price Cache ---

    def save_prices(self, prices: dict[str, float]) -> None:
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()
        for symbol, price in prices.items():
            conn.execute(
                "INSERT OR REPLACE INTO price_cache (symbol, price, updated_at) VALUES (?, ?, ?)",
                (symbol, price, now),
            )
        conn.commit()

    def get_cached_prices(self) -> dict[str, float]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM price_cache").fetchall()
        return {r["symbol"]: r["price"] for r in rows}

    # --- Strategy Scores ---

    def save_strategy_score(
        self, signal_id: str, strategy: str, score: float, details: Optional[dict] = None
    ) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO strategy_scores (signal_id, strategy, score, details, timestamp) VALUES (?, ?, ?, ?, ?)",
            (signal_id, strategy, score, json.dumps(details) if details else None, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()

    def get_strategy_scores(self, signal_id: str) -> list[dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM strategy_scores WHERE signal_id = ? ORDER BY timestamp",
            (signal_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Aggregations ---

    def get_stats(self) -> dict[str, Any]:
        conn = self._get_conn()
        total_signals = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
        total_trades = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        buy_signals = conn.execute("SELECT COUNT(*) FROM signals WHERE direction='buy'").fetchone()[0]
        sell_signals = conn.execute("SELECT COUNT(*) FROM signals WHERE direction='sell'").fetchone()[0]
        executed_trades = conn.execute("SELECT COUNT(*) FROM trades WHERE status='executed'").fetchone()[0]
        failed_trades = conn.execute("SELECT COUNT(*) FROM trades WHERE status='failed'").fetchone()[0]
        return {
            "total_signals": total_signals,
            "total_trades": total_trades,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "executed_trades": executed_trades,
            "failed_trades": failed_trades,
        }

    # --- Wallet Clusters ---

    def save_cluster(self, root_funder: str, members: list[dict[str, Any]]) -> int:
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()
        total_volume = sum(m.get("total_in", 0) + m.get("total_out", 0) for m in members)
        cursor = conn.execute(
            """INSERT INTO wallet_clusters (root_funder, total_members, total_volume, avg_success_rate, first_seen, last_seen)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (root_funder, len(members), total_volume, 0, now, now),
        )
        cluster_id = cursor.lastrowid
        for m in members:
            conn.execute(
                """INSERT OR REPLACE INTO cluster_members
                   (address, cluster_id, role, total_in, total_out, tx_count, first_seen, last_seen)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (m["address"], cluster_id, m.get("role", "member"),
                 m.get("total_in", 0), m.get("total_out", 0), m.get("tx_count", 0), now, now),
            )
        conn.commit()
        return cluster_id

    def get_cluster_by_id(self, cluster_id: int) -> Optional[dict[str, Any]]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM wallet_clusters WHERE id = ?", (cluster_id,)).fetchone()
        if not row:
            return None
        cluster = dict(row)
        members = conn.execute(
            "SELECT * FROM cluster_members WHERE cluster_id = ? ORDER BY total_in + total_out DESC",
            (cluster_id,),
        ).fetchall()
        cluster["members"] = [dict(m) for m in members]
        return cluster

    def get_all_clusters(self, min_members: int = 2) -> list[dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM wallet_clusters WHERE total_members >= ? ORDER BY total_volume DESC",
            (min_members,),
        ).fetchall()
        return [dict(r) for r in rows]

    def find_cluster_by_address(self, address: str) -> Optional[dict[str, Any]]:
        conn = self._get_conn()
        row = conn.execute(
            """SELECT c.* FROM wallet_clusters c
               JOIN cluster_members m ON c.id = m.cluster_id
               WHERE m.address = ?""",
            (address.lower(),),
        ).fetchone()
        if not row:
            return None
        cluster = dict(row)
        members = conn.execute(
            "SELECT * FROM cluster_members WHERE cluster_id = ?",
            (cluster["id"],),
        ).fetchall()
        cluster["members"] = [dict(m) for m in members]
        return cluster

    def save_funding_link(self, from_addr: str, to_addr: str, value_eth: float,
                          tx_hash: str = "", block_number: int = 0, timestamp: str = "") -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO funding_links (from_address, to_address, value_eth, tx_hash, block_number, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (from_addr.lower(), to_addr.lower(), value_eth, tx_hash, block_number, timestamp),
        )
        conn.commit()

    # --- Anomaly Patterns ---

    def save_anomaly_pattern(self, pattern: dict[str, Any]) -> int:
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute(
            """INSERT INTO anomaly_patterns
               (pattern_type, feature_vector, wallet_addresses, cluster_id, confidence, description, outcome, first_observed, last_observed)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                pattern["pattern_type"],
                pattern["feature_vector"],
                json.dumps(pattern.get("wallet_addresses", [])),
                pattern.get("cluster_id"),
                pattern.get("confidence", 0.5),
                pattern.get("description", ""),
                pattern.get("outcome", ""),
                now,
                now,
            ),
        )
        conn.commit()
        return cursor.lastrowid

    def find_similar_patterns(self, feature_vector_str: str, limit: int = 10) -> list[dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM anomaly_patterns ORDER BY times_seen DESC, confidence DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_anomaly_patterns(self, pattern_type: Optional[str] = None, limit: int = 50) -> list[dict[str, Any]]:
        conn = self._get_conn()
        if pattern_type:
            rows = conn.execute(
                "SELECT * FROM anomaly_patterns WHERE pattern_type = ? ORDER BY last_observed DESC LIMIT ?",
                (pattern_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM anomaly_patterns ORDER BY last_observed DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    async def call(self, fn, *args, **kwargs):
        """Run a DB method in a thread so it doesn't block the event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))


db = Database()
