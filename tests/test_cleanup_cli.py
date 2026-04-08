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
