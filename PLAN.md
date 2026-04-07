# OpenClaw Session Monitor MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use trycycle-executing to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a real-time token usage monitoring tool that watches OpenClaw session files and displays live dashboard with alerts

**Architecture:** File watcher (watchdog) detects JSONL changes → Incremental parser extracts tokens → Live terminal UI (rich) displays sessions with alerts at 80%/90% thresholds

**Tech Stack:** Python 3.8+, watchdog (file monitoring), rich (terminal UI), pytest (testing)

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

## Approved Testing Strategy Summary

32 tests total from approved strategy:
- 10 Core Parsing tests (data correctness, error handling)
- 6 File Watcher tests (real-time detection, robustness)
- 12 Dashboard tests (user-visible behavior, alerts, performance)
- 4 Edge case tests (malformed data, missing files)

Each task below integrates tests from this strategy following Red/Green/Refactor TDD.

---

## Implementation Tasks

Tasks follow Red/Green/Refactor TDD:
1. Write failing test (based on approved testing strategy)
2. Run test - verify it fails  
3. Write minimal implementation
4. Run test - verify it passes
5. Refactor and verify
6. Commit

### Task 1: Data Models (Session, Message, Alert)

Build foundation data structures with computed properties (window percentage, alert levels, spike detection).

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

**Tests:** 9 tests for data class creation, percentage calculation, alert thresholds (80%/90%), spike detection (>10K tokens)

**Implementation:** Use `@dataclass` for Session/Message/Alert, add `@property` for window_percent, alert_level, is_spike

**Success:** All model tests pass, properties compute correctly

---

### Task 2: Session Parser (JSONL Reading)

Parse sessions.json and session JSONL files, extract token data, handle malformed JSON gracefully.

**Files:**
- Create: `src/session_parser.py`
- Create: `tests/test_session_parser.py`
- Create: `tests/fixtures/sessions.json`
- Create: `tests/fixtures/test-session-active.jsonl`

**Tests:** 6 tests for parsing sessions metadata, extracting messages with tokens, handling missing usage fields, skipping malformed lines

**Implementation:** JSON parsing with error handling, filter active sessions (status="active", no .reset/.deleted), extract usage.totalTokens

**Success:** Parser tests pass, malformed lines skipped with warnings

---

### Task 3: Incremental File Reading

Add position tracking to read only new messages (not entire file) for efficiency.

**Files:**
- Modify: `src/session_parser.py`
- Modify: `tests/test_session_parser.py`

**Tests:** 1 test for incremental reads returning (messages, position), verify only new messages read on subsequent calls

**Implementation:** Add `parse_session_messages_incremental(path, start_pos) -> (messages, new_pos)`, use binary mode with seeking, refactor original function to delegate

**Success:** Incremental test passes, original tests still pass

---

### Task 4: Session Monitor Coordinator

Discover sessions from filesystem, maintain registry, calculate tokens per session.

**Files:**
- Create: `src/monitor.py`
- Create: `tests/test_monitor.py`

**Tests:** Integration tests for discovering sessions from agents/*/sessions/sessions.json, calculating total tokens, maintaining session registry

**Implementation:** SessionMonitor class scans filesystem, uses parser functions, stores sessions dict with file positions

**Success:** Monitor loads sessions, calculates tokens correctly

---

### Task 5: File Watcher

Detect file changes with watchdog, emit events for modifications/creations.

**Files:**
- Create: `src/session_watcher.py`
- Create: `tests/test_session_watcher.py`

**Tests:** 2 tests for detecting file modifications (append to existing) and new file creation

**Implementation:** SessionWatcher wraps watchdog Observer, filters .jsonl files, calls callback on changes

**Success:** Watcher detects file changes within <1 second

---

### Task 6: Dashboard with Test Mode

Render sessions with rich UI (terminal) or JSON (test mode), color-code by alert level.

**Files:**
- Create: `src/dashboard.py`
- Create: `tests/test_dashboard.py`

**Tests:** 2 tests for JSON structure (sessions/alerts arrays), verify alert detection in test mode output

**Implementation:** Dashboard class with test_mode flag, JSON output includes session data + alerts array, rich UI with colored table

**Success:** Test mode outputs valid JSON, alerts included for 80%+ sessions

---

### Task 7: Integrate Monitor + Watcher

Wire watcher events to monitor, update session tokens on file changes.

**Files:**
- Modify: `src/monitor.py`
- Create: `tests/test_monitor_integration.py`

**Tests:** Integration test creating temp session file, starting watcher, appending message, verifying token update

**Implementation:** Add start_watching/stop_watching to SessionMonitor, handle file change events, call incremental parser, update registry

**Success:** Integration test shows token counts update when files change

---

### Task 8: CLI Watch Command

Implement `session-monitor watch` with environment variable support, graceful shutdown.

**Files:**
- Modify: `src/cli.py`
- Create: `tests/test_cli.py`

**Tests:** 2 CLI tests for starting monitor and test mode output

**Implementation:** cmd_watch function reads OPENCLAW_STATE_DIR/OPENCLAW_CONTEXT_TOKENS, starts monitor with watching, renders dashboard in loop, handles Ctrl+C

**Success:** CLI starts monitor, displays dashboard, exits cleanly

---

### Task 9: End-to-End Integration Test

Complete workflow test: realistic session files → watcher → parser → dashboard JSON output.

**Files:**
- Create: `tests/test_end_to_end.py`

**Tests:** 1 comprehensive test creating agents/main/sessions/ structure with 3 sessions (low/warning/critical tokens), running CLI in test mode, verifying JSON output

**Implementation:** Set up complete OpenClaw directory structure in temp, run CLI with --test-mode, parse JSON, verify all sessions present with correct tokens/alerts

**Success:** End-to-end test proves entire system works - highest value test

---

### Task 10: Documentation

Update README, create INSTALLATION.md and USAGE.md with examples and troubleshooting.

**Files:**
- Modify: `README.md`
- Create: `docs/INSTALLATION.md`
- Create: `docs/USAGE.md`

**Implementation:** Update README with MVP completion status, add installation guide (pip install, venv setup), usage guide (watch command options, dashboard interpretation, workflow recommendations)

**Success:** Documentation is clear, installation steps work, usage examples are complete

---

## Execution Notes

- Each task contains 6 steps: failing test → run → implement → pass → refactor → commit
- Complete code in every step (not "add validation" - show actual code)
- Exact commands with expected output
- Tests must pass for legitimate reasons (no weakening tests)
- Failed checks mean continue improving code, not stop

## MVP Success Criteria

After execution:
- All 32+ tests from approved strategy passing
- Parse 8MB file <500ms
- File change detection <1s  
- Memory <30MB, CPU <2%
- Dashboard displays sessions with correct alerts (green/yellow/red)

User verification required:
- Run against live OpenClaw sessions for 1 week
- Confirm alerts are timely and accurate
- Measure session reset reduction (target: 50% fewer resets)

## Notes

- Refer to PLAN-strategic.md for architectural decisions, research findings, risk analysis, and future phases
- This plan covers MVP only (Phases 1-3: Parser, Watcher, Dashboard)
- Optional Phases 4-5 (Analysis, Metrics) deferred until MVP validated by user

---

## Approved Testing Strategy Summary

32 tests total from approved strategy:
- 10 Core Parsing tests (data correctness, error handling)
- 6 File Watcher tests (real-time detection, robustness)
- 12 Dashboard tests (user-visible behavior, alerts, performance)
- 4 Edge case tests (malformed data, missing files)

Each task below integrates tests from this strategy following Red/Green/Refactor TDD.

---

