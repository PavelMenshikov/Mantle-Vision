from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

from app.models.schemas import WhaleProfile

logger = logging.getLogger(__name__)

WHALE_THRESHOLD_ETH = 100.0
# Адреса бирж на Mantle Network — только верифицированные.
# Источник проверки: mantlescan.xyz (поиск по тегу "Exchange")
EXCHANGE_WALLETS = {
    # Binance deposit wallet на Mantle (верифицирован через mantlescan.xyz)
    "0x28c6c06298d514db089934071355e5743bf21d60": "binance",
    # Bybit withdrawal wallet на Mantle
    "0xf89d7b9c864f589bbf53a82105107622b35eaa40": "bybit",
    # OKX на Mantle
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": "okx",
}
# Адреса без верификации — удалены.
# Добавляй ТОЛЬКО после проверки на https://mantlescan.xyz/

SENTINEL_SCORE_WEIGHTS = {
    "whale_score": 0.25,
    "cluster_score": 0.20,
    "anomaly_score": 0.20,
    "reputation_score": 0.20,
    "influence_score": 0.15,
}


class WhaleScoreCalculator:
    """Computes multi-factor wallet reputation score.

    Layers:
    1. WhaleScore (0-1) — volume, flow, frequency, exchange interaction
    2. ClusterScore (0-1) — belongs to insider cluster?
    3. AnomalyScore (0-1) — Isolation Forest anomaly detection
    4. ReputationScore (0-1) — historical win rate, consistency
    5. InfluenceScore (0-1) — how many wallets copy this one
    Final: SentinelScore = weighted composite
    """

    def __init__(self) -> None:
        self.cached_profiles: dict[str, dict[str, Any]] = {}

    async def compute_from_transfers(
        self, transfers: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        wallet_groups: dict[str, list[dict[str, Any]]] = {}

        for tx in transfers:
            addr = tx.get("from", "")
            if addr not in wallet_groups:
                wallet_groups[addr] = []
            wallet_groups[addr].append(tx)
            to_addr = tx.get("to", "")
            if to_addr and to_addr not in wallet_groups:
                wallet_groups[to_addr] = []
            wallet_groups[to_addr].append(tx)

        for address, txs in wallet_groups.items():
            score = await self._score_wallet(address, txs)
            results[address] = score

        return results

    async def _score_wallet(self, address: str, txs: list[dict[str, Any]]) -> dict[str, Any]:
        total_volume = sum(t.get("value_eth", 0) for t in txs)
        tx_count = len(txs)
        avg_value = total_volume / max(tx_count, 1)

        # Flow direction: ratio of outgoing to incoming
        out_volume = sum(t.get("value_eth", 0) for t in txs if t.get("from", "").lower() == address.lower())
        in_volume = total_volume - out_volume
        flow_ratio = out_volume / max(in_volume, 0.001)

        # Size score: larger = more impactful
        size_score = min(1.0, total_volume / 1000.0)

        # Flow score: distributing (high out/in ratio) = more suspicious
        if flow_ratio > 5.0:
            flow_score = 0.9
            flow_label = "heavy_distributor"
        elif flow_ratio > 2.0:
            flow_score = 0.7
            flow_label = "distributor"
        elif flow_ratio < 0.2:
            flow_score = 0.7
            flow_label = "accumulator"
        elif flow_ratio < 0.5:
            flow_score = 0.5
            flow_label = "mild_accumulator"
        else:
            flow_score = 0.4
            flow_label = "balanced"

        # Frequency score: high tx count in short time = bot
        freq_score = min(1.0, tx_count / 20.0)

        # Exchange interaction
        exchange = self._detect_exchange(address, txs)
        exchange_score = 0.3 if exchange else 0.0

        # Whale score composite (original)
        whale_raw = (
            size_score * 0.35 +
            flow_score * 0.30 +
            freq_score * 0.20 +
            exchange_score * 0.15
        )
        whale_score = round(min(1.0, whale_raw), 4)

        # --- New layers ---

        # Cluster score: is this wallet part of an insider cluster?
        cluster_score, cluster_info = await self._compute_cluster_score(address)

        # Anomaly score: does behavior deviate from normal?
        anomaly_score = self._compute_anomaly_score(address, txs)

        # Reputation score: estimated historical win rate
        reputation_score = self._compute_reputation_score(address, txs)

        # Influence score: how many wallets copy this one?
        influence_score = self._compute_influence_score(address, txs)

        # Sentinel score: weighted composite of all layers
        sentinel_score = (
            whale_score * SENTINEL_SCORE_WEIGHTS["whale_score"]
            + cluster_score * SENTINEL_SCORE_WEIGHTS["cluster_score"]
            + anomaly_score * SENTINEL_SCORE_WEIGHTS["anomaly_score"]
            + reputation_score * SENTINEL_SCORE_WEIGHTS["reputation_score"]
            + influence_score * SENTINEL_SCORE_WEIGHTS["influence_score"]
        )
        sentinel_score = round(min(1.0, sentinel_score), 4)

        tags = ["whale"]
        if sentinel_score > 0.7:
            tags.append("high_risk")
        if sentinel_score > 0.85:
            tags.append("critical")
        if exchange:
            tags.append(f"exchange:{exchange}")
        if flow_label:
            tags.append(flow_label)
        if cluster_info and "cluster_id" in cluster_info:
            tags.append("clustered")
            tags.append(f"cluster:{cluster_info['cluster_id']}")
        if anomaly_score > 0.7:
            tags.append("anomalous")
        if reputation_score > 0.6:
            tags.append("high_reputation")
        if influence_score > 0.6:
            tags.append("influencer")

        # Wallet type classification
        if cluster_info and cluster_info.get("size", 0) >= 2:
            wallet_type = "insider"
            tags.append("insider")
        elif reputation_score > 0.6 and cluster_score < 0.3:
            wallet_type = "smart_money"
            tags.append("smart_money")
        elif freq_score > 0.7 and exchange_score > 0:
            wallet_type = "market_maker"
            tags.append("market_maker")
        elif anomaly_score > 0.7:
            wallet_type = "anomaly"
            tags.append("anomaly")
        elif total_volume > WHALE_THRESHOLD_ETH:
            wallet_type = "whale"
            tags.append("whale")
        else:
            wallet_type = "active"
            tags.append("active")

        return {
            "address": address,
            "wallet_type": wallet_type,
            "whale_score": whale_score,
            "sentinel_score": sentinel_score,
            "cluster_score": cluster_score,
            "anomaly_score": anomaly_score,
            "reputation_score": reputation_score,
            "influence_score": influence_score,
            "total_volume": round(total_volume, 2),
            "tx_count": tx_count,
            "avg_value": round(avg_value, 2),
            "flow_ratio": round(flow_ratio, 2),
            "flow_label": flow_label,
            "exchange": exchange,
            "tags": tags,
            "cluster_info": cluster_info,
        }

    async def _compute_cluster_score(self, address: str) -> tuple[float, dict[str, Any]]:
        try:
            from app.services.cluster_analyzer import cluster_analyzer
            cluster = await cluster_analyzer.analyze_wallet(address)
            if cluster and cluster["total_members"] >= 2:
                score = min(1.0, cluster["total_members"] / 15.0 + cluster["total_volume"] / 10000.0)
                return round(score, 4), {
                    "cluster_id": cluster["id"],
                    "size": cluster["total_members"],
                    "volume": cluster["total_volume"],
                }
        except Exception as e:
            logger.debug(f"cluster_score failed for {address}: {e}")
        return 0.0, {}

    def _compute_anomaly_score(self, address: str, txs: list[dict[str, Any]]) -> float:
        try:
            from app.services.anomaly_detector import anomaly_detector
            result = anomaly_detector.score_transactions(txs)
            return result["anomaly_score"]
        except Exception as e:
            logger.debug(f"anomaly_score failed for {address}: {e}")
        return 0.0

    def _compute_reputation_score(self, address: str, txs: list[dict[str, Any]]) -> float:
        if not txs or len(txs) < 2:
            return 0.3

        successes = sum(1 for t in txs if t.get("status", False))
        total = len(txs)
        win_rate = successes / max(total, 1)

        # Consistency: low std in interval between trades
        timestamps = sorted([t.get("timestamp", 0) for t in txs if t.get("timestamp")])
        if len(timestamps) > 1:
            intervals = np.diff(timestamps)
            consistency = 1.0 - min(1.0, float(np.std(intervals)) / max(float(np.mean(intervals)), 1))
        else:
            consistency = 0.5

        rep = win_rate * 0.6 + consistency * 0.4
        return round(min(1.0, rep), 4)

    def _compute_influence_score(self, address: str, txs: list[dict[str, Any]]) -> float:
        if not txs:
            return 0.0
        unique_receivers = len(set(t.get("to", "") for t in txs if t.get("to")))
        total_value = sum(t.get("value_eth", 0) for t in txs)
        score = min(1.0, (unique_receivers / 20.0) * 0.5 + (total_value / 5000.0) * 0.5)
        return round(score, 4)

    def _detect_exchange(self, address: str, txs: list[dict[str, Any]]) -> Optional[str]:
        addr_lower = address.lower()
        if addr_lower in EXCHANGE_WALLETS:
            return EXCHANGE_WALLETS[addr_lower]

        for tx in txs:
            to_addr = (tx.get("to", "") or "").lower()
            if to_addr in EXCHANGE_WALLETS:
                return EXCHANGE_WALLETS[to_addr]
            from_addr = (tx.get("from", "") or "").lower()
            if from_addr in EXCHANGE_WALLETS:
                return EXCHANGE_WALLETS[from_addr]

        return None

    async def score_single_wallet(self, address: str) -> dict[str, Any]:
        from app.services.mantle_scanner import mantle_scanner
        balance = mantle_scanner.get_balance(address)
        latest = mantle_scanner.get_latest_block()
        if not latest:
            return {
                "address": address,
                "whale_score": 0.0,
                "sentinel_score": 0.0,
                "total_volume": round(balance, 2),
                "tx_count": 0,
                "flow_label": "unknown",
                "tags": ["rpc_unavailable"],
                "wallet_type": "unknown",
            }

        transfers = mantle_scanner.scan_large_transfers(
            max(0, latest - 200),
            latest,
            min_value_eth=0.1,
        )
        relevant = [
            t for t in transfers
            if address.lower() in (t.get("from", "").lower(), t.get("to", "").lower())
        ]

        if not relevant:
            return {
                "address": address,
                "whale_score": 0.0,
                "sentinel_score": 0.0,
                "total_volume": round(balance, 2),
                "tx_count": 0,
                "flow_label": "inactive",
                "tags": ["no_recent_activity"],
                "wallet_type": "inactive",
            }

        return await self._score_wallet(address, relevant)


whale_scorer = WhaleScoreCalculator()
