"""Parse OpenClaw session files."""

import json
import jsonlines
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def parse_sessions_metadata(sessions_file: Path) -> List[Dict[str, Any]]:
    """
    Parse sessions.json and return list of active session metadata.

    Filters out archived sessions (those with .reset or .deleted suffixes).

    Args:
        sessions_file: Path to sessions.json

    Returns:
        List of session metadata dictionaries
    """
    with open(sessions_file, 'r') as f:
        data = json.load(f)

    sessions = data.get('sessions', [])

    # Filter out archived sessions
    active_sessions = [
        s for s in sessions
        if s.get('status') == 'active'
        and not s.get('sessionId', '').endswith('.reset')
        and not s.get('sessionId', '').endswith('.deleted')
    ]

    return active_sessions


def parse_session_messages(session_file: Path) -> List[Dict[str, Any]]:
    """
    Parse session JSONL file and extract message token data.

    Args:
        session_file: Path to session JSONL file

    Returns:
        List of message dictionaries with timestamp, role, tokens
    """
    messages = []

    with open(session_file, 'r') as f:
        for line_num, line in enumerate(f, start=1):
            try:
                obj = json.loads(line)

                if obj.get('type') != 'message':
                    continue

                message = obj.get('message', {})
                usage = message.get('usage', {})

                messages.append({
                    'timestamp': obj.get('timestamp', ''),
                    'role': obj.get('role', ''),
                    'tokens': usage.get('totalTokens', 0)
                })
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"Skipping malformed line {line_num}: {e}")
                continue

    return messages
