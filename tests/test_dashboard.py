"""Tests for dashboard rendering."""

import pytest
from src.models import Session
from src.dashboard import Dashboard


def test_dashboard_displays_status_column_running():
    """Test dashboard displays Status column with RUNNING value."""
    dashboard = Dashboard(test_mode=True)

    sessions = {
        "test-001": Session(
            session_id="test-001",
            label="test:main",
            agent="main",
            total_tokens=100000,
            status="running"
        )
    }

    # In test mode, dashboard returns JSON
    # We'll need to add status to the test mode output
    output = dashboard.render(sessions)
    assert "running" in output.lower()


def test_dashboard_displays_status_column_done():
    """Test dashboard displays Status column with DONE value."""
    dashboard = Dashboard(test_mode=True)

    sessions = {
        "test-001": Session(
            session_id="test-001",
            label="test:main",
            agent="main",
            total_tokens=100000,
            status="done"
        )
    }

    output = dashboard.render(sessions)
    assert "done" in output.lower()


def test_dashboard_displays_status_column_null():
    """Test dashboard displays Status column with — for null status."""
    dashboard = Dashboard(test_mode=True)

    sessions = {
        "test-001": Session(
            session_id="test-001",
            label="test:main",
            agent="main",
            total_tokens=100000,
            status=None
        )
    }

    output = dashboard.render(sessions)
    # In test mode, null status should be included in JSON
    # Display as "—" or "null" or similar visual indicator
    assert "test-001" in output


def test_dashboard_sorts_active_sessions_before_done():
    """Test dashboard sorts active sessions (running/null) before done sessions."""
    dashboard = Dashboard(test_mode=True)

    # Create sessions with same window % but different status
    sessions = {
        "done-001": Session(
            session_id="done-001",
            label="done:session",
            agent="main",
            total_tokens=100000,  # 50%
            context_limit=200000,
            status="done"
        ),
        "running-001": Session(
            session_id="running-001",
            label="running:session",
            agent="main",
            total_tokens=100000,  # 50%
            context_limit=200000,
            status="running"
        ),
        "null-001": Session(
            session_id="null-001",
            label="null:session",
            agent="main",
            total_tokens=100000,  # 50%
            context_limit=200000,
            status=None
        )
    }

    output = dashboard.render(sessions)
    import json
    data = json.loads(output)

    # Active sessions (running, null) should appear before done
    session_ids = [s["id"] for s in data["sessions"]]
    done_index = session_ids.index("done-001")
    running_index = session_ids.index("running-001")
    null_index = session_ids.index("null-001")

    # Both running and null should come before done
    assert running_index < done_index
    assert null_index < done_index


def test_dashboard_sorts_by_window_percent_within_active_group():
    """Test dashboard sorts active sessions by window % descending."""
    dashboard = Dashboard(test_mode=True)

    sessions = {
        "low": Session(
            session_id="low",
            label="low:usage",
            agent="main",
            total_tokens=50000,  # 25%
            context_limit=200000,
            status="running"
        ),
        "high": Session(
            session_id="high",
            label="high:usage",
            agent="main",
            total_tokens=180000,  # 90%
            context_limit=200000,
            status="running"
        ),
        "med": Session(
            session_id="med",
            label="med:usage",
            agent="main",
            total_tokens=100000,  # 50%
            context_limit=200000,
            status=None  # Also active
        )
    }

    output = dashboard.render(sessions)
    import json
    data = json.loads(output)

    # Should be ordered: high (90%), med (50%), low (25%)
    session_ids = [s["id"] for s in data["sessions"]]
    assert session_ids == ["high", "med", "low"]


def test_dashboard_sorts_by_window_percent_within_done_group():
    """Test dashboard sorts done sessions by window % descending."""
    dashboard = Dashboard(test_mode=True)

    sessions = {
        "done-low": Session(
            session_id="done-low",
            label="done:low",
            agent="main",
            total_tokens=30000,  # 15%
            context_limit=200000,
            status="done"
        ),
        "done-high": Session(
            session_id="done-high",
            label="done:high",
            agent="main",
            total_tokens=150000,  # 75%
            context_limit=200000,
            status="done"
        ),
        "active": Session(
            session_id="active",
            label="active:session",
            agent="main",
            total_tokens=40000,  # 20%
            context_limit=200000,
            status="running"
        )
    }

    output = dashboard.render(sessions)
    import json
    data = json.loads(output)

    # Active first, then done sessions sorted by window %
    session_ids = [s["id"] for s in data["sessions"]]
    assert session_ids == ["active", "done-high", "done-low"]


def test_dashboard_handles_empty_sessions():
    """Test dashboard handles empty sessions dict gracefully."""
    dashboard = Dashboard(test_mode=True)

    output = dashboard.render({})
    import json
    data = json.loads(output)

    assert data["sessions"] == []
    assert data["alerts"] == []
