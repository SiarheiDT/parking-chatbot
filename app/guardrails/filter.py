from __future__ import annotations

import re

from app.config import get_config
from app.guardrails.nlp_sensitive import semantic_sensitive_intent


SENSITIVE_PATTERNS = [
    r"\b\d{16}\b",
    # PAN-style: four groups of four digits (spaces or dashes), e.g. 1234-1234-1234-1234
    r"\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}\b",
    r"\b\d{3}-\d{2}-\d{4}\b",
    r"\b\d{3}\s\d{2}\s\d{4}\b",
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9_.-]+\b",
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
    Detect sensitive content: (1) regex for structured PII-style patterns,
    (2) pre-trained transformer encoder (SentenceTransformer) semantic match
    against sensitive-intent reference phrases.
    """
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, text):
            return True

    cfg = get_config()
    if cfg.GUARDRAILS_SEMANTIC_ENABLED and semantic_sensitive_intent(
        text, cfg.GUARDRAILS_SEMANTIC_THRESHOLD
    ):
        return True
    return False


def is_blocked_request(text: str) -> bool:
    """
    Block requests for private/internal data.
    """
    normalized = text.lower()

    return any(pattern in normalized for pattern in BLOCKED_REQUEST_PATTERNS)