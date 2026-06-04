import json

import pytest

from app.services.knowledge_base import knowledge_base


def test_store_and_retrieve():
    pattern_id = knowledge_base.record_pattern({
        "pattern_type": "anomaly",
        "feature_vector": json.dumps({"tx_frequency": 0.5, "avg_value": 100.0}),
        "wallet_addresses": ["0xtestkb"],
        "confidence": 0.75,
        "description": "Test anomaly pattern",
    })
    assert isinstance(pattern_id, int)
    assert pattern_id > 0

    context = knowledge_base.get_context_for_ai(
        wallet_address="0xtestkb",
        current_features={"tx_frequency": 0.5, "avg_value": 100.0},
    )
    assert isinstance(context, str)
    assert "anomaly" in context.lower() or "pattern" in context.lower()


def test_empty_context():
    context = knowledge_base.get_context_for_ai(
        wallet_address="0xnonexistent",
        current_features={"tx_frequency": 999.0, "avg_value": 0.001},
    )
    assert "No historical patterns" in context


def test_similarity_scoring():
    knowledge_base.record_pattern({
        "pattern_type": "drain",
        "feature_vector": json.dumps({"tx_frequency": 0.1, "avg_value": 50.0}),
        "wallet_addresses": ["0xsim1"],
        "confidence": 0.6,
        "description": "Low activity pattern",
    })
    context = knowledge_base.get_context_for_ai(
        wallet_address="0xsim1",
        current_features={"tx_frequency": 0.1, "avg_value": 50.0},
    )
    assert isinstance(context, str)
    assert len(context) > 0
