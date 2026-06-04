from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

from app.database import db

logger = logging.getLogger(__name__)


class KnowledgeBase:
    def __init__(self) -> None:
        self._pattern_cache: list[dict[str, Any]] = []

    def record_pattern(self, pattern: dict[str, Any]) -> int:
        existing = db.find_similar_patterns(
            json.dumps(pattern.get("feature_vector", {})), limit=1
        )
        if existing:
            return existing[0]["id"]
        return db.save_anomaly_pattern(pattern)

    def find_similar(self, feature_vector: dict[str, float], threshold: float = 0.7) -> list[dict[str, Any]]:
        patterns = db.find_similar_patterns(json.dumps(feature_vector), limit=20)

        matches = []
        query_vec = np.array(list(feature_vector.values()))
        for p in patterns:
            try:
                stored_vec = np.array(list(json.loads(p["feature_vector"]).values()))
                similarity = self._cosine_similarity(query_vec, stored_vec)
                if similarity >= threshold:
                    matches.append({
                        "pattern_id": p["id"],
                        "pattern_type": p["pattern_type"],
                        "confidence": p["confidence"],
                        "similarity": round(float(similarity), 4),
                        "outcome": p.get("outcome", ""),
                        "description": p.get("description", ""),
                        "times_seen": p["times_seen"],
                    })
            except Exception as e:
                logger.debug(f"similarity match error: {e}")
                continue

        return sorted(matches, key=lambda m: m["similarity"], reverse=True)

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
            return 0.0
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def get_context_for_ai(self, wallet_address: str, current_features: dict[str, float]) -> str:
        similar = self.find_similar(current_features, threshold=0.6)

        if not similar:
            return "No historical patterns match current wallet behavior."

        lines = ["📚 Knowledge Base Context:"]
        for s in similar[:5]:
            outcome = f"→ Outcome: {s['outcome']}" if s.get("outcome") else ""
            lines.append(
                f"  • Pattern #{s['pattern_id']} ({s['pattern_type']}) "
                f"confidence={s['confidence']:.0%} similarity={s['similarity']:.0%} "
                f"seen {s['times_seen']}x {outcome}"
            )

        return "\n".join(lines)

    def update_outcome(self, pattern_id: int, outcome: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        conn = db._get_conn()
        conn.execute(
            "UPDATE anomaly_patterns SET outcome = ?, last_observed = ?, times_seen = times_seen + 1 WHERE id = ?",
            (outcome, now, pattern_id),
        )
        conn.commit()


knowledge_base = KnowledgeBase()
