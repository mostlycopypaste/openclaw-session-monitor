# Add Model Column Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Model" column to the Session Monitor table to display which model each session is using.

**Architecture:** Extend the existing data flow (parse_sessions_metadata → Session model → Dashboard) to include model information. The model field already exists in OpenClaw's sessions.json, so we extract it during parsing and display it in the table.

**Tech Stack:** Python 3.8+, rich (terminal UI), pytest

**Issue:** mostlycopypaste/openclaw-session-monitor#1

---

## File Structure

The changes flow through four main components:

1. **src/models.py** - Add `model` field to Session dataclass
2. **src/session_parser.py** - Extract `model` from sessions.json
3. **src/monitor.py** - Pass model through to Session constructor
4. **src/dashboard.py** - Display model in table (with truncation for long names)
5. **tests/** - Update tests for all modified components

Each file has a single, clear responsibility and changes are minimal.

---

### Task 1: Add model field to Session dataclass

**Files:**
- Modify: `src/models.py:8-18`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write failing test for model field**

```python
def test_session_with_model():
    """Test Session includes model field."""
    session = Session(
        session_id="test-123",
        label="agent:main:test",
        agent="main",
        total_tokens=50000,
        model="kimi-k2.5:cloud"
    )
    
    assert session.model == "kimi-k2.5:cloud"


def test_session_model_defaults_to_none():
    """Test Session model field defaults to None when not provided."""
    session = Session(
        session_id="test-123",
        label="agent:main:test",
        agent="main",
        total_tokens=50000
    )
    
    assert session.model is None
```

Add to `tests/test_models.py` after the existing Session tests.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py::test_session_with_model -v`

Expected: FAIL with "Session.__init__() got an unexpected keyword argument 'model'"

- [ ] **Step 3: Add model field to Session dataclass**

In `src/models.py`, modify the Session dataclass to include model field:

```python
@dataclass
class Session:
    """Represents an OpenClaw session with token tracking."""

    session_id: str
    label: str
    agent: str
    total_tokens: int
    created_at: Optional[int] = None  # Unix timestamp in milliseconds
    status: Optional[str] = None  # "running", "done", or None (treated as running)
    model: Optional[str] = None  # Model identifier (e.g., "kimi-k2.5:cloud")
    context_limit: int = 200000
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_models.py -v`

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat: add model field to Session dataclass

Add optional model field to track which AI model each session uses.
Defaults to None for backward compatibility.

Refs: #1"
```

---

### Task 2: Extract model from sessions.json

**Files:**
- Modify: `src/session_parser.py:49-57`
- Test: `tests/test_session_parser.py`

- [ ] **Step 1: Write failing test for model extraction**

```python
def test_parse_sessions_metadata_extracts_model(tmp_path):
    """Test parser extracts model field from sessions.json."""
    session_file = tmp_path / "test-001.jsonl"
    session_file.write_text('{"type":"message","message":{"usage":{"totalTokens":100}}}\n')

    sessions_file = tmp_path / "sessions.json"
    sessions_file.write_text(f'''{{
  "agent:main:test": {{
    "sessionId": "test-001",
    "sessionFile": "{session_file}",
    "status": "running",
    "model": "kimi-k2.5:cloud"
  }}
}}''')

    sessions = parse_sessions_metadata(sessions_file)
    
    assert len(sessions) == 1
    assert sessions[0]["model"] == "kimi-k2.5:cloud"


def test_parse_sessions_metadata_model_missing(tmp_path):
    """Test parser handles missing model field."""
    session_file = tmp_path / "test-001.jsonl"
    session_file.write_text('{"type":"message","message":{"usage":{"totalTokens":100}}}\n')

    sessions_file = tmp_path / "sessions.json"
    sessions_file.write_text(f'''{{
  "agent:main:test": {{
    "sessionId": "test-001",
    "sessionFile": "{session_file}",
    "status": "running"
  }}
}}''')

    sessions = parse_sessions_metadata(sessions_file)
    
    assert len(sessions) == 1
    assert sessions[0]["model"] is None
```

Add to `tests/test_session_parser.py` at the end of the file.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_session_parser.py::test_parse_sessions_metadata_extracts_model -v`

Expected: FAIL with "KeyError: 'model'"

- [ ] **Step 3: Add model extraction to parse_sessions_metadata**

In `src/session_parser.py`, modify the sessions.append() call to include model:

```python
        sessions.append({
            'sessionId': session_data['sessionId'],
            'label': label,
            'agent': agent,
            'sessionFile': session_file,
            'startedAt': session_data.get('startedAt'),  # Unix timestamp in milliseconds
            'status': session_data.get('status'),  # "running", "done", or None
            'model': session_data.get('model'),  # Model identifier (e.g., "kimi-k2.5:cloud")
        })
```

This is at line 50-57 in `src/session_parser.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_session_parser.py -v`

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/session_parser.py tests/test_session_parser.py
git commit -m "feat: extract model field from sessions.json

Parse model identifier from OpenClaw sessions metadata.
Uses .get() to safely handle sessions without model field.

Refs: #1"
```

---

### Task 3: Pass model to Session constructor

**Files:**
- Modify: `src/monitor.py:86-94`
- Test: `tests/test_monitor.py`

- [ ] **Step 1: Write failing test for model propagation**

```python
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
    sessions_json.write_text(f'''{{
  "agent:main:test": {{
    "sessionId": "test-123",
    "sessionFile": "{session_file}",
    "status": "running",
    "model": "kimi-k2.5:cloud"
  }}
}}''')
    
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
    sessions_json.write_text(f'''{{
  "agent:main:test": {{
    "sessionId": "test-123",
    "sessionFile": "{session_file}",
    "status": "running"
  }}
}}''')
    
    # Execute
    monitor = SessionMonitor(state_dir)
    monitor.discover_sessions()
    
    # Verify
    assert len(monitor.sessions) == 1
    session = monitor.sessions["test-123"]
    assert session.model is None
```

Add to `tests/test_monitor.py` at the end of the file.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_monitor.py::test_monitor_includes_model_in_session -v`

Expected: FAIL with "AssertionError: assert None == 'kimi-k2.5:cloud'"

- [ ] **Step 3: Add model parameter to Session constructor**

In `src/monitor.py`, modify the Session instantiation to include model:

```python
                    # Create Session object
                    session = Session(
                        session_id=session_id,
                        label=metadata['label'],
                        agent=metadata['agent'],
                        total_tokens=total_tokens,
                        created_at=metadata.get('startedAt'),
                        status=metadata.get('status'),
                        model=metadata.get('model'),
                        context_limit=self.context_limit
                    )
```

This is at lines 86-94 in `src/monitor.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_monitor.py -v`

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/monitor.py tests/test_monitor.py
git commit -m "feat: pass model from metadata to Session

Wire model field through SessionMonitor to Session objects.
Allows model information to flow from sessions.json to display.

Refs: #1"
```

---

### Task 4: Display model in rich UI table

**Files:**
- Modify: `src/dashboard.py:133-183`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Write failing test for model column in rich UI**

```python
def test_dashboard_displays_model_column():
    """Test dashboard includes model in table output."""
    from src.models import Session
    
    dashboard = Dashboard(test_mode=False)
    sessions = {
        "test-123": Session(
            session_id="test-123",
            label="agent:main:test",
            agent="main",
            total_tokens=50000,
            model="kimi-k2.5:cloud"
        )
    }
    
    table = dashboard._render_rich_ui(sessions)
    
    # Check that table has Model column
    column_headers = [col.header for col in table.columns]
    assert "Model" in column_headers


def test_dashboard_truncates_long_model_names():
    """Test dashboard truncates model names longer than 20 characters."""
    from src.models import Session
    
    dashboard = Dashboard(test_mode=False)
    sessions = {
        "test-123": Session(
            session_id="test-123",
            label="agent:main:test",
            agent="main",
            total_tokens=50000,
            model="ollama/very-long-model-name-that-needs-truncation:latest"
        )
    }
    
    table = dashboard._render_rich_ui(sessions)
    
    # Get the model cell value (should be truncated)
    # Rich table stores rows as list of Text/str objects
    model_cell = str(table.rows[0][2])  # Model is 3rd column (after Session ID, Label)
    assert len(model_cell) <= 23  # 20 chars + "..." = 23


def test_dashboard_handles_null_model():
    """Test dashboard displays placeholder for None model."""
    from src.models import Session
    
    dashboard = Dashboard(test_mode=False)
    sessions = {
        "test-123": Session(
            session_id="test-123",
            label="agent:main:test",
            agent="main",
            total_tokens=50000,
            model=None
        )
    }
    
    table = dashboard._render_rich_ui(sessions)
    
    # Get the model cell value
    model_cell = str(table.rows[0][2])
    assert model_cell in ["—", "None", ""]  # Accept any reasonable placeholder
```

Add to `tests/test_dashboard.py` at the end of the file.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dashboard.py::test_dashboard_displays_model_column -v`

Expected: FAIL with "AssertionError: assert 'Model' in []" or column count mismatch

- [ ] **Step 3: Add model truncation helper method**

In `src/dashboard.py`, add a new helper method after `_truncate_label`:

```python
    def _format_model(self, model: str | None, max_length: int = 20) -> str:
        """
        Format model name for display.

        Args:
            model: Model identifier (e.g., "kimi-k2.5:cloud")
            max_length: Maximum length before truncation (default: 20)

        Returns:
            Formatted model name, truncated with "..." if too long, or "—" if None
        """
        if model is None:
            return "—"
        
        if len(model) <= max_length:
            return model
        
        return model[:max_length - 3] + "..."
```

Add this after the `_truncate_label` method (around line 63).

- [ ] **Step 4: Add Model column to rich UI table**

In `src/dashboard.py`, modify `_render_rich_ui` to add the Model column. Update the table column definitions:

```python
        table.add_column("Session ID", style="cyan")
        table.add_column("Label", style="white")
        table.add_column("Model", style="magenta")  # New column
        table.add_column("Status", justify="center", style="dim")
        table.add_column("Age", justify="right", style="dim")
        table.add_column("Tokens", justify="right", style="yellow")
        table.add_column("Window %", justify="right")
        table.add_column("Alert", style="bold")
```

And update the `table.add_row()` call to include model:

```python
            table.add_row(
                session.session_id[:12],
                self._truncate_label(session.label),
                self._format_model(session.model),  # New field
                f"[{status_style}]{status_display}[/{status_style}]",
                session.format_age(),
                f"{session.total_tokens:,}",
                f"[{percent_style}]{percent:.1f}%[/{percent_style}]",
                f"[{alert_style}]{alert_text}[/{alert_style}]"
            )
```

These changes are in the `_render_rich_ui` method around lines 133-183.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_dashboard.py -v`

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/dashboard.py tests/test_dashboard.py
git commit -m "feat: add Model column to session table

Display model identifier in rich UI table with truncation
for long names. Shows em dash (—) for sessions without model.

Refs: #1"
```

---

### Task 5: Display model in test mode (JSON output)

**Files:**
- Modify: `src/dashboard.py:79-126`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Write failing test for model in test mode JSON**

```python
def test_dashboard_test_mode_includes_model():
    """Test dashboard test mode includes model in JSON output."""
    from src.models import Session
    import json
    
    dashboard = Dashboard(test_mode=True)
    sessions = {
        "test-123": Session(
            session_id="test-123",
            label="agent:main:test",
            agent="main",
            total_tokens=50000,
            model="kimi-k2.5:cloud"
        )
    }
    
    output = dashboard.render(sessions)
    data = json.loads(output)
    
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["model"] == "kimi-k2.5:cloud"


def test_dashboard_test_mode_handles_null_model():
    """Test dashboard test mode handles None model."""
    from src.models import Session
    import json
    
    dashboard = Dashboard(test_mode=True)
    sessions = {
        "test-123": Session(
            session_id="test-123",
            label="agent:main:test",
            agent="main",
            total_tokens=50000,
            model=None
        )
    }
    
    output = dashboard.render(sessions)
    data = json.loads(output)
    
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["model"] is None
```

Add to `tests/test_dashboard.py` at the end of the file.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dashboard.py::test_dashboard_test_mode_includes_model -v`

Expected: FAIL with "KeyError: 'model'"

- [ ] **Step 3: Add model to test mode JSON output**

In `src/dashboard.py`, modify the `_render_test_mode` method to include model in the output:

```python
            output["sessions"].append({
                "id": session.session_id,
                "label": self._truncate_label(session.label),
                "model": session.model,  # New field
                "tokens": session.total_tokens,
                "window_percent": round(session.window_percent, 1),
                "session_status": display_status,
                "alert_level": session.alert_level
            })
```

This is in the `_render_test_mode` method around lines 103-110.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_dashboard.py -v`

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/dashboard.py tests/test_dashboard.py
git commit -m "feat: include model in test mode JSON output

Add model field to JSON output for test mode.
Maintains consistency between rich UI and test mode.

Refs: #1"
```

---

### Task 6: Run full test suite and verify

**Files:**
- All test files

- [ ] **Step 1: Run complete test suite**

Run: `pytest tests/ -v --cov=src --cov-report=term-missing`

Expected: All tests PASS, coverage includes new model field in all components

- [ ] **Step 2: Test with live OpenClaw data**

Run: `session-monitor watch --state-dir ~/.openclaw-primary`

Expected: 
- Table displays with new "Model" column
- Model names appear for sessions (e.g., "kimi-k2.5:cloud", "minimax-m2.5:cloud")
- Sessions without model show "—"
- Long model names are truncated with "..."

- [ ] **Step 3: Verify test mode output**

Run: `python -c "from src.dashboard import Dashboard; from src.monitor import SessionMonitor; from pathlib import Path; m = SessionMonitor(Path.home() / '.openclaw-primary'); m.discover_sessions(); d = Dashboard(test_mode=True); print(d.render(m.sessions))" | jq '.sessions[] | {id, model}'`

Expected: JSON output includes model field for each session

- [ ] **Step 4: Commit final integration**

```bash
git add -A
git commit -m "test: verify model column integration

All tests passing with model field flowing through
full pipeline from sessions.json to display.

Closes #1"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ New "Model" column in Session Monitor table
- ✅ Displays full model identifier (e.g., `kimi-k2.5:cloud`)
- ✅ Model updates if session switches models (handled by existing polling)
- ✅ Column appropriately sized (truncated at 20 chars with "...")
- ✅ Positioned after Label, before Status

**Placeholder scan:**
- ✅ No TBD, TODO, or "implement later"
- ✅ All code blocks are complete and runnable
- ✅ All test assertions are specific
- ✅ All file paths are exact

**Type consistency:**
- ✅ `model` field is `Optional[str]` throughout
- ✅ Method signatures match across all files
- ✅ Test mode JSON uses `"model"` key consistently
- ✅ Rich UI uses `"Model"` column header

**Open questions addressed:**
- Model path format: Show full identifier (e.g., `ollama/kimi-k2.5:cloud` → truncated if >20 chars)
- Column position: After Label, before Status (makes visual scanning easy)

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-11-add-model-column.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
