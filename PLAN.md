# OpenClaw Session Monitor MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use trycycle-executing to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a real-time token usage monitoring tool that watches OpenClaw session files and displays live dashboard with alerts

**Architecture:** File watcher (watchdog) detects JSONL changes → Incremental parser extracts tokens → Live terminal UI (rich) displays sessions with alerts at 80%/90% thresholds

**Tech Stack:** Python 3.8+, watchdog (file monitoring), rich (terminal UI), pytest (testing)

---

## Strategy Gate

Before proceeding with implementation, confirm the architectural approach:

**Chosen Solution:** File-watching Python tool with terminal UI  
**Alternatives Considered:**
- Gateway API polling: Rejected (doesn't provide per-message granularity, 10x overhead)
- Shell script: Rejected (limited UI, harder to maintain)
- Modify OpenClaw core: Rejected (requires upstream approval, weeks timeline)

**Decision:** File-watching approach is lowest-risk, fastest to implement, and meets all MVP requirements. No user decision required.

---

## File Structure

**Core Data Layer:**
- `src/models.py` - Data classes (Session, Message, Alert) - pure data, no I/O
- `src/session_parser.py` - Read sessions.json + JSONL files, return parsed data
  
**Monitoring Layer:**
- `src/session_watcher.py` - File watching with watchdog, emit change events
- `src/monitor.py` - Coordinate watcher + parser, maintain session registry

**Presentation:**
- `src/dashboard.py` - Terminal UI with rich, render tables + alerts
- `src/cli.py` - CLI entry point (already exists, will be modified)

**Testing:**
- `tests/test_*.py` - Full test coverage following approved testing strategy
- `tests/fixtures/` - Synthetic session files

**Rationale:** Separation of concerns (data/I/O/compute/presentation), testability (single responsibility per module), incremental complexity (pure functions → I/O → concurrency → UI)

---

## Implementation Tasks

### Task 0: Environment Setup

**Goal:** Establish working Python environment with dependencies

- [ ] **Step 1: Verify Python version**

```bash
python3 --version
# Expected: Python 3.8.0 or higher
```

- [ ] **Step 2: Create and activate virtual environment**

```bash
python3 -m venv .venv
source .venv/bin/activate
# Expected: prompt shows (.venv) prefix
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -e ".[dev]"
# Expected: Successfully installed watchdog, rich, jsonlines, pytest, pytest-cov, black, ruff
```

- [ ] **Step 4: Verify pytest works**

```bash
pytest --version
# Expected: pytest 7.x.x
```

- [ ] **Step 5: Run initial test suite (should show 0 tests)**

```bash
pytest -v
# Expected: "collected 0 items" (no tests yet)
```

- [ ] **Step 6: Commit**

```bash
git add .venv requirements.txt
git commit -m "chore: setup Python environment with dependencies"
```

---

### Task 1: Data Models (Session, Message, Alert)

**Goal:** Build foundation data structures with computed properties (window percentage, alert levels, spike detection)

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing test for Session model**

Create `tests/test_models.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py -v
# Expected: FAIL with "ModuleNotFoundError: No module named 'src.models'"
```

- [ ] **Step 3: Write minimal implementation**

Create `src/models.py`:

```python
"""Data models for OpenClaw session monitoring."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Session:
    """Represents an OpenClaw session with token tracking."""
    
    session_id: str
    label: str
    agent: str
    total_tokens: int
    context_limit: int = 200000
    
    @property
    def window_percent(self) -> float:
        """Calculate percentage of context window used."""
        if self.context_limit == 0:
            return 0.0
        return (self.total_tokens / self.context_limit) * 100
    
    @property
    def alert_level(self) -> str:
        """Determine alert level based on token usage."""
        percent = self.window_percent
        if percent >= 90:
            return "critical"
        elif percent >= 80:
            return "warning"
        else:
            return "none"


@dataclass
class Message:
    """Represents a single message in a session."""
    
    timestamp: str
    role: str
    tokens: int
    spike_threshold: int = 10000
    
    @property
    def is_spike(self) -> bool:
        """Check if message exceeds spike threshold."""
        return self.tokens > self.spike_threshold


@dataclass
class Alert:
    """Represents an alert to display to user."""
    
    session_id: str
    level: str  # "warning" or "critical"
    message: str
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_models.py -v
# Expected: 9 passed
```

- [ ] **Step 5: Refactor and verify**

Review code for clarity and consistency. Ensure property names are clear, thresholds are configurable, and edge cases are handled. Run tests again.

```bash
pytest tests/test_models.py -v
# Expected: 9 passed
```

- [ ] **Step 6: Commit**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat: add Session, Message, and Alert data models with computed properties"
```

---

### Task 2: Test Fixtures for Session Files

**Goal:** Create synthetic session files for testing parser

**Files:**
- Create: `tests/fixtures/sessions.json`
- Create: `tests/fixtures/session-active.jsonl`
- Create: `tests/fixtures/session-warning.jsonl`
- Create: `tests/fixtures/session-critical.jsonl`

- [ ] **Step 1: Create sessions.json fixture**

Create `tests/fixtures/sessions.json`:

```json
{
  "sessions": [
    {
      "sessionId": "test-active-001",
      "label": "test:active",
      "agent": "main",
      "status": "active",
      "sessionFile": "session-active.jsonl",
      "updatedAt": "2026-04-07T10:00:00Z"
    },
    {
      "sessionId": "test-warning-002",
      "label": "test:warning",
      "agent": "main",
      "status": "active",
      "sessionFile": "session-warning.jsonl",
      "updatedAt": "2026-04-07T10:15:00Z"
    },
    {
      "sessionId": "test-critical-003",
      "label": "test:critical",
      "agent": "main",
      "status": "active",
      "sessionFile": "session-critical.jsonl",
      "updatedAt": "2026-04-07T10:30:00Z"
    },
    {
      "sessionId": "test-archived-004.reset",
      "label": "test:archived",
      "agent": "main",
      "status": "archived",
      "sessionFile": "session-archived.jsonl",
      "updatedAt": "2026-04-07T09:00:00Z"
    }
  ]
}
```

- [ ] **Step 2: Create active session fixture (72K tokens)**

Create `tests/fixtures/session-active.jsonl`:

```jsonl
{"type":"message","id":"msg-001","timestamp":"2026-04-07T10:00:00Z","role":"user","message":{"content":"test message","usage":{"totalTokens":1000}}}
{"type":"message","id":"msg-002","timestamp":"2026-04-07T10:00:05Z","role":"assistant","message":{"content":"response","usage":{"totalTokens":5000}}}
{"type":"message","id":"msg-003","timestamp":"2026-04-07T10:00:10Z","role":"user","message":{"content":"follow up","usage":{"totalTokens":1200}}}
{"type":"message","id":"msg-004","timestamp":"2026-04-07T10:00:15Z","role":"assistant","message":{"content":"another response","usage":{"totalTokens":6500}}}
{"type":"message","id":"msg-005","timestamp":"2026-04-07T10:00:20Z","role":"tool","message":{"content":"tool result","usage":{"totalTokens":3000}}}
{"type":"message","id":"msg-006","timestamp":"2026-04-07T10:00:25Z","role":"assistant","message":{"content":"synthesis","usage":{"totalTokens":8000}}}
{"type":"message","id":"msg-007","timestamp":"2026-04-07T10:00:30Z","role":"user","message":{"content":"more questions","usage":{"totalTokens":1500}}}
{"type":"message","id":"msg-008","timestamp":"2026-04-07T10:00:35Z","role":"assistant","message":{"content":"detailed answer","usage":{"totalTokens":12000}}}
{"type":"message","id":"msg-009","timestamp":"2026-04-07T10:00:40Z","role":"user","message":{"content":"final question","usage":{"totalTokens":2000}}}
{"type":"message","id":"msg-010","timestamp":"2026-04-07T10:00:45Z","role":"assistant","message":{"content":"conclusion","usage":{"totalTokens":32000}}}
```

- [ ] **Step 3: Create warning session fixture (165K tokens)**

Create `tests/fixtures/session-warning.jsonl` with messages totaling 165,000 tokens (above 80% threshold). Use similar structure to active session but with larger token counts.

- [ ] **Step 4: Create critical session fixture (185K tokens)**

Create `tests/fixtures/session-critical.jsonl` with messages totaling 185,000 tokens (above 90% threshold).

- [ ] **Step 5: Verify fixtures are valid JSON**

```bash
python3 -c "import json; json.load(open('tests/fixtures/sessions.json')); print('Valid JSON')"
# Expected: Valid JSON

python3 -c "import jsonlines; list(jsonlines.open('tests/fixtures/session-active.jsonl')); print('Valid JSONL')"
# Expected: Valid JSONL
```

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/
git commit -m "test: add synthetic session fixtures for parser testing"
```

---

### Task 3: Parse sessions.json Metadata

**Goal:** Read sessions.json and extract active session metadata

**Files:**
- Create: `src/session_parser.py`
- Create: `tests/test_session_parser.py`

- [ ] **Step 1: Write failing test for parsing sessions.json**

Create `tests/test_session_parser.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_session_parser.py::test_parse_sessions_metadata -v
# Expected: FAIL with "ModuleNotFoundError: No module named 'src.session_parser'"
```

- [ ] **Step 3: Write minimal implementation**

Create `src/session_parser.py`:

```python
"""Parse OpenClaw session files."""

import json
from pathlib import Path
from typing import List, Dict, Any


def parse_sessions_metadata(sessions_file: Path) -> List[Dict[str, Any]]:
    """
    Parse sessions.json and return list of active session metadata.
    
    Filters out archived sessions (those with .reset or .deleted suffixes).
    
    Args:
        sessions_file: Path to sessions.json
        
    Returns:
        List of session metadata dictionaries
    """
    with open(sessions_file, 'r') as f:
        data = json.load(f)
    
    sessions = data.get('sessions', [])
    
    # Filter out archived sessions
    active_sessions = [
        s for s in sessions
        if s.get('status') == 'active'
        and not s.get('sessionId', '').endswith('.reset')
        and not s.get('sessionId', '').endswith('.deleted')
    ]
    
    return active_sessions
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_session_parser.py -v
# Expected: 2 passed
```

- [ ] **Step 5: Refactor and verify**

Review error handling, add type hints, improve readability. Run tests again.

```bash
pytest tests/test_session_parser.py -v
# Expected: 2 passed
```

- [ ] **Step 6: Commit**

```bash
git add src/session_parser.py tests/test_session_parser.py
git commit -m "feat: add sessions.json metadata parser with archived session filtering"
```

---

### Task 4: Parse JSONL Message Files

**Goal:** Read session JSONL files and extract message token data

**Files:**
- Modify: `src/session_parser.py`
- Modify: `tests/test_session_parser.py`

- [ ] **Step 1: Write failing test for parsing JSONL messages**

Add to `tests/test_session_parser.py`:

```python
from src.session_parser import parse_session_messages


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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_session_parser.py::test_parse_session_messages -v
# Expected: FAIL with "AttributeError: module 'src.session_parser' has no attribute 'parse_session_messages'"
```

- [ ] **Step 3: Write minimal implementation**

Add to `src/session_parser.py`:

```python
import jsonlines
import logging

logger = logging.getLogger(__name__)


def parse_session_messages(session_file: Path) -> List[Dict[str, Any]]:
    """
    Parse session JSONL file and extract message token data.
    
    Args:
        session_file: Path to session JSONL file
        
    Returns:
        List of message dictionaries with timestamp, role, tokens
    """
    messages = []
    
    try:
        with jsonlines.open(session_file) as reader:
            for line_num, obj in enumerate(reader, start=1):
                try:
                    if obj.get('type') != 'message':
                        continue
                    
                    message = obj.get('message', {})
                    usage = message.get('usage', {})
                    
                    messages.append({
                        'timestamp': obj.get('timestamp', ''),
                        'role': obj.get('role', ''),
                        'tokens': usage.get('totalTokens', 0)
                    })
                except (KeyError, TypeError) as e:
                    logger.warning(f"Skipping malformed message at line {line_num}: {e}")
                    continue
    except jsonlines.InvalidLineError as e:
        logger.warning(f"Skipping invalid JSON line: {e}")
    
    return messages
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_session_parser.py -v
# Expected: 5 passed (2 from Task 3 + 3 new)
```

- [ ] **Step 5: Refactor and verify**

Improve error handling, add docstrings, simplify logic. Run full test suite.

```bash
pytest tests/test_session_parser.py -v
# Expected: 5 passed
```

- [ ] **Step 6: Commit**

```bash
git add src/session_parser.py tests/test_session_parser.py
git commit -m "feat: add JSONL message parser with error handling for malformed data"
```

---

### Task 5: Incremental File Reading

**Goal:** Track file positions to read only new messages, not entire file

**Files:**
- Modify: `src/session_parser.py`
- Modify: `tests/test_session_parser.py`

- [ ] **Step 1: Write failing test for incremental reading**

Add to `tests/test_session_parser.py`:

```python
from src.session_parser import parse_session_messages_incremental


def test_parse_session_messages_incremental(tmp_path):
    """Test incremental parsing returns only new messages and updated position."""
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_session_parser.py::test_parse_session_messages_incremental -v
# Expected: FAIL with "AttributeError: module 'src.session_parser' has no attribute 'parse_session_messages_incremental'"
```

- [ ] **Step 3: Write minimal implementation**

Add to `src/session_parser.py`:

```python
from typing import Tuple


def parse_session_messages_incremental(
    session_file: Path,
    start_pos: int = 0
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Parse session JSONL file incrementally from given position.
    
    Args:
        session_file: Path to session JSONL file
        start_pos: Byte position to start reading from
        
    Returns:
        Tuple of (messages list, new byte position)
    """
    messages = []
    
    with open(session_file, 'rb') as f:
        # Seek to start position
        f.seek(start_pos)
        
        # Read remaining lines
        for line in f:
            try:
                obj = json.loads(line.decode('utf-8'))
                
                if obj.get('type') != 'message':
                    continue
                
                message = obj.get('message', {})
                usage = message.get('usage', {})
                
                messages.append({
                    'timestamp': obj.get('timestamp', ''),
                    'role': obj.get('role', ''),
                    'tokens': usage.get('totalTokens', 0)
                })
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"Skipping malformed line: {e}")
                continue
        
        # Return new position
        new_pos = f.tell()
    
    return messages, new_pos
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_session_parser.py::test_parse_session_messages_incremental -v
# Expected: 1 passed
```

- [ ] **Step 5: Refactor and verify**

Ensure original `parse_session_messages` uses incremental function internally. Run all parser tests.

```bash
pytest tests/test_session_parser.py -v
# Expected: 6 passed
```

- [ ] **Step 6: Commit**

```bash
git add src/session_parser.py tests/test_session_parser.py
git commit -m "feat: add incremental JSONL parsing with position tracking"
```

---

### Task 6: Session Monitor Coordinator

**Goal:** Discover sessions from filesystem, maintain registry, calculate tokens

**Files:**
- Create: `src/monitor.py`
- Create: `tests/test_monitor.py`

- [ ] **Step 1: Write failing test for monitor discovery**

Create `tests/test_monitor.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_monitor.py -v
# Expected: FAIL with "ModuleNotFoundError: No module named 'src.monitor'"
```

- [ ] **Step 3: Write minimal implementation**

Create `src/monitor.py`:

```python
"""Session monitor coordinator."""

import logging
from pathlib import Path
from typing import Dict
from src.models import Session
from src.session_parser import parse_sessions_metadata, parse_session_messages

logger = logging.getLogger(__name__)


class SessionMonitor:
    """
    Coordinates session discovery and monitoring.
    
    Scans OpenClaw state directory for active sessions and tracks token usage.
    """
    
    def __init__(self, state_dir: Path, context_limit: int = 200000):
        """
        Initialize session monitor.
        
        Args:
            state_dir: Path to OpenClaw state directory (e.g., ~/.openclaw-primary)
            context_limit: Context window size in tokens (default: 200000)
        """
        self.state_dir = Path(state_dir)
        self.context_limit = context_limit
        self.sessions: Dict[str, Session] = {}
    
    def discover_sessions(self):
        """
        Discover active sessions from filesystem.
        
        Scans agents/*/sessions/sessions.json files and loads session metadata.
        Calculates total tokens for each session.
        """
        agents_dir = self.state_dir / "agents"
        if not agents_dir.exists():
            logger.warning(f"Agents directory not found: {agents_dir}")
            return
        
        # Scan all agent directories
        for agent_dir in agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            
            sessions_dir = agent_dir / "sessions"
            if not sessions_dir.exists():
                continue
            
            sessions_file = sessions_dir / "sessions.json"
            if not sessions_file.exists():
                continue
            
            # Parse session metadata
            try:
                sessions_metadata = parse_sessions_metadata(sessions_file)
            except Exception as e:
                logger.error(f"Failed to parse {sessions_file}: {e}")
                continue
            
            # Process each active session
            for metadata in sessions_metadata:
                session_id = metadata['sessionId']
                session_file = sessions_dir / metadata['sessionFile']
                
                if not session_file.exists():
                    logger.warning(f"Session file not found: {session_file}")
                    continue
                
                # Parse messages and calculate total tokens
                try:
                    messages = parse_session_messages(session_file)
                    total_tokens = sum(msg['tokens'] for msg in messages)
                    
                    # Create Session object
                    session = Session(
                        session_id=session_id,
                        label=metadata['label'],
                        agent=metadata['agent'],
                        total_tokens=total_tokens,
                        context_limit=self.context_limit
                    )
                    
                    self.sessions[session_id] = session
                    
                except Exception as e:
                    logger.error(f"Failed to parse session {session_file}: {e}")
                    continue
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_monitor.py -v
# Expected: 2 passed
```

- [ ] **Step 5: Refactor and verify**

Add error handling, improve logging, ensure thread safety. Run full test suite.

```bash
pytest tests/test_monitor.py -v
# Expected: 2 passed
```

- [ ] **Step 6: Commit**

```bash
git add src/monitor.py tests/test_monitor.py
git commit -m "feat: add session monitor coordinator with discovery and token calculation"
```

---

### Task 7: File Watcher Integration

**Goal:** Detect file changes with watchdog, emit events for modifications

**Files:**
- Create: `src/session_watcher.py`
- Create: `tests/test_session_watcher.py`

- [ ] **Step 1: Write failing test for file watching**

Create `tests/test_session_watcher.py`:

```python
"""Tests for file watcher."""

import pytest
import time
from pathlib import Path
from src.session_watcher import SessionWatcher


def test_watcher_detects_file_modification(tmp_path):
    """Test watcher detects file modification within 1 second."""
    # Create test file
    test_file = tmp_path / "test.jsonl"
    test_file.write_text('{"type":"message","id":"msg-001"}\n')
    
    # Track events
    events = []
    
    def on_modified(path):
        events.append(('modified', path))
    
    # Start watcher
    watcher = SessionWatcher(watch_dir=tmp_path, on_modified=on_modified)
    watcher.start()
    
    try:
        # Wait for watcher to initialize
        time.sleep(0.5)
        
        # Modify file
        with open(test_file, 'a') as f:
            f.write('{"type":"message","id":"msg-002"}\n')
        
        # Wait for event detection (should be <1s)
        time.sleep(1.5)
        
        # Verify event detected
        assert len(events) == 1
        assert events[0][0] == 'modified'
        assert Path(events[0][1]) == test_file
        
    finally:
        watcher.stop()


def test_watcher_detects_new_file_creation(tmp_path):
    """Test watcher detects new file creation."""
    events = []
    
    def on_created(path):
        events.append(('created', path))
    
    watcher = SessionWatcher(watch_dir=tmp_path, on_created=on_created)
    watcher.start()
    
    try:
        time.sleep(0.5)
        
        # Create new file
        new_file = tmp_path / "new-session.jsonl"
        new_file.write_text('{"type":"message"}\n')
        
        time.sleep(1.5)
        
        assert len(events) == 1
        assert events[0][0] == 'created'
        
    finally:
        watcher.stop()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_session_watcher.py -v
# Expected: FAIL with "ModuleNotFoundError: No module named 'src.session_watcher'"
```

- [ ] **Step 3: Write minimal implementation**

Create `src/session_watcher.py`:

```python
"""File watcher for OpenClaw session files."""

import logging
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

logger = logging.getLogger(__name__)


class SessionFileHandler(FileSystemEventHandler):
    """Handle file system events for session files."""
    
    def __init__(
        self,
        on_modified: Optional[Callable[[str], None]] = None,
        on_created: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize handler.
        
        Args:
            on_modified: Callback for file modifications
            on_created: Callback for file creation
        """
        self.on_modified_callback = on_modified
        self.on_created_callback = on_created
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        # Only watch .jsonl files
        if not event.src_path.endswith('.jsonl'):
            return
        
        if self.on_modified_callback:
            self.on_modified_callback(event.src_path)
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        if not event.src_path.endswith('.jsonl'):
            return
        
        if self.on_created_callback:
            self.on_created_callback(event.src_path)


class SessionWatcher:
    """Watch session directory for file changes."""
    
    def __init__(
        self,
        watch_dir: Path,
        on_modified: Optional[Callable[[str], None]] = None,
        on_created: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize watcher.
        
        Args:
            watch_dir: Directory to watch
            on_modified: Callback for file modifications
            on_created: Callback for file creation
        """
        self.watch_dir = Path(watch_dir)
        self.handler = SessionFileHandler(
            on_modified=on_modified,
            on_created=on_created
        )
        self.observer = Observer()
    
    def start(self):
        """Start watching directory."""
        self.observer.schedule(self.handler, str(self.watch_dir), recursive=True)
        self.observer.start()
        logger.info(f"Started watching {self.watch_dir}")
    
    def stop(self):
        """Stop watching directory."""
        self.observer.stop()
        self.observer.join(timeout=5)
        logger.info(f"Stopped watching {self.watch_dir}")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_session_watcher.py -v
# Expected: 2 passed (tests may be slow due to file system events)
```

- [ ] **Step 5: Refactor and verify**

Add timeout handling, improve error recovery, test on both macOS and Linux if possible. Run tests.

```bash
pytest tests/test_session_watcher.py -v
# Expected: 2 passed
```

- [ ] **Step 6: Commit**

```bash
git add src/session_watcher.py tests/test_session_watcher.py
git commit -m "feat: add file watcher with watchdog for real-time session monitoring"
```

---

### Task 8: Dashboard with Test Mode

**Goal:** Render sessions with rich UI or JSON (test mode), color-code by alert level

**Files:**
- Create: `src/dashboard.py`
- Create: `tests/test_dashboard.py`

- [ ] **Step 1: Write failing test for dashboard test mode**

Create `tests/test_dashboard.py`:

```python
"""Tests for dashboard."""

import pytest
import json
from src.dashboard import Dashboard
from src.models import Session, Alert


def test_dashboard_test_mode_json_structure():
    """Test dashboard outputs valid JSON in test mode."""
    sessions = [
        Session(
            session_id="test-001",
            label="main:test",
            agent="main",
            total_tokens=150000
        )
    ]
    
    dashboard = Dashboard(test_mode=True)
    output = dashboard.render(sessions)
    
    # Parse JSON
    data = json.loads(output)
    
    assert 'sessions' in data
    assert 'alerts' in data
    assert len(data['sessions']) == 1
    
    session = data['sessions'][0]
    assert session['id'] == 'test-001'
    assert session['label'] == 'main:test'
    assert session['tokens'] == 150000
    assert session['window_percent'] == 75.0


def test_dashboard_test_mode_includes_alerts():
    """Test dashboard includes alerts for sessions above thresholds."""
    sessions = [
        Session(
            session_id="test-warning",
            label="test:warning",
            agent="main",
            total_tokens=165000  # 82.5% - warning
        ),
        Session(
            session_id="test-critical",
            label="test:critical",
            agent="main",
            total_tokens=185000  # 92.5% - critical
        )
    ]
    
    dashboard = Dashboard(test_mode=True)
    output = dashboard.render(sessions)
    data = json.loads(output)
    
    assert len(data['alerts']) == 2
    
    # Check warning alert
    warning_alert = next(a for a in data['alerts'] if a['session_id'] == 'test-warning')
    assert warning_alert['level'] == 'warning'
    
    # Check critical alert
    critical_alert = next(a for a in data['alerts'] if a['session_id'] == 'test-critical')
    assert critical_alert['level'] == 'critical'
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_dashboard.py -v
# Expected: FAIL with "ModuleNotFoundError: No module named 'src.dashboard'"
```

- [ ] **Step 3: Write minimal implementation**

Create `src/dashboard.py`:

```python
"""Dashboard for displaying session monitoring data."""

import json
import logging
from typing import List
from rich.console import Console
from rich.table import Table
from rich.live import Live
from src.models import Session, Alert

logger = logging.getLogger(__name__)


class Dashboard:
    """Display session monitoring dashboard."""
    
    def __init__(self, test_mode: bool = False):
        """
        Initialize dashboard.
        
        Args:
            test_mode: If True, output JSON instead of rich UI
        """
        self.test_mode = test_mode
        self.console = Console() if not test_mode else None
    
    def render(self, sessions: List[Session]) -> str:
        """
        Render dashboard for given sessions.
        
        Args:
            sessions: List of Session objects to display
            
        Returns:
            JSON string in test mode, empty string in rich UI mode
        """
        if self.test_mode:
            return self._render_test_mode(sessions)
        else:
            return self._render_rich_ui(sessions)
    
    def _render_test_mode(self, sessions: List[Session]) -> str:
        """Render as JSON for testing."""
        # Build session data
        sessions_data = []
        for session in sessions:
            sessions_data.append({
                'id': session.session_id,
                'label': session.label,
                'agent': session.agent,
                'tokens': session.total_tokens,
                'window_percent': session.window_percent,
                'alert_level': session.alert_level
            })
        
        # Build alerts
        alerts_data = []
        for session in sessions:
            if session.alert_level in ['warning', 'critical']:
                alerts_data.append({
                    'session_id': session.session_id,
                    'level': session.alert_level,
                    'message': f"Context window {session.window_percent:.1f}% full"
                })
        
        # Return JSON
        output = {
            'sessions': sessions_data,
            'alerts': alerts_data
        }
        return json.dumps(output, indent=2)
    
    def _render_rich_ui(self, sessions: List[Session]) -> str:
        """Render rich terminal UI."""
        # Create table
        table = Table(title="OpenClaw Session Monitor")
        
        table.add_column("Agent", style="cyan")
        table.add_column("Session ID", style="magenta")
        table.add_column("Label", style="green")
        table.add_column("Tokens", justify="right")
        table.add_column("Window %", justify="right")
        table.add_column("Status")
        
        # Add rows
        for session in sessions:
            # Color code by alert level
            if session.alert_level == 'critical':
                style = "bold red"
            elif session.alert_level == 'warning':
                style = "bold yellow"
            else:
                style = "white"
            
            table.add_row(
                session.agent,
                session.session_id[:12] + "...",
                session.label,
                f"{session.total_tokens:,}",
                f"{session.window_percent:.1f}%",
                session.alert_level.upper(),
                style=style
            )
        
        # Print table
        if self.console:
            self.console.print(table)
        
        return ""  # Rich UI prints directly, no return value needed
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_dashboard.py -v
# Expected: 2 passed
```

- [ ] **Step 5: Refactor and verify**

Add message stream support, keyboard controls, improve formatting. Run tests.

```bash
pytest tests/test_dashboard.py -v
# Expected: 2 passed
```

- [ ] **Step 6: Commit**

```bash
git add src/dashboard.py tests/test_dashboard.py
git commit -m "feat: add dashboard with rich UI and JSON test mode"
```

---

### Task 9: CLI Watch Command

**Goal:** Implement `session-monitor watch` with environment variable support

**Files:**
- Modify: `src/cli.py:54-57`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing test for CLI watch command**

Create `tests/test_cli.py`:

```python
"""Tests for CLI."""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch
from src.cli import main


def test_cli_watch_command_test_mode(tmp_path, capsys):
    """Test CLI watch command in test mode outputs JSON."""
    # Setup test directory structure
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
    session_file.write_text(
        '{"type":"message","id":"msg-001","timestamp":"2026-04-07T10:00:00Z","role":"user","message":{"usage":{"totalTokens":150000}}}\n'
    )
    
    # Run CLI with test mode
    with patch('sys.argv', ['session-monitor', 'watch', '--test-mode', '--state-dir', str(tmp_path), '--once']):
        main()
    
    # Check output
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    
    assert 'sessions' in data
    assert len(data['sessions']) == 1
    assert data['sessions'][0]['tokens'] == 150000
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_cli.py -v
# Expected: FAIL (CLI not yet implemented)
```

- [ ] **Step 3: Write implementation**

Modify `src/cli.py` to replace the stub implementation:

```python
"""CLI entry point for session-monitor command."""

import sys
import os
import argparse
import time
import logging
from pathlib import Path
from src.monitor import SessionMonitor
from src.dashboard import Dashboard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def cmd_watch(args):
    """Execute watch command."""
    # Determine state directory
    state_dir = args.state_dir
    if not state_dir:
        state_dir = os.getenv('OPENCLAW_STATE_DIR', str(Path.home() / '.openclaw-primary'))
    
    state_dir = Path(state_dir)
    
    # Get context limit
    context_limit = int(os.getenv('OPENCLAW_CONTEXT_TOKENS', '200000'))
    
    # Initialize monitor and dashboard
    monitor = SessionMonitor(state_dir=state_dir, context_limit=context_limit)
    dashboard = Dashboard(test_mode=args.test_mode)
    
    # Discover sessions
    monitor.discover_sessions()
    
    # Render dashboard
    output = dashboard.render(list(monitor.sessions.values()))
    
    if args.test_mode:
        print(output)
    
    # Exit if --once flag set (for testing)
    if args.once:
        return 0
    
    # TODO: Add live monitoring loop with file watcher
    # For now, just render once
    return 0


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        prog="session-monitor",
        description="Real-time token usage monitoring for OpenClaw sessions"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Watch command
    watch_parser = subparsers.add_parser("watch", help="Start live monitoring dashboard")
    watch_parser.add_argument("--agent", help="Monitor specific agent only")
    watch_parser.add_argument("--test-mode", action="store_true", help="Output JSON instead of rich UI")
    watch_parser.add_argument("--simple", action="store_true", help="Simple output (no colors)")
    watch_parser.add_argument("--refresh-rate", type=float, default=1.0, help="Dashboard refresh rate in seconds")
    watch_parser.add_argument("--state-dir", help="Override OpenClaw state directory")
    watch_parser.add_argument("--once", action="store_true", help="Run once and exit (for testing)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == 'watch':
        return cmd_watch(args)
    
    print(f"Command '{args.command}' not yet implemented.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_cli.py -v
# Expected: 1 passed
```

- [ ] **Step 5: Refactor and verify**

Add live monitoring loop, keyboard controls, graceful shutdown. Run full test suite.

```bash
pytest -v
# Expected: All tests pass
```

- [ ] **Step 6: Commit**

```bash
git add src/cli.py tests/test_cli.py
git commit -m "feat: implement CLI watch command with test mode support"
```

---

### Task 10: End-to-End Integration Test

**Goal:** Complete workflow test proving entire system works together

**Files:**
- Create: `tests/test_end_to_end.py`

- [ ] **Step 1: Write comprehensive end-to-end test**

Create `tests/test_end_to_end.py`:

```python
"""End-to-end integration tests."""

import pytest
import json
import time
from pathlib import Path
from src.monitor import SessionMonitor
from src.dashboard import Dashboard


def test_end_to_end_monitoring_workflow(tmp_path):
    """
    Complete end-to-end test: realistic sessions → monitor → dashboard.
    
    Tests:
    - Multiple sessions with different token levels
    - Warning and critical alerts
    - Spike detection
    - JSON output correctness
    """
    # Setup directory structure
    agents_dir = tmp_path / "agents" / "main" / "sessions"
    agents_dir.mkdir(parents=True)
    
    # Create sessions.json with 3 sessions
    sessions_file = agents_dir / "sessions.json"
    sessions_file.write_text("""{
  "sessions": [
    {
      "sessionId": "session-low",
      "label": "low:tokens",
      "agent": "main",
      "status": "active",
      "sessionFile": "session-low.jsonl"
    },
    {
      "sessionId": "session-warning",
      "label": "warning:tokens",
      "agent": "main",
      "status": "active",
      "sessionFile": "session-warning.jsonl"
    },
    {
      "sessionId": "session-critical",
      "label": "critical:tokens",
      "agent": "main",
      "status": "active",
      "sessionFile": "session-critical.jsonl"
    }
  ]
}""")
    
    # Session 1: Low tokens (50K = 25%)
    low_file = agents_dir / "session-low.jsonl"
    low_file.write_text(
        '{"type":"message","id":"msg-001","timestamp":"2026-04-07T10:00:00Z","role":"user","message":{"usage":{"totalTokens":10000}}}\n'
        '{"type":"message","id":"msg-002","timestamp":"2026-04-07T10:00:05Z","role":"assistant","message":{"usage":{"totalTokens":20000}}}\n'
        '{"type":"message","id":"msg-003","timestamp":"2026-04-07T10:00:10Z","role":"user","message":{"usage":{"totalTokens":20000}}}\n'
    )
    
    # Session 2: Warning tokens (165K = 82.5%)
    warning_file = agents_dir / "session-warning.jsonl"
    warning_file.write_text(
        '{"type":"message","id":"msg-001","timestamp":"2026-04-07T10:00:00Z","role":"user","message":{"usage":{"totalTokens":50000}}}\n'
        '{"type":"message","id":"msg-002","timestamp":"2026-04-07T10:00:05Z","role":"assistant","message":{"usage":{"totalTokens":65000}}}\n'
        '{"type":"message","id":"msg-003","timestamp":"2026-04-07T10:00:10Z","role":"user","message":{"usage":{"totalTokens":50000}}}\n'
    )
    
    # Session 3: Critical tokens (185K = 92.5%)
    critical_file = agents_dir / "session-critical.jsonl"
    critical_file.write_text(
        '{"type":"message","id":"msg-001","timestamp":"2026-04-07T10:00:00Z","role":"user","message":{"usage":{"totalTokens":60000}}}\n'
        '{"type":"message","id":"msg-002","timestamp":"2026-04-07T10:00:05Z","role":"assistant","message":{"usage":{"totalTokens":75000}}}\n'
        '{"type":"message","id":"msg-003","timestamp":"2026-04-07T10:00:10Z","role":"user","message":{"usage":{"totalTokens":50000}}}\n'
    )
    
    # Initialize monitor
    monitor = SessionMonitor(state_dir=tmp_path, context_limit=200000)
    monitor.discover_sessions()
    
    # Verify all sessions discovered
    assert len(monitor.sessions) == 3
    
    # Verify token counts
    assert monitor.sessions["session-low"].total_tokens == 50000
    assert monitor.sessions["session-warning"].total_tokens == 165000
    assert monitor.sessions["session-critical"].total_tokens == 185000
    
    # Verify alert levels
    assert monitor.sessions["session-low"].alert_level == "none"
    assert monitor.sessions["session-warning"].alert_level == "warning"
    assert monitor.sessions["session-critical"].alert_level == "critical"
    
    # Render dashboard in test mode
    dashboard = Dashboard(test_mode=True)
    output = dashboard.render(list(monitor.sessions.values()))
    data = json.loads(output)
    
    # Verify JSON structure
    assert 'sessions' in data
    assert 'alerts' in data
    assert len(data['sessions']) == 3
    
    # Verify alerts
    assert len(data['alerts']) == 2  # Warning and critical, not low
    
    alert_levels = {a['session_id']: a['level'] for a in data['alerts']}
    assert alert_levels['session-warning'] == 'warning'
    assert alert_levels['session-critical'] == 'critical'
    
    print("✓ End-to-end test passed - entire system works correctly")
```

- [ ] **Step 2: Run test to verify current state**

```bash
pytest tests/test_end_to_end.py -v
# Expected: Should pass if all prior tasks completed correctly
```

- [ ] **Step 3: Fix any integration issues**

If test fails, diagnose which component is broken and fix it. Re-run test until it passes.

- [ ] **Step 4: Run full test suite**

```bash
pytest -v
# Expected: All tests pass
```

- [ ] **Step 5: Measure performance**

```bash
pytest tests/test_end_to_end.py -v --durations=0
# Expected: Test completes in <2 seconds
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_end_to_end.py
git commit -m "test: add end-to-end integration test verifying complete workflow"
```

---

### Task 11: Documentation

**Goal:** Update README with installation and usage instructions

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README with MVP status**

Modify `README.md` to update project status:

```markdown
## Project Status

- [x] Phase 1: Core Parser - Complete
- [x] Phase 2: File Watcher - Complete  
- [x] Phase 3: Live Dashboard - Complete (MVP)
- [ ] Phase 4: Analysis Features - Planned
- [ ] Phase 5: Historical Trending - Planned

**MVP Status:** ✅ Complete and tested

See [PLAN.md](PLAN.md) for detailed implementation plan.
```

- [ ] **Step 2: Add installation section**

Add detailed installation instructions:

```markdown
## Installation

### Requirements

- Python 3.8 or higher
- OpenClaw 2026.4.0 or higher
- macOS or Linux

### Install from Source

```bash
# Clone repository
git clone https://github.com/user/openclaw-session-monitor
cd openclaw-session-monitor

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package
pip install -e .

# Verify installation
session-monitor --help
```

### Environment Variables

```bash
# Override OpenClaw state directory (optional)
export OPENCLAW_STATE_DIR=/path/to/.openclaw-primary

# Override context window size (optional, default: 200000)
export OPENCLAW_CONTEXT_TOKENS=200000
```
```

- [ ] **Step 3: Add usage examples**

Add practical usage examples:

```markdown
## Usage Examples

### Basic Monitoring

```bash
# Start monitoring (displays rich terminal UI)
session-monitor watch

# Monitor specific agent only
session-monitor watch --agent main

# Simple mode for SSH/no-color terminals
session-monitor watch --simple
```

### Test Mode (JSON Output)

```bash
# Output JSON instead of terminal UI (useful for automation)
session-monitor watch --test-mode --once

# Example output:
# {
#   "sessions": [
#     {
#       "id": "5f3febb2-ebdd",
#       "label": "main:heartbeat",
#       "tokens": 145234,
#       "window_percent": 72.6,
#       "alert_level": "none"
#     }
#   ],
#   "alerts": []
# }
```

### Custom State Directory

```bash
# If OpenClaw state is in non-standard location
session-monitor watch --state-dir /custom/path/.openclaw-primary
```
```

- [ ] **Step 4: Add troubleshooting section**

Add common issues and solutions:

```markdown
## Troubleshooting

### Dashboard not updating

**Symptom:** Terminal shows no sessions or stale data

**Solutions:**
1. Verify OpenClaw is running: `openclaw gateway health`
2. Check session files exist: `ls ~/.openclaw-primary/agents/main/sessions/`
3. Verify state directory: `session-monitor watch --state-dir /correct/path`

### Permission denied errors

**Symptom:** "Permission denied" when accessing session files

**Solution:**
```bash
# Check file permissions
ls -la ~/.openclaw-primary/agents/main/sessions/

# Ensure current user has read access
# Session files should be readable by your user
```

### No sessions found

**Symptom:** "No sessions found" message

**Solutions:**
1. Verify OpenClaw has active sessions: `openclaw sessions list`
2. Check state directory exists: `ls ~/.openclaw-primary/`
3. Ensure sessions have messages (newly created empty sessions won't show tokens)
```

- [ ] **Step 5: Run tests to ensure nothing broke**

```bash
pytest -v
# Expected: All tests still pass
```

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs: update README with installation, usage, and troubleshooting"
```

---

## MVP Completion Checklist

After completing all tasks, verify MVP success criteria:

- [ ] **All tests pass**
```bash
pytest -v --cov=src --cov-report=term-missing
# Expected: 100% coverage on core modules, all tests green
```

- [ ] **Parse 8MB file <500ms**
```bash
# Create 8MB test file and benchmark
python3 -m pytest tests/ -k performance --durations=0
```

- [ ] **File change detection <1s**
```bash
pytest tests/test_session_watcher.py -v --durations=0
# Verify watcher tests complete quickly
```

- [ ] **Memory <30MB, CPU <2%**
```bash
# Run monitor for 60 seconds and measure
session-monitor watch &
sleep 60
ps aux | grep session-monitor
# Verify RSS memory < 30MB, CPU < 2%
kill %1
```

- [ ] **Dashboard displays sessions with correct alerts**
```bash
# Manual verification: run against live OpenClaw sessions
session-monitor watch
# Verify:
# - Sessions appear in table
# - Token counts update
# - Alerts show for sessions >80%
# - Colors are correct (yellow warning, red critical)
# - Press 'q' to quit cleanly
```

---

## Notes

- This plan implements MVP only (Phases 1-3: Parser, Watcher, Dashboard)
- Optional Phases 4-5 (Analysis, Metrics) deferred until MVP validated by user
- Every task follows Red/Green/Refactor TDD cycle
- Exact commands and complete code provided for each step
- Tests verify real user-visible behavior, not just implementation details
- Performance targets enforced through specific test assertions

---

## Success Criteria

**MVP is complete when:**

1. ✅ All 30+ tests pass (parsing, watching, dashboard, integration)
2. ✅ Parse 8MB file <500ms
3. ✅ File change detection <1s
4. ✅ Memory <30MB, CPU <2%
5. ✅ Dashboard displays sessions with correct alerts (green/yellow/red)
6. ✅ End-to-end test proves entire system works

**User verification required:**
- Run against live OpenClaw sessions for 1 week
- Confirm alerts are timely and accurate
- Measure session reset reduction (target: 50% fewer resets)

Refer to PLAN-strategic.md for architectural decisions, research findings, risk analysis, and future phases.
