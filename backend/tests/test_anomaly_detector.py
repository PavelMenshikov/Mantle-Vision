import numpy as np
import pytest

from app.services.anomaly_detector import anomaly_detector, ANOMALY_FEATURES


def test_extract_features_empty():
    features = anomaly_detector._extract_features([])
    assert features.shape == (1, len(ANOMALY_FEATURES))
    assert np.all(features == 0)


def test_extract_features_normal(sample_txs_for_anomaly):
    features = anomaly_detector._extract_features(sample_txs_for_anomaly)
    assert features.shape == (1, len(ANOMALY_FEATURES))
    assert features[0][0] > 0  # tx_frequency should be > 0


def test_score_transactions_empty():
    result = anomaly_detector.score_transactions([])
    assert result["anomaly_score"] == 0.0
    assert result["is_anomaly"] is False
    assert result["details"] == "no data"


def test_score_transactions_normal(sample_txs_for_anomaly):
    result = anomaly_detector.score_transactions(sample_txs_for_anomaly)
    assert 0.0 <= result["anomaly_score"] <= 1.0
    assert isinstance(result["is_anomaly"], bool)
    assert "features" in result


def test_anomaly_detected(sample_anomaly_txs):
    result = anomaly_detector.score_transactions(sample_anomaly_txs)
    assert "details" in result


def test_anomaly_features_structure(sample_txs_for_anomaly):
    result = anomaly_detector.score_transactions(sample_txs_for_anomaly)
    for feature in ANOMALY_FEATURES:
        assert feature in result["features"], f"Missing feature: {feature}"
