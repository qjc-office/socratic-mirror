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
    re.compile(r"\bbearer\s+[A-Za-z0-9._~+/\-]{16,}=*", re.IGNORECASE),
]
_SECRET_WORDS = r"(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD)"
# Quoted values honour escapes; unquoted values run to the end of the line, since a
# password can contain spaces. Over-masking the rest of a line is the safe failure.
_VALUE = r"(\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.|'')*'|[^\n}\]]*[^\s}\]])"
# OPENAI_API_KEY=..., DB_PASSWORD: "..."  (all-caps names, = or :)
_UPPER_ASSIGN = re.compile(
    r"(?<![A-Za-z0-9_])((?:[A-Z][A-Z0-9_]*)?" + _SECRET_WORDS + r"[A-Z0-9_]*)(\s*[=:]\s*)" + _VALUE
)
# {"api_key": "..."}, {'password': '...'}  (quoted keys as in JSON, YAML, dicts)
_QUOTED_KEY = re.compile(
    r"([\"'])((?:[A-Za-z_][\w\-]*)?" + _SECRET_WORDS + r"[\w\-]*)\1(\s*[=:]\s*)" + _VALUE,
    re.IGNORECASE,
)
# api_key = ..., authToken=...  (any case, = only)
_ANY_ASSIGN = re.compile(
    r"(?<![A-Za-z0-9_])((?:[A-Za-z_][A-Za-z0-9_]*)?" + _SECRET_WORDS + r"[A-Za-z0-9_]*)(\s*=\s*)" + _VALUE,
    re.IGNORECASE,
)
# client_secret: ..., apiKey: ..., password: ...  A colon only counts for compound
# (snake, kebab or camelCase) names or the bare word password, so prose like
# "key: ..." or "Secret: ..." survives. Only key + separator is consumed while
# scanning, so a parent key ("config: {apiKey: v}") never swallows a nested one.
_COLON_KEY = re.compile(r"(?<![\w\-])([A-Za-z][\w\-]*)(\s*:\s*)")
_VALUE_RE = re.compile(_VALUE)
_SECRET_RE = re.compile(_SECRET_WORDS, re.IGNORECASE)


def _is_secret_colon_key(name: str) -> bool:
    if name.lower() in ("password", "passwd"):
        return True
    compound = "_" in name or "-" in name or re.search(r"[a-z][A-Z]", name)
    return bool(compound and _SECRET_RE.search(name))


def _mask_colon_values(text: str) -> str:
    out = []
    pos = 0
    for m in _COLON_KEY.finditer(text):
        if m.start() < pos or not _is_secret_colon_key(m.group(1)):
            continue
        value = _VALUE_RE.match(text, m.end())
        if not value:
            continue
        out.append(text[pos:m.end()])
        out.append(MASK)
        pos = value.end()
    out.append(text[pos:])
    return "".join(out)


def redact(text: str) -> str:
    for pattern in _TOKEN_PATTERNS:
        text = pattern.sub(MASK, text)
    text = _QUOTED_KEY.sub(lambda m: m.group(1) + m.group(2) + m.group(1) + m.group(3) + MASK, text)
    text = _UPPER_ASSIGN.sub(lambda m: m.group(1) + m.group(2) + MASK, text)
    text = _ANY_ASSIGN.sub(lambda m: m.group(1) + m.group(2) + MASK, text)
    return _mask_colon_values(text)
