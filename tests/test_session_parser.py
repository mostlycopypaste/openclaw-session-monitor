"""Tests for session parser."""

import pytest
from pathlib import Path
from src.session_parser import parse_sessions_metadata


def test_parse_sessions_metadata(tmp_path):
    """Test parsing sessions.json returns session metadata."""
    sessions_file = tmp_path / "sessions.json"
    sessions_file.write_text("""{
  "sessions": [
    {
      "sessionId": "test-001",
      "label": "main:test",
      "agent": "main",
      "status": "active",
      "sessionFile": "test-001.jsonl"
    }
  ]
}""")

    sessions = parse_sessions_metadata(sessions_file)

    assert len(sessions) == 1
    assert sessions[0]["sessionId"] == "test-001"
    assert sessions[0]["label"] == "main:test"
    assert sessions[0]["agent"] == "main"
    assert sessions[0]["sessionFile"] == "test-001.jsonl"


def test_parse_sessions_filters_archived(tmp_path):
    """Test parsing sessions.json filters out archived sessions."""
    sessions_file = tmp_path / "sessions.json"
    sessions_file.write_text("""{
  "sessions": [
    {
      "sessionId": "test-001",
      "label": "active",
      "agent": "main",
      "status": "active",
      "sessionFile": "test-001.jsonl"
    },
    {
      "sessionId": "test-002.reset",
      "label": "archived",
      "agent": "main",
      "status": "archived",
      "sessionFile": "test-002.jsonl"
    }
  ]
}""")

    sessions = parse_sessions_metadata(sessions_file)

    assert len(sessions) == 1
    assert sessions[0]["sessionId"] == "test-001"
