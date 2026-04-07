"""Terminal dashboard for session monitoring."""

import json
from typing import Dict, List
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from src.models import Session, Alert


class Dashboard:
    """
    Terminal UI dashboard for displaying session status.

    Supports both rich terminal UI and simple test mode.
    """

    def __init__(self, test_mode: bool = False):
        """
        Initialize dashboard.

        Args:
            test_mode: If True, output JSON instead of rich UI
        """
        self.test_mode = test_mode
        self.console = Console() if not test_mode else None

    def render(self, sessions: Dict[str, Session]) -> str:
        """
        Render dashboard for current sessions.

        Args:
            sessions: Dictionary of session_id -> Session

        Returns:
            Rendered output (JSON in test mode, rich output otherwise)
        """
        if self.test_mode:
            return self._render_test_mode(sessions)
        else:
            return self._render_rich_ui(sessions)

    def _render_test_mode(self, sessions: Dict[str, Session]) -> str:
        """Render dashboard as JSON for testing."""
        output = {
            "sessions": [],
            "alerts": []
        }

        for session_id, session in sessions.items():
            output["sessions"].append({
                "id": session.session_id,
                "label": session.label,
                "tokens": session.total_tokens,
                "window_percent": round(session.window_percent, 1),
                "status": "active",
                "alert_level": session.alert_level
            })

            # Add alerts for warning/critical levels
            if session.alert_level == "warning":
                output["alerts"].append({
                    "session_id": session.session_id,
                    "level": "warning",
                    "message": f"Approaching context limit: {session.total_tokens}/200K ({session.window_percent:.0f}%)"
                })
            elif session.alert_level == "critical":
                output["alerts"].append({
                    "session_id": session.session_id,
                    "level": "critical",
                    "message": f"CRITICAL: Near context limit: {session.total_tokens}/200K ({session.window_percent:.0f}%)"
                })

        return json.dumps(output, indent=2)

    def _render_rich_ui(self, sessions: Dict[str, Session]) -> str:
        """Render dashboard with rich terminal UI."""
        # Create session table
        table = Table(title="OpenClaw Session Monitor", show_header=True)
        table.add_column("Session ID", style="cyan")
        table.add_column("Label", style="white")
        table.add_column("Tokens", justify="right", style="yellow")
        table.add_column("Window %", justify="right")
        table.add_column("Alert", style="bold")

        for session_id, session in sorted(sessions.items()):
            # Determine alert color
            if session.alert_level == "critical":
                alert_style = "bold red"
                alert_text = "CRITICAL"
            elif session.alert_level == "warning":
                alert_style = "bold yellow"
                alert_text = "WARNING"
            else:
                alert_style = "green"
                alert_text = "OK"

            # Determine window % color
            percent = session.window_percent
            if percent >= 90:
                percent_style = "bold red"
            elif percent >= 80:
                percent_style = "bold yellow"
            else:
                percent_style = "green"

            table.add_row(
                session_id[:12],
                session.label,
                f"{session.total_tokens:,}",
                f"[{percent_style}]{percent:.1f}%[/{percent_style}]",
                f"[{alert_style}]{alert_text}[/{alert_style}]"
            )

        # Render to string for Live display
        return table

    def display_live(self, get_sessions_callback):
        """
        Display live-updating dashboard.

        Args:
            get_sessions_callback: Function that returns current sessions dict
        """
        if self.test_mode:
            # In test mode, just print once
            sessions = get_sessions_callback()
            print(self.render(sessions))
        else:
            # Live updating display
            with Live(self.render(get_sessions_callback()), refresh_per_second=1) as live:
                while True:
                    try:
                        sessions = get_sessions_callback()
                        live.update(self._render_rich_ui(sessions))
                    except KeyboardInterrupt:
                        break
