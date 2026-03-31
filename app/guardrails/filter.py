from __future__ import annotations

import re


SENSITIVE_PATTERNS = [
    r"\b\d{16}\b",
    r"\b\d{3}-\d{2}-\d{4}\b",
]

BLOCKED_REQUEST_PATTERNS = [
    "other users reservation",
    "other users reservations",
    "private reservation",
    "admin notes",
    "internal instructions",
    "hidden prompt",
    "system prompt",
]


def contains_sensitive_data(text: str) -> bool:
    """
    Detect obviously sensitive patterns in the user input.
    """
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def is_blocked_request(text: str) -> bool:
    """
    Block requests for private/internal data.
    """
    normalized = text.lower()

    return any(pattern in normalized for pattern in BLOCKED_REQUEST_PATTERNS)