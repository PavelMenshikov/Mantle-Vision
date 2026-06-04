import pytest

from app.services.cluster_analyzer import cluster_analyzer


@pytest.mark.asyncio
@pytest.mark.slow
async def test_analyze_wallet_no_funding():
    result = await cluster_analyzer.analyze_wallet(
        "0xf000000000000000000000000000000000000000",
        depth=1,
    )
    assert result is None


def test_detect_insider_cluster_empty():
    clusters = cluster_analyzer.detect_insider_cluster([])
    assert clusters == []


def test_detect_insider_cluster(sample_transfers):
    clusters = cluster_analyzer.detect_insider_cluster(sample_transfers)
    assert isinstance(clusters, list)


def test_compute_cluster_score_empty():
    score = cluster_analyzer.compute_cluster_score([])
    assert score == 0.0


def test_compute_cluster_score():
    members = [
        {"address": "0xa", "total_in": 100.0, "total_out": 0.0, "role": "funder"},
        {"address": "0xb", "total_in": 0.0, "total_out": 50.0, "role": "member"},
        {"address": "0xc", "total_in": 0.0, "total_out": 30.0, "role": "member"},
    ]
    score = cluster_analyzer.compute_cluster_score(members)
    assert 0.0 < score <= 1.0
