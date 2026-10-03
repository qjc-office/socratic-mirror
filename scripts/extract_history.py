#!/usr/bin/env python3
"""Extract human-written utterances from Claude Code session history (~/.claude/projects)."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

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


EXIT_OK, EXIT_NO_HISTORY, EXIT_FORMAT_CHANGED, EXIT_USAGE = 0, 2, 3, 64


def parse_timestamp(value) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def is_within(path: str, root: str) -> bool:
    p = os.path.normcase(os.path.realpath(path))
    r = os.path.normcase(os.path.realpath(root))
    return p == r or p.startswith(r.rstrip(os.sep) + os.sep)


def project_root(cwd: str) -> Tuple[str, bool]:
    """Return (root, is_git). Inside a git repo the root is the toplevel."""
    try:
        res = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return cwd, False
    top = res.stdout.strip()
    return (top, True) if res.returncode == 0 and top else (cwd, False)


def same_path(a: str, b: str) -> bool:
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def first_cwd(path: Path, max_lines: int = 200) -> Optional[str]:
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh):
                if i >= max_lines:
                    break
                rec = parse_line(line)
                if rec and isinstance(rec.get("cwd"), str):
                    return rec["cwd"]
    except OSError:
        return None
    return None


def find_session_files(projects_dir: Path, root: Optional[str], cutoff: datetime,
                       subtree: bool = True) -> List[Path]:
    """root=None means all projects. subtree=False matches the exact folder only."""
    if not projects_dir.is_dir():
        return []
    found: List[Path] = []
    for folder in sorted(p for p in projects_dir.iterdir() if p.is_dir()):
        files = sorted(folder.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
        recent = [f for f in files
                  if datetime.fromtimestamp(f.stat().st_mtime, timezone.utc) >= cutoff]
        if not recent:
            continue
        if root is not None:
            cwd = first_cwd(files[0])
            matches = is_within if subtree else same_path
            if cwd is None or not matches(cwd, root):
                continue
        found.extend(recent)
    return found


def collect(files: List[Path], cutoff: datetime) -> Tuple[List[Tuple[datetime, str, str]], int]:
    rows: List[Tuple[datetime, str, str]] = []
    malformed = 0
    for path in files:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    continue
                rec = parse_line(line)
                if rec is None:
                    malformed += 1
                    continue
                text = extract_text(rec)
                ts = parse_timestamp(rec.get("timestamp"))
                if text is None or ts is None or ts < cutoff:
                    continue
                session = str(rec.get("sessionId") or path.stem)
                rows.append((ts, session, clean_line(text)))
    rows.sort(key=lambda r: r[0])
    return rows, malformed


def render(rows, max_chars: int) -> Tuple[List[str], int]:
    lines: List[str] = []
    used = 0
    for ts, session, text in reversed(rows):
        line = f"{ts.astimezone().date().isoformat()} | {session[:8]} | {text}"
        if used + len(line) + 1 > max_chars:
            break
        lines.append(line)
        used += len(line) + 1
    lines.reverse()
    return lines, len(rows) - len(lines)


def build_parser() -> argparse.ArgumentParser:
    default_dir = os.environ.get("SOCRATIC_MIRROR_PROJECTS_DIR",
                                 str(Path.home() / ".claude" / "projects"))
    p = argparse.ArgumentParser(prog="extract_history", description=__doc__)
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--all-projects", action="store_true")
    p.add_argument("--max-chars", type=int, default=60000)
    p.add_argument("--projects-dir", default=default_dir)
    p.add_argument("--cwd", default=os.getcwd())
    p.add_argument("--out")
    return p


def write_private(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(path, 0o600)


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return EXIT_USAGE
    if args.days < 1 or args.max_chars < 200:
        print("--days must be >= 1 and --max-chars >= 200", file=sys.stderr)
        return EXIT_USAGE
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    root, is_git = (None, False) if args.all_projects else project_root(args.cwd)
    files = find_session_files(Path(args.projects_dir).expanduser(), root, cutoff, subtree=is_git)
    if not files:
        print("no session history in range; try a larger --days or --all-projects",
              file=sys.stderr)
        return EXIT_NO_HISTORY
    rows, malformed = collect(files, cutoff)
    if not rows:
        print("session files exist but no human utterances were extracted; "
              "the history format may have changed", file=sys.stderr)
        return EXIT_FORMAT_CHANGED
    lines, omitted = render(rows, args.max_chars)
    sessions = len({r[1] for r in rows})
    header = (f"# socratic-mirror: {len(lines)} utterances, {sessions} sessions, "
              f"scope={'all' if root is None else 'project'}, days={args.days}, "
              f"omitted={omitted}, malformed={malformed}")
    body = "\n".join([header, *lines]) + "\n"
    if args.out:
        write_private(Path(args.out).expanduser(), body)
    else:
        sys.stdout.write(body)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
