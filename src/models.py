"""Data models for OpenClaw session monitoring."""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone


@dataclass
class Session:
    """Represents an OpenClaw session with token tracking."""

    session_id: str
    label: str
    agent: str
    total_tokens: int
    created_at: Optional[int] = None  # Unix timestamp in milliseconds
    status: Optional[str] = None  # "running", "done", or None (treated as running)
    model: Optional[str] = None  # Model identifier (e.g., "kimi-k2.5:cloud")
    context_limit: int = 200000

    @property
    def window_percent(self) -> float:
        """Calculate percentage of context window used."""
        if self.context_limit == 0:
            return 0.0
        return (self.total_tokens / self.context_limit) * 100

    @property
    def alert_level(self) -> str:
        """Determine alert level based on token usage."""
        percent = self.window_percent
        if percent >= 90:
            return "critical"
        elif percent >= 80:
            return "warning"
        else:
            return "none"

    @property
    def age_seconds(self) -> Optional[int]:
        """Calculate session age in seconds."""
        if self.created_at is None:
            return None
        current_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        age_ms = current_ms - self.created_at
        return age_ms // 1000

    def format_age(self) -> str:
        """Format age as human-readable string."""
        age = self.age_seconds
        if age is None:
            return "Unknown"

        if age < 60:
            return f"{age}s"
        elif age < 3600:
            mins = age // 60
            return f"{mins}m"
        elif age < 86400:
            hours = age // 3600
            return f"{hours}h"
        else:
            days = age // 86400
            return f"{days}d"


@dataclass
class Message:
    """Represents a single message in a session."""

    timestamp: str
    role: str
    tokens: int
    spike_threshold: int = 10000

    @property
    def is_spike(self) -> bool:
        """Check if message exceeds spike threshold."""
        return self.tokens > self.spike_threshold


@dataclass
class Alert:
    """Represents an alert to display to user."""

    session_id: str
    level: str  # "warning" or "critical"
    message: str
