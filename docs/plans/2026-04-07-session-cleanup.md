# Session Cleanup Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use trycycle-executing to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `session-monitor cleanup` command that wraps OpenClaw's `openclaw sessions cleanup` command to provide preview, confirmation, and better error messaging for cleaning up old registered sessions across all agents.

**Architecture:** CLI command → Run OpenClaw cleanup in dry-run mode → Display preview to user → Confirm → Execute with --enforce flag → Report results. Delegates all session selection and cleanup logic to OpenClaw's native mechanism, which operates on registered sessions in sessions.json (not orphaned files).

**Tech Stack:** Python 3.8+, subprocess module (with timeout) for OpenClaw CLI integration, existing CLI patterns from cmd_watch()

**User Requirements:**
- Use OpenClaw's native cleanup mechanism (`openclaw sessions cleanup`)
- Clean all registered sessions across all agents (not orphaned files - out of scope for this simple wrapper)
- Show preview before deletion
- Require confirmation
- Support --dry-run (preview only) and --force (skip confirmation) flags
- Keep it simple—delegate to OpenClaw rather than reimplementing

**All commands run from:** `/Volumes/RayCue-Drive/Documents/projects/openclaw-session-monitor/.worktrees/add-session-cleanup` with `.venv` activated via `source ../../.venv/bin/activate`

---

## File Structure

**New Files:**
- `tests/test_cleanup_cli.py` - Test CLI integration (mocked subprocess)

**Modified Files:**
- `src/cli.py` - Add `cleanup` subcommand that wraps OpenClaw CLI
- `README.md` - Document cleanup command

**Rationale:**
- No new cleanup.py or models needed—just CLI command that shells out to OpenClaw
- All logic in cli.py keeps it simple and avoids premature abstraction
- Tests mock subprocess.run() to verify command construction and error handling
- Subprocess calls include 30-second timeout to prevent hangs
- Follows user's preference: "use openclaw's native approach unless LOE is too high"
- Orphaned .jsonl file cleanup excluded (would require filesystem scanning, validation logic - too high LOE for nice-to-have feature)

---

## Implementation Tasks

### Task 12: Add Cleanup Command to CLI (TDD Red-Green-Refactor)

**Goal:** Implement `session-monitor cleanup` command using proper TDD workflow - one test at a time

**Files:**
- Modify: `src/cli.py` (116 lines currently)
- Create: `tests/test_cleanup_cli.py`

---

#### Subtask 12.1: Basic cleanup command structure

- [ ] **Step 1 (Red): Write first test - command registration**

Create `tests/test_cleanup_cli.py`:
```python
"""Tests for cleanup CLI command."""

import sys
import subprocess
from unittest.mock import patch, MagicMock
import pytest
from src.cli import main


def test_cleanup_command_dry_run_calls_openclaw():
    """Test cleanup --dry-run calls openclaw sessions cleanup --dry-run."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Cleanup preview:\nWould prune 3 sessions\nTotal: 12.5 MB",
            stderr=""
        )
        
        with patch('sys.argv', ['session-monitor', 'cleanup', '--dry-run']):
            result = main()
        
        # Verify openclaw command was called correctly
        mock_run.assert_called_once()
        args = mock_run.call_args
        assert args[0][0] == ['openclaw', 'sessions', 'cleanup', '--dry-run', '--all-agents']
        assert args[1]['capture_output'] == True
        assert args[1]['text'] == True
        assert args[1]['timeout'] == 30  # Prevent hangs
        assert result == 0
```

Run test:
```bash
pytest tests/test_cleanup_cli.py::test_cleanup_command_dry_run_calls_openclaw -v
# Expected: FAIL - cleanup command doesn't exist
```

- [ ] **Step 2 (Green): Implement minimal cleanup command**

Modify `src/cli.py`:

After line 6 (after existing imports), add:
```python
import subprocess
```

After line 50 (after `report_parser` definition), before line 52 (`args = parser.parse_args()`), add cleanup subparser:
```python
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old sessions via OpenClaw")
    cleanup_parser.add_argument("--dry-run", action="store_true", 
                                help="Preview what would be cleaned without actually cleaning")
    cleanup_parser.add_argument("--force", action="store_true",
                                help="Skip confirmation prompt")
```

Replace lines 58-63 (command dispatch) with:
```python
    if args.command == "watch":
        return cmd_watch(args)
    elif args.command == "cleanup":
        return cmd_cleanup(args)
    else:
        print(f"Command '{args.command}' not yet implemented.")
        print("See PLAN.md for implementation phases.")
        return 1
```

After line 112 (end of `cmd_watch` function), before line 115 (`if __name__`), add:
```python


def cmd_cleanup(args):
    """Execute cleanup command via OpenClaw CLI."""
    print("Checking for sessions to clean up...")
    print()
    
    try:
        result = subprocess.run(
            ['openclaw', 'sessions', 'cleanup', '--dry-run', '--all-agents'],
            capture_output=True,
            text=True,
            timeout=30,  # Prevent indefinite hangs
            check=False
        )
    except FileNotFoundError:
        print("Error: 'openclaw' command not found")
        print("Make sure OpenClaw CLI is installed and in your PATH")
        return 1
    except subprocess.TimeoutExpired:
        print("Error: OpenClaw cleanup timed out after 30 seconds")
        return 1
    
    if result.returncode != 0:
        print("Error running OpenClaw cleanup:")
        print(result.stderr)
        return 1
    
    # Display preview
    print(result.stdout)
    print()
    
    if args.dry_run:
        print("Preview only (--dry-run). No sessions were deleted.")
        return 0
    
    # For now, just stop at preview - we'll add confirmation in next test
    print("Cleanup cancelled (confirmation not yet implemented).")
    return 0
```

Run test:
```bash
pytest tests/test_cleanup_cli.py::test_cleanup_command_dry_run_calls_openclaw -v
# Expected: PASS
```

- [ ] **Step 3 (Refactor): Verify subprocess call structure**

Check that timeout is included and error handling is correct. No refactor needed yet - code is clean.

Run test again:
```bash
pytest tests/test_cleanup_cli.py::test_cleanup_command_dry_run_calls_openclaw -v
# Expected: PASS
```

- [ ] **Step 4: Commit**
```bash
git add src/cli.py tests/test_cleanup_cli.py
git commit -m "feat: add cleanup command - dry-run support

Add basic cleanup command that:
- Registers cleanup subcommand with --dry-run and --force flags
- Calls openclaw sessions cleanup --dry-run with 30s timeout
- Handles FileNotFoundError and TimeoutExpired
- Displays preview output"
```

---

#### Subtask 12.2: Add confirmation flow

- [ ] **Step 1 (Red): Write test for interactive confirmation**

Add to `tests/test_cleanup_cli.py`:
```python


def test_cleanup_command_interactive_confirmation_yes(monkeypatch):
    """Test cleanup with interactive confirmation (user says yes)."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Would prune 5 sessions", stderr=""),
            MagicMock(returncode=0, stdout="Pruned 5 sessions", stderr="")
        ]
        
        # Mock input to return 'y'
        monkeypatch.setattr('builtins.input', lambda _: 'y')
        
        with patch('sys.argv', ['session-monitor', 'cleanup']):
            result = main()
        
        # Should call twice: preview then enforce
        assert mock_run.call_count == 2
        # Second call should use --enforce
        assert '--enforce' in mock_run.call_args_list[1][0][0]
        assert result == 0
```

Run test:
```bash
pytest tests/test_cleanup_cli.py::test_cleanup_command_interactive_confirmation_yes -v
# Expected: FAIL - confirmation not implemented
```

- [ ] **Step 2 (Green): Implement confirmation and enforce**

Modify `src/cli.py`, replace the "For now, just stop" section (last 3 lines of `cmd_cleanup`) with:
```python
    # Confirm with user (unless --force)
    if not args.force:
        response = input("Proceed with cleanup? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Cleanup cancelled.")
            return 0
    
    # Run actual cleanup
    print("Cleaning up sessions...")
    print()
    
    try:
        result = subprocess.run(
            ['openclaw', 'sessions', 'cleanup', '--enforce', '--all-agents'],
            capture_output=True,
            text=True,
            timeout=30,
            check=False
        )
    except FileNotFoundError:
        print("Error: 'openclaw' command not found")
        return 1
    except subprocess.TimeoutExpired:
        print("Error: OpenClaw cleanup timed out after 30 seconds")
        return 1
    
    if result.returncode != 0:
        print("Error during cleanup:")
        print(result.stderr)
        return 1
    
    # Display results
    print(result.stdout)
    print()
    print("Cleanup complete!")
    
    return 0
```

Run test:
```bash
pytest tests/test_cleanup_cli.py::test_cleanup_command_interactive_confirmation_yes -v
# Expected: PASS
```

- [ ] **Step 3 (Refactor): Extract duplicate subprocess call logic**

Review code - there's duplication in subprocess error handling. Consider extracting, but keep it simple. For now, leave as-is since it's only 2 calls and extraction would add complexity.

Run all tests:
```bash
pytest tests/test_cleanup_cli.py -v
# Expected: 2 tests PASS
```

- [ ] **Step 4: Commit**
```bash
git add src/cli.py tests/test_cleanup_cli.py
git commit -m "feat: add cleanup confirmation and enforce

Add interactive confirmation with:
- User prompt when not using --force flag
- Second subprocess call with --enforce flag if confirmed
- Timeout and error handling for enforce call"
```

---

#### Subtask 12.3: Add remaining test cases

- [ ] **Step 1 (Red): Add test for cancellation**

Add to `tests/test_cleanup_cli.py`:
```python


def test_cleanup_command_interactive_confirmation_no(monkeypatch):
    """Test cleanup with interactive confirmation (user says no)."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Would prune 5 sessions",
            stderr=""
        )
        
        # Mock input to return 'n'
        monkeypatch.setattr('builtins.input', lambda _: 'n')
        
        with patch('sys.argv', ['session-monitor', 'cleanup']):
            result = main()
        
        # Should only call once (preview), not enforce
        assert mock_run.call_count == 1
        assert result == 0
```

Run test:
```bash
pytest tests/test_cleanup_cli.py::test_cleanup_command_interactive_confirmation_no -v
# Expected: PASS (should already work)
```

- [ ] **Step 2 (Green): Test for force flag**

Add to `tests/test_cleanup_cli.py`:
```python


def test_cleanup_command_force_skips_confirmation():
    """Test cleanup --force skips confirmation prompt."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Would prune 2 sessions", stderr=""),
            MagicMock(returncode=0, stdout="Pruned 2 sessions successfully", stderr="")
        ]
        
        with patch('sys.argv', ['session-monitor', 'cleanup', '--force']):
            result = main()
        
        # Should call twice: once for preview, once for enforce
        assert mock_run.call_count == 2
        assert result == 0
```

Run test:
```bash
pytest tests/test_cleanup_cli.py::test_cleanup_command_force_skips_confirmation -v
# Expected: PASS (should already work)
```

- [ ] **Step 3 (Red): Add error handling tests**

Add to `tests/test_cleanup_cli.py`:
```python


def test_cleanup_command_openclaw_not_found():
    """Test cleanup gracefully handles openclaw command not found."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = FileNotFoundError("openclaw: command not found")
        
        with patch('sys.argv', ['session-monitor', 'cleanup', '--dry-run']):
            result = main()
        
        # Should return error code
        assert result == 1


def test_cleanup_command_openclaw_error():
    """Test cleanup handles openclaw returning error."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: permission denied"
        )
        
        with patch('sys.argv', ['session-monitor', 'cleanup', '--dry-run']):
            result = main()
        
        # Should return error code
        assert result == 1


def test_cleanup_command_timeout():
    """Test cleanup handles timeout gracefully."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired('openclaw', 30)
        
        with patch('sys.argv', ['session-monitor', 'cleanup', '--dry-run']):
            result = main()
        
        # Should return error code
        assert result == 1
```

Run tests:
```bash
pytest tests/test_cleanup_cli.py -v
# Expected: All 7 tests PASS (should already work)
```

- [ ] **Step 4 (Refactor): Review all error paths and improve messaging**

Manual test of error messages:
```bash
session-monitor --help  # Should show cleanup in command list
session-monitor cleanup --help  # Should show flags
```

Review code for clarity and consistency. Refactor if needed.

Run full test suite:
```bash
pytest tests/test_cleanup_cli.py -v
# Expected: All 7 tests PASS
```

- [ ] **Step 5: Commit**
```bash
git add src/cli.py tests/test_cleanup_cli.py
git commit -m "test: add comprehensive cleanup command tests

Add tests for:
- Interactive cancellation (user says no)
- Force flag (skips confirmation)
- FileNotFoundError handling
- Non-zero exit code handling
- Timeout handling

All 7 tests passing."
```

---

### Task 13: Document Cleanup Command

**Goal:** Add cleanup command documentation to README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write test for README content (manual verification)**

Read current README structure:
```bash
cat README.md | head -50
# Identify where to add cleanup documentation
```

- [ ] **Step 2: Add cleanup documentation to README**

In `README.md`, find the "Commands" or "Usage" section (after the "Historical Metrics" section) and add:

```markdown
### Cleanup Old Sessions

Clean up old registered sessions using OpenClaw's native cleanup mechanism:

```bash
# Preview what would be cleaned (no changes made)
session-monitor cleanup --dry-run

# Interactive cleanup with confirmation
session-monitor cleanup

# Force cleanup without confirmation
session-monitor cleanup --force
```

**How it works:**
- Delegates to OpenClaw's `openclaw sessions cleanup --all-agents` command
- Always shows preview before deleting
- Cleans sessions registered in sessions.json according to OpenClaw's maintenance configuration
- Respects OpenClaw's session lifecycle and internal criteria

**What gets cleaned:**
- Registered sessions tracked in sessions.json across all agents (main, claude, etc.)
- Sessions selected by OpenClaw's maintenance settings

**What does NOT get cleaned:**
- Orphaned .jsonl files not tracked in sessions.json (would require custom file scanning - out of scope)

**Configuration:**
OpenClaw determines which sessions to clean based on its maintenance settings in `openclaw.json`. To configure retention policies, see OpenClaw's documentation for maintenance configuration options.

**Note:** 
- This command is a convenience wrapper providing preview and confirmation
- You can also run `openclaw sessions cleanup --enforce --all-agents` directly
- If OpenClaw reports "0 sessions to prune", your maintenance config may need adjustment
```

Save file.

- [ ] **Step 3: Verify documentation accuracy**

Read through README:
```bash
cat README.md
# Verify cleanup section is clear and accurate
```

Check for:
- Command examples are correct
- Flags are documented
- Expectations are clear (delegates to OpenClaw)
- Tone matches rest of README

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add cleanup command documentation"
```

---

## Completion Criteria

Task is complete when:
- [ ] All 7 tests pass (`pytest tests/test_cleanup_cli.py -v` shows all green)
- [ ] Cleanup command accessible via `session-monitor cleanup`
- [ ] `session-monitor cleanup --dry-run` shows preview without making changes
- [ ] `session-monitor cleanup` prompts for confirmation before cleaning
- [ ] `session-monitor cleanup --force` skips confirmation and cleans immediately
- [ ] Error handling is graceful for all cases:
  - [ ] Missing openclaw command (FileNotFoundError)
  - [ ] OpenClaw returns non-zero exit code
  - [ ] OpenClaw times out after 30 seconds (TimeoutExpired)
- [ ] README documents cleanup command with:
  - [ ] Clear examples of all three usage modes
  - [ ] Explanation of what gets cleaned (registered sessions) and what doesn't (orphaned files)
  - [ ] Note about OpenClaw maintenance configuration
- [ ] No regressions in existing functionality (`session-monitor watch` still works)
- [ ] Manual verification acceptance test:
  - [ ] Run `session-monitor cleanup --dry-run` shows preview
  - [ ] Run `session-monitor cleanup` prompts and executes on "y"
  - [ ] Verify output is readable and error messages are helpful

---

## Testing Strategy

**Unit tests (test_cleanup_cli.py) - 7 total:**
1. `test_cleanup_command_dry_run_calls_openclaw` - Verifies basic dry-run flow and subprocess call structure
2. `test_cleanup_command_interactive_confirmation_yes` - Verifies confirmation prompt and enforce call
3. `test_cleanup_command_interactive_confirmation_no` - Verifies cancellation stops at preview
4. `test_cleanup_command_force_skips_confirmation` - Verifies --force flag skips prompt
5. `test_cleanup_command_openclaw_not_found` - Verifies FileNotFoundError handling
6. `test_cleanup_command_openclaw_error` - Verifies non-zero exit code handling
7. `test_cleanup_command_timeout` - Verifies TimeoutExpired handling

**Mocking approach:**
- Mock `subprocess.run()` to test command construction
- Mock `builtins.input` to test confirmation flow
- Verify timeout=30 is passed to prevent hangs
- Tests don't require OpenClaw installation or modify real data
- Fast, predictable, repeatable test execution

**Manual verification acceptance test (required before completion):**
Run these three commands against real OpenClaw installation:

1. **Preview mode:**
   ```bash
   session-monitor cleanup --dry-run
   ```
   ✅ Success if: Shows list of sessions to clean, displays sizes, exits without deleting

2. **Interactive mode:**
   ```bash
   session-monitor cleanup
   # Type 'y' at prompt
   ```
   ✅ Success if: Shows preview, prompts "Proceed with cleanup? (y/N):", actually deletes sessions, shows "Cleanup complete!"

3. **Error handling:**
   ```bash
   PATH=/usr/bin:/bin session-monitor cleanup --dry-run
   ```
   ✅ Success if: Shows clear error "openclaw command not found" with helpful message

**Why manual verification is still required:**
- Validates real OpenClaw command format hasn't changed
- Confirms preview output is actually readable for users
- Catches integration issues with OpenClaw's current version
- Verifies user experience is smooth (error messages make sense)

---

## Remember

- **YAGNI**: Don't build custom filtering/preview when OpenClaw provides it
- **User requirement**: "use openclaw's native approach unless LOE is too high"
- **Simplicity**: 1 CLI command, 2 subprocess calls, done
- **Safety**: Always preview first, confirm before deletion
- **Delegation**: Let OpenClaw handle all cleanup logic and decisions
- **Testing**: Mock for unit tests, manual verify for integration
- **DRY**: All commands run from workspace root with .venv activated
