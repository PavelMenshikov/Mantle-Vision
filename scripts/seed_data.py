#!/usr/bin/env python3
"""Pre-seed the database with test patterns for demo purposes."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database import db

SEED_PATTERNS = [ 
    {
        "pattern_type": "insider_dump",
        "feature_vector": json.dumps({
            "tx_frequency": 0.8, "avg_value": 500.0, "value_std": 50.0,
            "pause_mean": 5.0, "night_tx": 0.6, "unique_contracts": 2,
        }),
        "wallet_addresses": json.dumps([
            "0x28C6c06298d514Db089934071355E5743bf21d60",
            "0xRecipient1",
            "0xRecipient2",
        ]),
        "confidence": 0.85,
        "description": "Common donor funded 3 wallets within 2 hours, all dumped within 15 min",
        "outcome": "price dropped 12% within 1 hour",
    },
    {
        "pattern_type": "accumulation",
        "feature_vector": json.dumps({
            "tx_frequency": 0.2, "avg_value": 50.0, "value_std": 10.0,
            "pause_mean": 3600.0, "night_tx": 0.1, "unique_contracts": 1,
        }),
        "wallet_addresses": json.dumps(["0xAccumulator"]),
        "confidence": 0.7,
        "description": "Steady DCA accumulation over 2 weeks, no outflows",
        "outcome": "wallet grew 40% in value over 2 weeks",
    },
    {
        "pattern_type": "bot_activity",
        "feature_vector": json.dumps({
            "tx_frequency": 0.01, "avg_value": 0.5, "value_std": 0.1,
            "pause_mean": 0.5, "night_tx": 0.5, "unique_contracts": 10,
        }),
        "wallet_addresses": json.dumps(["0xBotWallet"]),
        "confidence": 0.95,
        "description": "High-frequency micro-transactions to 10+ unique contracts",
        "outcome": "identified as MEV bot",
    },
]


def seed():
    count = 0
    for p in SEED_PATTERNS:
        existing = db.find_similar_patterns(p["feature_vector"], limit=1)
        if not existing:
            db.save_anomaly_pattern(p)
            count += 1
    print(f"Seeded {count} anomaly patterns")
    print(f"Total patterns in DB: {len(db.get_anomaly_patterns())}")


if __name__ == "__main__":
    seed()
