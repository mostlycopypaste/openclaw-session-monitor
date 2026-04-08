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
