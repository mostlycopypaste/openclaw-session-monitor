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

    def _format_status_display(self, status: str | None) -> tuple[str, str]:
        """
        Format status value for display.

        Args:
            status: Session status ("running", "done", or None)

        Returns:
            Tuple of (display_text, style)
        """
        if status == "done":
            return ("DONE", "dim")
        elif status == "running":
            return ("RUNNING", "green")
        elif status is None:
            return ("—", "dim")  # Em dash for null
        else:
            return (str(status), "white")  # Fallback

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

        # Apply same sorting as rich UI
        def sort_key(session: Session) -> tuple[int, float]:
            is_done = 1 if session.status == "done" else 0
            window_pct = -session.window_percent
            return (is_done, window_pct)

        sorted_sessions = sorted(sessions.values(), key=sort_key)

        for session in sorted_sessions:
            # Determine display status
            if session.status == "done":
                display_status = "done"
            elif session.status == "running" or session.status is None:
                display_status = "running"
            else:
                display_status = session.status  # Fallback for unknown values

            output["sessions"].append({
                "id": session.session_id,
                "label": session.label,
                "tokens": session.total_tokens,
                "window_percent": round(session.window_percent, 1),
                "session_status": display_status,  # New field
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
        # Create session table with total count in title
        total_sessions = len(sessions)
        title = f"OpenClaw Session Monitor ({total_sessions} sessions)"
        table = Table(title=title, show_header=True)
        table.add_column("Session ID", style="cyan")
        table.add_column("Label", style="white")
        table.add_column("Status", justify="center", style="dim")  # New column
        table.add_column("Age", justify="right", style="dim")
        table.add_column("Tokens", justify="right", style="yellow")
        table.add_column("Window %", justify="right")
        table.add_column("Alert", style="bold")

        # Sort by: 1) active status (running/null) before done, 2) window % descending
        def sort_key(session: Session) -> tuple[int, float]:
            # Primary: active (0) before done (1)
            is_done = 1 if session.status == "done" else 0
            # Secondary: window % descending (negate for desc order)
            window_pct = -session.window_percent
            return (is_done, window_pct)

        sorted_sessions = sorted(sessions.values(), key=sort_key)

        for session in sorted_sessions:
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

            status_display, status_style = self._format_status_display(session.status)

            table.add_row(
                session.session_id[:12],
                session.label,
                f"[{status_style}]{status_display}[/{status_style}]",
                session.format_age(),
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
