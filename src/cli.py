"""CLI entry point for session-monitor command."""

import sys
import os
import argparse
import time
import subprocess
from pathlib import Path
from src.monitor import SessionMonitor
from src.dashboard import Dashboard


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        prog="session-monitor",
        description="Real-time token usage monitoring for OpenClaw sessions"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Watch command
    watch_parser = subparsers.add_parser("watch", help="Start live monitoring dashboard")
    watch_parser.add_argument("--agent", help="Monitor specific agent only")
    watch_parser.add_argument("--simple", action="store_true", help="Simple output (no colors)")
    watch_parser.add_argument("--refresh-rate", type=float, default=2.0, help="Dashboard refresh rate in seconds")
    watch_parser.add_argument("--state-dir", help="Override OpenClaw state directory")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a session")
    analyze_parser.add_argument("session_id", help="Session ID to analyze")
    analyze_parser.add_argument("--report", action="store_true", help="Generate markdown report")
    analyze_parser.add_argument("--output", help="Output directory for report")

    # List command
    list_parser = subparsers.add_parser("list", help="List sessions")
    list_parser.add_argument("--agent", help="Filter by agent")
    list_parser.add_argument("--status", help="Filter by status")

    # Metrics command
    metrics_parser = subparsers.add_parser("metrics", help="Historical metrics")
    metrics_subparsers = metrics_parser.add_subparsers(dest="metrics_command")

    export_parser = metrics_subparsers.add_parser("export", help="Export metrics to JSONL")
    export_parser.add_argument("--interval", type=int, default=5, help="Export interval in minutes")

    view_parser = metrics_subparsers.add_parser("view", help="View historical metrics")
    view_parser.add_argument("--days", type=int, default=7, help="Number of days to view")
    view_parser.add_argument("--agent", help="Filter by agent")

    report_parser = metrics_subparsers.add_parser("report", help="Generate weekly report")

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old sessions via OpenClaw")
    cleanup_parser.add_argument("--dry-run", action="store_true",
                                help="Preview what would be cleaned without actually cleaning")
    cleanup_parser.add_argument("--force", action="store_true",
                                help="Skip confirmation prompt")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "watch":
        return cmd_watch(args)
    elif args.command == "cleanup":
        return cmd_cleanup(args)
    else:
        print(f"Command '{args.command}' not yet implemented.")
        print("See PLAN.md for implementation phases.")
        return 1


def cmd_watch(args):
    """Execute watch command to monitor sessions in real-time."""
    # Determine state directory
    state_dir = args.state_dir
    if not state_dir:
        # Try environment variable first
        state_dir = os.environ.get('OPENCLAW_STATE_DIR')
        if not state_dir:
            # Default location
            state_dir = Path.home() / '.openclaw-primary'
        else:
            state_dir = Path(state_dir)
    else:
        state_dir = Path(state_dir)

    if not state_dir.exists():
        print(f"Error: OpenClaw state directory not found: {state_dir}")
        print("Set OPENCLAW_STATE_DIR environment variable or use --state-dir")
        return 1

    # Initialize monitor and dashboard
    monitor = SessionMonitor(state_dir=state_dir)
    dashboard = Dashboard(test_mode=False)

    # Discover initial sessions
    print(f"Monitoring OpenClaw sessions at {state_dir}")
    print("Press Ctrl+C to exit\n")

    try:
        # Simple polling loop (Task 7 file watcher would make this real-time)
        while True:
            monitor.discover_sessions()

            # Clear screen and display dashboard
            dashboard.console.clear()

            if monitor.sessions:
                output = dashboard._render_rich_ui(monitor.sessions)
                dashboard.console.print(output)
            else:
                print("No active sessions found")

            time.sleep(args.refresh_rate)

    except KeyboardInterrupt:
        print("\nMonitoring stopped")
        return 0


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


if __name__ == "__main__":
    sys.exit(main())
