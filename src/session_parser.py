"""Parse OpenClaw session files."""

import json
import jsonlines
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

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

    # OpenClaw sessions.json is a dict with keys like "agent:main:main"
    # Each value is a session object
    sessions = []

    for label, session_data in data.items():
        # Skip if no sessionFile or sessionId
        if 'sessionFile' not in session_data or 'sessionId' not in session_data:
            continue

        session_file = session_data['sessionFile']

        # Filter out archived sessions (those with .reset or .deleted in filename)
        if '.reset' in session_file or '.deleted' in session_file:
            continue

        # Check if session file actually exists
        session_path = Path(session_file)
        if not session_path.exists():
            continue

        # Extract agent name from label (e.g., "agent:main:main" -> "main")
        agent = label.split(':')[1] if ':' in label else 'unknown'

        sessions.append({
            'sessionId': session_data['sessionId'],
            'label': label,
            'agent': agent,
            'sessionFile': session_file,
            'startedAt': session_data.get('startedAt'),  # Unix timestamp in milliseconds
        })

    return sessions


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


def parse_session_messages_incremental(
    session_file: Path,
    start_pos: int = 0
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Parse session JSONL file incrementally from given position.

    Args:
        session_file: Path to session JSONL file
        start_pos: Byte position to start reading from

    Returns:
        Tuple of (messages list, new byte position)
    """
    messages = []

    with open(session_file, 'rb') as f:
        # Seek to start position
        f.seek(start_pos)

        # Read remaining lines
        for line in f:
            try:
                obj = json.loads(line.decode('utf-8'))

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
                logger.warning(f"Skipping malformed line: {e}")
                continue

        # Return new position
        new_pos = f.tell()

    return messages, new_pos
