"""Data models for OpenClaw session monitoring."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Session:
    """Represents an OpenClaw session with token tracking."""

    session_id: str
    label: str
    agent: str
    total_tokens: int
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
