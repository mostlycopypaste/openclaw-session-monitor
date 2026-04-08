"""Tests for data models."""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from src.models import Session, Message, Alert


def test_session_creation():
    """Test Session dataclass creation with basic fields."""
    session = Session(
        session_id="5f3febb2-ebdd",
        label="main:heartbeat",
        agent="main",
        total_tokens=145234
    )
    assert session.session_id == "5f3febb2-ebdd"
    assert session.label == "main:heartbeat"
    assert session.agent == "main"
    assert session.total_tokens == 145234


def test_session_window_percent():
    """Test window_percent property calculation."""
    session = Session(
        session_id="test",
        label="test",
        agent="main",
        total_tokens=150000,
        context_limit=200000
    )
    assert session.window_percent == pytest.approx(75.0)


def test_session_alert_level_none():
    """Test alert_level property returns none when below thresholds."""
    session = Session(
        session_id="test",
        label="test",
        agent="main",
        total_tokens=100000,
        context_limit=200000
    )
    assert session.alert_level == "none"


def test_session_alert_level_warning():
    """Test alert_level property returns warning at 80% threshold."""
    session = Session(
        session_id="test",
        label="test",
        agent="main",
        total_tokens=160000,
        context_limit=200000
    )
    assert session.alert_level == "warning"


def test_session_alert_level_critical():
    """Test alert_level property returns critical at 90% threshold."""
    session = Session(
        session_id="test",
        label="test",
        agent="main",
        total_tokens=180000,
        context_limit=200000
    )
    assert session.alert_level == "critical"


def test_message_creation():
    """Test Message dataclass creation."""
    message = Message(
        timestamp="2026-04-07T10:45:32Z",
        role="user",
        tokens=1234
    )
    assert message.timestamp == "2026-04-07T10:45:32Z"
    assert message.role == "user"
    assert message.tokens == 1234


def test_message_is_spike_false():
    """Test is_spike property returns False for normal messages."""
    message = Message(timestamp="2026-04-07T10:45:32Z", role="user", tokens=5000)
    assert message.is_spike is False


def test_message_is_spike_true():
    """Test is_spike property returns True for messages >10K tokens."""
    message = Message(timestamp="2026-04-07T10:45:32Z", role="assistant", tokens=12000)
    assert message.is_spike is True


def test_alert_creation():
    """Test Alert dataclass creation."""
    alert = Alert(
        session_id="test",
        level="warning",
        message="Approaching context limit: 160K/200K (80%)"
    )
    assert alert.session_id == "test"
    assert alert.level == "warning"
    assert alert.message == "Approaching context limit: 160K/200K (80%)"


def test_session_age_seconds_none_when_created_at_none():
    """Test age_seconds returns None when created_at is not set."""
    session = Session(
        session_id="test",
        label="test",
        agent="main",
        total_tokens=10000,
        created_at=None
    )
    assert session.age_seconds is None


def test_session_age_seconds_calculation():
    """Test age_seconds calculates correct age in seconds."""
    # Mock current time to 2026-04-07 12:00:00 UTC (1744200000000 ms)
    mock_now = datetime(2026, 4, 7, 12, 0, 0, tzinfo=timezone.utc)

    with patch('src.models.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now

        # Session created 5 minutes (300 seconds) ago
        created_ms = int(mock_now.timestamp() * 1000) - (300 * 1000)
        session = Session(
            session_id="test",
            label="test",
            agent="main",
            total_tokens=10000,
            created_at=created_ms
        )

        assert session.age_seconds == 300


def test_session_age_seconds_rounds_down():
    """Test age_seconds rounds down partial seconds."""
    mock_now = datetime(2026, 4, 7, 12, 0, 0, 500000, tzinfo=timezone.utc)

    with patch('src.models.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now

        # Created 1500ms (1.5 seconds) ago - should round down to 1 second
        created_ms = int(mock_now.timestamp() * 1000) - 1500
        session = Session(
            session_id="test",
            label="test",
            agent="main",
            total_tokens=10000,
            created_at=created_ms
        )

        assert session.age_seconds == 1


def test_format_age_unknown_when_none():
    """Test format_age returns 'Unknown' when created_at is None."""
    session = Session(
        session_id="test",
        label="test",
        agent="main",
        total_tokens=10000,
        created_at=None
    )
    assert session.format_age() == "Unknown"


def test_format_age_seconds():
    """Test format_age formats seconds correctly."""
    mock_now = datetime(2026, 4, 7, 12, 0, 0, tzinfo=timezone.utc)

    with patch('src.models.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now

        # 45 seconds ago
        created_ms = int(mock_now.timestamp() * 1000) - (45 * 1000)
        session = Session(
            session_id="test",
            label="test",
            agent="main",
            total_tokens=10000,
            created_at=created_ms
        )

        assert session.format_age() == "45s"


def test_format_age_minutes():
    """Test format_age formats minutes correctly."""
    mock_now = datetime(2026, 4, 7, 12, 0, 0, tzinfo=timezone.utc)

    with patch('src.models.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now

        # 15 minutes (900 seconds) ago
        created_ms = int(mock_now.timestamp() * 1000) - (900 * 1000)
        session = Session(
            session_id="test",
            label="test",
            agent="main",
            total_tokens=10000,
            created_at=created_ms
        )

        assert session.format_age() == "15m"


def test_format_age_hours():
    """Test format_age formats hours correctly."""
    mock_now = datetime(2026, 4, 7, 12, 0, 0, tzinfo=timezone.utc)

    with patch('src.models.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now

        # 3 hours (10800 seconds) ago
        created_ms = int(mock_now.timestamp() * 1000) - (10800 * 1000)
        session = Session(
            session_id="test",
            label="test",
            agent="main",
            total_tokens=10000,
            created_at=created_ms
        )

        assert session.format_age() == "3h"


def test_format_age_days():
    """Test format_age formats days correctly."""
    mock_now = datetime(2026, 4, 7, 12, 0, 0, tzinfo=timezone.utc)

    with patch('src.models.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now

        # 2 days (172800 seconds) ago
        created_ms = int(mock_now.timestamp() * 1000) - (172800 * 1000)
        session = Session(
            session_id="test",
            label="test",
            agent="main",
            total_tokens=10000,
            created_at=created_ms
        )

        assert session.format_age() == "2d"


def test_format_age_edge_case_exactly_60_seconds():
    """Test format_age at boundary - exactly 60 seconds shows as minutes."""
    mock_now = datetime(2026, 4, 7, 12, 0, 0, tzinfo=timezone.utc)

    with patch('src.models.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now

        # Exactly 60 seconds ago
        created_ms = int(mock_now.timestamp() * 1000) - (60 * 1000)
        session = Session(
            session_id="test",
            label="test",
            agent="main",
            total_tokens=10000,
            created_at=created_ms
        )

        assert session.format_age() == "1m"


def test_format_age_edge_case_exactly_3600_seconds():
    """Test format_age at boundary - exactly 3600 seconds shows as hours."""
    mock_now = datetime(2026, 4, 7, 12, 0, 0, tzinfo=timezone.utc)

    with patch('src.models.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now

        # Exactly 3600 seconds (1 hour) ago
        created_ms = int(mock_now.timestamp() * 1000) - (3600 * 1000)
        session = Session(
            session_id="test",
            label="test",
            agent="main",
            total_tokens=10000,
            created_at=created_ms
        )

        assert session.format_age() == "1h"


def test_format_age_edge_case_exactly_86400_seconds():
    """Test format_age at boundary - exactly 86400 seconds shows as days."""
    mock_now = datetime(2026, 4, 7, 12, 0, 0, tzinfo=timezone.utc)

    with patch('src.models.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now

        # Exactly 86400 seconds (1 day) ago
        created_ms = int(mock_now.timestamp() * 1000) - (86400 * 1000)
        session = Session(
            session_id="test",
            label="test",
            agent="main",
            total_tokens=10000,
            created_at=created_ms
        )

        assert session.format_age() == "1d"
