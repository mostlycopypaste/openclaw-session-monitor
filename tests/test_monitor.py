"""Tests for session monitor coordinator."""

import pytest
from pathlib import Path
from src.monitor import SessionMonitor


def test_monitor_discover_sessions(tmp_path):
    """Test monitor discovers sessions from directory structure."""
    # Create mock directory structure
    agents_dir = tmp_path / "agents" / "main" / "sessions"
    agents_dir.mkdir(parents=True)

    # Create sessions.json
    sessions_file = agents_dir / "sessions.json"
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

    # Create session JSONL
    session_file = agents_dir / "test-001.jsonl"
    session_file.write_text(
        '{"type":"message","id":"msg-001","timestamp":"2026-04-07T10:00:00Z","role":"user","message":{"usage":{"totalTokens":1000}}}\n'
        '{"type":"message","id":"msg-002","timestamp":"2026-04-07T10:00:05Z","role":"assistant","message":{"usage":{"totalTokens":5000}}}\n'
    )

    # Initialize monitor
    monitor = SessionMonitor(state_dir=tmp_path)
    monitor.discover_sessions()

    # Verify session discovered
    assert len(monitor.sessions) == 1
    session = monitor.sessions["test-001"]
    assert session.session_id == "test-001"
    assert session.label == "main:test"
    assert session.total_tokens == 6000


def test_monitor_calculate_total_tokens(tmp_path):
    """Test monitor calculates total tokens correctly."""
    agents_dir = tmp_path / "agents" / "main" / "sessions"
    agents_dir.mkdir(parents=True)

    sessions_file = agents_dir / "sessions.json"
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

    session_file = agents_dir / "test-001.jsonl"
    # Write 10 messages with known token counts
    lines = []
    for i in range(10):
        lines.append(
            f'{{"type":"message","id":"msg-{i:03d}","timestamp":"2026-04-07T10:00:{i:02d}Z","role":"user","message":{{"usage":{{"totalTokens":{(i+1)*1000}}}}}}}\n'
        )
    session_file.write_text(''.join(lines))

    monitor = SessionMonitor(state_dir=tmp_path)
    monitor.discover_sessions()

    # Sum should be 1000+2000+...+10000 = 55000
    assert monitor.sessions["test-001"].total_tokens == 55000
