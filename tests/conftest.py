"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_sessions_json():
    """Return path to sample sessions.json."""
    return Path(__file__).parent / "fixtures" / "sessions.json"


@pytest.fixture
def sample_session_jsonl():
    """Return path to sample session JSONL file."""
    return Path(__file__).parent / "fixtures" / "test-session.jsonl"
