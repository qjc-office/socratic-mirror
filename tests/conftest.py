from __future__ import annotations
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))


def write_session(directory: Path, name: str, records: list) -> Path:
    """Write a fake Claude Code session jsonl. Strings are written as raw lines."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(rec if isinstance(rec, str) else json.dumps(rec, ensure_ascii=False))
            fh.write("\n")
    return path


def user(text, *, ts="2026-10-01T03:00:00.000Z", cwd="/proj", session="s-0001-aaaa", **extra):
    """A human-typed user record as Claude Code writes it."""
    rec = {"type": "user", "timestamp": ts, "cwd": cwd, "sessionId": session,
           "userType": "external", "isSidechain": False,
           "message": {"role": "user", "content": text}}
    rec.update(extra)
    return rec
