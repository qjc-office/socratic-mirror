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
from safe_io import open_private  # noqa: E402


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
    project = args.project or Path.cwd().name
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    block = f"\n## {stamp} · {project}\n\n{redact(entry)}\n"
    try:
        with open_private(path, append=True) as fh:
            fh.write(block)
    except OSError as exc:
        print(f"cannot write log: {exc}", file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
