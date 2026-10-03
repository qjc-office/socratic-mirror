#!/usr/bin/env python3
"""Append a socratic-mirror session summary to ~/.socratic-mirror/log.md (private)."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, TextIO

sys.path.insert(0, str(Path(__file__).resolve().parent))
from redact import redact  # noqa: E402


def log_path() -> Path:
    home = os.environ.get("SOCRATIC_MIRROR_HOME") or str(Path.home() / ".socratic-mirror")
    return Path(home).expanduser() / "log.md"


def main(argv: Optional[list] = None, stdin: Optional[TextIO] = None) -> int:
    parser = argparse.ArgumentParser(prog="append_log", description=__doc__)
    parser.add_argument("--project", default=None,
                        help="label for the entry (default: current folder name)")
    args = parser.parse_args(argv)
    entry = (stdin or sys.stdin).read().strip()
    if not entry:
        print("empty entry; nothing written", file=sys.stderr)
        return 1
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    project = args.project or Path.cwd().name
    block = f"\n## {stamp} · {project}\n\n{redact(entry)}\n"
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as fh:
        fh.write(block)
    os.chmod(path, 0o600)
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
