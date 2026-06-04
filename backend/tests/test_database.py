import os
import tempfile
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.database import Database
from app.models.schemas import Signal, SignalDirection, SignalSource


@pytest.fixture
def tmp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = Database(db_path)
    yield db
    db.close()
    os.unlink(db_path)


def test_save_and_get_signal(tmp_db):
    signal = Signal(
        id=str(uuid4()),
        type="test_signal",
        asset="MNT",
        direction=SignalDirection.BUY,
        confidence=0.75,
        reasoning="Test signal reasoning",
        timestamp=datetime.now(timezone.utc),
        source=SignalSource.ANALYZER,
    )
    tmp_db.save_signal(signal)
    rows = tmp_db.get_signals(limit=10)
    assert len(rows) == 1
    assert rows[0]["id"] == signal.id
    assert rows[0]["direction"] == "buy"


def test_save_signal_with_scores(tmp_db):
    signal = Signal(
        id=str(uuid4()),
        type="test_signal",
        asset="mETH",
        direction=SignalDirection.SELL,
        confidence=0.6,
        reasoning="Sell signal",
        timestamp=datetime.now(timezone.utc),
        source=SignalSource.ANALYZER,
    )
    tmp_db.save_signal_with_scores(
        signal,
        rsi_score=0.3,
        volume_score=0.7,
        nostalgia_score=0.5,
        whale_score=0.4,
        ai_decision="sell",
        ai_confidence=0.6,
    )
    row = tmp_db.get_signal_by_id(signal.id)
    assert row is not None
    assert row["rsi_score"] == 0.3
    assert row["ai_decision"] == "sell"
    assert row["whale_score"] == 0.4


def test_get_signal_not_found(tmp_db):
    row = tmp_db.get_signal_by_id("nonexistent")
    assert row is None


def test_save_and_get_whale_profile(tmp_db):
    from app.models.schemas import WhaleProfile
    profile = WhaleProfile(
        address="0xtestwallet",
        label="Test Whale",
        totalValue=5000.0,
        riskScore=0.7,
        tags=["whale", "high_risk"],
    )
    tmp_db.save_whale_profile(profile)
    profiles = tmp_db.get_whale_profiles()
    assert len(profiles) >= 1
    assert profiles[0]["address"] == "0xtestwallet"


def test_stats(tmp_db):
    stats = tmp_db.get_stats()
    assert "total_signals" in stats
    assert "total_trades" in stats
    assert "buy_signals" in stats
    assert "sell_signals" in stats
