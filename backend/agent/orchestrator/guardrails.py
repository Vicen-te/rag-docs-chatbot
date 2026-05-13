"""Post-generation sanitiser for assistant output."""
from __future__ import annotations

import re

# Strip any leaked control tokens or fake system blocks from the LLM.
FORBIDDEN_PATTERNS = (
    re.compile(r"<\|.*?\|>"),
    re.compile(r"\[system\].*?\[/system\]", re.DOTALL | re.IGNORECASE),
)


def sanitize(text: str) -> str:
    out = text
    for pattern in FORBIDDEN_PATTERNS:
        out = pattern.sub("", out)
    return out.strip()
