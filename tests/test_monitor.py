"""Tests for session monitor coordinator."""

import pytest
from pathlib import Path
from src.monitor import SessionMonitor


def test_monitor_discover_sessions(tmp_path):
    """Test monitor discovers sessions from directory structure."""
    # Create mock directory structure
    agents_dir = tmp_path / "agents" / "main" / "sessions"
    agents_dir.mkdir(parents=True)

    # Create session JSONL
    # Note: totalTokens is cumulative, so later messages have larger values
    session_file = agents_dir / "test-001.jsonl"
    session_file.write_text(
        '{"type":"message","id":"msg-001","timestamp":"2026-04-07T10:00:00Z","role":"user","message":{"usage":{"totalTokens":1000}}}\n'
        '{"type":"message","id":"msg-002","timestamp":"2026-04-07T10:00:05Z","role":"assistant","message":{"usage":{"totalTokens":6000}}}\n'
    )

    # Create sessions.json with real dict format and absolute path
    sessions_file = agents_dir / "sessions.json"
    sessions_file.write_text(f"""{{
  "agent:main:test": {{
    "sessionId": "test-001",
    "sessionFile": "{session_file}",
    "status": "active"
  }}
}}""")

    # Initialize monitor
    monitor = SessionMonitor(state_dir=tmp_path)
    monitor.discover_sessions()

    # Verify session discovered
    assert len(monitor.sessions) == 1
    session = monitor.sessions["test-001"]
    assert session.session_id == "test-001"
    assert session.label == "agent:main:test"
    # Should use max (most recent context size), not sum
    assert session.total_tokens == 6000


def test_monitor_calculate_total_tokens(tmp_path):
    """Test monitor uses max tokens (most recent context size)."""
    agents_dir = tmp_path / "agents" / "main" / "sessions"
    agents_dir.mkdir(parents=True)

    session_file = agents_dir / "test-001.jsonl"
    # Write 10 messages with cumulative token counts (simulating growing context)
    lines = []
    for i in range(10):
        lines.append(
            f'{{"type":"message","id":"msg-{i:03d}","timestamp":"2026-04-07T10:00:{i:02d}Z","role":"user","message":{{"usage":{{"totalTokens":{(i+1)*1000}}}}}}}\n'
        )
    session_file.write_text(''.join(lines))

    sessions_file = agents_dir / "sessions.json"
    sessions_file.write_text(f"""{{
  "agent:main:test": {{
    "sessionId": "test-001",
    "sessionFile": "{session_file}",
    "status": "active"
  }}
}}""")

    monitor = SessionMonitor(state_dir=tmp_path)
    monitor.discover_sessions()

    # Should use max (most recent) = 10000, not sum = 55000
    assert monitor.sessions["test-001"].total_tokens == 10000


def test_monitor_removes_cleaned_sessions(tmp_path):
    """Test monitor removes sessions that are no longer in metadata."""
    agents_dir = tmp_path / "agents" / "main" / "sessions"
    agents_dir.mkdir(parents=True)

    # Create two session files
    session1 = agents_dir / "test-001.jsonl"
    session1.write_text('{"type":"message","message":{"usage":{"totalTokens":1000}}}\n')

    session2 = agents_dir / "test-002.jsonl"
    session2.write_text('{"type":"message","message":{"usage":{"totalTokens":2000}}}\n')

    # Initial sessions.json with both sessions
    sessions_file = agents_dir / "sessions.json"
    sessions_file.write_text(f"""{{
  "agent:main:test1": {{
    "sessionId": "test-001",
    "sessionFile": "{session1}"
  }},
  "agent:main:test2": {{
    "sessionId": "test-002",
    "sessionFile": "{session2}"
  }}
}}""")

    # First discovery - should find both
    monitor = SessionMonitor(state_dir=tmp_path)
    monitor.discover_sessions()
    assert len(monitor.sessions) == 2
    assert "test-001" in monitor.sessions
    assert "test-002" in monitor.sessions

    # Simulate cleanup: remove test-001 from sessions.json
    sessions_file.write_text(f"""{{
  "agent:main:test2": {{
    "sessionId": "test-002",
    "sessionFile": "{session2}"
  }}
}}""")

    # Second discovery - should only have test-002, test-001 should be removed
    monitor.discover_sessions()
    assert len(monitor.sessions) == 1
    assert "test-001" not in monitor.sessions
    assert "test-002" in monitor.sessions


def test_monitor_includes_model_in_session(tmp_path):
    """Test monitor passes model from metadata to Session object."""
    # Setup
    state_dir = tmp_path / ".openclaw-primary"
    agent_dir = state_dir / "agents" / "main"
    sessions_dir = agent_dir / "sessions"
    sessions_dir.mkdir(parents=True)

    # Create session file
    session_file = sessions_dir / "test-123.jsonl"
    session_file.write_text(
        '{"type":"message","role":"user","message":{"usage":{"totalTokens":5000}}}\n'
    )

    # Create sessions.json with model
    sessions_json = sessions_dir / "sessions.json"
    sessions_json.write_text(f"""{{
  "agent:main:test": {{
    "sessionId": "test-123",
    "sessionFile": "{session_file}",
    "status": "running",
    "model": "kimi-k2.5:cloud"
  }}
}}""")

    # Execute
    monitor = SessionMonitor(state_dir)
    monitor.discover_sessions()

    # Verify
    assert len(monitor.sessions) == 1
    session = monitor.sessions["test-123"]
    assert session.model == "kimi-k2.5:cloud"


def test_monitor_handles_missing_model(tmp_path):
    """Test monitor handles sessions without model field."""
    # Setup
    state_dir = tmp_path / ".openclaw-primary"
    agent_dir = state_dir / "agents" / "main"
    sessions_dir = agent_dir / "sessions"
    sessions_dir.mkdir(parents=True)

    # Create session file
    session_file = sessions_dir / "test-123.jsonl"
    session_file.write_text(
        '{"type":"message","role":"user","message":{"usage":{"totalTokens":5000}}}\n'
    )

    # Create sessions.json without model
    sessions_json = sessions_dir / "sessions.json"
    sessions_json.write_text(f"""{{
  "agent:main:test": {{
    "sessionId": "test-123",
    "sessionFile": "{session_file}",
    "status": "running"
  }}
}}""")

    # Execute
    monitor = SessionMonitor(state_dir)
    monitor.discover_sessions()

    # Verify
    assert len(monitor.sessions) == 1
    session = monitor.sessions["test-123"]
    assert session.model is None
