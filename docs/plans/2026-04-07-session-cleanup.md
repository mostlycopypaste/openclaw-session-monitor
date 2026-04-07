# Session Cleanup Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use trycycle-executing to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `session-monitor cleanup` command that provides a simple, safe wrapper around OpenClaw's native `openclaw sessions cleanup` command with preview and confirmation.

**Architecture:** CLI command → Run OpenClaw cleanup in dry-run mode → Display preview to user → Confirm → Execute with --enforce flag → Report results. No custom filtering or preview logic—delegate everything to OpenClaw's native mechanism.

**Tech Stack:** Python 3.8+, subprocess module for OpenClaw CLI integration, existing CLI patterns from cmd_watch()

**User Requirements:**
- Use OpenClaw's native cleanup mechanism (`openclaw sessions cleanup`)
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
- Tests mock subprocess.run() to verify command construction
- Follows user's preference: "use openclaw's native approach unless LOE is too high"

---

## Implementation Tasks

### Task 12: Add Cleanup Command to CLI

**Goal:** Implement `session-monitor cleanup` command that wraps `openclaw sessions cleanup` with preview and confirmation

**Files:**
- Modify: `src/cli.py`
- Create: `tests/test_cleanup_cli.py`

- [ ] **Step 1 (Red): Write failing test for cleanup command structure**

Add to `tests/test_cleanup_cli.py`:

```python
"""Tests for cleanup CLI command."""

import subprocess
from unittest.mock import patch, MagicMock
import pytest
from src.cli import main


def test_cleanup_command_dry_run_calls_openclaw_dry_run():
    """Test cleanup --dry-run calls openclaw sessions cleanup --dry-run."""
    with patch('src.cli.subprocess.run') as mock_run:
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
        assert result == 0


def test_cleanup_command_force_skips_confirmation():
    """Test cleanup --force skips confirmation prompt."""
    with patch('src.cli.subprocess.run') as mock_run:
        # First call: dry-run preview
        # Second call: actual cleanup
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Would prune 2 sessions", stderr=""),
            MagicMock(returncode=0, stdout="Pruned 2 sessions successfully", stderr="")
        ]
        
        with patch('sys.argv', ['session-monitor', 'cleanup', '--force']):
            result = main()
        
        # Should call twice: once for preview, once for enforce
        assert mock_run.call_count == 2
        
        # First call: dry-run
        assert mock_run.call_args_list[0][0][0] == [
            'openclaw', 'sessions', 'cleanup', '--dry-run', '--all-agents'
        ]
        
        # Second call: enforce
        assert mock_run.call_args_list[1][0][0] == [
            'openclaw', 'sessions', 'cleanup', '--enforce', '--all-agents'
        ]
        
        assert result == 0


def test_cleanup_command_interactive_confirmation_yes(monkeypatch):
    """Test cleanup with interactive confirmation (user says yes)."""
    with patch('src.cli.subprocess.run') as mock_run:
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
        assert result == 0


def test_cleanup_command_interactive_confirmation_no(monkeypatch):
    """Test cleanup with interactive confirmation (user says no)."""
    with patch('src.cli.subprocess.run') as mock_run:
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


def test_cleanup_command_openclaw_not_found():
    """Test cleanup gracefully handles openclaw command not found."""
    with patch('src.cli.subprocess.run') as mock_run:
        mock_run.side_effect = FileNotFoundError("openclaw: command not found")
        
        with patch('sys.argv', ['session-monitor', 'cleanup', '--dry-run']):
            result = main()
        
        # Should return error code
        assert result == 1


def test_cleanup_command_openclaw_error():
    """Test cleanup handles openclaw returning error."""
    with patch('src.cli.subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: permission denied"
        )
        
        with patch('sys.argv', ['session-monitor', 'cleanup', '--dry-run']):
            result = main()
        
        # Should return error code
        assert result == 1
```

Run test:
```bash
pytest tests/test_cleanup_cli.py -v
# Expected: FAIL - no cleanup command exists yet
```

- [ ] **Step 2 (Green): Implement cleanup command in CLI**

Modify `src/cli.py`:

At top of file, add subprocess import:
```python
import subprocess
```

In `main()` function, add cleanup subparser after watch_parser definition (around line 27):
```python
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old sessions via OpenClaw")
    cleanup_parser.add_argument("--dry-run", action="store_true", 
                                help="Preview what would be cleaned without actually cleaning")
    cleanup_parser.add_argument("--force", action="store_true",
                                help="Skip confirmation prompt")
```

In `main()` function, update command dispatch (around line 58):
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

At end of file, add cleanup command implementation:
```python
def cmd_cleanup(args):
    """Execute cleanup command via OpenClaw CLI."""
    import subprocess
    
    # Step 1: Always run dry-run first to preview
    print("Checking for sessions to clean up...")
    print()
    
    try:
        result = subprocess.run(
            ['openclaw', 'sessions', 'cleanup', '--dry-run', '--all-agents'],
            capture_output=True,
            text=True,
            check=False
        )
    except FileNotFoundError:
        print("Error: 'openclaw' command not found")
        print("Make sure OpenClaw CLI is installed and in your PATH")
        return 1
    
    if result.returncode != 0:
        print("Error running OpenClaw cleanup:")
        print(result.stderr)
        return 1
    
    # Display preview
    print(result.stdout)
    print()
    
    # If dry-run only, stop here
    if args.dry_run:
        print("Preview only (--dry-run). No sessions were deleted.")
        return 0
    
    # Step 2: Confirm with user (unless --force)
    if not args.force:
        response = input("Proceed with cleanup? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Cleanup cancelled.")
            return 0
    
    # Step 3: Run actual cleanup
    print("Cleaning up sessions...")
    print()
    
    try:
        result = subprocess.run(
            ['openclaw', 'sessions', 'cleanup', '--enforce', '--all-agents'],
            capture_output=True,
            text=True,
            check=False
        )
    except FileNotFoundError:
        print("Error: 'openclaw' command not found")
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
pytest tests/test_cleanup_cli.py -v
# Expected: All tests PASS
```

- [ ] **Step 3 (Refactor): Verify integration with actual CLI and improve error messages**

Test manually:
```bash
# Should show help including cleanup command
session-monitor --help

# Should run preview without OpenClaw (will error)
session-monitor cleanup --dry-run
# Expected: Error message about openclaw not found or OpenClaw output
```

Refactor to improve user experience:
- Ensure error messages are clear
- Ensure output formatting is clean
- Remove any duplicate code

Run full CLI test suite:
```bash
pytest tests/test_cleanup_cli.py -v
# Expected: All tests PASS
```

- [ ] **Step 4: Commit**

```bash
git add src/cli.py tests/test_cleanup_cli.py
git commit -m "feat: add session cleanup command wrapping OpenClaw CLI

Implements session-monitor cleanup command that:
- Runs openclaw sessions cleanup --dry-run for preview
- Prompts for confirmation (unless --force)
- Runs openclaw sessions cleanup --enforce if confirmed
- Supports --dry-run for preview-only mode
- Handles errors gracefully

All cleanup logic delegated to OpenClaw's native mechanism."
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

In `README.md`, find the "Commands" or "Usage" section and add:

```markdown
### Cleanup Old Sessions

Clean up old session files using OpenClaw's native cleanup mechanism:

```bash
# Preview what would be cleaned (no changes made)
session-monitor cleanup --dry-run

# Interactive cleanup with confirmation
session-monitor cleanup

# Force cleanup without confirmation
session-monitor cleanup --force
```

**How it works:**
- Delegates to OpenClaw's `openclaw sessions cleanup` command
- Always shows preview before deleting
- Cleans sessions according to OpenClaw's maintenance configuration
- Respects OpenClaw's session lifecycle and internal criteria

**Configuration:**
OpenClaw determines which sessions to clean based on its maintenance settings in `openclaw.json`. To configure retention policies, see OpenClaw's documentation for maintenance configuration options.

**Note:** This command is a convenience wrapper. You can also run `openclaw sessions cleanup` directly for more advanced options.
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
- [ ] All tests pass (`pytest tests/test_cleanup_cli.py -v` shows all green)
- [ ] Cleanup command accessible via `session-monitor cleanup`
- [ ] `session-monitor cleanup --dry-run` shows preview without making changes
- [ ] `session-monitor cleanup` prompts for confirmation before cleaning
- [ ] `session-monitor cleanup --force` skips confirmation and cleans immediately
- [ ] Error handling is graceful (missing openclaw command, OpenClaw errors)
- [ ] README documents cleanup command with examples and clear explanation
- [ ] No regressions in existing functionality (monitor still works)
- [ ] Manual verification: run cleanup against real OpenClaw installation

---

## Testing Strategy

**Unit tests (test_cleanup_cli.py):**
- Mock subprocess.run() to test command construction
- Test all flag combinations (--dry-run, --force, interactive)
- Test error cases (openclaw not found, openclaw returns error)
- Test confirmation flow (yes/no responses)

**Manual verification (required before completion):**
- Run against actual OpenClaw installation
- Verify preview output is readable
- Verify confirmation prompt works
- Verify actual cleanup succeeds
- Verify error messages are helpful

**Why mocking subprocess:**
- Tests shouldn't require OpenClaw installation
- Tests shouldn't delete real session data
- Fast test execution
- Predictable test behavior

**Why manual verification still needed:**
- Validate real OpenClaw command format
- Ensure output parsing assumptions are correct
- Catch integration issues
- Verify user experience

---

## Remember

- **YAGNI**: Don't build custom filtering/preview when OpenClaw provides it
- **User requirement**: "use openclaw's native approach unless LOE is too high"
- **Simplicity**: 1 CLI command, 2 subprocess calls, done
- **Safety**: Always preview first, confirm before deletion
- **Delegation**: Let OpenClaw handle all cleanup logic and decisions
- **Testing**: Mock for unit tests, manual verify for integration
- **DRY**: All commands run from workspace root with .venv activated
