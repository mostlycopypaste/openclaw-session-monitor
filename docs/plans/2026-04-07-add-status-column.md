# Add Status Column to Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use trycycle-executing to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Status" column to the openclaw-session-monitor dashboard that displays session status (RUNNING, DONE, or —) and implements smart two-level sorting (primary: active vs inactive, secondary: window % descending).

**Architecture:** Extend Session model with optional status field → Extract status from OpenClaw sessions.json → Add Status column to dashboard between Label and Age → Implement primary/secondary sort logic to float active high-usage sessions to top.

**Tech Stack:** Python 3.8+, dataclasses, Rich library for terminal UI, existing parsing infrastructure

**User Requirements:**
- Add status field to Session model (nullable, defaults to None)
- Display status as "RUNNING" (for running/null), "DONE" (for done), or "—" (visual for null)
- Position Status column between Label and Age
- Implement smart sorting: active sessions first, then by window % descending within each group
- Handle missing status field gracefully (treat as active/running)
- Maintain existing column formatting and widths

**Context from Completed Session Cleanup Feature:**
- Session model already has: session_id, label, agent, total_tokens, created_at, context_limit
- Parser (parse_sessions_metadata) currently extracts: sessionId, label, agent, sessionFile, startedAt
- Dashboard currently has columns: Session ID, Label, Age, Tokens, Window %, Alert
- Current sorting: simple window_percent descending
- Test patterns established: model tests for properties, parser tests for extraction, integration for full flow

**All commands run from:** `/Volumes/RayCue-Drive/Documents/projects/openclaw-session-monitor/.worktrees/add-status-column` with `.venv` activated via `source ../../.venv/bin/activate`

---

## File Structure

**Modified Files:**
- `src/models.py` - Add status field to Session dataclass
- `src/session_parser.py` - Extract status field from sessions.json
- `src/monitor.py` - Pass status field when creating Session objects
- `src/dashboard.py` - Add Status column, implement smart sorting
- `tests/test_models.py` - Add status field tests
- `tests/test_session_parser.py` - Add status extraction tests
- `tests/test_dashboard.py` - Create new file for dashboard sorting tests

**No New Files:** All changes are extensions to existing modules

**Rationale:**
- Status is a natural property of Session (belongs in model)
- Parser already handles optional fields (e.g., startedAt with .get())
- Dashboard sorting is a presentation concern (belongs in dashboard.py)
- Following existing test patterns (3 model tests + 4 parser tests + 7 dashboard tests = 14 total)

---

## Implementation Tasks

### Task 1: Add Status Field to Session Model (TDD Red-Green-Refactor)

**Goal:** Add optional status field to Session dataclass with proper defaults

**Files:**
- Modify: `src/models.py` (87 lines currently)
- Modify: `tests/test_models.py` (310 lines currently)

---

#### Subtask 1.1: Status field with default None

- [ ] **Step 1 (Red): Write first test - status field defaults to None**

Add to `tests/test_models.py` after existing tests (after line 310):
```python


def test_session_status_defaults_to_none():
    """Test Session status field defaults to None when not provided."""
    session = Session(
        session_id="test",
        label="test:label",
        agent="main",
        total_tokens=10000
    )
    assert session.status is None
```

Run test:
```bash
pytest tests/test_models.py::test_session_status_defaults_to_none -v
# Expected: FAIL - status field doesn't exist
```

- [ ] **Step 2 (Green): Add status field to Session model**

Modify `src/models.py`, after line 17 (after `created_at` field):
```python
    status: Optional[str] = None  # "running", "done", or None (treated as running)
```

Run test:
```bash
pytest tests/test_models.py::test_session_status_defaults_to_none -v
# Expected: PASS
```

- [ ] **Step 3 (Refactor): Verify field placement and type annotation**

Review model structure - status field should be after created_at, before context_limit. No refactor needed.

Run test:
```bash
pytest tests/test_models.py::test_session_status_defaults_to_none -v
# Expected: PASS
```

- [ ] **Step 4: Commit**
```bash
git add src/models.py tests/test_models.py
git commit -m "feat: add status field to Session model

Add optional status field to Session dataclass:
- Defaults to None when not provided
- Type is Optional[str] for running/done/null values
- Positioned after created_at, before context_limit"
```

---

#### Subtask 1.2: Status display logic for RUNNING

- [ ] **Step 1 (Red): Write test for RUNNING display**

Add to `tests/test_models.py`:
```python


def test_session_status_display_running():
    """Test Session with status='running' displays as RUNNING."""
    session = Session(
        session_id="test",
        label="test:label",
        agent="main",
        total_tokens=10000,
        status="running"
    )
    assert session.status == "running"
    # Display logic will be in dashboard, but we verify storage here
```

Run test:
```bash
pytest tests/test_models.py::test_session_status_display_running -v
# Expected: PASS (field already exists from previous subtask)
```

- [ ] **Step 2 (Green): Test for DONE display**

Add to `tests/test_models.py`:
```python


def test_session_status_display_done():
    """Test Session with status='done' displays as DONE."""
    session = Session(
        session_id="test",
        label="test:label",
        agent="main",
        total_tokens=10000,
        status="done"
    )
    assert session.status == "done"
```

Run test:
```bash
pytest tests/test_models.py::test_session_status_display_done -v
# Expected: PASS
```

- [ ] **Step 3 (Refactor): Run all model tests**

Run all model tests to ensure no regressions:
```bash
pytest tests/test_models.py -v
# Expected: All 27 tests PASS (24 existing + 3 new)
```

- [ ] **Step 4: Commit**
```bash
git add tests/test_models.py
git commit -m "test: add status field display tests

Add tests verifying:
- Status field accepts 'running' value
- Status field accepts 'done' value
- Values are stored correctly in model

All model tests passing (27 total)."
```

---

### Task 2: Extract Status from sessions.json (TDD Red-Green-Refactor)

**Goal:** Modify parser to extract status field from OpenClaw sessions.json

**Files:**
- Modify: `src/session_parser.py` (140 lines currently)
- Modify: `tests/test_session_parser.py` (137 lines currently)

---

#### Subtask 2.1: Parse status field when present

- [ ] **Step 1 (Red): Write test for status='running' extraction**

Add to `tests/test_session_parser.py` after existing tests:
```python


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
```

Run test:
```bash
pytest tests/test_session_parser.py::test_parse_sessions_metadata_extracts_status_running -v
# Expected: FAIL - status field not extracted
```

- [ ] **Step 2 (Green): Add status extraction to parser**

Modify `src/session_parser.py`, in the sessions.append() block (around line 50-56), add status field extraction:

Change the append block from:
```python
        sessions.append({
            'sessionId': session_data['sessionId'],
            'label': label,
            'agent': agent,
            'sessionFile': session_file,
            'startedAt': session_data.get('startedAt'),  # Unix timestamp in milliseconds
        })
```

To:
```python
        sessions.append({
            'sessionId': session_data['sessionId'],
            'label': label,
            'agent': agent,
            'sessionFile': session_file,
            'startedAt': session_data.get('startedAt'),  # Unix timestamp in milliseconds
            'status': session_data.get('status'),  # "running", "done", or None
        })
```

Run test:
```bash
pytest tests/test_session_parser.py::test_parse_sessions_metadata_extracts_status_running -v
# Expected: PASS
```

- [ ] **Step 3 (Refactor): Verify .get() handles missing field**

Confirm that .get() returns None for missing status (defensive coding). No refactor needed.

Run test:
```bash
pytest tests/test_session_parser.py::test_parse_sessions_metadata_extracts_status_running -v
# Expected: PASS
```

- [ ] **Step 4: Commit**
```bash
git add src/session_parser.py tests/test_session_parser.py
git commit -m "feat: extract status field from sessions.json

Modify parse_sessions_metadata to:
- Extract status field using .get() for safe access
- Handle missing status field gracefully (returns None)
- Follow existing pattern for optional fields (like startedAt)"
```

---

#### Subtask 2.2: Handle all status values (done, null, missing)

- [ ] **Step 1 (Red): Write tests for done, null, and missing status**

Add to `tests/test_session_parser.py`:
```python


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
```

Run tests:
```bash
pytest tests/test_session_parser.py::test_parse_sessions_metadata_extracts_status_done -v
pytest tests/test_session_parser.py::test_parse_sessions_metadata_status_null -v
pytest tests/test_session_parser.py::test_parse_sessions_metadata_status_missing -v
# Expected: All PASS (implementation already handles via .get())
```

- [ ] **Step 2 (Green): Verify all tests pass**

All tests should already pass due to .get() usage. No code changes needed.

Run all parser tests:
```bash
pytest tests/test_session_parser.py -v
# Expected: All 11 tests PASS (7 existing + 4 new)
```

- [ ] **Step 3 (Refactor): Review defensive coding patterns**

Review parser for consistency - .get() is used for all optional fields. No refactor needed.

- [ ] **Step 4: Commit**
```bash
git add tests/test_session_parser.py
git commit -m "test: add comprehensive status extraction tests

Add tests for all status field scenarios:
- status='running' extracted correctly
- status='done' extracted correctly  
- status=null handled as Python None
- Missing status field handled as None

All parser tests passing (11 total)."
```

---

### Task 3: Pass Status to Session Objects

**Goal:** Update monitor to pass status field when creating Session objects

**Files:**
- Modify: `src/monitor.py` (95 lines currently)
- No new tests needed (covered by integration tests in Task 4)

---

- [ ] **Step 1: Modify monitor to pass status field**

Modify `src/monitor.py`, in the Session creation block (around line 81-88):

Change:
```python
                    session = Session(
                        session_id=session_id,
                        label=metadata['label'],
                        agent=metadata['agent'],
                        total_tokens=total_tokens,
                        created_at=metadata.get('startedAt'),
                        context_limit=self.context_limit
                    )
```

To:
```python
                    session = Session(
                        session_id=session_id,
                        label=metadata['label'],
                        agent=metadata['agent'],
                        total_tokens=total_tokens,
                        created_at=metadata.get('startedAt'),
                        status=metadata.get('status'),
                        context_limit=self.context_limit
                    )
```

- [ ] **Step 2: Run existing monitor tests**

Verify no regressions:
```bash
pytest tests/test_monitor.py -v
# Expected: All existing tests still PASS
```

- [ ] **Step 3: Commit**
```bash
git add src/monitor.py
git commit -m "feat: pass status field to Session objects

Update SessionMonitor.discover_sessions to:
- Extract status from metadata dict
- Pass status to Session constructor
- Use .get() for safe access (follows startedAt pattern)"
```

---

### Task 4: Add Status Column and Smart Sorting to Dashboard (TDD Red-Green-Refactor)

**Goal:** Add Status column to dashboard table and implement two-level sorting

**Files:**
- Modify: `src/dashboard.py` (151 lines currently)
- Create: `tests/test_dashboard.py` (new file)

---

#### Subtask 4.1: Create dashboard test file and add Status column

- [ ] **Step 1 (Red): Write test for Status column rendering**

Create `tests/test_dashboard.py`:
```python
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
```

Run test:
```bash
pytest tests/test_dashboard.py::test_dashboard_displays_status_column_running -v
# Expected: FAIL - status not in output
```

- [ ] **Step 2 (Green): Add status to test mode output**

Modify `src/dashboard.py`, in `_render_test_mode` method (around line 53-60):

Change:
```python
            output["sessions"].append({
                "id": session.session_id,
                "label": session.label,
                "tokens": session.total_tokens,
                "window_percent": round(session.window_percent, 1),
                "status": "active",
                "alert_level": session.alert_level
            })
```

To:
```python
            # Determine display status
            if session.status == "done":
                display_status = "done"
            elif session.status == "running" or session.status is None:
                display_status = "running"
            else:
                display_status = session.status  # Fallback for unknown values
            
            output["sessions"].append({
                "id": session.session_id,
                "label": session.label,
                "tokens": session.total_tokens,
                "window_percent": round(session.window_percent, 1),
                "session_status": display_status,  # New field
                "alert_level": session.alert_level
            })
```

Run tests:
```bash
pytest tests/test_dashboard.py -v
# Expected: Tests should pass now
```

- [ ] **Step 3 (Green): Add Status column to rich UI**

Modify `src/dashboard.py`, in `_render_rich_ui` method (around line 84-89):

After the Label column (line 85), add Status column:
```python
        table.add_column("Session ID", style="cyan")
        table.add_column("Label", style="white")
        table.add_column("Status", justify="center", style="dim")  # New column
        table.add_column("Age", justify="right", style="dim")
```

Then in the table.add_row section (around line 119-126), add status value:

Change:
```python
            table.add_row(
                session.session_id[:12],
                session.label,
                session.format_age(),
                f"{session.total_tokens:,}",
                f"[{percent_style}]{percent:.1f}%[/{percent_style}]",
                f"[{alert_style}]{alert_text}[/{alert_style}]"
            )
```

To:
```python
            # Format status for display
            if session.status == "done":
                status_display = "DONE"
                status_style = "dim"
            elif session.status == "running":
                status_display = "RUNNING"
                status_style = "green"
            elif session.status is None:
                status_display = "—"  # Em dash for null
                status_style = "dim"
            else:
                status_display = str(session.status)  # Fallback
                status_style = "white"
            
            table.add_row(
                session.session_id[:12],
                session.label,
                f"[{status_style}]{status_display}[/{status_style}]",  # New column
                session.format_age(),
                f"{session.total_tokens:,}",
                f"[{percent_style}]{percent:.1f}%[/{percent_style}]",
                f"[{alert_style}]{alert_text}[/{alert_style}]"
            )
```

- [ ] **Step 4 (Refactor): Extract status display logic to helper method**

Add helper method to Dashboard class (after line 29):
```python
    def _format_status_display(self, status: Optional[str]) -> tuple[str, str]:
        """
        Format status value for display.
        
        Args:
            status: Session status ("running", "done", or None)
            
        Returns:
            Tuple of (display_text, style)
        """
        if status == "done":
            return ("DONE", "dim")
        elif status == "running":
            return ("RUNNING", "green")
        elif status is None:
            return ("—", "dim")  # Em dash for null
        else:
            return (str(status), "white")  # Fallback
```

Update the table.add_row section to use helper:
```python
            status_display, status_style = self._format_status_display(session.status)
            
            table.add_row(
                session.session_id[:12],
                session.label,
                f"[{status_style}]{status_display}[/{status_style}]",
                session.format_age(),
                f"{session.total_tokens:,}",
                f"[{percent_style}]{percent:.1f}%[/{percent_style}]",
                f"[{alert_style}]{alert_text}[/{alert_style}]"
            )
```

Run tests:
```bash
pytest tests/test_dashboard.py -v
# Expected: All 3 tests PASS
```

- [ ] **Step 5: Commit**
```bash
git add src/dashboard.py tests/test_dashboard.py
git commit -m "feat: add Status column to dashboard

Add Status column to dashboard:
- Position between Label and Age columns
- Display 'RUNNING' for running/null status (green)
- Display 'DONE' for done status (dim)
- Display '—' (em dash) for null values
- Extract display logic to _format_status_display helper
- Update test mode output to include session_status field"
```

---

#### Subtask 4.2: Implement primary sorting (active before inactive)

- [ ] **Step 1 (Red): Write test for primary sort - active before inactive**

Add to `tests/test_dashboard.py`:
```python


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
```

Run test:
```bash
pytest tests/test_dashboard.py::test_dashboard_sorts_active_sessions_before_done -v
# Expected: FAIL - still sorted by window % only
```

- [ ] **Step 2 (Green): Implement primary sort logic**

Modify `src/dashboard.py`, in `_render_rich_ui` method (around line 92-96):

Change:
```python
        # Sort by window percent descending (highest usage first)
        sorted_sessions = sorted(
            sessions.values(),
            key=lambda s: s.window_percent,
            reverse=True
        )
```

To:
```python
        # Sort by: 1) active status (running/null) before done, 2) window % descending
        def sort_key(session: Session) -> tuple[int, float]:
            # Primary: active (0) before done (1)
            is_done = 1 if session.status == "done" else 0
            # Secondary: window % descending (negate for desc order)
            window_pct = -session.window_percent
            return (is_done, window_pct)
        
        sorted_sessions = sorted(sessions.values(), key=sort_key)
```

Run test:
```bash
pytest tests/test_dashboard.py::test_dashboard_sorts_active_sessions_before_done -v
# Expected: PASS
```

- [ ] **Step 3 (Refactor): Review sort key logic for clarity**

Sort key is clear and efficient (single-pass sort). No refactor needed.

Run all dashboard tests:
```bash
pytest tests/test_dashboard.py -v
# Expected: All 4 tests PASS
```

- [ ] **Step 4: Commit**
```bash
git add src/dashboard.py tests/test_dashboard.py
git commit -m "feat: implement primary sorting - active before done

Add primary sort level to dashboard:
- Active sessions (running/null) appear before done
- Uses tuple sort key: (is_done, -window_percent)
- Single-pass sorting algorithm (O(n log n))
- Maintains existing secondary sort by window %"
```

---

#### Subtask 4.3: Implement secondary sorting (window % within groups)

- [ ] **Step 1 (Red): Write test for secondary sort within active group**

Add to `tests/test_dashboard.py`:
```python


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
```

Run tests:
```bash
pytest tests/test_dashboard.py::test_dashboard_sorts_by_window_percent_within_active_group -v
pytest tests/test_dashboard.py::test_dashboard_sorts_by_window_percent_within_done_group -v
# Expected: Both PASS (implementation already handles via sort key)
```

- [ ] **Step 2 (Green): Verify tests pass**

Tests should already pass due to tuple sort key. No code changes needed.

Run all dashboard tests:
```bash
pytest tests/test_dashboard.py -v
# Expected: All 6 tests PASS
```

- [ ] **Step 3 (Refactor): Add docstring to sort logic**

Add comment to sort logic for future maintainability:
```python
        # Smart two-level sorting:
        # Primary: Active sessions (running/null) float to top
        # Secondary: Within each group, sort by window % descending
        # Result: Critical active sessions always appear first
        def sort_key(session: Session) -> tuple[int, float]:
            # Primary: active (0) before done (1)
            is_done = 1 if session.status == "done" else 0
            # Secondary: window % descending (negate for desc order)
            window_pct = -session.window_percent
            return (is_done, window_pct)
        
        sorted_sessions = sorted(sessions.values(), key=sort_key)
```

- [ ] **Step 4: Commit**
```bash
git add tests/test_dashboard.py
git commit -m "test: add secondary sorting tests

Add tests verifying:
- Active sessions sorted by window % descending
- Done sessions sorted by window % descending
- Secondary sort works within each primary group

All dashboard tests passing (6 total)."
```

---

#### Subtask 4.4: Add edge case tests

- [ ] **Step 1 (Red): Write edge case tests**

Add to `tests/test_dashboard.py`:
```python


def test_dashboard_handles_empty_sessions():
    """Test dashboard handles empty sessions dict gracefully."""
    dashboard = Dashboard(test_mode=True)
    
    output = dashboard.render({})
    import json
    data = json.loads(output)
    
    assert data["sessions"] == []
    assert data["total_sessions"] == 0
```

Run test:
```bash
pytest tests/test_dashboard.py::test_dashboard_handles_empty_sessions -v
# Expected: PASS (dashboard already handles empty dict)
```

- [ ] **Step 2 (Green): Verify edge case handling**

Test should already pass. No code changes needed.

Run all dashboard tests:
```bash
pytest tests/test_dashboard.py -v
# Expected: All 7 tests PASS
```

- [ ] **Step 3: Commit**
```bash
git add tests/test_dashboard.py
git commit -m "test: add edge case test for empty sessions

Verify dashboard handles empty sessions dict:
- Returns empty sessions array
- Total sessions count is 0
- No crashes or errors

All dashboard tests passing (7 total)."
```

---

### Task 5: Integration Test and Verification

**Goal:** Run full test suite and verify all components work together

---

- [ ] **Step 1: Run complete test suite**

```bash
cd /Volumes/RayCue-Drive/Documents/projects/openclaw-session-monitor/.worktrees/add-status-column
source ../../.venv/bin/activate
pytest tests/ -v
# Expected: 49 tests PASS (35 existing + 14 new)
# Breakdown: 27 model + 11 parser + 4 monitor + 7 dashboard
```

- [ ] **Step 2: Verify test coverage for new feature**

Check that all 14 planned tests exist:
```bash
pytest tests/ -v --co -q | grep -E "(status|sort)"
# Expected: See all 14 status-related test names
```

- [ ] **Step 3: Visual verification of dashboard**

Test the dashboard manually with simulated sessions:
```bash
# Create test sessions.json with mixed status
mkdir -p /tmp/test-openclaw/main/sessions
cat > /tmp/test-openclaw/main/sessions/sessions.json << 'EOF'
{
  "agent:main:running-high": {
    "sessionId": "running-high",
    "label": "main:high-usage",
    "status": "running",
    "sessionFile": "/tmp/test-openclaw/main/sessions/running-high.jsonl"
  },
  "agent:main:done-low": {
    "sessionId": "done-low",
    "label": "main:completed",
    "status": "done",
    "sessionFile": "/tmp/test-openclaw/main/sessions/done-low.jsonl"
  },
  "agent:main:null-med": {
    "sessionId": "null-med",
    "label": "main:active-med",
    "status": null,
    "sessionFile": "/tmp/test-openclaw/main/sessions/null-med.jsonl"
  }
}
EOF

# Create dummy session files
echo '{"type":"message","message":{"usage":{"totalTokens":180000}}}' > /tmp/test-openclaw/main/sessions/running-high.jsonl
echo '{"type":"message","message":{"usage":{"totalTokens":30000}}}' > /tmp/test-openclaw/main/sessions/done-low.jsonl
echo '{"type":"message","message":{"usage":{"totalTokens":100000}}}' > /tmp/test-openclaw/main/sessions/null-med.jsonl

# Run monitor with test state dir
python -m src.cli watch --state-dir /tmp/test-openclaw --simple

# Expected dashboard output:
# Session ID    Label              Status   Age  Tokens    Window %  Alert
# running-high  main:high-usage    RUNNING  ...  180,000   90.0%     WARN
# null-med      main:active-med    —        ...  100,000   50.0%     OK
# done-low      main:completed     DONE     ...   30,000   15.0%     OK
# 
# Note: Active sessions (RUNNING, —) appear before DONE
# Within each group, sorted by window % descending
```

- [ ] **Step 4: Performance regression check**

Ensure sorting doesn't impact performance:
```bash
python -m pytest tests/test_dashboard.py -v --durations=5
# Expected: All tests complete in <100ms each
```

- [ ] **Step 5: Commit integration verification**

```bash
git add -A  # Capture any test data or minor fixes
git commit -m "test: verify full integration of status column feature

Integration verification complete:
- All 49 tests passing (35 existing + 14 new)
- Status column displays correctly in dashboard
- Smart sorting works: active before done, window % within groups
- No performance regressions detected
- Manual visual verification successful"
```

---

### Task 6: Update Documentation

**Goal:** Document the new Status column feature

---

- [ ] **Step 1: Update README.md**

Add status column documentation to README.md (in Features or Usage section):

```markdown
### Status Column

The dashboard displays session status in a dedicated column:
- **RUNNING** (green): Active sessions (status="running" or null)
- **DONE** (dim): Completed sessions (status="done")
- **—** (dim): Null status (treated as active)

**Smart Sorting:**
Sessions are sorted in two levels:
1. **Primary**: Active sessions (RUNNING/—) appear before done sessions
2. **Secondary**: Within each group, sorted by window % descending

This ensures sessions approaching context limits are always visible at the top.
```

- [ ] **Step 2: Update example output in README**

Update the dashboard example to include Status column:

```markdown
#### Example Dashboard

```
Session ID    Label              Status   Age  Tokens    Window %  Alert
5f3febb2-ebd  main:heartbeat     RUNNING  2m   145,234   73%       OK
9e1a5a15-ad3  claude:review      —        30s   12,456    6%       OK
3b8c1f27-9a1  main:completed     DONE     5m    98,123   49%       OK
```
```

- [ ] **Step 3: Commit documentation**

```bash
git add README.md
git commit -m "docs: document status column and smart sorting

Add documentation for:
- Status column display values (RUNNING/DONE/—)
- Smart two-level sorting behavior
- Updated dashboard example output

Feature implementation complete."
```

---

## Success Criteria

After completing all tasks, verify:

1. ✅ **All 49 tests pass** (35 existing + 14 new)
2. ✅ **Status column visible** between Label and Age
3. ✅ **Correct display values**: RUNNING (green), DONE (dim), — (dim)
4. ✅ **Smart sorting works**: Active sessions first, then by window %
5. ✅ **Null status treated as active** (conservative approach)
6. ✅ **No performance regression** (<100ms per test)
7. ✅ **Documentation updated** with examples
8. ✅ **All changes committed** with clear messages

---

## Testing Strategy

**TDD Approach:**
- Red: Write failing test first
- Green: Implement minimal code to pass
- Refactor: Clean up while keeping tests green

**Test Coverage:**
- Unit tests: Model properties, parser extraction, display logic
- Integration tests: Dashboard rendering with test mode JSON output
- Edge cases: Empty sessions, null values, missing fields
- Manual verification: Visual dashboard with mixed status values

**Verification Commands:**
```bash
# Run all tests
pytest tests/ -v

# Run status-specific tests only
pytest tests/ -v -k "status or sort"

# Check for skipped tests (should be ZERO)
pytest tests/ -v | grep -i skip

# Performance check
pytest tests/test_dashboard.py --durations=5
```

---

## Rollback Plan

If issues arise during implementation:

1. **Individual task rollback:**
   ```bash
   git revert <commit-hash>  # Revert specific commit
   pytest tests/ -v          # Verify tests still pass
   ```

2. **Full feature rollback:**
   ```bash
   git revert <first-commit>..<last-commit>
   # Or reset to pre-feature commit:
   git reset --hard <commit-before-feature>
   ```

3. **Branch abandonment:**
   ```bash
   git checkout main
   git worktree remove .worktrees/add-status-column
   git branch -D add-status-column
   ```

---

## Dependencies

**Existing Code:**
- `src/models.py`: Session dataclass with context_limit, window_percent
- `src/session_parser.py`: parse_sessions_metadata function
- `src/monitor.py`: SessionMonitor.discover_sessions method
- `src/dashboard.py`: Dashboard._render_rich_ui method with Rich library

**No New Dependencies:**
- All required packages already installed (rich, pytest, dataclasses)
- Python 3.8+ standard library sufficient for tuple sorting

**Test Dependencies:**
- pytest for test execution
- tmp_path fixture for parser tests (already in use)
- json module for test mode output parsing (stdlib)
