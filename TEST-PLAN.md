# OpenClaw Session Monitor - Test Plan

## Overview

This test plan provides enumerated test cases that verify the quality and functionality of the OpenClaw Session Monitor MVP. Tests follow the Red-Green-Refactor TDD methodology and ensure all success criteria are met.

## Test Organization

Tests are organized by implementation task, with each task having unit tests followed by integration tests. All tests must pass before the task is considered complete.

---

## Task 1: Data Models

### Unit Tests - Session Model

**T1.1: Session creation with basic fields**
- **Input:** Session(session_id="5f3febb2-ebdd", label="main:heartbeat", agent="main", total_tokens=145234)
- **Expected:** All fields correctly assigned
- **Validates:** Dataclass initialization

**T1.2: Window percentage calculation**
- **Input:** Session with 150K tokens, 200K limit
- **Expected:** window_percent == 75.0
- **Validates:** Computed property accuracy

**T1.3: Alert level - none**
- **Input:** Session with 100K/200K tokens (50%)
- **Expected:** alert_level == "none"
- **Validates:** Threshold logic below 80%

**T1.4: Alert level - warning**
- **Input:** Session with 160K/200K tokens (80%)
- **Expected:** alert_level == "warning"
- **Validates:** Warning threshold at 80%

**T1.5: Alert level - critical**
- **Input:** Session with 180K/200K tokens (90%)
- **Expected:** alert_level == "critical"
- **Validates:** Critical threshold at 90%

**T1.6: Edge case - zero context limit**
- **Input:** Session with context_limit=0
- **Expected:** window_percent == 0.0, no division error
- **Validates:** Error handling for invalid limits

### Unit Tests - Message Model

**T1.7: Message creation**
- **Input:** Message(timestamp="2026-04-07T10:45:32Z", role="user", tokens=1234)
- **Expected:** All fields correctly assigned
- **Validates:** Dataclass initialization

**T1.8: Spike detection - false**
- **Input:** Message with 5000 tokens
- **Expected:** is_spike == False
- **Validates:** Normal message detection

**T1.9: Spike detection - true**
- **Input:** Message with 12000 tokens
- **Expected:** is_spike == True
- **Validates:** Spike threshold at 10K tokens

**T1.10: Spike detection - boundary**
- **Input:** Message with exactly 10000 tokens
- **Expected:** is_spike == False (threshold not exceeded)
- **Validates:** Boundary condition

### Unit Tests - Alert Model

**T1.11: Alert creation**
- **Input:** Alert(session_id="test", level="warning", message="80% full")
- **Expected:** All fields correctly assigned
- **Validates:** Dataclass initialization

---

## Task 2: Test Fixtures

### Fixture Validation Tests

**T2.1: sessions.json is valid JSON**
- **Input:** tests/fixtures/sessions.json
- **Expected:** json.load() succeeds without error
- **Validates:** JSON syntax correctness

**T2.2: sessions.json contains all test sessions**
- **Input:** tests/fixtures/sessions.json
- **Expected:** Contains active, warning, critical, and archived sessions
- **Validates:** Complete test data coverage

**T2.3: session-active.jsonl is valid JSONL**
- **Input:** tests/fixtures/session-active.jsonl
- **Expected:** jsonlines.open() succeeds, all lines parse
- **Validates:** JSONL syntax correctness

**T2.4: session-active.jsonl totals 72K tokens**
- **Input:** tests/fixtures/session-active.jsonl
- **Expected:** Sum of all message tokens == 72000
- **Validates:** Expected token totals for test scenarios

**T2.5: session-warning.jsonl totals 165K tokens**
- **Input:** tests/fixtures/session-warning.jsonl
- **Expected:** Sum of all message tokens == 165000
- **Validates:** Warning threshold test data

**T2.6: session-critical.jsonl totals 185K tokens**
- **Input:** tests/fixtures/session-critical.jsonl
- **Expected:** Sum of all message tokens == 185000
- **Validates:** Critical threshold test data

---

## Task 3: Parse sessions.json Metadata

### Unit Tests - Metadata Parser

**T3.1: Parse single active session**
- **Input:** sessions.json with one active session
- **Expected:** Returns list with 1 session dict containing sessionId, label, agent, sessionFile
- **Validates:** Basic parsing functionality

**T3.2: Parse multiple active sessions**
- **Input:** sessions.json with 3 active sessions
- **Expected:** Returns list with 3 session dicts
- **Validates:** Multiple session handling

**T3.3: Filter out archived sessions**
- **Input:** sessions.json with 1 active, 1 archived (status="archived")
- **Expected:** Returns list with only 1 active session
- **Validates:** Status filtering

**T3.4: Filter out .reset sessions**
- **Input:** sessions.json with session ending in .reset
- **Expected:** Returns empty list or excludes .reset session
- **Validates:** Suffix filtering

**T3.5: Filter out .deleted sessions**
- **Input:** sessions.json with session ending in .deleted
- **Expected:** Returns empty list or excludes .deleted session
- **Validates:** Suffix filtering

**T3.6: Handle missing sessions key**
- **Input:** JSON with no "sessions" key
- **Expected:** Returns empty list
- **Validates:** Graceful degradation

**T3.7: Handle empty sessions array**
- **Input:** {"sessions": []}
- **Expected:** Returns empty list
- **Validates:** Empty state handling

**T3.8: Handle file not found**
- **Input:** Non-existent file path
- **Expected:** Raises FileNotFoundError or similar
- **Validates:** Error handling for missing files

---

## Task 4: Parse JSONL Message Files

### Unit Tests - Message Parser

**T4.1: Parse messages with valid usage field**
- **Input:** JSONL with 2 messages, both have usage.totalTokens
- **Expected:** Returns list with 2 message dicts, tokens extracted correctly
- **Validates:** Standard message parsing

**T4.2: Handle missing usage field**
- **Input:** JSONL with message lacking usage field
- **Expected:** Returns message with tokens=0 (default)
- **Validates:** Graceful handling of missing data

**T4.3: Handle missing totalTokens in usage**
- **Input:** JSONL with usage: {} (empty object)
- **Expected:** Returns message with tokens=0
- **Validates:** Nested field handling

**T4.4: Skip malformed JSON lines**
- **Input:** JSONL with one invalid JSON line between valid lines
- **Expected:** Returns only valid messages, logs warning
- **Validates:** Error recovery

**T4.5: Skip non-message types**
- **Input:** JSONL with type="event", type="message"
- **Expected:** Returns only type="message" entries
- **Validates:** Type filtering

**T4.6: Handle empty file**
- **Input:** Empty JSONL file
- **Expected:** Returns empty list
- **Validates:** Empty state handling

**T4.7: Handle large token counts**
- **Input:** Message with tokens=999999999
- **Expected:** Correctly stores and returns large integer
- **Validates:** Numeric range handling

**T4.8: Extract timestamps and roles**
- **Input:** Messages with various roles (user, assistant, tool)
- **Expected:** All roles and timestamps correctly extracted
- **Validates:** Multi-field extraction

---

## Task 5: Incremental File Reading

### Unit Tests - Incremental Parser

**T5.1: Read from start position**
- **Input:** JSONL file, start_pos=0
- **Expected:** Returns all messages, position at EOF
- **Validates:** Initial read behavior

**T5.2: Read only new messages**
- **Input:** Read file, append new line, read from last position
- **Expected:** Second read returns only new message
- **Validates:** Incremental reading core functionality

**T5.3: Track byte position accurately**
- **Input:** Read file with known byte count
- **Expected:** Returned position matches file size
- **Validates:** Position tracking correctness

**T5.4: Handle append-only updates**
- **Input:** File with 10 messages, read, append 5 more, read incrementally
- **Expected:** First read: 10 messages, second read: 5 messages
- **Validates:** Real-world append scenario

**T5.5: Handle no new data**
- **Input:** Read file, read again from same position without appending
- **Expected:** Second read returns empty list, position unchanged
- **Validates:** Idempotency

**T5.6: Handle file truncation**
- **Input:** Read file, truncate file, read from old position
- **Expected:** Handles gracefully (seeks to start or returns empty)
- **Validates:** Edge case handling

**T5.7: Multi-byte character handling**
- **Input:** JSONL with Unicode characters in messages
- **Expected:** Byte positions correct across multi-byte boundaries
- **Validates:** UTF-8 safety

---

## Task 6: Session Monitor Coordinator

### Unit Tests - Monitor Discovery

**T6.1: Discover single session**
- **Input:** Mock directory with 1 agent, 1 session
- **Expected:** monitor.sessions has 1 entry with correct metadata
- **Validates:** Basic discovery

**T6.2: Discover multiple sessions**
- **Input:** Mock directory with 3 sessions
- **Expected:** monitor.sessions has 3 entries
- **Validates:** Multi-session discovery

**T6.3: Calculate total tokens correctly**
- **Input:** Session with 10 messages, known token counts
- **Expected:** total_tokens matches sum of all messages
- **Validates:** Token aggregation

**T6.4: Skip sessions with missing files**
- **Input:** sessions.json references session-001.jsonl but file doesn't exist
- **Expected:** Session not added to registry, warning logged
- **Validates:** Missing file handling

**T6.5: Handle multiple agents**
- **Input:** Directory with agents/main and agents/worker subdirectories
- **Expected:** Discovers sessions from both agents
- **Validates:** Multi-agent support

**T6.6: Handle missing agents directory**
- **Input:** State directory without agents/ subdirectory
- **Expected:** Returns empty registry, logs warning
- **Validates:** Graceful degradation

**T6.7: Apply context limit to sessions**
- **Input:** Monitor with context_limit=150000
- **Expected:** All sessions have context_limit=150000
- **Validates:** Configuration propagation

### Integration Tests - Monitor End-to-End

**T6.8: Full discovery with token calculation**
- **Input:** Complete mock directory structure with 3 sessions (low, warning, critical)
- **Expected:** All 3 sessions discovered with correct token totals and alert levels
- **Validates:** Complete monitoring workflow

---

## Task 7: File Watcher Integration

### Unit Tests - File Watcher

**T7.1: Detect file modification**
- **Input:** Start watcher, modify watched file
- **Expected:** on_modified callback invoked with file path within 1.5s
- **Validates:** Modification detection

**T7.2: Detect file creation**
- **Input:** Start watcher, create new .jsonl file
- **Expected:** on_created callback invoked with file path within 1.5s
- **Validates:** Creation detection

**T7.3: Ignore non-JSONL files**
- **Input:** Start watcher, modify .txt file
- **Expected:** No callback invoked
- **Validates:** File type filtering

**T7.4: Recursive directory watching**
- **Input:** Start watcher on parent dir, modify file in subdirectory
- **Expected:** Callback invoked for subdirectory file
- **Validates:** Recursive monitoring

**T7.5: Handle rapid successive changes**
- **Input:** Modify file 5 times in quick succession
- **Expected:** All modifications detected (or coalesced appropriately)
- **Validates:** High-frequency change handling

**T7.6: Start and stop cleanly**
- **Input:** Start watcher, stop watcher
- **Expected:** Thread stops within 5s timeout, no errors
- **Validates:** Lifecycle management

**T7.7: Multiple file changes**
- **Input:** Modify 3 different files
- **Expected:** 3 separate callbacks invoked with correct paths
- **Validates:** Multi-file monitoring

---

## Task 8: Dashboard with Test Mode

### Unit Tests - Dashboard Test Mode

**T8.1: Test mode outputs valid JSON**
- **Input:** Dashboard(test_mode=True), render([session])
- **Expected:** json.loads() succeeds on output
- **Validates:** JSON format correctness

**T8.2: JSON contains sessions array**
- **Input:** Render 2 sessions in test mode
- **Expected:** Output has "sessions" key with 2 entries
- **Validates:** Data structure

**T8.3: JSON contains alerts array**
- **Input:** Render sessions with warning and critical levels
- **Expected:** Output has "alerts" key with 2 entries
- **Validates:** Alert generation

**T8.4: Session data completeness**
- **Input:** Render session with all fields
- **Expected:** JSON includes id, label, agent, tokens, window_percent, alert_level
- **Validates:** Field mapping

**T8.5: No alerts for normal sessions**
- **Input:** Render session with 50% tokens
- **Expected:** Alerts array is empty
- **Validates:** Alert filtering

**T8.6: Alert message formatting**
- **Input:** Render warning session
- **Expected:** Alert message includes percentage (e.g., "82.5% full")
- **Validates:** User-readable messages

### Unit Tests - Dashboard Rich UI

**T8.7: Rich UI mode renders without error**
- **Input:** Dashboard(test_mode=False), render([session])
- **Expected:** No exceptions, console output occurs
- **Validates:** UI rendering stability

**T8.8: Color coding by alert level**
- **Input:** Mock console, render sessions with different alert levels
- **Expected:** Styles applied: white (none), yellow (warning), red (critical)
- **Validates:** Visual differentiation

**T8.9: Empty session list**
- **Input:** Render empty list
- **Expected:** No error, displays empty table or message
- **Validates:** Empty state handling

---

## Task 9: CLI Watch Command

### Unit Tests - CLI Interface

**T9.1: CLI help text**
- **Input:** session-monitor --help
- **Expected:** Shows usage, available commands
- **Validates:** User documentation

**T9.2: Watch command accepts state-dir**
- **Input:** session-monitor watch --state-dir /tmp/test
- **Expected:** Uses specified directory, no error
- **Validates:** Argument parsing

**T9.3: Watch command test mode**
- **Input:** session-monitor watch --test-mode --once
- **Expected:** Outputs JSON, exits immediately
- **Validates:** Test mode integration

**T9.4: Environment variable OPENCLAW_STATE_DIR**
- **Input:** OPENCLAW_STATE_DIR=/custom/path session-monitor watch --once --test-mode
- **Expected:** Uses /custom/path as state directory
- **Validates:** Environment variable support

**T9.5: Environment variable OPENCLAW_CONTEXT_TOKENS**
- **Input:** OPENCLAW_CONTEXT_TOKENS=150000 session-monitor watch --once --test-mode
- **Expected:** Sessions use 150000 as context limit
- **Validates:** Configurable context window

**T9.6: Default state directory**
- **Input:** No --state-dir, no env var set
- **Expected:** Uses ~/.openclaw-primary
- **Validates:** Fallback behavior

**T9.7: Agent filtering**
- **Input:** session-monitor watch --agent main --once --test-mode
- **Expected:** Only shows sessions for "main" agent
- **Validates:** Filter functionality

**T9.8: Invalid command**
- **Input:** session-monitor invalid-command
- **Expected:** Shows error message, exits with code 1
- **Validates:** Error handling

### Integration Tests - CLI End-to-End

**T9.9: Full CLI workflow with test fixtures**
- **Input:** Prepared test directory, run CLI in test mode
- **Expected:** JSON output contains correct sessions and alerts
- **Validates:** Complete CLI integration

---

## Task 10: End-to-End Integration Test

### Integration Tests - Complete Workflow

**T10.1: Realistic multi-session scenario**
- **Input:** Directory with 3 sessions (low, warning, critical tokens)
- **Expected:** 
  - Monitor discovers all 3 sessions
  - Tokens calculated correctly (50K, 165K, 185K)
  - Alert levels correct (none, warning, critical)
  - Dashboard JSON shows all data
  - 2 alerts generated (warning, critical only)
- **Validates:** Entire system working together

**T10.2: File modification updates session**
- **Input:** Start monitor, append message to session file
- **Expected:** 
  - Watcher detects change
  - Parser reads new message incrementally
  - Session token count updates
  - Dashboard reflects new totals
- **Validates:** Real-time monitoring workflow

**T10.3: New session creation**
- **Input:** Start monitor, create new session file
- **Expected:**
  - Watcher detects new file
  - Monitor discovers new session
  - Dashboard includes new session
- **Validates:** Dynamic session discovery

**T10.4: Alert threshold crossing**
- **Input:** Session at 79%, append messages to push to 81%
- **Expected:**
  - Alert level changes from none to warning
  - New alert appears in dashboard
- **Validates:** Alert trigger behavior

---

## Task 11: Documentation Validation

### Documentation Tests

**T11.1: README installation steps work**
- **Manual Test:** Follow README installation steps from scratch
- **Expected:** Virtual env created, dependencies installed, CLI runs
- **Validates:** User onboarding

**T11.2: Usage examples execute**
- **Manual Test:** Run each example command from README
- **Expected:** All examples work without modification
- **Validates:** Documentation accuracy

**T11.3: Troubleshooting scenarios**
- **Manual Test:** Simulate each troubleshooting scenario
- **Expected:** Suggested solutions resolve issues
- **Validates:** Support documentation

---

## Performance Tests

### Performance Validation

**P1: Parse 8MB file in <500ms**
- **Input:** Generate 8MB JSONL file with ~2000 messages
- **Expected:** parse_session_messages() completes in <500ms
- **Validates:** Parser performance target

**P2: File change detection in <1s**
- **Input:** Modify file while watcher running
- **Expected:** Callback invoked within 1000ms
- **Validates:** Responsiveness target

**P3: Memory usage <30MB**
- **Input:** Run monitor for 60 seconds with 10 active sessions
- **Expected:** RSS memory <30MB throughout
- **Validates:** Memory footprint target

**P4: CPU usage <2%**
- **Input:** Run monitor for 60 seconds with 10 active sessions
- **Expected:** Average CPU <2%
- **Validates:** CPU efficiency target

**P5: Incremental parsing overhead**
- **Input:** File with 1000 messages, read incrementally 10 times (100 messages each)
- **Expected:** Incremental reading <10% slower than full file read
- **Validates:** Incremental efficiency

---

## Error Handling Tests

### Error Scenarios

**E1: Corrupted JSONL file**
- **Input:** JSONL with half-written line at EOF
- **Expected:** Parses valid lines, skips incomplete line, logs warning
- **Validates:** Partial failure recovery

**E2: Permission denied on session file**
- **Input:** Session file with no read permission
- **Expected:** Logs error, continues with other sessions
- **Validates:** Access error handling

**E3: Rapidly changing files**
- **Input:** File being written while parser reads
- **Expected:** Parser handles gracefully, no crashes
- **Validates:** Race condition handling

**E4: Disk full during metric export**
- **Input:** Attempt to write metrics when disk full
- **Expected:** Logs error, continues monitoring
- **Validates:** I/O error handling

**E5: Invalid token count values**
- **Input:** Message with tokens="not a number"
- **Expected:** Defaults to 0 or skips message, logs warning
- **Validates:** Data validation

---

## Regression Tests

### Regression Prevention

**R1: Large message spike detection**
- **Input:** Message with 50K tokens
- **Expected:** Correctly identified as spike
- **Validates:** Prevents false negatives on large messages

**R2: Context window overflow**
- **Input:** Session with tokens > context_limit
- **Expected:** Alert level is critical, window_percent >100%
- **Validates:** Handles overflow scenario

**R3: Concurrent file access**
- **Input:** Two monitors reading same files simultaneously
- **Expected:** Both monitors function correctly, no corruption
- **Validates:** Thread safety

**R4: Session ID edge cases**
- **Input:** Session IDs with special characters, very long IDs
- **Expected:** Parsed and displayed correctly
- **Validates:** Input sanitization

---

## Test Execution Plan

### Phase 1: Unit Tests (Tasks 1-5)
Run after each task completion:
```bash
pytest tests/test_models.py -v
pytest tests/test_session_parser.py -v
```
**Pass Criteria:** All unit tests green, no warnings

### Phase 2: Integration Tests (Tasks 6-7)
Run after monitor and watcher complete:
```bash
pytest tests/test_monitor.py -v
pytest tests/test_session_watcher.py -v
```
**Pass Criteria:** All tests green, watcher tests <2s each

### Phase 3: UI and CLI Tests (Tasks 8-9)
Run after dashboard and CLI complete:
```bash
pytest tests/test_dashboard.py -v
pytest tests/test_cli.py -v
```
**Pass Criteria:** All tests green, JSON output valid

### Phase 4: End-to-End Tests (Task 10)
Run after all components integrated:
```bash
pytest tests/test_end_to_end.py -v --durations=0
```
**Pass Criteria:** Complete workflow test passes, <2s duration

### Phase 5: Full Test Suite
Run before marking MVP complete:
```bash
pytest -v --cov=src --cov-report=term-missing
```
**Pass Criteria:** 
- All tests pass
- Coverage >90% on core modules
- No performance test failures

### Phase 6: Performance Tests
Run as final validation:
```bash
pytest tests/ -k performance -v --durations=10
```
**Pass Criteria:** All performance targets met

---

## Success Criteria Summary

### MVP Complete When:

1. **All Functional Tests Pass**
   - 85+ test cases across all tasks
   - No skipped tests
   - No flaky tests (100% pass rate on 3 consecutive runs)

2. **Performance Targets Met**
   - Parse 8MB file <500ms ✓
   - File change detection <1s ✓
   - Memory <30MB ✓
   - CPU <2% ✓

3. **Integration Validated**
   - End-to-end test proves complete workflow ✓
   - CLI produces correct JSON output ✓
   - Real-time monitoring updates correctly ✓

4. **Documentation Verified**
   - Installation steps work on fresh system ✓
   - All usage examples execute correctly ✓
   - Troubleshooting covers common issues ✓

5. **User Validation Required**
   - Run against live OpenClaw sessions for 1 week
   - Confirm alerts are timely (within 2s of threshold crossing)
   - Measure session reset reduction (target: 50% fewer resets)

---

## Test Coverage Goals

### Coverage by Module

- **src/models.py**: 100% (pure data, no I/O)
- **src/session_parser.py**: 95%+ (core parsing logic)
- **src/session_watcher.py**: 85%+ (file system I/O)
- **src/monitor.py**: 90%+ (coordinator logic)
- **src/dashboard.py**: 80%+ (UI rendering)
- **src/cli.py**: 85%+ (CLI interface)

### Coverage Exclusions
- Logging statements
- Type checking branches
- Defensive assertions that can't be triggered
- Platform-specific code paths

---

## Test Data Requirements

### Fixtures Needed
- **sessions.json**: 4 variants (active, warning, critical, archived)
- **Session JSONL files**: 10+ files with varying token counts
- **Malformed data**: Corrupted JSON, missing fields, invalid types
- **Large files**: 8MB+ files for performance testing
- **Edge cases**: Empty files, single-line files, Unicode content

### Test Environment
- Python 3.8, 3.9, 3.10, 3.11, 3.12 (CI matrix)
- macOS and Linux (file watcher behavior differs)
- Tmp directories for isolation
- Mock OpenClaw state directory structure

---

## Notes

- Tests follow Red-Green-Refactor cycle strictly
- Each test has clear input, expected output, and validation target
- Integration tests prove components work together
- Performance tests have hard pass/fail thresholds
- Manual tests documented for one-time validation
- Test data includes realistic OpenClaw session structure
- Error handling tests ensure graceful degradation
- Regression tests prevent known failure modes

This test plan ensures the MVP meets all quality requirements and user needs before deployment.
