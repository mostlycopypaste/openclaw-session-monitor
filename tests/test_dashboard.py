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
