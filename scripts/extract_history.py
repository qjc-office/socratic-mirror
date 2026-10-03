#!/usr/bin/env python3
"""Extract human-written utterances from Claude Code session history (~/.claude/projects)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from redact import redact  # noqa: E402

MAX_UTTERANCE = 1000
_TAGS = ("system-reminder", "task-notification", "command-name", "command-message",
         "command-args", "local-command-stdout", "local-command-stderr",
         "local-command-caveat", "bash-input", "bash-stdout", "bash-stderr")
TAG_BLOCK = re.compile(r"<(" + "|".join(_TAGS) + r")>.*?</\1>", re.DOTALL)
NOISE = {"[Request interrupted by user]", "[Request interrupted by user for tool use]"}


def parse_line(line: str) -> Optional[dict]:
    try:
        obj = json.loads(line)
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def extract_text(record: dict) -> Optional[str]:
    if record.get("type") != "user":
        return None
    if record.get("isMeta") or record.get("isSidechain") or record.get("isCompactSummary"):
        return None
    if record.get("userType", "external") != "external":
        return None
    content = (record.get("message") or {}).get("content")
    if isinstance(content, str):
        parts = [content]
    elif isinstance(content, list):
        parts = [b.get("text", "") for b in content
                 if isinstance(b, dict) and b.get("type") == "text"]
    else:
        return None
    text = TAG_BLOCK.sub("", "\n".join(parts)).strip()
    if not text or text in NOISE:
        return None
    return text


def clean_line(text: str) -> str:
    flat = redact(" ⏎ ".join(part.strip() for part in text.splitlines() if part.strip()))
    if len(flat) > MAX_UTTERANCE:
        flat = flat[:MAX_UTTERANCE] + "…"
    return flat
