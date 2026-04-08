"""Tests for cleanup CLI command."""

import sys
import subprocess
from unittest.mock import patch, MagicMock
from pathlib import Path
import pytest
from src.cli import main


def test_cleanup_command_dry_run_calls_openclaw(tmp_path):
    """Test cleanup --dry-run calls openclaw sessions cleanup --dry-run."""
    # Create mock state directory structure
    agents_dir = tmp_path / "agents" / "main" / "sessions"
    agents_dir.mkdir(parents=True)
    (agents_dir / "sessions.json").write_text("{}")

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Cleanup preview:\nWould prune 3 sessions\nTotal: 12.5 MB",
            stderr=""
        )

        with patch('sys.argv', ['session-monitor', 'cleanup', '--dry-run', '--state-dir', str(tmp_path)]):
            result = main()

        # Verify openclaw command was called once per agent
        mock_run.assert_called_once()
        args = mock_run.call_args
        assert 'openclaw' in args[0][0]
        assert '--dry-run' in args[0][0]
        assert '--store' in args[0][0]
        assert args[1]['capture_output'] == True
        assert args[1]['text'] == True
        assert args[1]['timeout'] == 120
        assert result == 0


def test_cleanup_command_interactive_confirmation_yes(monkeypatch, tmp_path):
    """Test cleanup with interactive confirmation (user says yes)."""
    # Create mock state directory
    agents_dir = tmp_path / "agents" / "main" / "sessions"
    agents_dir.mkdir(parents=True)
    (agents_dir / "sessions.json").write_text("{}")

    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Would prune 5 sessions", stderr=""),
            MagicMock(returncode=0, stdout="Pruned 5 sessions", stderr="")
        ]

        # Mock input to return 'y'
        monkeypatch.setattr('builtins.input', lambda _: 'y')

        with patch('sys.argv', ['session-monitor', 'cleanup', '--state-dir', str(tmp_path)]):
            result = main()

        # Should call twice per agent: preview then enforce
        assert mock_run.call_count == 2
        # Second call should use --enforce
        assert '--enforce' in mock_run.call_args_list[1][0][0]
        assert result == 0


def test_cleanup_command_interactive_confirmation_no(monkeypatch, tmp_path):
    """Test cleanup with interactive confirmation (user says no)."""
    # Create mock state directory
    agents_dir = tmp_path / "agents" / "main" / "sessions"
    agents_dir.mkdir(parents=True)
    (agents_dir / "sessions.json").write_text("{}")

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Would prune 5 sessions",
            stderr=""
        )

        # Mock input to return 'n'
        monkeypatch.setattr('builtins.input', lambda _: 'n')

        with patch('sys.argv', ['session-monitor', 'cleanup', '--state-dir', str(tmp_path)]):
            result = main()

        # Should only call once (preview), not enforce
        assert mock_run.call_count == 1
        assert result == 0


def test_cleanup_command_force_skips_confirmation(tmp_path):
    """Test cleanup --force skips confirmation prompt."""
    # Create mock state directory
    agents_dir = tmp_path / "agents" / "main" / "sessions"
    agents_dir.mkdir(parents=True)
    (agents_dir / "sessions.json").write_text("{}")

    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Would prune 2 sessions", stderr=""),
            MagicMock(returncode=0, stdout="Pruned 2 sessions successfully", stderr="")
        ]

        with patch('sys.argv', ['session-monitor', 'cleanup', '--force', '--state-dir', str(tmp_path)]):
            result = main()

        # Should call twice: once for preview, once for enforce
        assert mock_run.call_count == 2
        assert result == 0


def test_cleanup_command_openclaw_not_found(tmp_path):
    """Test cleanup gracefully handles openclaw command not found."""
    # Create mock state directory
    agents_dir = tmp_path / "agents" / "main" / "sessions"
    agents_dir.mkdir(parents=True)
    (agents_dir / "sessions.json").write_text("{}")

    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = FileNotFoundError("openclaw: command not found")

        with patch('sys.argv', ['session-monitor', 'cleanup', '--dry-run', '--state-dir', str(tmp_path)]):
            result = main()

        # Should return error code
        assert result == 1


def test_cleanup_command_openclaw_error(tmp_path):
    """Test cleanup handles openclaw returning error."""
    # Create mock state directory
    agents_dir = tmp_path / "agents" / "main" / "sessions"
    agents_dir.mkdir(parents=True)
    (agents_dir / "sessions.json").write_text("{}")

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: permission denied"
        )

        with patch('sys.argv', ['session-monitor', 'cleanup', '--dry-run', '--state-dir', str(tmp_path)]):
            result = main()

        # Errors on individual agents don't fail the whole command if no sessions to clean
        assert result == 0


def test_cleanup_command_timeout(tmp_path):
    """Test cleanup handles timeout gracefully."""
    # Create mock state directory
    agents_dir = tmp_path / "agents" / "main" / "sessions"
    agents_dir.mkdir(parents=True)
    (agents_dir / "sessions.json").write_text("{}")

    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired('openclaw', 120)

        with patch('sys.argv', ['session-monitor', 'cleanup', '--dry-run', '--state-dir', str(tmp_path)]):
            result = main()

        # Timeout on individual agents doesn't fail the whole command if no sessions to clean
        assert result == 0
