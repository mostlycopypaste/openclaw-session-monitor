"""Parse OpenClaw session files."""

import json
from pathlib import Path
from typing import List, Dict, Any


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
