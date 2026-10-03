"""Mask secret-looking strings before they are shown or stored."""
from __future__ import annotations

import re

MASK = "[REDACTED]"

_TOKEN_PATTERNS = [
    re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"),
]
_SECRET_WORDS = r"(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD)"
# OPENAI_API_KEY=..., DB_PASSWORD: "..."  (all-caps names, = or :)
_UPPER_ASSIGN = re.compile(
    r"\b([A-Z][A-Z0-9_]*" + _SECRET_WORDS + r"[A-Z0-9_]*)(\s*[=:]\s*)(\"[^\"]*\"|'[^']*'|\S+)"
)
# api_key=..., authToken=...  (any case, = only, so prose like "key: ..." survives)
_ANY_ASSIGN = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*" + _SECRET_WORDS + r"[A-Za-z0-9_]*)(=)(\"[^\"]*\"|'[^']*'|\S+)",
    re.IGNORECASE,
)


def redact(text: str) -> str:
    for pattern in _TOKEN_PATTERNS:
        text = pattern.sub(MASK, text)
    text = _UPPER_ASSIGN.sub(lambda m: m.group(1) + m.group(2) + MASK, text)
    return _ANY_ASSIGN.sub(lambda m: m.group(1) + m.group(2) + MASK, text)
