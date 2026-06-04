from unittest.mock import AsyncMock, patch

import pytest

from app.services.whale_score import whale_scorer, SENTINEL_SCORE_WEIGHTS


@pytest.mark.asyncio
async def test_whale_scorer_keys(sample_transfers):
    with patch.object(whale_scorer, "_compute_cluster_score", new_callable=AsyncMock) as mock_cluster:
        mock_cluster.return_value = (0.3, {"cluster_id": 1, "size": 2, "volume": 1000})
        results = await whale_scorer.compute_from_transfers(sample_transfers)
    assert len(results) > 0
    for addr, data in results.items():
        assert "address" in data
        assert "whale_score" in data
        assert "sentinel_score" in data
        assert "wallet_type" in data
        assert "tags" in data
        assert 0 <= data["whale_score"] <= 1
        assert 0 <= data["sentinel_score"] <= 1


def test_sentinel_score_weights():
    total = sum(SENTINEL_SCORE_WEIGHTS.values())
    assert abs(total - 1.0) < 0.01, "Weights must sum to 1.0"


@pytest.mark.asyncio
async def test_wallet_types(sample_transfers):
    with patch.object(whale_scorer, "_compute_cluster_score", new_callable=AsyncMock) as mock_cluster:
        mock_cluster.return_value = (0.0, {})
        results = await whale_scorer.compute_from_transfers(sample_transfers)
    for data in results.values():
        assert data["wallet_type"] in ("insider", "smart_money", "market_maker", "anomaly", "whale", "active")


@pytest.mark.asyncio
async def test_high_risk_tag(sample_transfers):
    with patch.object(whale_scorer, "_compute_cluster_score", new_callable=AsyncMock) as mock_cluster:
        mock_cluster.return_value = (0.0, {})
        results = await whale_scorer.compute_from_transfers(sample_transfers)
    for data in results.values():
        if data["sentinel_score"] > 0.7:
            assert "high_risk" in data["tags"]
        if data["sentinel_score"] > 0.85:
            assert "critical" in data["tags"]


@pytest.mark.asyncio
async def test_flow_labels(sample_transfers):
    with patch.object(whale_scorer, "_compute_cluster_score", new_callable=AsyncMock) as mock_cluster:
        mock_cluster.return_value = (0.0, {})
        results = await whale_scorer.compute_from_transfers(sample_transfers)
    for data in results.values():
        assert data["flow_label"] in ("heavy_distributor", "distributor", "accumulator", "mild_accumulator", "balanced")
