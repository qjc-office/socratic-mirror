#!/usr/bin/env python3
"""Extract human-written utterances from Claude Code session history (~/.claude/projects)."""
from __future__ import annotations

import argparse
import heapq
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, NamedTuple, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from redact import redact  # noqa: E402
from safe_io import write_atomic  # noqa: E402

MAX_UTTERANCE = 1000
MAX_LINE = 2_000_000  # chars; longer jsonl lines are pastes or tool output, skipped unread
_TAGS = ("system-reminder", "task-notification", "command-name", "command-message",
         "command-args", "local-command-stdout", "local-command-stderr",
         "local-command-caveat", "bash-input", "bash-stdout", "bash-stderr")
TAG_BLOCK = re.compile(r"<(" + "|".join(_TAGS) + r")>.*?</\1>", re.DOTALL)
NOISE = {"[Request interrupted by user]", "[Request interrupted by user for tool use]"}


def bounded_lines(fh):
    """Yield lines, or None for a line longer than MAX_LINE (drained, never held whole)."""
    limit = MAX_LINE
    while True:
        line = fh.readline(limit)
        if not line:
            return
        if len(line) >= limit and not line.endswith("\n"):
            while True:
                rest = fh.readline(limit)
                if not rest or rest.endswith("\n"):
                    break
            yield None
            continue
        yield line


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
    message = record.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, str):
        parts = [content]
    elif isinstance(content, list):
        parts = [b["text"] for b in content
                 if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str)]
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


def first_cwd(path: Path) -> Optional[str]:
    """First cwd recorded in a session file. Raises OSError if unreadable."""
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in bounded_lines(fh):
            rec = parse_line(line) if line is not None else None
            if rec and isinstance(rec.get("cwd"), str):
                return rec["cwd"]
    return None


def _cwd_matches(cwd: Optional[str], root: str, matches) -> bool:
    return cwd is not None and matches(cwd, root)


def find_session_files(projects_dir: Path, root: Optional[str], cutoff: datetime,
                       subtree: bool = True) -> Tuple[List[Path], int]:
    """Return (session files in range, unreadable count).

    root=None means all projects. subtree=False matches the exact folder only.
    """
    if not projects_dir.is_dir():
        return [], 0
    matches = is_within if subtree else same_path
    found: List[Path] = []
    unreadable = 0
    for folder in sorted(p for p in projects_dir.iterdir() if p.is_dir()):
        for path in sorted(folder.glob("*.jsonl")):
            try:
                if datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) < cutoff:
                    continue
                if root is not None and not _cwd_matches(first_cwd(path), root, matches):
                    continue
            except OSError:
                unreadable += 1
                continue
            found.append(path)
    return found, unreadable


ROW_OVERHEAD = 25  # "YYYY-MM-DD | 12345678 | " plus newline


class Collected(NamedTuple):
    rows: list  # (timestamp, session, line), oldest first, newest that fit max_chars
    total: int
    sessions: int
    malformed: int
    oversized: int
    unreadable: int


def collect(files: List[Path], cutoff: datetime, max_chars: int) -> Collected:
    """Keep a bounded min-heap so memory stays near max_chars, not the whole history."""
    heap: list = []
    size = total = malformed = oversized = unreadable = seq = 0
    sessions = set()
    for path in files:
        try:
            fh = path.open(encoding="utf-8", errors="replace")
        except OSError:
            unreadable += 1
            continue
        with fh:
            for line in bounded_lines(fh):
                if line is None:
                    oversized += 1
                    continue
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
                line = clean_line(text)
                total += 1
                sessions.add(session)
                heapq.heappush(heap, (ts, seq, session, line))
                seq += 1
                size += len(line) + ROW_OVERHEAD
                while len(heap) > 1 and size - len(heap[0][3]) - ROW_OVERHEAD >= max_chars:
                    size -= len(heapq.heappop(heap)[3]) + ROW_OVERHEAD
    rows = [(ts, session, line) for ts, _, session, line in sorted(heap)]
    return Collected(rows, total, len(sessions), malformed, oversized, unreadable)


def render(rows, max_chars: int) -> Tuple[List[str], int]:
    lines: List[str] = []
    used = 0
    for ts, session, text in reversed(rows):
        line = f"{ts.astimezone().date().isoformat()} | {session[:8]} | {text}"
        if used + len(line) + 1 > max_chars:
            if not lines:  # never return nothing: cut the newest line to fit
                lines.append(line[:max_chars - 2] + "…")
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
    files, skipped = find_session_files(Path(args.projects_dir).expanduser(), root, cutoff,
                                        subtree=is_git)
    if not files:
        print("no session history in range; try a larger --days or --all-projects",
              file=sys.stderr)
        return EXIT_NO_HISTORY
    got = collect(files, cutoff, args.max_chars)
    if not got.total:
        print("session files exist but no human utterances were extracted; "
              "the history format may have changed", file=sys.stderr)
        return EXIT_FORMAT_CHANGED
    lines, _ = render(got.rows, args.max_chars)
    header = (f"# socratic-mirror: {len(lines)} utterances, {got.sessions} sessions, "
              f"scope={'all' if root is None else 'project'}, days={args.days}, "
              f"omitted={got.total - len(lines)}, malformed={got.malformed}, "
              f"oversized={got.oversized}, unreadable={skipped + got.unreadable}")
    body = "\n".join([header, *lines]) + "\n"
    if args.out:
        try:
            write_atomic(Path(args.out).expanduser(), body)
        except OSError as exc:
            print(f"cannot write --out: {exc}", file=sys.stderr)
            return EXIT_USAGE
    else:
        sys.stdout.write(body)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
