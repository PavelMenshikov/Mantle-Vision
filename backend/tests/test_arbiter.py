from unittest.mock import AsyncMock, patch

import pytest

from app.models.schemas import Signal, SignalDirection


@pytest.mark.asyncio
async def test_arbiter_high_risk_hold():
    from app.services.arbiter import arbiter
    with patch.object(arbiter, "_call_ai", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = '{"approve": true, "decision": "buy", "confidence": 0.8, "explanation": "Looks good"}'
        signal = await arbiter.decide(
            asset="MNT",
            rsi_result={"signal": "buy", "score": 0.8},
            volume_result={"signal": "buy", "score": 0.7},
            nostalgia_result={"signal": "buy", "score": 0.6},
            whale_result={"whale_score": 0.9, "sentinel_score": 0.95, "wallet_type": "insider"},
        )
    assert signal.direction == SignalDirection.HOLD
    assert signal.confidence >= 0.9
    assert "Risk threshold exceeded" in signal.reasoning


@pytest.mark.asyncio
async def test_arbiter_buy_consensus():
    from app.services.arbiter import arbiter
    with patch.object(arbiter, "_call_ai", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = '{"approve": true, "decision": "buy", "confidence": 0.75, "explanation": "Bullish momentum"}'
        signal = await arbiter.decide(
            asset="MNT",
            rsi_result={"signal": "buy", "score": 0.8},
            volume_result={"signal": "buy", "score": 0.7},
            nostalgia_result={"signal": "buy", "score": 0.65},
            whale_result={"whale_score": 0.3, "sentinel_score": 0.4, "wallet_type": "whale"},
        )
    assert signal.direction == SignalDirection.BUY
    assert signal.reasoning is not None


@pytest.mark.asyncio
async def test_arbiter_ai_fallback():
    from app.services.arbiter import arbiter
    with patch.object(arbiter, "_call_ai", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = None
        signal = await arbiter.decide(
            asset="MNT",
            rsi_result={},
            volume_result={},
            nostalgia_result={},
            whale_result={},
        )
    assert signal.direction == SignalDirection.HOLD


@pytest.mark.asyncio
async def test_arbiter_with_cluster_context():
    from app.services.arbiter import arbiter
    with patch.object(arbiter, "_call_ai", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = '{"approve": false, "decision": "hold", "confidence": 0.7, "explanation": "Insider cluster detected"}'
        signal = await arbiter.decide(
            asset="mETH",
            rsi_result={"signal": "buy", "score": 0.6},
            volume_result={"signal": "sell", "score": 0.7},
            nostalgia_result={"signal": "sell", "score": 0.55},
            whale_result={"whale_score": 0.7, "sentinel_score": 0.8, "wallet_type": "insider"},
            wallet_context={
                "cluster": {"total_members": 5, "total_volume": 50000, "root_funder": "0xabc"},
            },
            market_snapshot={
                "price_usd": 2500.0,
                "change_24h": -5.0,
                "volume_24h": 200000000,
            },
        )
    assert isinstance(signal.reasoning, str)
    assert len(signal.reasoning) > 0
