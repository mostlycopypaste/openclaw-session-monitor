"""Tests for data models."""

import pytest
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
