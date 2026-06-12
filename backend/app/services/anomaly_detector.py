from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
from sklearn.ensemble import IsolationForest

from app.database import db
from app.services.mantle_scanner import mantle_scanner

logger = logging.getLogger(__name__)

ANOMALY_FEATURES = [
    "tx_frequency", "avg_value", "value_std", "pause_mean",
    "pause_std", "unique_contracts", "hourly_entropy",
    "avg_gas", "night_tx", "value_skew",
]


class AnomalyDetector:
    def __init__(self, contamination: float = 0.05) -> None:
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
        )
        self._trained = False
        self._ensure_fitted()

    def _extract_features(self, txs: list[dict[str, Any]]) -> np.ndarray:
        if not txs:
            return np.zeros((1, len(ANOMALY_FEATURES)))

        values = np.array([t.get("value_eth", 0) for t in txs])
        timestamps = np.array([t.get("timestamp", 0) for t in txs])
        timestamps_sorted = np.sort(timestamps)

        tx_frequency = len(txs) / max(timestamps_sorted[-1] - timestamps_sorted[0], 1) * 3600 if len(txs) > 1 else 0
        avg_value = float(np.mean(values)) if len(values) > 0 else 0
        value_std = float(np.std(values)) if len(values) > 1 else 0

        pauses = np.diff(timestamps_sorted) if len(timestamps_sorted) > 1 else np.array([0])
        pause_mean = float(np.mean(pauses)) if len(pauses) > 0 else 0
        pause_std = float(np.std(pauses)) if len(pauses) > 1 else 0

        unique_contracts = len(set(t.get("to", "") for t in txs if t.get("to")))

        hours = [datetime.fromtimestamp(t.get("timestamp", 0), tz=timezone.utc).hour
                 for t in txs if t.get("timestamp")]
        hour_counts = np.zeros(24)
        for h in hours:
            hour_counts[h] += 1
        hour_dist = hour_counts / max(hour_counts.sum(), 1)
        hourly_entropy = -np.sum(hour_dist[hour_dist > 0] * np.log2(hour_dist[hour_dist > 0])) if hour_dist.sum() > 0 else 0

        avg_gas = float(np.mean([t.get("gas_used", 0) for t in txs])) if txs else 0

        night_tx = sum(1 for h in hours if h < 6 or h > 22) / max(len(hours), 1)

        value_skew = float(
            np.abs(np.mean((values - np.mean(values)) ** 3) / max(np.std(values) ** 3, 0.001))
            if len(values) > 2 and np.std(values) > 0 else 0
        )

        return np.array([[
            tx_frequency, avg_value, value_std, pause_mean, pause_std,
            unique_contracts, hourly_entropy, avg_gas, night_tx, value_skew,
        ]])

    def _ensure_fitted(self) -> None:
        """
        Инициализирует модель на синтетическом baseline Mantle-транзакций.
        Параметры подобраны по реальной статистике Mantle mainnet.
        """
        if self._trained:
            return

        rng = np.random.default_rng(seed=42)
        n = 500

        synthetic = np.column_stack([
            rng.exponential(scale=0.5, size=n),
            rng.lognormal(mean=1.0, sigma=2.0, size=n),
            rng.lognormal(mean=0.5, sigma=1.5, size=n),
            rng.uniform(3600, 86400, size=n),
            rng.uniform(0, 7200, size=n),
            rng.integers(1, 15, size=n).astype(float),
            rng.uniform(1.0, 4.0, size=n),
            rng.uniform(21000, 200000, size=n),
            rng.beta(1, 5, size=n),
            rng.exponential(scale=0.5, size=n),
        ])

        self.model.fit(synthetic)
        self._trained = True
        logger.info(
            f"AnomalyDetector: fitted on {n} synthetic Mantle baseline samples. "
            f"Contamination={self.model.contamination}"
        )

    def score_transactions(self, txs: list[dict[str, Any]]) -> dict[str, Any]:
        if not txs:
            return {"anomaly_score": 0.0, "is_anomaly": False, "features": {}, "details": "no data"}

        features = self._extract_features(txs)
        self._ensure_fitted()

        anomaly_score = float(self.model.score_samples(features)[0])
        is_anomaly = self.model.predict(features)[0] == -1

        anomaly_score_normalized = 1.0 - (anomaly_score + 0.5)
        anomaly_score_normalized = max(0.0, min(1.0, anomaly_score_normalized))

        feature_dict = dict(zip(ANOMALY_FEATURES, features[0].tolist()))

        return {
            "anomaly_score": round(anomaly_score_normalized, 4),
            "is_anomaly": bool(is_anomaly),
            "features": feature_dict,
            "details": "Anomalous wallet behavior detected" if is_anomaly else "Normal behavior pattern",
        }

    async def scan_block_anomalies(self, from_block: int, to_block: int) -> list[dict[str, Any]]:
        transfers = mantle_scanner.scan_large_transfers(from_block, to_block, min_value_eth=1.0)

        wallet_txs: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for t in transfers:
            addr = t.get("from", "").lower()
            if addr:
                wallet_txs[addr].append(t)

        anomalies = []
        for addr, txs in wallet_txs.items():
            if len(txs) < 2:
                continue

            result = self.score_transactions(txs)
            if result["is_anomaly"]:
                cluster = db.find_cluster_by_address(addr)
                anomaly = {
                    "wallet": addr,
                    "anomaly_score": result["anomaly_score"],
                    "features": result["features"],
                    "details": result["details"],
                    "cluster_id": cluster["id"] if cluster else None,
                    "tx_count": len(txs),
                    "total_value": sum(t.get("value_eth", 0) for t in txs),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                anomalies.append(anomaly)

                db.save_anomaly_pattern({
                    "pattern_type": "wallet_anomaly",
                    "feature_vector": json.dumps(result["features"]),
                    "wallet_addresses": [addr],
                    "cluster_id": cluster["id"] if cluster else None,
                    "confidence": result["anomaly_score"],
                    "description": result["details"],
                    "outcome": "monitoring",
                })

        return anomalies

    def analyze_wallet_history(self, address: str, txs: list[dict[str, Any]]) -> dict[str, Any]:
        result = self.score_transactions(txs)

        cluster = db.find_cluster_by_address(address)
        if cluster:
            result["cluster_id"] = cluster["id"]
            result["cluster_size"] = cluster["total_members"]

        similar = db.find_similar_patterns(json.dumps(result.get("features", {})), limit=3)
        result["similar_patterns"] = [
            {"id": p["id"], "type": p["pattern_type"], "outcome": p.get("outcome", ""), "confidence": p["confidence"]}
            for p in similar
        ]

        return result


anomaly_detector = AnomalyDetector()
