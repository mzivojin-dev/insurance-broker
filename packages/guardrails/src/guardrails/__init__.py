"""Input and output guardrails shared by all agents (episode 11)."""

import re

_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "card": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
}


def redact_pii(text: str) -> str:
    """Replace obvious PII with placeholders before it is logged or sent onward."""
    for label, pattern in _PATTERNS.items():
        text = pattern.sub(f"[{label.upper()} REDACTED]", text)
    return text
