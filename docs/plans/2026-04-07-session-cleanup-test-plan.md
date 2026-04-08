# Session Cleanup Command Test Plan

**Date:** 2026-04-07  
**Feature:** `session-monitor cleanup` command  
**Implementation Plan:** [2026-04-07-session-cleanup.md](./2026-04-07-session-cleanup.md)

---

## Strategy Reconciliation

The implementation plan defines a clear testing strategy using TDD with mocked subprocess calls. This analysis verifies the strategy is complete and identifies no changes requiring user approval.

### Implementation Architecture Review

**Planned approach:**
- CLI command wrapper around OpenClaw's native `openclaw sessions cleanup`
- Subprocess calls: one for dry-run preview, one for enforce execution
- Simple confirmation flow with --dry-run and --force flags
- All cleanup logic delegated to OpenClaw (no custom session selection)

**Testing strategy alignment:**
- ✅ Strategy correctly assumes subprocess mocking as primary test mechanism
- ✅ No external dependencies beyond OpenClaw CLI (already available)
- ✅ Command construction and error handling are the critical test surfaces
- ✅ Manual acceptance test for integration validation is appropriate
- ✅ No performance concerns (simple subprocess wrapper)

**Coverage assessment:**
- The 7 planned unit tests in the implementation plan cover all code paths
- Mocking strategy correctly isolates the wrapper from OpenClaw availability
- User-facing surface is simple (CLI flags + preview output + confirmation)
- No additional tests needed beyond what the implementation plan specifies

**Conclusion:** Testing strategy is complete. No adjustments required.

---

## Test Plan

Tests are ordered by implementation sequence (TDD red-green-refactor) as specified in the implementation plan. All tests use pytest with mocked subprocess calls.

### Test 1: Dry-run calls OpenClaw correctly

**Name:** Cleanup dry-run constructs correct subprocess command  
**Type:** Integration (CLI → subprocess boundary)  
**Disposition:** New  
**Harness:** pytest + unittest.mock for subprocess  

**Preconditions:**
- `src/cli.py` has basic cleanup command registered
- Test file `tests/test_cleanup_cli.py` exists

**Actions:**
1. Mock `subprocess.run()` to return success with preview output
2. Invoke CLI with `['session-monitor', 'cleanup', '--dry-run']`
3. Capture subprocess call arguments

**Expected outcome:**
- Source of truth: OpenClaw CLI documentation (command format verified in implementation plan)
- subprocess.run called once with:
  - Command: `['openclaw', 'sessions', 'cleanup', '--dry-run', '--all-agents']`
  - `capture_output=True`, `text=True`, `timeout=30`
- CLI returns exit code 0
- Preview output displayed to user

**Interactions:**
- subprocess module (mocked)
- sys.argv parsing (mocked via patch)

**Implementation phase:** Subtask 12.1, Steps 1-2

---

### Test 2: Interactive confirmation executes on yes

**Name:** Cleanup confirmation flow proceeds when user confirms  
**Type:** Scenario (user accepts confirmation)  
**Disposition:** New  
**Harness:** pytest + monkeypatch for input mocking  

**Preconditions:**
- Test 1 passes (dry-run working)
- Confirmation logic implemented in cmd_cleanup()

**Actions:**
1. Mock subprocess.run() to return success twice (preview + enforce)
2. Mock builtins.input to return 'y'
3. Invoke CLI with `['session-monitor', 'cleanup']` (no flags)
4. Capture subprocess call count and arguments

**Expected outcome:**
- Source of truth: Implementation plan requirement "require confirmation before deletion"
- subprocess.run called exactly twice:
  - First call: `--dry-run` (preview)
  - Second call: `--enforce` (actual cleanup)
- Both calls include `--all-agents`, `timeout=30`
- CLI returns exit code 0
- Confirmation prompt displayed: "Proceed with cleanup? (y/N): "

**Interactions:**
- subprocess module (mocked, 2 calls)
- builtins.input (mocked)
- sys.stdout (confirmation prompt)

**Implementation phase:** Subtask 12.2, Steps 1-2

---

### Test 3: Interactive confirmation cancels on no

**Name:** Cleanup confirmation flow cancels when user declines  
**Type:** Scenario (user rejects confirmation)  
**Disposition:** New  
**Harness:** pytest + monkeypatch for input mocking  

**Preconditions:**
- Test 2 passes (confirmation working)

**Actions:**
1. Mock subprocess.run() to return success (preview only)
2. Mock builtins.input to return 'n'
3. Invoke CLI with `['session-monitor', 'cleanup']`
4. Verify subprocess call count

**Expected outcome:**
- Source of truth: Implementation plan requirement "require confirmation"
- subprocess.run called exactly once (preview only)
- No --enforce call made
- CLI returns exit code 0
- Cancellation message displayed: "Cleanup cancelled."

**Interactions:**
- subprocess module (mocked, 1 call)
- builtins.input (mocked)

**Implementation phase:** Subtask 12.3, Step 1

---

### Test 4: Force flag skips confirmation

**Name:** Cleanup --force bypasses user prompt  
**Type:** Integration (flag handling)  
**Disposition:** New  
**Harness:** pytest + unittest.mock  

**Preconditions:**
- Test 2 passes (confirmation working)
- --force flag registered in argument parser

**Actions:**
1. Mock subprocess.run() to return success twice
2. Invoke CLI with `['session-monitor', 'cleanup', '--force']`
3. Verify no input() call is made

**Expected outcome:**
- Source of truth: Implementation plan requirement "--force (skip confirmation)"
- subprocess.run called twice (preview + enforce)
- No call to builtins.input
- CLI returns exit code 0
- No "if not args.force:" branch entered

**Interactions:**
- subprocess module (mocked, 2 calls)
- builtins.input should NOT be called

**Implementation phase:** Subtask 12.3, Step 2

---

### Test 5: OpenClaw not found error handling

**Name:** Cleanup handles missing openclaw command gracefully  
**Type:** Boundary (error condition)  
**Disposition:** New  
**Harness:** pytest + unittest.mock  

**Preconditions:**
- Basic cleanup command implemented

**Actions:**
1. Mock subprocess.run() to raise FileNotFoundError
2. Invoke CLI with `['session-monitor', 'cleanup', '--dry-run']`
3. Capture stdout and exit code

**Expected outcome:**
- Source of truth: Implementation plan error handling requirements
- CLI returns exit code 1
- Error message displayed:
  - "Error: 'openclaw' command not found"
  - "Make sure OpenClaw CLI is installed and in your PATH"
- No exception bubbles up to user

**Interactions:**
- subprocess module (mocked, raises FileNotFoundError)
- sys.stderr or sys.stdout (error message)

**Implementation phase:** Subtask 12.3, Step 3

---

### Test 6: OpenClaw error exit code handling

**Name:** Cleanup handles non-zero openclaw exit codes  
**Type:** Boundary (error condition)  
**Disposition:** New  
**Harness:** pytest + unittest.mock  

**Preconditions:**
- Basic cleanup command implemented

**Actions:**
1. Mock subprocess.run() to return MagicMock with returncode=1, stderr="Error: permission denied"
2. Invoke CLI with `['session-monitor', 'cleanup', '--dry-run']`
3. Capture stdout and exit code

**Expected outcome:**
- Source of truth: Implementation plan error handling requirements
- CLI returns exit code 1
- Error message displayed:
  - "Error running OpenClaw cleanup:"
  - stderr content from OpenClaw
- subprocess called with check=False (allows error codes through)

**Interactions:**
- subprocess module (mocked, returns error)
- sys.stderr or sys.stdout (error propagation)

**Implementation phase:** Subtask 12.3, Step 3

---

### Test 7: Timeout handling

**Name:** Cleanup handles openclaw timeout gracefully  
**Type:** Boundary (error condition)  
**Disposition:** New  
**Harness:** pytest + unittest.mock  

**Preconditions:**
- Basic cleanup command implemented with timeout parameter

**Actions:**
1. Mock subprocess.run() to raise subprocess.TimeoutExpired('openclaw', 30)
2. Invoke CLI with `['session-monitor', 'cleanup', '--dry-run']`
3. Capture stdout and exit code

**Expected outcome:**
- Source of truth: Implementation plan timeout requirement (30 seconds)
- CLI returns exit code 1
- Error message displayed: "Error: OpenClaw cleanup timed out after 30 seconds"
- No exception bubbles up to user

**Interactions:**
- subprocess module (mocked, raises TimeoutExpired)
- sys.stderr or sys.stdout (timeout message)

**Implementation phase:** Subtask 12.3, Step 3

---

## Manual Acceptance Tests

These tests validate integration with real OpenClaw installation. Run after all automated tests pass, before marking feature complete.

### Manual Test 1: Preview mode

**Name:** Cleanup dry-run shows preview without deleting  
**Type:** Integration (real OpenClaw)  
**Disposition:** New  
**Harness:** User terminal, real OpenClaw CLI  

**Preconditions:**
- OpenClaw installed and `openclaw` command in PATH
- session-monitor installed in .venv
- At least one registered session exists in sessions.json

**Actions:**
1. Run: `session-monitor cleanup --dry-run`
2. Observe output
3. Check sessions.json for changes

**Expected outcome:**
- Source of truth: OpenClaw CLI behavior + implementation plan requirements
- Displays preview text from OpenClaw (session count, size estimates)
- Message: "Preview only (--dry-run). No sessions were deleted."
- Exit code 0
- sessions.json unchanged
- No .jsonl files deleted

**Success criteria:**
- ✅ Preview output is readable and informative
- ✅ No actual deletion occurs
- ✅ Command completes in <5 seconds

---

### Manual Test 2: Interactive cleanup

**Name:** Cleanup prompts and executes on confirmation  
**Type:** Scenario (real user interaction)  
**Disposition:** New  
**Harness:** User terminal, real OpenClaw CLI  

**Preconditions:**
- OpenClaw installed and functional
- Test sessions available (or use OpenClaw's maintenance config to target old sessions)

**Actions:**
1. Run: `session-monitor cleanup`
2. Review preview output
3. Type 'y' at prompt
4. Observe execution and results

**Expected outcome:**
- Source of truth: Implementation plan requirements + OpenClaw cleanup behavior
- Shows preview (session count, sizes)
- Displays prompt: "Proceed with cleanup? (y/N): "
- After 'y': shows "Cleaning up sessions..."
- Displays OpenClaw's cleanup results
- Message: "Cleanup complete!"
- Exit code 0
- sessions.json reflects cleanup (removed sessions)

**Success criteria:**
- ✅ Preview is clear and accurate
- ✅ Prompt is obvious and safe (defaults to N)
- ✅ Execution feedback is reassuring
- ✅ Results match preview expectations

---

### Manual Test 3: Error handling

**Name:** Cleanup shows helpful error when openclaw unavailable  
**Type:** Boundary (real error condition)  
**Disposition:** New  
**Harness:** User terminal with restricted PATH  

**Preconditions:**
- session-monitor installed

**Actions:**
1. Run with restricted PATH: `PATH=/usr/bin:/bin session-monitor cleanup --dry-run`
2. Observe error message

**Expected outcome:**
- Source of truth: Implementation plan error handling requirements
- Clear error message:
  - "Error: 'openclaw' command not found"
  - "Make sure OpenClaw CLI is installed and in your PATH"
- Exit code 1
- No confusing stack traces

**Success criteria:**
- ✅ Error message is actionable
- ✅ User understands what to fix
- ✅ No technical jargon or stack traces

---

## Coverage Summary

### Automated Test Coverage

**Command construction and subprocess interaction:**
- ✅ Dry-run flag mapping (Test 1)
- ✅ Enforce flag mapping (Tests 2, 4)
- ✅ --all-agents flag inclusion (Tests 1, 2, 4)
- ✅ Timeout parameter (Tests 1-7)
- ✅ Capture output settings (Test 1)

**User interaction flow:**
- ✅ Interactive confirmation - yes path (Test 2)
- ✅ Interactive confirmation - no path (Test 3)
- ✅ Force flag - skip confirmation (Test 4)
- ✅ Dry-run flag - skip enforcement (Test 1)

**Error handling:**
- ✅ FileNotFoundError (openclaw not installed) (Test 5)
- ✅ Non-zero exit codes (openclaw errors) (Test 6)
- ✅ TimeoutExpired (hanging openclaw) (Test 7)

**Code paths covered:** 100% of cmd_cleanup() function  
**Mocking approach:** Isolates wrapper from OpenClaw availability  
**Execution speed:** <1 second for all 7 automated tests  

### Manual Test Coverage

**Real OpenClaw integration:**
- ✅ Preview accuracy (Manual Test 1)
- ✅ Actual cleanup execution (Manual Test 2)
- ✅ User experience validation (Manual Tests 1-3)

**User-facing surface validation:**
- ✅ Output readability and formatting
- ✅ Error message helpfulness
- ✅ Confirmation prompt clarity

### Explicitly Excluded

Per implementation plan scope limitations:

**Out of scope - not tested:**
- ❌ Orphaned .jsonl file cleanup (requires custom file scanning - too high LOE)
- ❌ Custom session filtering (delegates entirely to OpenClaw's maintenance config)
- ❌ OpenClaw maintenance configuration management (user configures OpenClaw directly)
- ❌ Session selection criteria validation (trusts OpenClaw's judgment)

**Risks of exclusions:**
- **Low risk:** OpenClaw's native cleanup is well-tested upstream
- **Low risk:** Orphaned files are rare (only occur if sessions.json is manually edited)
- **Mitigation:** README documentation explains what gets cleaned and what doesn't

### Testing Gaps and Mitigation

**Gap 1: OpenClaw command format stability**  
- **Risk:** OpenClaw CLI syntax could change in future versions
- **Mitigation:** Manual acceptance tests catch breaking changes before users do
- **Detection:** Manual Test 1 will fail with clear error if format changes

**Gap 2: Preview output format assumptions**  
- **Risk:** Tests don't validate that OpenClaw's preview output is actually useful
- **Mitigation:** Manual Test 1 explicitly validates readability
- **Detection:** User feedback if preview is unclear

**Gap 3: Concurrent cleanup execution**  
- **Risk:** What if user runs cleanup while OpenClaw is actively using sessions?
- **Mitigation:** OpenClaw handles locking (not session-monitor's responsibility)
- **Detection:** OpenClaw would return error, caught by Test 6

---

## Test Execution Order

### TDD Implementation Sequence

Follow implementation plan exactly:

1. **Subtask 12.1:** Test 1 (red → green → refactor)
2. **Subtask 12.2:** Test 2 (red → green → refactor)
3. **Subtask 12.3:** Tests 3-7 (all should pass immediately, verify coverage)

### Pre-Completion Validation

After all automated tests pass:

1. Run full test suite: `pytest tests/test_cleanup_cli.py -v`
2. Verify 7/7 tests passing
3. Execute Manual Test 1 (dry-run)
4. Execute Manual Test 2 (interactive cleanup)
5. Execute Manual Test 3 (error handling)

### Success Criteria

Feature is complete when:
- ✅ All 7 automated tests passing
- ✅ All 3 manual tests successful
- ✅ README documentation added (Task 13)
- ✅ No regressions in existing tests (`pytest tests/` all green)
- ✅ Help text accurate (`session-monitor cleanup --help`)

---

## Sources of Truth

All test expectations derive from:

1. **Implementation plan** (2026-04-07-session-cleanup.md) - Requirements and architecture
2. **OpenClaw CLI documentation** - Command format and behavior (`openclaw sessions cleanup --help`)
3. **User requirements** (in implementation plan) - Feature specifications
4. **Python subprocess documentation** - Error types and timeout behavior
5. **Existing test patterns** (tests/conftest.py, tests/test_*.py) - Test style conventions

---

## Notes

- **TDD approach:** Tests written before implementation (red-green-refactor)
- **Fast feedback:** Mocked tests run in <1s, no OpenClaw dependency
- **Integration validation:** Manual tests catch real-world issues mocks miss
- **Simplicity bias:** Tests match simple implementation (no premature abstraction)
- **User focus:** Manual tests validate user experience, not just code correctness
