from __future__ import annotations
import os
import stat
import subprocess
import sys
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from conftest import SCRIPTS, user, write_session
import extract_history as eh

RECENT = "2026-10-01T03:00:00.000Z"


@pytest.fixture
def projects(tmp_path):
    return tmp_path / "projects"


def run(projects, *args, cwd="/proj"):
    return eh.main(["--projects-dir", str(projects), "--cwd", cwd, "--days", "36500", *args])


def test_basic_output_format(projects, capsys):
    write_session(projects / "-proj", "a", [user("나는 혼자 해야 빨라", ts=RECENT)])
    assert run(projects) == eh.EXIT_OK
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("# socratic-mirror: 1 utterances, 1 sessions, scope=project")
    assert out[1].endswith("| s-0001-a | 나는 혼자 해야 빨라")


def test_matches_dir_by_cwd_not_name(projects, capsys):
    write_session(projects / "weird-legacy-name", "a", [user("내 프로젝트 발화", cwd="/proj")])
    write_session(projects / "-proj", "b", [user("다른 곳 발화", cwd="/elsewhere")])
    assert run(projects) == eh.EXIT_OK
    out = capsys.readouterr().out
    assert "내 프로젝트 발화" in out and "다른 곳 발화" not in out


def test_all_projects_includes_everything(projects, capsys):
    write_session(projects / "x", "a", [user("하나", cwd="/proj")])
    write_session(projects / "y", "b", [user("둘", cwd="/elsewhere", session="s-0002-bbbb")])
    assert run(projects, "--all-projects") == eh.EXIT_OK
    out = capsys.readouterr().out
    assert "하나" in out and "둘" in out and "scope=all" in out


def test_scope_uses_git_root_from_subdir(tmp_path, projects, capsys):
    repo = tmp_path / "repo"
    (repo / "sub").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    write_session(projects / "r", "a", [user("루트에서 한 말", cwd=str(repo))])
    assert run(projects, cwd=str(repo / "sub")) == eh.EXIT_OK
    assert "루트에서 한 말" in capsys.readouterr().out


def test_days_filter_by_record_timestamp(projects, capsys):
    now = datetime.now(timezone.utc)
    old = (now - timedelta(days=400)).isoformat().replace("+00:00", "Z")
    new = (now - timedelta(days=1)).isoformat().replace("+00:00", "Z")
    write_session(projects / "-proj", "a", [user("옛날 말", ts=old), user("최근 말", ts=new)])
    code = eh.main(["--projects-dir", str(projects), "--cwd", "/proj", "--days", "30"])
    assert code == eh.EXIT_OK
    out = capsys.readouterr().out
    assert "최근 말" in out and "옛날 말" not in out


def test_max_chars_keeps_newest(projects, capsys):
    recs = [user(f"발화{i:02d} " + "가" * 50, ts=f"2026-09-{i + 1:02d}T00:00:00.000Z") for i in range(20)]
    write_session(projects / "-proj", "a", recs)
    assert run(projects, "--max-chars", "400") == eh.EXIT_OK
    out = capsys.readouterr().out
    assert "발화19" in out and "발화00" not in out
    assert re.search(r"omitted=[1-9]\d*", out.splitlines()[0])


def test_no_history_exit_2(projects, capsys):
    assert run(projects) == eh.EXIT_NO_HISTORY
    assert "no session history" in capsys.readouterr().err


def test_format_changed_exit_3(projects, capsys):
    write_session(projects / "-proj", "a", [{"type": "user", "cwd": "/proj", "weird": True}])
    assert run(projects) == eh.EXIT_FORMAT_CHANGED
    assert "format" in capsys.readouterr().err


def test_malformed_lines_skipped(projects, capsys):
    write_session(projects / "-proj", "a", ["{broken", user("살아남은 말"), "\xff\xfe junk"])
    assert run(projects) == eh.EXIT_OK
    out = capsys.readouterr().out
    assert "살아남은 말" in out and "malformed=2" in out


def test_out_file_is_private(projects, tmp_path):
    write_session(projects / "-proj", "a", [user("비공개 확인")])
    target = tmp_path / "cache" / "extract.txt"
    assert run(projects, "--out", str(target)) == eh.EXIT_OK
    assert "비공개 확인" in target.read_text(encoding="utf-8")
    assert stat.S_IMODE(os.stat(target).st_mode) == 0o600


def test_bad_days_is_usage_error(projects):
    assert eh.main(["--projects-dir", str(projects), "--days", "0"]) == eh.EXIT_USAGE


def test_streams_large_file(projects, capsys):
    path = projects / "-proj"
    path.mkdir(parents=True)
    filler = '{"type":"assistant","message":{"content":"' + "y" * 500 + '"}}\n'
    with (path / "big.jsonl").open("w", encoding="utf-8") as fh:
        fh.write('{"type":"user","cwd":"/proj","timestamp":"%s","sessionId":"s-big-0000",'
                 '"message":{"content":"큰 파일 속 발화"}}\n' % RECENT)
        for _ in range(60000):  # about 30 MB
            fh.write(filler)
    started = time.monotonic()
    assert run(projects) == eh.EXIT_OK
    assert time.monotonic() - started < 30
    assert "큰 파일 속 발화" in capsys.readouterr().out


def test_cli_entrypoint_runs(projects):
    write_session(projects / "-proj", "a", [user("엔트리포인트")])
    res = subprocess.run([sys.executable, str(SCRIPTS / "extract_history.py"),
                          "--projects-dir", str(projects), "--cwd", "/proj", "--days", "36500"],
                         capture_output=True, text=True)
    assert res.returncode == 0 and "엔트리포인트" in res.stdout


def test_non_git_cwd_matches_exactly(tmp_path, projects, capsys):
    home = tmp_path / "home"
    (home / "other").mkdir(parents=True)
    write_session(projects / "h", "a", [user("홈에서 한 말", cwd=str(home))])
    write_session(projects / "o", "b", [user("하위 프로젝트 말", cwd=str(home / "other"),
                                             session="s-0002-bbbb")])
    assert run(projects, cwd=str(home)) == eh.EXIT_OK
    out = capsys.readouterr().out
    assert "홈에서 한 말" in out and "하위 프로젝트 말" not in out


def test_mixed_cwd_files_in_one_folder(projects, capsys):
    folder = projects / "shared"
    write_session(folder, "mine", [user("내 세션 말", cwd="/proj")])
    newer = write_session(folder, "other", [user("남의 세션 말", cwd="/elsewhere", session="s-0002-bbbb")])
    os.utime(newer, (time.time() + 60, time.time() + 60))
    assert run(projects) == eh.EXIT_OK
    out = capsys.readouterr().out
    assert "내 세션 말" in out and "남의 세션 말" not in out


def test_tiny_budget_still_returns_newest_line(projects, capsys):
    write_session(projects / "-proj", "a", [user("길다 " * 200)])
    assert run(projects, "--max-chars", "200") == eh.EXIT_OK
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 2 and len(lines[1]) <= 200 and lines[1].endswith("…")


def test_cwd_found_beyond_first_200_lines(projects, capsys):
    filler = ['{"type":"file-history-snapshot","snapshot":{}}'] * 300
    write_session(projects / "late", "a", filler + [user("늦게 나온 cwd")])
    assert run(projects) == eh.EXIT_OK
    assert "늦게 나온 cwd" in capsys.readouterr().out


def test_existing_cache_dir_permissions_tightened(projects, tmp_path):
    write_session(projects / "-proj", "a", [user("권한")])
    cache = tmp_path / "cache"
    cache.mkdir(mode=0o755)
    os.chmod(cache, 0o755)
    assert run(projects, "--out", str(cache / "extract.txt")) == eh.EXIT_OK
    assert stat.S_IMODE(os.stat(cache).st_mode) == 0o700


def test_collect_keeps_only_bounded_newest(projects):
    recs = [user(f"발화{i:03d}", ts=f"2026-09-{1 + i % 28:02d}T{i % 24:02d}:00:00.000Z") for i in range(300)]
    path = write_session(projects / "-proj", "a", recs)
    cutoff = eh.datetime(2000, 1, 1, tzinfo=eh.timezone.utc)
    got = eh.collect([path], cutoff, max_chars=500)
    kept = got.rows
    assert (got.total, got.sessions, got.malformed, got.oversized, got.unreadable) == (300, 1, 0, 0, 0)
    assert sum(len(r[2]) for r in kept) <= 500 + eh.MAX_UTTERANCE + 40
    assert len(kept) < 300
    assert kept == sorted(kept, key=lambda r: r[0])


def test_oversized_line_skipped_without_loading(projects, capsys, monkeypatch):
    monkeypatch.setattr(eh, "MAX_LINE", 1000)
    huge = '{"type":"user","cwd":"/proj","message":{"content":"' + "z" * 5000 + '"}}'
    write_session(projects / "-proj", "a", [user("앞 발화"), huge, user("뒤 발화")])
    assert run(projects) == eh.EXIT_OK
    out = capsys.readouterr().out
    assert "앞 발화" in out and "뒤 발화" in out and "zzzz" not in out
    assert "oversized=1" in out.splitlines()[0]


def test_symlinked_out_file_refused(projects, tmp_path):
    write_session(projects / "-proj", "a", [user("새면 안 되는 말")])
    victim = tmp_path / "victim.txt"
    victim.write_text("원본", encoding="utf-8")
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "extract.txt").symlink_to(victim)
    assert run(projects, "--out", str(cache / "extract.txt")) == eh.EXIT_USAGE
    assert victim.read_text(encoding="utf-8") == "원본"


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores file permissions")
def test_unreadable_file_skipped_and_counted(projects, capsys):
    write_session(projects / "-proj", "ok", [user("읽히는 말")])
    bad = write_session(projects / "-proj", "bad", [user("못 읽는 말", session="s-0002-bbbb")])
    os.chmod(bad, 0)
    try:
        assert run(projects) == eh.EXIT_OK
    finally:
        os.chmod(bad, 0o600)
    out = capsys.readouterr().out
    assert "읽히는 말" in out and "unreadable=" in out.splitlines()[0]


def test_out_dir_gives_each_run_its_own_private_file(projects, tmp_path, capsys):
    write_session(projects / "-proj", "a", [user("고유 파일")])
    out_dir = tmp_path / "cache"
    assert run(projects, "--out-dir", str(out_dir)) == eh.EXIT_OK
    first = Path(capsys.readouterr().out.strip())
    assert run(projects, "--out-dir", str(out_dir)) == eh.EXIT_OK
    second = Path(capsys.readouterr().out.strip())
    assert first != second and first.parent == second.parent == out_dir
    assert "고유 파일" in first.read_text(encoding="utf-8")
    assert stat.S_IMODE(os.stat(second).st_mode) == 0o600


def test_records_after_cd_elsewhere_excluded(projects, capsys):
    write_session(projects / "-proj", "a", [user("프로젝트 안 발화", cwd="/proj"),
                                            user("다른 곳으로 옮긴 뒤 발화", cwd="/elsewhere")])
    assert run(projects) == eh.EXIT_OK
    out = capsys.readouterr().out
    assert "프로젝트 안 발화" in out and "다른 곳으로 옮긴 뒤 발화" not in out


def test_session_that_cds_into_project_later_is_included(projects, capsys):
    write_session(projects / "-home", "a", [user("홈에서 시작", cwd="/elsewhere"),
                                            user("프로젝트로 옮긴 뒤 발화", cwd="/proj")])
    assert run(projects) == eh.EXIT_OK
    out = capsys.readouterr().out
    assert "프로젝트로 옮긴 뒤 발화" in out and "홈에서 시작" not in out


def test_file_mentions_spans_chunk_boundary(tmp_path):
    path = tmp_path / "x.jsonl"
    path.write_bytes(b"a" * 10 + b'"/proj' + b"b" * 10)
    assert eh.file_mentions(path, b'"/proj', chunk=8)
    assert not eh.file_mentions(path, b'"/nope', chunk=8)


def test_non_ascii_project_path(tmp_path, projects, capsys):
    proj = tmp_path / "나의_회사"
    proj.mkdir()
    write_session(projects / "k", "a", [user("한글 경로 발화", cwd=str(proj))])
    assert run(projects, cwd=str(proj)) == eh.EXIT_OK
    assert "한글 경로 발화" in capsys.readouterr().out


def test_records_without_cwd_excluded_in_project_scope(projects, capsys):
    no_cwd = user("cwd 없는 발화", session="s-0002-bbbb")
    del no_cwd["cwd"]
    write_session(projects / "-proj", "a", [user("정상 발화"), no_cwd])
    assert run(projects) == eh.EXIT_OK
    out = capsys.readouterr().out
    assert "정상 발화" in out and "cwd 없는 발화" not in out


def test_symlinked_session_file_ignored(projects, tmp_path, capsys):
    write_session(projects / "-proj", "real", [user("진짜 세션")])
    outside = write_session(tmp_path / "outside", "secret", [user("밖의 파일 내용")])
    (projects / "-proj" / "link.jsonl").symlink_to(outside)
    assert run(projects) == eh.EXIT_OK
    out = capsys.readouterr().out
    assert "진짜 세션" in out and "밖의 파일 내용" not in out


def test_out_dir_prunes_stale_extracts(projects, tmp_path, capsys):
    write_session(projects / "-proj", "a", [user("정리 확인")])
    out_dir = tmp_path / "cache"
    out_dir.mkdir()
    stale = out_dir / "extract-old.txt"
    stale.write_text("오래된 추출", encoding="utf-8")
    old = time.time() - 7200
    os.utime(stale, (old, old))
    keep = out_dir / "notes.txt"
    keep.write_text("남의 파일", encoding="utf-8")
    os.utime(keep, (old, old))
    assert run(projects, "--out-dir", str(out_dir)) == eh.EXIT_OK
    assert not stale.exists() and keep.exists()


def test_symlinked_project_folder_ignored(projects, tmp_path, capsys):
    write_session(projects / "-proj", "real", [user("진짜 세션")])
    outside = tmp_path / "sensitive"
    write_session(outside, "x", [user("링크 폴더 속 내용")])
    (projects / "alias").symlink_to(outside, target_is_directory=True)
    assert run(projects) == eh.EXIT_OK
    out = capsys.readouterr().out
    assert "진짜 세션" in out and "링크 폴더 속 내용" not in out


def test_remove_deletes_only_extract_files(tmp_path):
    ours = tmp_path / "extract-abc.txt"
    ours.write_text("x", encoding="utf-8")
    other = tmp_path / "notes.txt"
    other.write_text("x", encoding="utf-8")
    assert eh.main(["--remove", str(ours)]) == eh.EXIT_OK and not ours.exists()
    assert eh.main(["--remove", str(other)]) == eh.EXIT_USAGE and other.exists()
    link = tmp_path / "extract-link.txt"
    link.symlink_to(other)
    assert eh.main(["--remove", str(link)]) == eh.EXIT_USAGE and other.exists()
