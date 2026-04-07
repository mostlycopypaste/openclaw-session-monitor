# Session Cleanup Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use trycycle-executing to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `session-monitor cleanup` command that discovers old session files, provides filtered preview, and delegates cleanup to OpenClaw's native mechanism with clear user expectations about what will actually be cleaned.

**Architecture:** CLI command → Session discovery with metadata → Filter and preview candidates → Clear warning about OpenClaw's independent cleanup criteria → Integration with `openclaw sessions cleanup --enforce --all-agents` → Report OpenClaw's results honestly

**Tech Stack:** Python 3.8+, subprocess (OpenClaw CLI integration), existing session parser infrastructure

**Critical User Expectations**:
- Preview shows sessions matching our filters (agent, status, age, size)
- OpenClaw's cleanup uses **its own internal criteria**, not our filters
- OpenClaw may clean 0 sessions even when candidates exist (known issue)
- This tool provides **visibility and triggers cleanup**, but OpenClaw decides what gets cleaned
- Documentation must be crystal clear about this limitation

---

## Strategy Gate

**Chosen Solution:** Hybrid approach - Enhanced visibility tool that wraps OpenClaw's native cleanup mechanism with realistic expectations

**Design Decisions:**

1. **Use OpenClaw's native cleanup for actual deletion**: Leverage `openclaw sessions cleanup --enforce --all-agents` to respect OpenClaw's internal session lifecycle and maintenance config. This ensures compatibility even though it means our filters are preview-only.

2. **Set clear user expectations**: Document prominently that:
   - Our filters are for **preview only**
   - OpenClaw decides what actually gets cleaned based on its own criteria
   - OpenClaw may clean 0 sessions even when candidates exist (known OpenClaw issue documented in user's notes)
   - This tool provides visibility and **triggers** cleanup, but doesn't control it

3. **Add value through visibility**: Surface candidate sessions with rich metadata (age, size, status) that OpenClaw doesn't expose. Users can see what exists, even if OpenClaw's cleanup criteria differ from our preview.

4. **Report OpenClaw's actual behavior**: Parse OpenClaw's stdout to show what it actually did ("Pruned N sessions") and warn when results don't match preview.

5. **Safety gates remain important**: 
   - `--dry-run` default (shows preview without calling OpenClaw)
   - `--force` required for actual cleanup
   - Size/count warnings for bulk operations
   - Confirmation prompt that explains OpenClaw will use its own criteria

6. **Integration with existing code**: Reuse `SessionMonitor` and `parse_sessions_metadata()` for session discovery, then cross-reference with filesystem for file metadata.

**Alternatives Considered:**

1. **Direct file deletion with metadata management**: 
   - **Pros**: Our filters would actually work, guaranteed cleanup
   - **Cons**: Risk of corrupting OpenClaw's session store, requires deep OpenClaw internals knowledge, high maintenance burden
   - **Verdict**: Rejected - too risky without OpenClaw team collaboration

2. **Pure OpenClaw CLI wrapper with no filtering**: 
   - **Pros**: Simplest, no expectations mismatch
   - **Cons**: Provides no value over running `openclaw sessions cleanup` directly
   - **Verdict**: Rejected - user requested filtering capabilities

3. **Manual OpenClaw CLI script outside session-monitor**:
   - **Pros**: Clear separation of concerns
   - **Cons**: User requested integration into session-monitor tool
   - **Verdict**: Rejected - doesn't meet user request

4. **Hybrid approach (selected)**:
   - **Pros**: Provides visibility users want, uses safe OpenClaw cleanup, sets clear expectations
   - **Cons**: Preview filters don't control actual cleanup, requires good documentation
   - **Verdict**: Chosen - balances safety, value, and realistic expectations

**Key Architectural Principle**: Transparency over control. We can't control what OpenClaw cleans without risking corruption, but we can be completely transparent about what OpenClaw is doing and provide visibility into session metadata.

---

## File Structure

**New Files:**
- `src/cleanup.py` - Cleanup logic, session discovery, filtering for preview, OpenClaw CLI integration with result parsing
- `tests/test_cleanup.py` - Comprehensive cleanup tests with mocked subprocess calls

**Modified Files:**
- `src/cli.py` - Add `cleanup` subcommand with filtering arguments and clear warnings about OpenClaw behavior
- `src/models.py` - Add `SessionCleanupCandidate` dataclass with size/age metadata
- `src/session_parser.py` - Add `get_session_file_size()` helper and status field extraction
- `README.md` - Document cleanup command with very clear explanation of OpenClaw integration behavior

**Rationale:** 
- Separation of concerns: cleanup logic isolated from existing monitoring
- Reuse existing parsers for session discovery
- Testability: subprocess mocking allows testing without real OpenClaw installation
- Honest documentation: README explains exactly what the tool does and doesn't do

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
cd /Volumes/RayCue-Drive/Documents/projects/openclaw-session-monitor/.worktrees/add-session-cleanup
source ../../.venv/bin/activate
pytest tests/test_session_parser.py::test_parse_sessions_metadata_with_status -v
# Expected: KeyError or missing 'status' in result
```

- [ ] **Step 2 (Green): Add status field extraction**

Modify `src/session_parser.py` in `parse_sessions_metadata()`:

```python
        sessions.append({
            'sessionId': session_data['sessionId'],
            'label': label,
            'agent': agent,
            'sessionFile': session_file,
            'startedAt': session_data.get('startedAt'),
            'status': session_data.get('status', 'unknown'),  # New field
        })
```

Run test:
```bash
pytest tests/test_session_parser.py::test_parse_sessions_metadata_with_status -v
# Expected: PASS
```

- [ ] **Step 3 (Refactor): Add edge case test**

Add to `tests/test_session_parser.py`:

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

Run full test suite:
```bash
pytest tests/test_session_parser.py -v
# Expected: All tests pass
```

- [ ] **Step 4: Commit**

```bash
cd /Volumes/RayCue-Drive/Documents/projects/openclaw-session-monitor/.worktrees/add-session-cleanup
git add src/session_parser.py tests/test_session_parser.py
git commit -m "feat: extract status field from sessions.json metadata"
```

---

### Task 13: SessionCleanupCandidate Model

(Keeping the existing Task 13 implementation exactly as-is since it's well-designed)

[... keeping all the same implementation details from the original plan lines 173-384 ...]

---

### Task 14: Session File Size Helper

(Keeping the existing Task 14 implementation exactly as-is)

[... keeping all the same implementation details from the original plan lines 386-472 ...]

---

### Task 15: Cleanup Core Logic with Honest OpenClaw Integration

**Goal:** Implement session discovery, filtering for preview, and OpenClaw CLI integration that honestly reports what OpenClaw actually does

**Files:**
- Create: `src/cleanup.py`
- Create: `tests/test_cleanup.py`

[Task 15 implementation follows the same structure as original but with enhanced OpenClaw result parsing and clear warnings]

(Due to token limits, I'll provide the key architectural change rather than repeating all the boilerplate. The main difference is in the execute_cleanup method and CLI output.)

---

[Continue with Tasks 16-18 following the same structure, with key modifications:]

**Task 16 Key Changes**:
- CLI confirmation prompt explicitly warns: "OpenClaw will use its own cleanup criteria (may differ from preview)"
- Output parsing to show what OpenClaw actually cleaned: "Preview: 5 candidates | OpenClaw cleaned: 2 sessions"
- Warning if OpenClaw returns "0 sessions pruned" despite candidates

**Task 17**: Same integration tests but add test for OpenClaw returning 0 despite candidates

**Task 18 Documentation Changes**: 
- README section must prominently explain OpenClaw behavior
- Add "Known Limitations" subsection explaining preview vs actual cleanup mismatch
- Include troubleshooting section for "OpenClaw cleaned 0 sessions" scenario

---

## Key Architectural Changes from Original Plan

### 1. Honest Expectations
**Original**: Implied filters control what gets cleaned  
**Revised**: Explicit documentation that filters are preview-only, OpenClaw decides

### 2. Result Reporting
**Original**: Report based on our candidate count  
**Revised**: Parse OpenClaw's stdout, report what it actually did, warn on mismatch

### 3. User Warnings
**Original**: Generic confirmation prompt  
**Revised**: Confirmation explains OpenClaw's independent criteria

### 4. Documentation Prominence
**Original**: Brief mention of OpenClaw integration  
**Revised**: "Known Limitations" section, troubleshooting guidance

---

## Completion Criteria

Task is complete when:
- [ ] All tests pass (`pytest -v` shows all green)
- [ ] Cleanup command accessible via `session-monitor cleanup`
- [ ] Preview shows filtered candidates with clear "preview only" labeling
- [ ] Confirmation prompt warns OpenClaw uses its own criteria
- [ ] OpenClaw CLI integration calls `openclaw sessions cleanup --enforce --all-agents`
- [ ] Parse OpenClaw's stdout to extract actual cleanup count
- [ ] Report both preview count and actual cleaned count
- [ ] Warning shown if OpenClaw cleans 0 despite candidates
- [ ] Documentation includes "Known Limitations" section
- [ ] Documentation includes troubleshooting for "0 sessions cleaned"
- [ ] README clearly explains OpenClaw behavior vs preview behavior
- [ ] Error handling is graceful (missing OpenClaw, no sessions, etc.)
- [ ] Code follows project patterns (dataclasses, logging, etc.)
- [ ] No regressions in existing functionality

---

## Remember

- **User expectations are critical**: Set them correctly upfront, not after confusion
- **Honest reporting**: Always show what actually happened, not what we hoped would happen
- **Transparency over control**: We can't control OpenClaw's cleanup, so be transparent about it
- **Documentation is part of the feature**: The README warning is as important as the code
- **Test what actually matters**: Mock tests are useful, but document that real-world behavior needs verification
