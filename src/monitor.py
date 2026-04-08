"""Session monitor coordinator."""

import logging
from pathlib import Path
from typing import Dict
from src.models import Session
from src.session_parser import parse_sessions_metadata, parse_session_messages

logger = logging.getLogger(__name__)


class SessionMonitor:
    """
    Coordinates session discovery and monitoring.

    Scans OpenClaw state directory for active sessions and tracks token usage.
    """

    def __init__(self, state_dir: Path, context_limit: int = 200000):
        """
        Initialize session monitor.

        Args:
            state_dir: Path to OpenClaw state directory (e.g., ~/.openclaw-primary)
            context_limit: Context window size in tokens (default: 200000)
        """
        self.state_dir = Path(state_dir)
        self.context_limit = context_limit
        self.sessions: Dict[str, Session] = {}

    def discover_sessions(self):
        """
        Discover active sessions from filesystem.

        Scans agents/*/sessions/sessions.json files and loads session metadata.
        Calculates total tokens for each session.
        """
        agents_dir = self.state_dir / "agents"
        if not agents_dir.exists():
            logger.warning(f"Agents directory not found: {agents_dir}")
            return

        # Scan all agent directories
        for agent_dir in agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue

            sessions_dir = agent_dir / "sessions"
            if not sessions_dir.exists():
                continue

            sessions_file = sessions_dir / "sessions.json"
            if not sessions_file.exists():
                continue

            # Parse session metadata
            try:
                sessions_metadata = parse_sessions_metadata(sessions_file)
            except Exception as e:
                logger.error(f"Failed to parse {sessions_file}: {e}")
                continue

            # Process each active session
            for metadata in sessions_metadata:
                session_id = metadata['sessionId']
                # sessionFile is an absolute path in real OpenClaw sessions.json
                session_file = Path(metadata['sessionFile'])

                if not session_file.exists():
                    logger.warning(f"Session file not found: {session_file}")
                    continue

                # Parse messages and get current context size
                # Note: totalTokens is cumulative (includes full context at that point),
                # so we take the max (most recent) value, not sum all messages
                try:
                    messages = parse_session_messages(session_file)
                    total_tokens = max((msg['tokens'] for msg in messages), default=0)

                    # Create Session object
                    session = Session(
                        session_id=session_id,
                        label=metadata['label'],
                        agent=metadata['agent'],
                        total_tokens=total_tokens,
                        created_at=metadata.get('startedAt'),
                        status=metadata.get('status'),
                        context_limit=self.context_limit
                    )

                    self.sessions[session_id] = session

                except Exception as e:
                    logger.error(f"Failed to parse session {session_file}: {e}")
                    continue
