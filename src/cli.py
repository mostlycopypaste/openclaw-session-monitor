"""CLI entry point for session-monitor command."""

import sys
import argparse
from pathlib import Path


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
    watch_parser.add_argument("--refresh-rate", type=float, default=1.0, help="Dashboard refresh rate in seconds")
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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Phase 1: Not implemented yet
    print(f"Command '{args.command}' not yet implemented.")
    print("See PLAN.md for implementation phases.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
