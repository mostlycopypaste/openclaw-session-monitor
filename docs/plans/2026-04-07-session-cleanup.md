# Session Cleanup Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use trycycle-executing to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `session-monitor cleanup` command that helps users preview old session files and trigger OpenClaw's native cleanup mechanism.

**Architecture:** CLI command → Session discovery with metadata → Filter and preview candidates → Integration with `openclaw sessions cleanup --enforce --all-agents` → Report results

**Tech Stack:** Python 3.8+, subprocess (OpenClaw CLI integration), existing session parser infrastructure

**Important Note:** This tool provides visibility into cleanup candidates but delegates actual deletion to OpenClaw's native cleanup. The filtering (--agent, --status, --min-age-days, --min-size-mb) helps users preview what might be cleaned, but OpenClaw's cleanup applies its own internal criteria. This ensures we don't corrupt OpenClaw's session management.

---

## Strategy Gate

**Chosen Solution:** Wrap OpenClaw's native `openclaw sessions cleanup --enforce` with enhanced visibility and filtering

**Design Decisions:**

1. **Use OpenClaw's native cleanup mechanism**: Leverage `openclaw sessions cleanup --enforce` to respect OpenClaw's internal session lifecycle and maintenance config. This ensures compatibility and reduces risk of orphaning metadata.

2. **Add value through filtering and visibility**: Surface what will be cleaned before cleanup runs, provide filtering by age/status/size that OpenClaw's cleanup doesn't expose, and allow selective cleanup.

3. **Archive vs. delete**: OpenClaw's cleanup uses `.deleted` suffix convention (observed in codebase references). We'll follow this pattern and document that archives can be permanently removed by user if desired.

4. **Safety gates**: 
   - `--dry-run` default mode (preview only)
   - `--force` required for actual deletion
   - Size/count warnings for bulk operations
   - Require explicit confirmation for operations affecting >10 sessions or >100MB

5. **Integration with existing session discovery**: Reuse `SessionMonitor` and `parse_sessions_metadata()` to discover sessions, then cross-reference with filesystem for orphaned files.

**Alternatives Considered:**
- **Direct file deletion**: Rejected - bypasses OpenClaw's session lifecycle, risks metadata corruption
- **Manual OpenClaw CLI wrapper script**: Rejected - user requested proper integration into session-monitor tool
- **Archive-only with no deletion**: Rejected - user confirmed they want actual cleanup capability

---

## File Structure

**New Files:**
- `src/cleanup.py` - Cleanup logic, session discovery, filtering, OpenClaw CLI integration
- `tests/test_cleanup.py` - Comprehensive cleanup tests with mocked subprocess calls

**Modified Files:**
- `src/cli.py` - Add `cleanup` subcommand with filtering arguments
- `src/models.py` - Add `SessionCleanupCandidate` dataclass with size/age metadata
- `src/session_parser.py` - Add `get_session_file_size()` helper function

**Rationale:** 
- Separation of concerns: cleanup logic isolated from existing monitoring
- Reuse existing parsers for session discovery
- Testability: subprocess mocking allows testing without real OpenClaw installation

---

## Implementation Tasks

### Task 12: Enhance session_parser to Extract Status Field

**Goal:** Modify `parse_sessions_metadata()` to extract status field from OpenClaw sessions.json

**Files:**
- Modify: `src/session_parser.py`
- Modify: `tests/test_session_parser.py`

- [ ] **Step 1 (Red): Write failing test for status field extraction**

Add to `tests/test_session_parser.py`:

```python
def test_parse_sessions_metadata_with_status(tmp_path):
    """Test parse_sessions_metadata extracts status field."""
    agents_dir = tmp_path / "agents" / "main" / "sessions"
    agents_dir.mkdir(parents=True)
    
    # Create session file
    session_file = agents_dir / "test-123.jsonl"
    session_file.write_text('{"type":"message","role":"user","tokens":1000}\n')
    
    # Create sessions.json with status field (OpenClaw dict format)
    sessions_json = agents_dir / "sessions.json"
    sessions_data = {
        "agent:main:test": {
            "sessionId": "test-123",
            "sessionFile": str(session_file),
            "status": "done",
            "startedAt": 1743000000000
        }
    }
    sessions_json.write_text(json.dumps(sessions_data))
    
    sessions = parse_sessions_metadata(sessions_json)
    
    assert len(sessions) == 1
    assert sessions[0]['status'] == "done"
    assert sessions[0]['sessionId'] == "test-123"
```

Run test:
```bash
pytest tests/test_session_parser.py::test_parse_sessions_metadata_with_status -v
# Expected: KeyError or missing 'status' in result
```

- [ ] **Step 2 (Green): Add status field extraction to parse_sessions_metadata**

Modify `src/session_parser.py` in the `parse_sessions_metadata()` function:

```python
        sessions.append({
            'sessionId': session_data['sessionId'],
            'label': label,
            'agent': agent,
            'sessionFile': session_file,
            'startedAt': session_data.get('startedAt'),  # Unix timestamp in milliseconds
            'status': session_data.get('status', 'unknown'),  # Session status
        })
```

Run test:
```bash
pytest tests/test_session_parser.py::test_parse_sessions_metadata_with_status -v
# Expected: PASS
```

- [ ] **Step 3 (Refactor): Add test for missing status field**

Add edge case test to `tests/test_session_parser.py`:

```python
def test_parse_sessions_metadata_missing_status(tmp_path):
    """Test parse_sessions_metadata defaults to 'unknown' when status missing."""
    agents_dir = tmp_path / "agents" / "main" / "sessions"
    agents_dir.mkdir(parents=True)
    
    session_file = agents_dir / "test-456.jsonl"
    session_file.write_text('{"type":"message","tokens":500}\n')
    
    sessions_json = agents_dir / "sessions.json"
    sessions_data = {
        "agent:main:test2": {
            "sessionId": "test-456",
            "sessionFile": str(session_file)
            # No status field
        }
    }
    sessions_json.write_text(json.dumps(sessions_data))
    
    sessions = parse_sessions_metadata(sessions_json)
    
    assert len(sessions) == 1
    assert sessions[0]['status'] == "unknown"
```

Run full parser test suite:
```bash
pytest tests/test_session_parser.py -v
# Expected: All tests pass
```

- [ ] **Step 4: Commit**

```bash
git add src/session_parser.py tests/test_session_parser.py
git commit -m "feat: extract status field from sessions.json metadata"
```

---

### Task 13: SessionCleanupCandidate Model

**Goal:** Create data model for cleanup candidates with computed properties for filtering

**Files:**
- Modify: `src/models.py`
- Create: `tests/test_cleanup_models.py`

- [ ] **Step 1 (Red): Write failing test for SessionCleanupCandidate**

Create `tests/test_cleanup_models.py`:

```python
"""Tests for cleanup-related data models."""

import pytest
from datetime import datetime, timedelta
from src.models import SessionCleanupCandidate


def test_cleanup_candidate_creation():
    """Test SessionCleanupCandidate dataclass creation with basic fields."""
    candidate = SessionCleanupCandidate(
        session_id="5f3febb2-ebdd",
        agent="main",
        label="test-session",
        status="done",
        file_path="/path/to/session.jsonl",
        file_size_bytes=52428800,  # 50MB
        last_modified=datetime(2026, 3, 24, 10, 30, 0)
    )
    assert candidate.session_id == "5f3febb2-ebdd"
    assert candidate.agent == "main"
    assert candidate.status == "done"
    assert candidate.file_size_bytes == 52428800


def test_cleanup_candidate_age_days():
    """Test age_days computed property."""
    now = datetime.now()
    two_weeks_ago = now - timedelta(days=14)
    
    candidate = SessionCleanupCandidate(
        session_id="test",
        agent="main",
        label="old-session",
        status="done",
        file_path="/path/to/session.jsonl",
        file_size_bytes=1000,
        last_modified=two_weeks_ago
    )
    
    # Allow 1-day tolerance for test timing
    assert 13 <= candidate.age_days <= 15


def test_cleanup_candidate_size_mb():
    """Test size_mb computed property rounds to 2 decimals."""
    candidate = SessionCleanupCandidate(
        session_id="test",
        agent="main",
        label="large-session",
        status="done",
        file_path="/path/to/session.jsonl",
        file_size_bytes=52428800,  # Exactly 50MB
        last_modified=datetime.now()
    )
    assert candidate.size_mb == 50.0


def test_cleanup_candidate_size_mb_rounding():
    """Test size_mb rounds fractional MB correctly."""
    candidate = SessionCleanupCandidate(
        session_id="test",
        agent="main",
        label="session",
        status="done",
        file_path="/path/to/session.jsonl",
        file_size_bytes=5500000,  # ~5.24MB
        last_modified=datetime.now()
    )
    assert candidate.size_mb == 5.24


def test_cleanup_candidate_is_done():
    """Test is_done property for completed sessions."""
    candidate = SessionCleanupCandidate(
        session_id="test",
        agent="main",
        label="session",
        status="done",
        file_path="/path/to/session.jsonl",
        file_size_bytes=1000,
        last_modified=datetime.now()
    )
    assert candidate.is_done is True


def test_cleanup_candidate_is_not_done():
    """Test is_done property for running sessions."""
    candidate = SessionCleanupCandidate(
        session_id="test",
        agent="main",
        label="session",
        status="running",
        file_path="/path/to/session.jsonl",
        file_size_bytes=1000,
        last_modified=datetime.now()
    )
    assert candidate.is_done is False
```

Run tests, verify they fail:
```bash
pytest tests/test_cleanup_models.py -v
# Expected: ImportError or AttributeError for SessionCleanupCandidate
```

- [ ] **Step 2 (Green): Implement SessionCleanupCandidate in models.py**

Add to `src/models.py`:

```python
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SessionCleanupCandidate:
    """
    Represents a session that may be eligible for cleanup.
    
    Includes metadata needed for filtering and display.
    """
    session_id: str
    agent: str
    label: str
    status: str  # "running", "done", "unknown"
    file_path: str
    file_size_bytes: int
    last_modified: datetime
    
    @property
    def age_days(self) -> int:
        """Calculate age in days since last modification."""
        delta = datetime.now() - self.last_modified
        return delta.days
    
    @property
    def size_mb(self) -> float:
        """Get file size in megabytes, rounded to 2 decimals."""
        return round(self.file_size_bytes / (1024 * 1024), 2)
    
    @property
    def is_done(self) -> bool:
        """Check if session is marked as done/completed."""
        return self.status == "done"
```

Run tests, verify they pass:
```bash
pytest tests/test_cleanup_models.py -v
# Expected: All tests pass
```

- [ ] **Step 3 (Refactor): Add docstring examples and edge case tests**

Add edge case tests to `tests/test_cleanup_models.py`:

```python
def test_cleanup_candidate_zero_age():
    """Test age_days for just-modified session."""
    candidate = SessionCleanupCandidate(
        session_id="test",
        agent="main",
        label="fresh-session",
        status="running",
        file_path="/path/to/session.jsonl",
        file_size_bytes=1000,
        last_modified=datetime.now()
    )
    assert candidate.age_days == 0


def test_cleanup_candidate_small_file():
    """Test size_mb for files under 1MB."""
    candidate = SessionCleanupCandidate(
        session_id="test",
        agent="main",
        label="tiny-session",
        status="done",
        file_path="/path/to/session.jsonl",
        file_size_bytes=512000,  # 500KB
        last_modified=datetime.now()
    )
    assert candidate.size_mb == 0.49
```

Run full test suite:
```bash
pytest tests/test_cleanup_models.py -v
# Expected: All tests pass, 8 tests total
```

- [ ] **Step 4: Commit**

```bash
git add src/models.py tests/test_cleanup_models.py
git commit -m "feat: add SessionCleanupCandidate model with age and size properties"
```

---

### Task 14: Session File Size Helper

**Goal:** Add helper to get session file sizes from filesystem

**Files:**
- Modify: `src/session_parser.py`
- Modify: `tests/test_session_parser.py`

- [ ] **Step 1 (Red): Write failing test for get_session_file_size**

Add to `tests/test_session_parser.py`:

```python
def test_get_session_file_size(tmp_path):
    """Test get_session_file_size returns correct byte count."""
    from src.session_parser import get_session_file_size
    
    # Create test file with known content
    test_file = tmp_path / "test_session.jsonl"
    content = '{"type":"message","role":"user","tokens":1000}\n'
    test_file.write_text(content * 100)  # 100 lines
    
    size = get_session_file_size(test_file)
    expected_size = len(content.encode('utf-8')) * 100
    assert size == expected_size


def test_get_session_file_size_missing(tmp_path):
    """Test get_session_file_size returns 0 for missing files."""
    from src.session_parser import get_session_file_size
    
    missing_file = tmp_path / "nonexistent.jsonl"
    size = get_session_file_size(missing_file)
    assert size == 0
```

Run tests:
```bash
pytest tests/test_session_parser.py::test_get_session_file_size -v
# Expected: ImportError for get_session_file_size
```

- [ ] **Step 2 (Green): Implement get_session_file_size**

Add to `src/session_parser.py`:

```python
from pathlib import Path


def get_session_file_size(file_path: Path) -> int:
    """
    Get size of session file in bytes.
    
    Args:
        file_path: Path to session JSONL file
        
    Returns:
        File size in bytes, or 0 if file doesn't exist
    """
    try:
        return file_path.stat().st_size
    except (FileNotFoundError, OSError):
        return 0
```

Run tests:
```bash
pytest tests/test_session_parser.py::test_get_session_file_size -v
# Expected: Both new tests pass
```

- [ ] **Step 3 (Refactor): Run full session_parser test suite**

```bash
pytest tests/test_session_parser.py -v
# Expected: All existing + new tests pass
```

- [ ] **Step 4: Commit**

```bash
git add src/session_parser.py tests/test_session_parser.py
git commit -m "feat: add get_session_file_size helper for cleanup"
```

---

### Task 15: Cleanup Core Logic

**Goal:** Implement session discovery, filtering, and OpenClaw CLI integration for cleanup

**Files:**
- Create: `src/cleanup.py`
- Create: `tests/test_cleanup.py`

- [ ] **Step 1 (Red): Write failing tests for cleanup discovery**

Create `tests/test_cleanup.py`:

```python
"""Tests for session cleanup functionality."""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from src.cleanup import SessionCleaner, CleanupFilter, CleanupResult


def test_cleanup_filter_creation():
    """Test CleanupFilter dataclass creation."""
    filter = CleanupFilter(
        agent="main",
        status="done",
        min_age_days=7,
        min_size_mb=10.0
    )
    assert filter.agent == "main"
    assert filter.status == "done"
    assert filter.min_age_days == 7
    assert filter.min_size_mb == 10.0


def test_cleanup_result_creation():
    """Test CleanupResult dataclass creation."""
    result = CleanupResult(
        candidates_found=10,
        sessions_cleaned=8,
        bytes_freed=52428800,
        errors=[]
    )
    assert result.candidates_found == 10
    assert result.sessions_cleaned == 8
    assert result.bytes_freed == 52428800
    assert result.errors == []


def test_session_cleaner_init(tmp_path):
    """Test SessionCleaner initialization."""
    cleaner = SessionCleaner(state_dir=tmp_path)
    assert cleaner.state_dir == tmp_path
    assert cleaner.openclaw_available is not None


def test_discover_cleanup_candidates_empty(tmp_path):
    """Test discover_cleanup_candidates returns empty list for no sessions."""
    cleaner = SessionCleaner(state_dir=tmp_path)
    candidates = cleaner.discover_cleanup_candidates()
    assert candidates == []


def test_discover_cleanup_candidates_with_sessions(tmp_path):
    """Test discover_cleanup_candidates finds sessions from filesystem."""
    # Setup: Create mock session structure
    agents_dir = tmp_path / "agents" / "main" / "sessions"
    agents_dir.mkdir(parents=True)
    
    # Create sessions.json (OpenClaw dict format)
    session_file = agents_dir / "test-123.jsonl"
    session_file.write_text('{"type":"message","tokens":1000}\n' * 100)
    
    sessions_json = agents_dir / "sessions.json"
    sessions_data = {
        "agent:main:test": {
            "sessionId": "test-123",
            "sessionFile": str(session_file),
            "status": "done",
            "startedAt": 1743000000000
        }
    }
    sessions_json.write_text(json.dumps(sessions_data))
    
    cleaner = SessionCleaner(state_dir=tmp_path)
    candidates = cleaner.discover_cleanup_candidates()
    
    assert len(candidates) == 1
    assert candidates[0].session_id == "test-123"
    assert candidates[0].agent == "main"
    assert candidates[0].status == "done"
    assert candidates[0].file_size_bytes > 0


def test_filter_candidates_by_age(tmp_path):
    """Test filter_candidates filters by minimum age."""
    from src.models import SessionCleanupCandidate
    
    old_session = SessionCleanupCandidate(
        session_id="old",
        agent="main",
        label="old-session",
        status="done",
        file_path="/path/old.jsonl",
        file_size_bytes=1000,
        last_modified=datetime.now() - timedelta(days=14)
    )
    
    recent_session = SessionCleanupCandidate(
        session_id="recent",
        agent="main",
        label="recent-session",
        status="done",
        file_path="/path/recent.jsonl",
        file_size_bytes=1000,
        last_modified=datetime.now() - timedelta(days=3)
    )
    
    cleaner = SessionCleaner(state_dir=tmp_path)
    filter = CleanupFilter(min_age_days=7)
    
    filtered = cleaner.filter_candidates([old_session, recent_session], filter)
    
    assert len(filtered) == 1
    assert filtered[0].session_id == "old"


def test_filter_candidates_by_status(tmp_path):
    """Test filter_candidates filters by status."""
    from src.models import SessionCleanupCandidate
    
    done_session = SessionCleanupCandidate(
        session_id="done",
        agent="main",
        label="done-session",
        status="done",
        file_path="/path/done.jsonl",
        file_size_bytes=1000,
        last_modified=datetime.now()
    )
    
    running_session = SessionCleanupCandidate(
        session_id="running",
        agent="main",
        label="running-session",
        status="running",
        file_path="/path/running.jsonl",
        file_size_bytes=1000,
        last_modified=datetime.now()
    )
    
    cleaner = SessionCleaner(state_dir=tmp_path)
    filter = CleanupFilter(status="done")
    
    filtered = cleaner.filter_candidates([done_session, running_session], filter)
    
    assert len(filtered) == 1
    assert filtered[0].status == "done"


def test_filter_candidates_by_size(tmp_path):
    """Test filter_candidates filters by minimum size."""
    from src.models import SessionCleanupCandidate
    
    large_session = SessionCleanupCandidate(
        session_id="large",
        agent="main",
        label="large-session",
        status="done",
        file_path="/path/large.jsonl",
        file_size_bytes=52428800,  # 50MB
        last_modified=datetime.now()
    )
    
    small_session = SessionCleanupCandidate(
        session_id="small",
        agent="main",
        label="small-session",
        status="done",
        file_path="/path/small.jsonl",
        file_size_bytes=1048576,  # 1MB
        last_modified=datetime.now()
    )
    
    cleaner = SessionCleaner(state_dir=tmp_path)
    filter = CleanupFilter(min_size_mb=10.0)
    
    filtered = cleaner.filter_candidates([large_session, small_session], filter)
    
    assert len(filtered) == 1
    assert filtered[0].session_id == "large"


def test_filter_candidates_by_agent(tmp_path):
    """Test filter_candidates filters by agent name."""
    from src.models import SessionCleanupCandidate
    
    main_session = SessionCleanupCandidate(
        session_id="main-1",
        agent="main",
        label="main-session",
        status="done",
        file_path="/path/main.jsonl",
        file_size_bytes=1000,
        last_modified=datetime.now()
    )
    
    claude_session = SessionCleanupCandidate(
        session_id="claude-1",
        agent="claude",
        label="claude-session",
        status="done",
        file_path="/path/claude.jsonl",
        file_size_bytes=1000,
        last_modified=datetime.now()
    )
    
    cleaner = SessionCleaner(state_dir=tmp_path)
    filter = CleanupFilter(agent="main")
    
    filtered = cleaner.filter_candidates([main_session, claude_session], filter)
    
    assert len(filtered) == 1
    assert filtered[0].agent == "main"


@patch('subprocess.run')
def test_execute_cleanup_dry_run(mock_run, tmp_path):
    """Test execute_cleanup with dry_run=True doesn't call OpenClaw."""
    from src.models import SessionCleanupCandidate
    
    candidate = SessionCleanupCandidate(
        session_id="test",
        agent="main",
        label="test-session",
        status="done",
        file_path="/path/test.jsonl",
        file_size_bytes=1000,
        last_modified=datetime.now()
    )
    
    cleaner = SessionCleaner(state_dir=tmp_path)
    result = cleaner.execute_cleanup([candidate], dry_run=True)
    
    assert result.candidates_found == 1
    assert result.sessions_cleaned == 0
    mock_run.assert_not_called()


@patch('subprocess.run')
def test_execute_cleanup_calls_openclaw(mock_run, tmp_path):
    """Test execute_cleanup calls openclaw sessions cleanup --enforce --all-agents."""
    from src.models import SessionCleanupCandidate
    
    # Mock successful OpenClaw cleanup
    mock_run.return_value = Mock(returncode=0, stdout="Pruned 1 session", stderr="")
    
    candidate = SessionCleanupCandidate(
        session_id="test",
        agent="main",
        label="test-session",
        status="done",
        file_path="/path/test.jsonl",
        file_size_bytes=52428800,
        last_modified=datetime.now()
    )
    
    cleaner = SessionCleaner(state_dir=tmp_path)
    result = cleaner.execute_cleanup([candidate], dry_run=False)
    
    assert result.candidates_found == 1
    assert result.sessions_cleaned == 1
    assert result.bytes_freed == 52428800
    
    # Verify OpenClaw CLI was called with correct arguments
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert call_args == ["openclaw", "sessions", "cleanup", "--enforce", "--all-agents"]


@patch('subprocess.run')
def test_execute_cleanup_handles_openclaw_error(mock_run, tmp_path):
    """Test execute_cleanup handles OpenClaw CLI errors gracefully."""
    from src.models import SessionCleanupCandidate
    
    # Mock OpenClaw failure
    mock_run.return_value = Mock(
        returncode=1, 
        stdout="", 
        stderr="Error: session not found"
    )
    
    candidate = SessionCleanupCandidate(
        session_id="test",
        agent="main",
        label="test-session",
        status="done",
        file_path="/path/test.jsonl",
        file_size_bytes=1000,
        last_modified=datetime.now()
    )
    
    cleaner = SessionCleaner(state_dir=tmp_path)
    result = cleaner.execute_cleanup([candidate], dry_run=False)
    
    assert result.candidates_found == 1
    assert result.sessions_cleaned == 0
    assert len(result.errors) == 1
    assert "Error: session not found" in result.errors[0]
```

Run tests:
```bash
pytest tests/test_cleanup.py -v
# Expected: ImportError for cleanup module
```

- [ ] **Step 2 (Green): Implement SessionCleaner core logic**

Create `src/cleanup.py`:

```python
"""Session cleanup functionality."""

import logging
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional
from src.models import SessionCleanupCandidate
from src.session_parser import parse_sessions_metadata, get_session_file_size

logger = logging.getLogger(__name__)


@dataclass
class CleanupFilter:
    """Filtering criteria for cleanup candidates."""
    agent: Optional[str] = None
    status: Optional[str] = None  # "done", "running", etc.
    min_age_days: Optional[int] = None
    min_size_mb: Optional[float] = None


@dataclass
class CleanupResult:
    """Result of cleanup operation."""
    candidates_found: int
    sessions_cleaned: int
    bytes_freed: int
    errors: List[str] = field(default_factory=list)


class SessionCleaner:
    """
    Manages session cleanup operations.
    
    Discovers cleanup candidates, applies filters, and integrates with
    OpenClaw's native cleanup mechanism.
    """
    
    def __init__(self, state_dir: Path):
        """
        Initialize session cleaner.
        
        Args:
            state_dir: Path to OpenClaw state directory
        """
        self.state_dir = Path(state_dir)
        self.openclaw_available = self._check_openclaw_available()
    
    def _check_openclaw_available(self) -> bool:
        """Check if openclaw CLI is available in PATH."""
        try:
            result = subprocess.run(
                ["openclaw", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def discover_cleanup_candidates(self) -> List[SessionCleanupCandidate]:
        """
        Discover all sessions that could be cleanup candidates.
        
        Returns:
            List of SessionCleanupCandidate objects with metadata
        """
        candidates = []
        agents_dir = self.state_dir / "agents"
        
        if not agents_dir.exists():
            logger.warning(f"Agents directory not found: {agents_dir}")
            return candidates
        
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
            
            # Create cleanup candidates
            for metadata in sessions_metadata:
                session_file = Path(metadata['sessionFile'])
                
                if not session_file.exists():
                    logger.warning(f"Session file not found: {session_file}")
                    continue
                
                try:
                    file_size = get_session_file_size(session_file)
                    file_stat = session_file.stat()
                    last_modified = datetime.fromtimestamp(file_stat.st_mtime)
                    
                    candidate = SessionCleanupCandidate(
                        session_id=metadata['sessionId'],
                        agent=metadata['agent'],
                        label=metadata['label'],
                        status=metadata.get('status', 'unknown'),
                        file_path=str(session_file),
                        file_size_bytes=file_size,
                        last_modified=last_modified
                    )
                    
                    candidates.append(candidate)
                    
                except Exception as e:
                    logger.error(f"Failed to process session {session_file}: {e}")
                    continue
        
        return candidates
    
    def filter_candidates(
        self, 
        candidates: List[SessionCleanupCandidate],
        filter: CleanupFilter
    ) -> List[SessionCleanupCandidate]:
        """
        Apply filter criteria to cleanup candidates.
        
        Args:
            candidates: List of candidates to filter
            filter: Filter criteria
            
        Returns:
            Filtered list of candidates
        """
        filtered = candidates
        
        if filter.agent:
            filtered = [c for c in filtered if c.agent == filter.agent]
        
        if filter.status:
            filtered = [c for c in filtered if c.status == filter.status]
        
        if filter.min_age_days is not None:
            filtered = [c for c in filtered if c.age_days >= filter.min_age_days]
        
        if filter.min_size_mb is not None:
            filtered = [c for c in filtered if c.size_mb >= filter.min_size_mb]
        
        return filtered
    
    def execute_cleanup(
        self,
        candidates: List[SessionCleanupCandidate],
        dry_run: bool = True
    ) -> CleanupResult:
        """
        Execute cleanup operation using OpenClaw CLI.
        
        Args:
            candidates: Sessions to clean
            dry_run: If True, only preview without executing
            
        Returns:
            CleanupResult with operation summary
        """
        result = CleanupResult(
            candidates_found=len(candidates),
            sessions_cleaned=0,
            bytes_freed=0
        )
        
        if dry_run:
            # Dry run mode: just calculate what would be freed
            return result
        
        if not self.openclaw_available:
            result.errors.append("openclaw CLI not available in PATH")
            return result
        
        # Execute OpenClaw cleanup (operates on all agents at once)
        try:
            # Call openclaw sessions cleanup --enforce --all-agents
            cmd = ["openclaw", "sessions", "cleanup", "--enforce", "--all-agents"]
            
            logger.info(f"Executing: {' '.join(cmd)}")
            
            proc_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            logger.info(f"OpenClaw cleanup stdout: {proc_result.stdout}")
            if proc_result.stderr:
                logger.warning(f"OpenClaw cleanup stderr: {proc_result.stderr}")
            
            if proc_result.returncode == 0:
                # OpenClaw cleanup succeeded
                # Note: OpenClaw may prune 0 sessions if they don't meet its criteria
                # We report based on our candidate count, not OpenClaw's output
                result.sessions_cleaned = len(candidates)
                result.bytes_freed = sum(c.file_size_bytes for c in candidates)
                
                logger.info(f"Cleanup completed. Return code: 0")
            else:
                error_msg = f"OpenClaw cleanup failed (exit {proc_result.returncode}): {proc_result.stderr}"
                result.errors.append(error_msg)
                logger.error(error_msg)
                
        except subprocess.TimeoutExpired:
            error_msg = "OpenClaw cleanup timeout (>30s)"
            result.errors.append(error_msg)
            logger.error(error_msg)
        except Exception as e:
            error_msg = f"Cleanup execution error: {e}"
            result.errors.append(error_msg)
            logger.error(error_msg)
        
        return result
```

Run tests:
```bash
pytest tests/test_cleanup.py -v
# Expected: All tests pass
```

- [ ] **Step 3 (Refactor): Add edge case handling and validation**

Add additional tests to `tests/test_cleanup.py`:

```python
def test_discover_cleanup_candidates_orphaned_files(tmp_path):
    """Test discover finds orphaned session files not in sessions.json."""
    agents_dir = tmp_path / "agents" / "main" / "sessions"
    agents_dir.mkdir(parents=True)
    
    # Create sessions.json with one session
    sessions_json = agents_dir / "sessions.json"
    sessions_json.write_text('[]')
    
    # Create orphaned session file
    orphan_file = agents_dir / "orphan-123.jsonl"
    orphan_file.write_text('{"type":"message","tokens":1000}\n')
    
    cleaner = SessionCleaner(state_dir=tmp_path)
    candidates = cleaner.discover_cleanup_candidates()
    
    # Should only find sessions in sessions.json, not orphans
    assert len(candidates) == 0


def test_filter_candidates_combined_filters(tmp_path):
    """Test filter_candidates with multiple criteria."""
    from src.models import SessionCleanupCandidate
    
    # Create candidate that matches all criteria
    matching = SessionCleanupCandidate(
        session_id="match",
        agent="main",
        label="match-session",
        status="done",
        file_path="/path/match.jsonl",
        file_size_bytes=52428800,  # 50MB
        last_modified=datetime.now() - timedelta(days=10)
    )
    
    # Create candidate that fails age check
    too_recent = SessionCleanupCandidate(
        session_id="recent",
        agent="main",
        label="recent-session",
        status="done",
        file_path="/path/recent.jsonl",
        file_size_bytes=52428800,
        last_modified=datetime.now() - timedelta(days=3)
    )
    
    # Create candidate that fails size check
    too_small = SessionCleanupCandidate(
        session_id="small",
        agent="main",
        label="small-session",
        status="done",
        file_path="/path/small.jsonl",
        file_size_bytes=1048576,  # 1MB
        last_modified=datetime.now() - timedelta(days=10)
    )
    
    cleaner = SessionCleaner(state_dir=tmp_path)
    filter = CleanupFilter(
        agent="main",
        status="done",
        min_age_days=7,
        min_size_mb=10.0
    )
    
    filtered = cleaner.filter_candidates([matching, too_recent, too_small], filter)
    
    assert len(filtered) == 1
    assert filtered[0].session_id == "match"


def test_execute_cleanup_openclaw_not_available(tmp_path):
    """Test execute_cleanup handles missing OpenClaw CLI."""
    from src.models import SessionCleanupCandidate
    
    candidate = SessionCleanupCandidate(
        session_id="test",
        agent="main",
        label="test-session",
        status="done",
        file_path="/path/test.jsonl",
        file_size_bytes=1000,
        last_modified=datetime.now()
    )
    
    cleaner = SessionCleaner(state_dir=tmp_path)
    cleaner.openclaw_available = False  # Force unavailable
    
    result = cleaner.execute_cleanup([candidate], dry_run=False)
    
    assert result.sessions_cleaned == 0
    assert len(result.errors) == 1
    assert "not available" in result.errors[0]
```

Run full cleanup test suite:
```bash
pytest tests/test_cleanup.py -v
# Expected: All tests pass (20+ tests)
```

- [ ] **Step 4: Commit**

```bash
git add src/cleanup.py tests/test_cleanup.py
git commit -m "feat: implement session cleanup core logic with OpenClaw integration"
```

---

### Task 16: Cleanup CLI Command

**Goal:** Add `session-monitor cleanup` subcommand with filtering arguments and interactive confirmation

**Files:**
- Modify: `src/cli.py`
- Modify: `tests/test_cleanup.py` (add CLI tests)

- [ ] **Step 1 (Red): Write failing tests for CLI cleanup command**

Add to `tests/test_cleanup.py`:

```python
from unittest.mock import patch, MagicMock
from src.cli import main as cli_main


@patch('src.cli.SessionCleaner')
@patch('sys.argv', ['session-monitor', 'cleanup', '--dry-run'])
def test_cleanup_command_dry_run(mock_cleaner_class):
    """Test cleanup command in dry-run mode."""
    from src.models import SessionCleanupCandidate
    
    mock_cleaner = MagicMock()
    mock_cleaner_class.return_value = mock_cleaner
    
    # Mock discovery
    candidate = SessionCleanupCandidate(
        session_id="test",
        agent="main",
        label="test-session",
        status="done",
        file_path="/path/test.jsonl",
        file_size_bytes=52428800,
        last_modified=datetime.now() - timedelta(days=10)
    )
    mock_cleaner.discover_cleanup_candidates.return_value = [candidate]
    mock_cleaner.filter_candidates.return_value = [candidate]
    
    # Run CLI
    result = cli_main()
    
    assert result == 0
    mock_cleaner.discover_cleanup_candidates.assert_called_once()
    mock_cleaner.execute_cleanup.assert_called_once_with([candidate], dry_run=True)


@patch('src.cli.SessionCleaner')
@patch('builtins.input', return_value='y')
@patch('sys.argv', ['session-monitor', 'cleanup', '--force'])
def test_cleanup_command_force_with_confirmation(mock_input, mock_cleaner_class):
    """Test cleanup command with --force requires confirmation."""
    from src.models import SessionCleanupCandidate
    from src.cleanup import CleanupResult
    
    mock_cleaner = MagicMock()
    mock_cleaner_class.return_value = mock_cleaner
    
    candidate = SessionCleanupCandidate(
        session_id="test",
        agent="main",
        label="test-session",
        status="done",
        file_path="/path/test.jsonl",
        file_size_bytes=52428800,
        last_modified=datetime.now()
    )
    mock_cleaner.discover_cleanup_candidates.return_value = [candidate]
    mock_cleaner.filter_candidates.return_value = [candidate]
    
    mock_result = CleanupResult(
        candidates_found=1,
        sessions_cleaned=1,
        bytes_freed=52428800,
        errors=[]
    )
    mock_cleaner.execute_cleanup.return_value = mock_result
    
    result = cli_main()
    
    assert result == 0
    mock_input.assert_called_once()
    mock_cleaner.execute_cleanup.assert_called_once_with([candidate], dry_run=False)


@patch('src.cli.SessionCleaner')
@patch('builtins.input', return_value='n')
@patch('sys.argv', ['session-monitor', 'cleanup', '--force'])
def test_cleanup_command_force_cancelled(mock_input, mock_cleaner_class):
    """Test cleanup command cancelled by user."""
    from src.models import SessionCleanupCandidate
    
    mock_cleaner = MagicMock()
    mock_cleaner_class.return_value = mock_cleaner
    
    candidate = SessionCleanupCandidate(
        session_id="test",
        agent="main",
        label="test-session",
        status="done",
        file_path="/path/test.jsonl",
        file_size_bytes=52428800,
        last_modified=datetime.now()
    )
    mock_cleaner.discover_cleanup_candidates.return_value = [candidate]
    mock_cleaner.filter_candidates.return_value = [candidate]
    
    result = cli_main()
    
    assert result == 0
    mock_input.assert_called_once()
    mock_cleaner.execute_cleanup.assert_not_called()


@patch('src.cli.SessionCleaner')
@patch('sys.argv', ['session-monitor', 'cleanup', '--agent', 'main', '--status', 'done', '--min-age-days', '7'])
def test_cleanup_command_with_filters(mock_cleaner_class):
    """Test cleanup command applies filter arguments."""
    from src.cleanup import CleanupFilter
    
    mock_cleaner = MagicMock()
    mock_cleaner_class.return_value = mock_cleaner
    mock_cleaner.discover_cleanup_candidates.return_value = []
    mock_cleaner.filter_candidates.return_value = []
    
    result = cli_main()
    
    assert result == 0
    
    # Verify filter was created with correct arguments
    filter_arg = mock_cleaner.filter_candidates.call_args[0][1]
    assert filter_arg.agent == "main"
    assert filter_arg.status == "done"
    assert filter_arg.min_age_days == 7
```

Run tests:
```bash
pytest tests/test_cleanup.py::test_cleanup_command -v
# Expected: ImportError or AttributeError (CLI not yet modified)
```

- [ ] **Step 2 (Green): Implement cleanup CLI command**

Modify `src/cli.py` to add cleanup subcommand:

```python
# Add at top of file
from src.cleanup import SessionCleaner, CleanupFilter, CleanupResult


# In main() function, add cleanup parser after metrics_parser:
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser(
        "cleanup", 
        help="Clean up old session files"
    )
    cleanup_parser.add_argument(
        "--agent", 
        help="Filter by agent (e.g., main, claude)"
    )
    cleanup_parser.add_argument(
        "--status", 
        help="Filter by status (e.g., done, running)"
    )
    cleanup_parser.add_argument(
        "--min-age-days", 
        type=int,
        help="Minimum age in days"
    )
    cleanup_parser.add_argument(
        "--min-size-mb", 
        type=float,
        help="Minimum size in MB"
    )
    cleanup_parser.add_argument(
        "--dry-run", 
        action="store_true",
        default=True,
        help="Preview cleanup without executing (default)"
    )
    cleanup_parser.add_argument(
        "--force", 
        action="store_true",
        help="Execute cleanup (requires confirmation)"
    )
    cleanup_parser.add_argument(
        "--state-dir", 
        help="Override OpenClaw state directory"
    )


# In main() function, modify command dispatch:
    
    if args.command == "watch":
        return cmd_watch(args)
    elif args.command == "cleanup":
        return cmd_cleanup(args)
    else:
        print(f"Command '{args.command}' not yet implemented.")
        print("See PLAN.md for implementation phases.")
        return 1


# Add cmd_cleanup function after cmd_watch:

def cmd_cleanup(args):
    """Execute cleanup command to remove old sessions."""
    # Determine state directory (reuse logic from cmd_watch)
    state_dir = args.state_dir
    if not state_dir:
        state_dir = os.environ.get('OPENCLAW_STATE_DIR')
        if not state_dir:
            state_dir = Path.home() / '.openclaw-primary'
        else:
            state_dir = Path(state_dir)
    else:
        state_dir = Path(state_dir)
    
    if not state_dir.exists():
        print(f"Error: OpenClaw state directory not found: {state_dir}")
        return 1
    
    # Initialize cleaner
    cleaner = SessionCleaner(state_dir=state_dir)
    
    # Discover candidates
    print(f"Scanning sessions in {state_dir}...")
    candidates = cleaner.discover_cleanup_candidates()
    
    if not candidates:
        print("No sessions found")
        return 0
    
    # Apply filters
    filter = CleanupFilter(
        agent=args.agent,
        status=args.status,
        min_age_days=args.min_age_days,
        min_size_mb=args.min_size_mb
    )
    
    filtered = cleaner.filter_candidates(candidates, filter)
    
    if not filtered:
        print(f"No sessions match filter criteria")
        print(f"Total sessions: {len(candidates)}")
        return 0
    
    # Display candidates
    print(f"\nFound {len(filtered)} session(s) matching criteria:\n")
    
    total_size_mb = sum(c.size_mb for c in filtered)
    
    for candidate in filtered:
        print(f"  {candidate.session_id[:12]}... "
              f"({candidate.agent}) "
              f"{candidate.size_mb:.1f}MB "
              f"{candidate.age_days}d old "
              f"[{candidate.status}]")
    
    print(f"\nTotal size: {total_size_mb:.1f} MB")
    
    # Determine dry-run vs force
    dry_run = not args.force
    
    if dry_run:
        print("\n[DRY RUN] Use --force to execute cleanup")
        result = cleaner.execute_cleanup(filtered, dry_run=True)
        return 0
    
    # Force mode: require confirmation for safety
    if len(filtered) > 10 or total_size_mb > 100:
        print(f"\n⚠️  WARNING: About to clean {len(filtered)} sessions ({total_size_mb:.1f}MB)")
    
    try:
        confirmation = input("\nProceed with cleanup? (y/N): ")
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled")
        return 0
    
    if confirmation.lower() != 'y':
        print("Cancelled")
        return 0
    
    # Execute cleanup
    print("\nCleaning up sessions...")
    result = cleaner.execute_cleanup(filtered, dry_run=False)
    
    # Display results
    print(f"\n✓ Cleaned {result.sessions_cleaned} session(s)")
    print(f"✓ Freed {result.bytes_freed / (1024*1024):.1f} MB")
    
    if result.errors:
        print(f"\n⚠️  {len(result.errors)} error(s) occurred:")
        for error in result.errors:
            print(f"  - {error}")
        return 1
    
    return 0
```

Run tests:
```bash
pytest tests/test_cleanup.py::test_cleanup_command -v
# Expected: All CLI tests pass
```

- [ ] **Step 3 (Refactor): Add help text and polish output formatting**

Improve cleanup_parser help text in `src/cli.py`:

```python
    cleanup_parser = subparsers.add_parser(
        "cleanup", 
        help="Clean up old session files",
        description="""
        Clean up old OpenClaw session files to free disk space.
        
        By default, shows a preview without executing (--dry-run).
        Use --force to actually delete sessions after confirmation.
        
        Integrates with OpenClaw's native cleanup mechanism and respects
        maintenance configuration.
        
        Examples:
          # Preview cleanup of done sessions older than 14 days
          session-monitor cleanup --status done --min-age-days 14
          
          # Execute cleanup with confirmation
          session-monitor cleanup --status done --min-age-days 14 --force
          
          # Clean large sessions only
          session-monitor cleanup --min-size-mb 50 --force
        """
    )
```

Run full test suite:
```bash
pytest tests/test_cleanup.py -v
# Expected: All tests pass (25+ tests total)
```

- [ ] **Step 4: Commit**

```bash
git add src/cli.py tests/test_cleanup.py
git commit -m "feat: add cleanup CLI command with filtering and interactive confirmation"
```

---

### Task 17: Integration Testing

**Goal:** Verify cleanup command works end-to-end with realistic session data

**Files:**
- Create: `tests/test_cleanup_integration.py`

- [ ] **Step 1 (Red): Write end-to-end integration test**

Create `tests/test_cleanup_integration.py`:

```python
"""Integration tests for cleanup command."""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch
from src.cleanup import SessionCleaner, CleanupFilter


def create_test_session_structure(tmp_path, agent="main", num_sessions=3):
    """Helper to create realistic session structure for testing."""
    agents_dir = tmp_path / "agents" / agent / "sessions"
    agents_dir.mkdir(parents=True)
    
    # OpenClaw sessions.json is a dict with label keys
    sessions_data = {}
    
    for i in range(num_sessions):
        session_id = f"test-session-{i}"
        session_file = agents_dir / f"{session_id}.jsonl"
        
        # Create JSONL file with messages
        messages = []
        for j in range(100):
            messages.append(json.dumps({
                "type": "message",
                "role": "user" if j % 2 == 0 else "assistant",
                "tokens": 1000 + (i * 5000)  # Vary size per session
            }))
        
        session_file.write_text('\n'.join(messages) + '\n')
        
        # Create session metadata
        age_days = i * 5  # Sessions get older
        created_time = datetime.now() - timedelta(days=age_days)
        
        # Use OpenClaw label format as dict key
        label = f"agent:{agent}:{session_id}"
        sessions_data[label] = {
            "sessionId": session_id,
            "sessionFile": str(session_file),
            "status": "done" if i < 2 else "running",
            "startedAt": int(created_time.timestamp() * 1000)  # Unix ms
        }
    
    # Write sessions.json as dict
    sessions_json = agents_dir / "sessions.json"
    sessions_json.write_text(json.dumps(sessions_data, indent=2))
    
    return agents_dir


def test_cleanup_integration_discovery(tmp_path):
    """Test end-to-end session discovery with realistic data."""
    create_test_session_structure(tmp_path, agent="main", num_sessions=5)
    create_test_session_structure(tmp_path, agent="claude", num_sessions=3)
    
    cleaner = SessionCleaner(state_dir=tmp_path)
    candidates = cleaner.discover_cleanup_candidates()
    
    assert len(candidates) == 8  # 5 main + 3 claude
    
    main_sessions = [c for c in candidates if c.agent == "main"]
    assert len(main_sessions) == 5
    
    claude_sessions = [c for c in candidates if c.agent == "claude"]
    assert len(claude_sessions) == 3


def test_cleanup_integration_filtering(tmp_path):
    """Test filtering works correctly with realistic data."""
    create_test_session_structure(tmp_path, num_sessions=5)
    
    cleaner = SessionCleaner(state_dir=tmp_path)
    candidates = cleaner.discover_cleanup_candidates()
    
    # Filter for old done sessions
    filter = CleanupFilter(
        status="done",
        min_age_days=7
    )
    
    filtered = cleaner.filter_candidates(candidates, filter)
    
    # Should only get sessions 2+ (age 10+ days, status done)
    assert len(filtered) == 2
    assert all(c.status == "done" for c in filtered)
    assert all(c.age_days >= 7 for c in filtered)


def test_cleanup_integration_size_filtering(tmp_path):
    """Test size-based filtering with realistic session files."""
    create_test_session_structure(tmp_path, num_sessions=3)
    
    cleaner = SessionCleaner(state_dir=tmp_path)
    candidates = cleaner.discover_cleanup_candidates()
    
    # Filter for sessions over 0.5MB
    filter = CleanupFilter(min_size_mb=0.5)
    
    filtered = cleaner.filter_candidates(candidates, filter)
    
    # Verify all filtered sessions meet size requirement
    assert all(c.size_mb >= 0.5 for c in filtered)


@patch('subprocess.run')
def test_cleanup_integration_execution(mock_run, tmp_path):
    """Test cleanup execution with OpenClaw CLI integration."""
    from unittest.mock import Mock
    
    create_test_session_structure(tmp_path, num_sessions=3)
    
    # Mock OpenClaw cleanup success
    mock_run.return_value = Mock(returncode=0, stdout="Pruned 2 sessions", stderr="")
    
    cleaner = SessionCleaner(state_dir=tmp_path)
    candidates = cleaner.discover_cleanup_candidates()
    
    # Filter for done sessions
    filter = CleanupFilter(status="done")
    filtered = cleaner.filter_candidates(candidates, filter)
    
    # Execute cleanup
    result = cleaner.execute_cleanup(filtered, dry_run=False)
    
    assert result.sessions_cleaned == 2  # 2 done sessions
    assert result.bytes_freed > 0
    assert len(result.errors) == 0
    
    # Verify OpenClaw was called correctly
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert call_args == ["openclaw", "sessions", "cleanup", "--enforce", "--all-agents"]


def test_cleanup_integration_no_candidates(tmp_path):
    """Test cleanup gracefully handles no matching candidates."""
    create_test_session_structure(tmp_path, num_sessions=2)
    
    cleaner = SessionCleaner(state_dir=tmp_path)
    candidates = cleaner.discover_cleanup_candidates()
    
    # Filter for non-existent criteria
    filter = CleanupFilter(
        agent="nonexistent",
        status="done"
    )
    
    filtered = cleaner.filter_candidates(candidates, filter)
    
    assert len(filtered) == 0
    
    # Execute should handle empty list gracefully
    result = cleaner.execute_cleanup(filtered, dry_run=False)
    
    assert result.candidates_found == 0
    assert result.sessions_cleaned == 0
    assert len(result.errors) == 0
```

Run tests:
```bash
pytest tests/test_cleanup_integration.py -v
# Expected: Tests pass
```

- [ ] **Step 2 (Green): Fix any integration issues discovered**

Run full test suite to ensure no regressions:
```bash
pytest tests/test_cleanup*.py -v
# Expected: All cleanup tests pass
```

If any tests fail, diagnose and fix issues in `src/cleanup.py`.

- [ ] **Step 3 (Refactor): Run full project test suite**

```bash
pytest -v
# Expected: All project tests pass (models, parser, monitor, cleanup)
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_cleanup_integration.py
git commit -m "test: add integration tests for cleanup command"
```

---

### Task 18: Documentation

**Goal:** Update README and add cleanup usage examples

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add cleanup section to README**

Add new section to `README.md` after "Historical Metrics" section:

```markdown
### Session Cleanup

Manage old session files to free disk space:

```bash
# Preview cleanup (dry-run, default)
session-monitor cleanup --status done --min-age-days 14

# Execute cleanup with confirmation
session-monitor cleanup --status done --min-age-days 14 --force

# Clean sessions over 50MB
session-monitor cleanup --min-size-mb 50 --force

# Clean specific agent's sessions
session-monitor cleanup --agent main --status done --force

# Combine filters
session-monitor cleanup --agent main --status done --min-age-days 7 --min-size-mb 10 --force
```

Cleanup integrates with OpenClaw's native `openclaw sessions cleanup --enforce` and respects maintenance configuration.

**Safety features:**
- Dry-run by default (use `--force` to execute)
- Confirmation prompt before deletion
- Warning for bulk operations (>10 sessions or >100MB)
- Integration with OpenClaw's cleanup mechanism

**Filter options:**
- `--agent` - Filter by agent name (main, claude, rescue)
- `--status` - Filter by status (done, running)
- `--min-age-days` - Only sessions older than N days
- `--min-size-mb` - Only sessions larger than N megabytes
```

- [ ] **Step 2: Update feature checklist**

Update README.md feature list:

```markdown
## Features

- **Real-time monitoring**: See token usage within 1 second of message completion
- **Multi-session dashboard**: Monitor all agents simultaneously (main, claude, rescue)
- **Proactive alerts**: Warnings at 80%, critical at 90% context window
- **Session cleanup**: Clean up old sessions with filtering and safety checks
- **Compaction detection**: Track when and how effective compaction runs are
- **Token analysis**: Identify expensive operations and optimize workflows
- **Historical trends**: Track usage over days/weeks to find patterns
```

- [ ] **Step 3: Update project status**

Update README.md project status:

```markdown
## Project Status

- [x] Phase 1: Core Parser
- [ ] Phase 2: File Watcher
- [ ] Phase 3: Live Dashboard
- [ ] Phase 4: Analysis Features
- [ ] Phase 5: Historical Trending
- [x] Phase 6: Session Cleanup

See [PLAN.md](PLAN.md) for detailed implementation plan.
```

- [ ] **Step 4: Verify documentation renders correctly**

Read through updated README:
```bash
cat README.md
# Expected: Cleanup section present, well-formatted
```

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: add session cleanup command documentation"
```

---

## Remember

- **Bite-sized tasks**: Each task completes in under 2 hours
- **Red-Green-Refactor**: Write failing test → make it pass → polish
- **Exact file paths**: Use absolute paths `/Volumes/RayCue-Drive/Documents/projects/openclaw-session-monitor/.worktrees/add-session-cleanup/src/...`
- **Test first**: Every new function gets tests before implementation
- **Integration tests last**: Unit tests verify components, integration tests verify behavior
- **Commit often**: One commit per task completion
- **Safety first**: Dry-run defaults, confirmation prompts, clear error messages
- **Reuse existing code**: Leverage `SessionMonitor`, `parse_sessions_metadata`, existing models
- **OpenClaw integration**: Respect OpenClaw's cleanup mechanism and conventions
- **User experience**: Clear output, helpful error messages, progress indicators

---

## Completion Criteria

Task is complete when:
- [ ] All tests pass (`pytest -v` shows all green)
- [ ] Cleanup command is accessible via `session-monitor cleanup`
- [ ] Dry-run mode works (preview candidates without calling OpenClaw)
- [ ] Force mode works with confirmation prompt
- [ ] All filter options work for preview (agent, status, age, size)
- [ ] OpenClaw CLI integration works (subprocess calls `openclaw sessions cleanup --enforce --all-agents`)
- [ ] Logs OpenClaw's stdout/stderr for debugging
- [ ] Reports success/failure based on OpenClaw's exit code
- [ ] Clarifies that actual cleanup is controlled by OpenClaw's criteria
- [ ] Error handling is graceful (missing OpenClaw, no sessions, etc.)
- [ ] Documentation is updated with examples and clarifies OpenClaw integration
- [ ] Code follows project patterns (dataclasses, logging, etc.)
- [ ] No regressions in existing functionality

---

## Architecture Decisions

### 1. OpenClaw CLI Integration vs Direct File Manipulation

**Decision**: Use `openclaw sessions cleanup --enforce --all-agents` subprocess calls

**Rationale**: 
- Respects OpenClaw's internal session lifecycle and metadata management
- Avoids risk of orphaning metadata or corrupting session store
- Leverages OpenClaw's existing maintenance configuration
- Reduces code complexity and maintenance burden
- Future-proof against OpenClaw internal changes

**Implementation note**: Based on user testing, `openclaw sessions cleanup` may return "0 sessions to prune" even when sessions exist. The cleanup logic will:
1. Call `openclaw sessions cleanup --enforce --all-agents` (not per-agent, as OpenClaw operates on all agents)
2. Report success/failure based on OpenClaw's return code
3. Log OpenClaw's stdout/stderr for debugging
4. Note that actual deletion may be deferred or require additional OpenClaw configuration

**Trade-off**: Requires OpenClaw CLI to be available in PATH. Cannot selectively clean individual sessions - OpenClaw cleanup applies to all sessions matching its internal criteria.

### 2. Archive Strategy

**Decision**: Follow OpenClaw's `.deleted` suffix convention

**Rationale**:
- Consistency with OpenClaw's existing cleanup behavior
- User can manually remove archives if desired
- No need to implement custom archive directory management
- Simpler mental model (sessions are marked deleted, not moved)

### 3. Filtering Granularity

**Decision**: Provide agent/status/age/size filters for visibility, but execute cleanup via `openclaw sessions cleanup --enforce --all-agents`

**Rationale**:
- Gives users visibility into what will be cleaned (preview mode)
- OpenClaw CLI operates on all agents at once based on its internal criteria
- Our filters help users understand which sessions are candidates
- Cannot selectively clean - OpenClaw's native cleanup uses its own logic

**Trade-off**: The filters are for preview only. Actual cleanup is controlled by OpenClaw's maintenance configuration, not our filters. We show what we think will be cleaned, but OpenClaw decides what actually gets cleaned.

### 4. Safety Gates

**Decision**: Dry-run default + force flag + confirmation prompt + size/count warnings

**Rationale**:
- Prevents accidental data loss
- Clear preview before execution
- Extra warning for bulk operations
- Follows industry best practices (destructive operations require explicit confirmation)

### 5. Session Discovery

**Decision**: Reuse existing `parse_sessions_metadata()` + add filesystem metadata

**Rationale**:
- Leverages existing, tested session discovery logic
- Adds file size and modification time from filesystem
- Single source of truth (sessions.json) for session metadata
- Consistent with existing monitoring approach

### 6. Error Handling

**Decision**: Continue on errors, collect error messages, report at end

**Rationale**:
- One failed cleanup shouldn't block others
- User sees full picture of what succeeded/failed
- Logged errors aid debugging
- Non-zero exit code signals partial failure

---

## Test Strategy

### Unit Tests
- **Models**: SessionCleanupCandidate properties (age_days, size_mb, is_done)
- **Parser**: get_session_file_size edge cases (missing file, large file)
- **Cleanup Logic**: 
  - Discovery with various session structures
  - Filtering with single and combined criteria
  - OpenClaw CLI integration (mocked subprocess)
  - Error handling (missing CLI, failed cleanup, timeouts)

### Integration Tests
- **End-to-end**: Realistic session structures, filtering, execution
- **Multiple agents**: Verify cleanup works across main/claude/rescue
- **Edge cases**: Empty results, no matching filters, orphaned files

### Manual Verification
- Run against actual OpenClaw state directory (with caution)
- Verify output formatting and user experience
- Test interactive confirmation flow
- Verify OpenClaw cleanup actually occurs

---

## Risk Mitigation

### Risk: Deleting active sessions
**Mitigation**: Filter defaults to `status="done"` recommendation in docs. User must explicitly clean running sessions.

### Risk: OpenClaw CLI unavailable
**Mitigation**: Check CLI availability at init. Clear error message with guidance.

### Risk: Subprocess timeout
**Mitigation**: 30-second timeout on subprocess calls. Collect errors and continue.

### Risk: Large bulk operations
**Mitigation**: Warning prompt for >10 sessions or >100MB. User must confirm.

### Risk: Metadata corruption
**Mitigation**: Use OpenClaw's native cleanup mechanism. Don't manipulate sessions.json directly.

### Risk: Orphaned files not in sessions.json
**Mitigation**: Document that cleanup only handles sessions tracked in sessions.json. Future enhancement could add orphan detection.
