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
