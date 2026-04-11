"""Tests for session parser."""

import pytest
from pathlib import Path
from src.session_parser import parse_sessions_metadata, parse_session_messages


def test_parse_sessions_metadata(tmp_path):
    """Test parsing sessions.json returns session metadata."""
    # Create actual session file so existence check passes
    session_file = tmp_path / "test-001.jsonl"
    session_file.write_text('{"type":"message","message":{"usage":{"totalTokens":100}}}\n')

    sessions_file = tmp_path / "sessions.json"
    sessions_file.write_text(f"""{{
  "agent:main:test": {{
    "sessionId": "test-001",
    "sessionFile": "{session_file}",
    "status": "active"
  }}
}}""")

    sessions = parse_sessions_metadata(sessions_file)

    assert len(sessions) == 1
    assert sessions[0]["sessionId"] == "test-001"
    assert sessions[0]["label"] == "agent:main:test"
    assert sessions[0]["agent"] == "main"
    assert sessions[0]["sessionFile"] == str(session_file)


def test_parse_sessions_filters_archived(tmp_path):
    """Test parsing sessions.json filters out archived sessions."""
    # Create actual session files
    active_file = tmp_path / "test-001.jsonl"
    active_file.write_text('{"type":"message","message":{"usage":{"totalTokens":100}}}\n')

    # Archived file should have .reset in filename
    archived_file = tmp_path / "test-002.reset.jsonl"
    archived_file.write_text('{"type":"message","message":{"usage":{"totalTokens":200}}}\n')

    sessions_file = tmp_path / "sessions.json"
    sessions_file.write_text(f"""{{
  "agent:main:active": {{
    "sessionId": "test-001",
    "sessionFile": "{active_file}",
    "status": "active"
  }},
  "agent:main:archived": {{
    "sessionId": "test-002",
    "sessionFile": "{archived_file}",
    "status": "archived"
  }}
}}""")

    sessions = parse_sessions_metadata(sessions_file)

    assert len(sessions) == 1
    assert sessions[0]["sessionId"] == "test-001"

def test_parse_session_messages(tmp_path):
    """Test parsing session JSONL returns messages with tokens."""
    session_file = tmp_path / "test.jsonl"
    session_file.write_text(
        '{"type":"message","id":"msg-001","timestamp":"2026-04-07T10:00:00Z","role":"user","message":{"content":"test","usage":{"totalTokens":1234}}}\n'
        '{"type":"message","id":"msg-002","timestamp":"2026-04-07T10:00:05Z","role":"assistant","message":{"content":"response","usage":{"totalTokens":5678}}}\n'
    )

    messages = parse_session_messages(session_file)

    assert len(messages) == 2
    assert messages[0]["timestamp"] == "2026-04-07T10:00:00Z"
    assert messages[0]["role"] == "user"
    assert messages[0]["tokens"] == 1234
    assert messages[1]["tokens"] == 5678


def test_parse_session_messages_handles_missing_usage(tmp_path):
    """Test parsing handles messages with missing usage field."""
    session_file = tmp_path / "test.jsonl"
    session_file.write_text(
        '{"type":"message","id":"msg-001","timestamp":"2026-04-07T10:00:00Z","role":"user","message":{"content":"test"}}\n'
        '{"type":"message","id":"msg-002","timestamp":"2026-04-07T10:00:05Z","role":"assistant","message":{"content":"response","usage":{"totalTokens":5678}}}\n'
    )

    messages = parse_session_messages(session_file)

    assert len(messages) == 2
    assert messages[0]["tokens"] == 0  # Missing usage defaults to 0
    assert messages[1]["tokens"] == 5678


def test_parse_session_messages_skips_malformed_lines(tmp_path):
    """Test parsing skips malformed JSONL lines with warning."""
    session_file = tmp_path / "test.jsonl"
    session_file.write_text(
        '{"type":"message","id":"msg-001","timestamp":"2026-04-07T10:00:00Z","role":"user","message":{"content":"test","usage":{"totalTokens":1234}}}\n'
        'this is not valid json\n'
        '{"type":"message","id":"msg-003","timestamp":"2026-04-07T10:00:10Z","role":"assistant","message":{"content":"response","usage":{"totalTokens":5678}}}\n'
    )

    messages = parse_session_messages(session_file)

    assert len(messages) == 2  # Skipped malformed line
    assert messages[0]["tokens"] == 1234
    assert messages[1]["tokens"] == 5678


def test_parse_session_messages_incremental(tmp_path):
    """Test incremental parsing returns only new messages and updated position."""
    from src.session_parser import parse_session_messages_incremental
    
    session_file = tmp_path / "test.jsonl"
    
    # Write initial messages
    session_file.write_text(
        '{"type":"message","id":"msg-001","timestamp":"2026-04-07T10:00:00Z","role":"user","message":{"usage":{"totalTokens":1000}}}\n'
        '{"type":"message","id":"msg-002","timestamp":"2026-04-07T10:00:05Z","role":"assistant","message":{"usage":{"totalTokens":2000}}}\n'
    )
    
    # First read - should get all messages
    messages, pos = parse_session_messages_incremental(session_file, start_pos=0)
    assert len(messages) == 2
    assert messages[0]["tokens"] == 1000
    assert messages[1]["tokens"] == 2000
    assert pos > 0  # Position updated
    
    # Append new message
    with open(session_file, 'a') as f:
        f.write('{"type":"message","id":"msg-003","timestamp":"2026-04-07T10:00:10Z","role":"user","message":{"usage":{"totalTokens":3000}}}\n')
    
    # Second read from last position - should only get new message
    new_messages, new_pos = parse_session_messages_incremental(session_file, start_pos=pos)
    assert len(new_messages) == 1
    assert new_messages[0]["tokens"] == 3000
    assert new_pos > pos  # Position advanced


def test_parse_sessions_metadata_extracts_status_running(tmp_path):
    """Test parser extracts status='running' from sessions.json."""
    # Create session file
    session_file = tmp_path / "test-001.jsonl"
    session_file.write_text('{"type":"message","message":{"usage":{"totalTokens":100}}}\n')

    sessions_file = tmp_path / "sessions.json"
    sessions_file.write_text(f"""{{
  "agent:main:test": {{
    "sessionId": "test-001",
    "sessionFile": "{session_file}",
    "status": "running"
  }}
}}""")

    sessions = parse_sessions_metadata(sessions_file)

    assert len(sessions) == 1
    assert sessions[0]["status"] == "running"


def test_parse_sessions_metadata_extracts_status_done(tmp_path):
    """Test parser extracts status='done' from sessions.json."""
    session_file = tmp_path / "test-001.jsonl"
    session_file.write_text('{"type":"message","message":{"usage":{"totalTokens":100}}}\n')

    sessions_file = tmp_path / "sessions.json"
    sessions_file.write_text(f"""{{
  "agent:main:test": {{
    "sessionId": "test-001",
    "sessionFile": "{session_file}",
    "status": "done"
  }}
}}""")

    sessions = parse_sessions_metadata(sessions_file)
    assert sessions[0]["status"] == "done"


def test_parse_sessions_metadata_status_null(tmp_path):
    """Test parser handles status=null in sessions.json."""
    session_file = tmp_path / "test-001.jsonl"
    session_file.write_text('{"type":"message","message":{"usage":{"totalTokens":100}}}\n')

    sessions_file = tmp_path / "sessions.json"
    sessions_file.write_text(f"""{{
  "agent:main:test": {{
    "sessionId": "test-001",
    "sessionFile": "{session_file}",
    "status": null
  }}
}}""")

    sessions = parse_sessions_metadata(sessions_file)
    # JSON null becomes Python None
    assert sessions[0]["status"] is None


def test_parse_sessions_metadata_status_missing(tmp_path):
    """Test parser handles missing status field in sessions.json."""
    session_file = tmp_path / "test-001.jsonl"
    session_file.write_text('{"type":"message","message":{"usage":{"totalTokens":100}}}\n')

    sessions_file = tmp_path / "sessions.json"
    sessions_file.write_text(f"""{{
  "agent:main:test": {{
    "sessionId": "test-001",
    "sessionFile": "{session_file}"
  }}
}}""")

    sessions = parse_sessions_metadata(sessions_file)
    # Missing field returns None via .get()
    assert sessions[0]["status"] is None


def test_parse_sessions_metadata_extracts_model(tmp_path):
    """Test parser extracts model field from sessions.json."""
    session_file = tmp_path / "test-001.jsonl"
    session_file.write_text('{"type":"message","message":{"usage":{"totalTokens":100}}}\n')

    sessions_file = tmp_path / "sessions.json"
    sessions_file.write_text(f"""{{
  "agent:main:test": {{
    "sessionId": "test-001",
    "sessionFile": "{session_file}",
    "status": "running",
    "model": "kimi-k2.5:cloud"
  }}
}}""")

    sessions = parse_sessions_metadata(sessions_file)

    assert len(sessions) == 1
    assert sessions[0]["model"] == "kimi-k2.5:cloud"


def test_parse_sessions_metadata_model_missing(tmp_path):
    """Test parser handles missing model field."""
    session_file = tmp_path / "test-001.jsonl"
    session_file.write_text('{"type":"message","message":{"usage":{"totalTokens":100}}}\n')

    sessions_file = tmp_path / "sessions.json"
    sessions_file.write_text(f"""{{
  "agent:main:test": {{
    "sessionId": "test-001",
    "sessionFile": "{session_file}",
    "status": "running"
  }}
}}""")

    sessions = parse_sessions_metadata(sessions_file)

    assert len(sessions) == 1
    assert sessions[0]["model"] is None
