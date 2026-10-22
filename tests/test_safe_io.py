from __future__ import annotations
import os
import stat
import time

import pytest
import safe_io


def mode(path) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)


def age(path, seconds: float) -> None:
    then = time.time() - seconds
    os.utime(path, (then, then))


# ensure_private_dir

def test_private_dir_created_nested_with_700(tmp_path):
    target = tmp_path / "a" / "b"
    safe_io.ensure_private_dir(target)
    assert target.is_dir()
    assert mode(target) == 0o700


def test_private_dir_tightens_existing_open_dir(tmp_path):
    target = tmp_path / "cache"
    target.mkdir(mode=0o755)
    os.chmod(target, 0o755)
    safe_io.ensure_private_dir(target)
    assert mode(target) == 0o700


def test_private_dir_refuses_symlink_and_leaves_target_alone(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    os.chmod(real, 0o755)
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(OSError, match="not a real directory"):
        safe_io.ensure_private_dir(link)
    assert mode(real) == 0o755


def test_private_dir_refuses_regular_file(tmp_path):
    target = tmp_path / "cache"
    target.write_text("x", encoding="utf-8")
    with pytest.raises(OSError):
        safe_io.ensure_private_dir(target)
    assert target.read_text(encoding="utf-8") == "x"


# write_atomic

def test_atomic_write_replaces_and_is_private(tmp_path):
    target = tmp_path / "cache" / "extract.txt"
    safe_io.write_atomic(target, "첫째")
    safe_io.write_atomic(target, "둘째")
    assert target.read_text(encoding="utf-8") == "둘째"
    assert mode(target) == 0o600
    assert mode(target.parent) == 0o700
    assert sorted(p.name for p in target.parent.iterdir()) == ["extract.txt"]


def test_atomic_write_failure_keeps_old_file(tmp_path, monkeypatch):
    target = tmp_path / "extract.txt"
    safe_io.write_atomic(target, "멀쩡한 이전 캐시")

    def boom(*_args):
        raise OSError("disk full")

    monkeypatch.setattr(safe_io.os, "replace", boom)
    with pytest.raises(OSError):
        safe_io.write_atomic(target, "반쯤 쓴 새 캐시")
    assert target.read_text(encoding="utf-8") == "멀쩡한 이전 캐시"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["extract.txt"]


def test_atomic_write_cleans_temp_on_interrupt(tmp_path, monkeypatch):
    target = tmp_path / "extract.txt"

    def interrupt(*_args):
        raise KeyboardInterrupt

    monkeypatch.setattr(safe_io.os, "replace", interrupt)
    with pytest.raises(KeyboardInterrupt):
        safe_io.write_atomic(target, "중단")
    assert list(tmp_path.iterdir()) == []


def test_atomic_write_keeps_original_error_when_cleanup_fails(tmp_path, monkeypatch):
    target = tmp_path / "extract.txt"

    def boom(*_args):
        raise OSError("disk full")

    def unlink_fails(*_args):
        raise OSError("cannot unlink")

    monkeypatch.setattr(safe_io.os, "replace", boom)
    monkeypatch.setattr(safe_io.os, "unlink", unlink_fails)
    with pytest.raises(OSError, match="disk full"):
        safe_io.write_atomic(target, "새 캐시")
    assert not target.exists()


def test_atomic_write_refuses_symlink_at_path(tmp_path):
    victim = tmp_path / "victim.txt"
    victim.write_text("원본", encoding="utf-8")
    link = tmp_path / "extract.txt"
    link.symlink_to(victim)
    with pytest.raises(OSError, match="symlink"):
        safe_io.write_atomic(link, "덮어쓰기")
    assert link.is_symlink()
    assert victim.read_text(encoding="utf-8") == "원본"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["extract.txt", "victim.txt"]


def test_atomic_write_refuses_symlinked_parent(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "cache"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(OSError):
        safe_io.write_atomic(link / "extract.txt", "내용")
    assert list(real.iterdir()) == []


# prune_stale

def test_prune_missing_dir_returns_zero(tmp_path):
    assert safe_io.prune_stale(tmp_path / "nope") == 0


def test_prune_removes_only_old_own_txt_files(tmp_path):
    old = tmp_path / "extract-old.txt"
    fresh = tmp_path / "extract-fresh.txt"
    other_prefix = tmp_path / "notes-old.txt"
    other_suffix = tmp_path / "extract-old.log"
    for path in (old, fresh, other_prefix, other_suffix):
        path.write_text("x", encoding="utf-8")
    for path in (old, other_prefix, other_suffix):
        age(path, 7200)

    assert safe_io.prune_stale(tmp_path) == 1
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "extract-fresh.txt", "extract-old.log", "notes-old.txt"]


def test_prune_skips_symlinks_and_directories(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    victim = outside / "victim.txt"
    victim.write_text("남의 파일", encoding="utf-8")
    age(victim, 7200)
    cache = tmp_path / "cache"
    cache.mkdir()
    link = cache / "extract-link.txt"
    link.symlink_to(victim)
    folder = cache / "extract-dir.txt"
    folder.mkdir()
    age(folder, 7200)

    assert safe_io.prune_stale(cache) == 0
    assert link.is_symlink()
    assert folder.is_dir()
    assert victim.read_text(encoding="utf-8") == "남의 파일"


def test_prune_honours_prefix_and_max_age(tmp_path):
    log = tmp_path / "session-1.txt"
    log.write_text("x", encoding="utf-8")
    age(log, 120)
    assert safe_io.prune_stale(tmp_path, prefix="session-", max_age=600) == 0
    assert safe_io.prune_stale(tmp_path, prefix="session-", max_age=60) == 1
    assert not log.exists()


def test_prune_continues_past_unremovable_file(tmp_path, monkeypatch):
    names = ["extract-a.txt", "extract-b.txt", "extract-c.txt"]
    for name in names:
        path = tmp_path / name
        path.write_text("x", encoding="utf-8")
        age(path, 7200)
    real_unlink = type(tmp_path).unlink

    def flaky_unlink(self, *args, **kwargs):
        if self.name == "extract-b.txt":
            raise PermissionError("busy")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(type(tmp_path), "unlink", flaky_unlink)
    assert safe_io.prune_stale(tmp_path) == 2
    assert [p.name for p in tmp_path.iterdir()] == ["extract-b.txt"]


# write_unique

def test_write_unique_makes_new_private_files(tmp_path):
    cache = tmp_path / "cache"
    first = safe_io.write_unique(cache, "하나")
    second = safe_io.write_unique(cache, "둘")
    assert first != second
    for path, text in ((first, "하나"), (second, "둘")):
        assert path.parent == cache
        assert path.name.startswith("extract-") and path.suffix == ".txt"
        assert path.read_text(encoding="utf-8") == text
        assert mode(path) == 0o600
    assert mode(cache) == 0o700


def test_write_unique_custom_prefix_is_prunable(tmp_path):
    path = safe_io.write_unique(tmp_path, "x", prefix="probe-")
    assert path.name.startswith("probe-")
    age(path, 7200)
    assert safe_io.prune_stale(tmp_path, prefix="probe-") == 1


def test_write_unique_refuses_symlinked_dir(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "cache"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(OSError):
        safe_io.write_unique(link, "내용")
    assert list(real.iterdir()) == []


# open_private

def test_open_private_creates_600_file(tmp_path):
    target = tmp_path / "logs" / "log.md"
    with safe_io.open_private(target, append=False) as fh:
        fh.write("한 줄\n")
    assert target.read_text(encoding="utf-8") == "한 줄\n"
    assert mode(target) == 0o600
    assert mode(target.parent) == 0o700


def test_open_private_append_vs_truncate(tmp_path):
    target = tmp_path / "log.md"
    with safe_io.open_private(target, append=True) as fh:
        fh.write("a\n")
    with safe_io.open_private(target, append=True) as fh:
        fh.write("b\n")
    assert target.read_text(encoding="utf-8") == "a\nb\n"
    with safe_io.open_private(target, append=False) as fh:
        fh.write("c\n")
    assert target.read_text(encoding="utf-8") == "c\n"


def test_open_private_tightens_existing_file(tmp_path):
    target = tmp_path / "log.md"
    target.write_text("old\n", encoding="utf-8")
    os.chmod(target, 0o644)
    with safe_io.open_private(target, append=True) as fh:
        fh.write("new\n")
    assert mode(target) == 0o600
    assert target.read_text(encoding="utf-8") == "old\nnew\n"


@pytest.mark.parametrize("append", [True, False])
def test_open_private_refuses_symlink(tmp_path, append):
    victim = tmp_path / "victim.md"
    victim.write_text("원본", encoding="utf-8")
    os.chmod(victim, 0o644)
    link = tmp_path / "log.md"
    link.symlink_to(victim)
    with pytest.raises(OSError, match="symlink"):
        safe_io.open_private(link, append=append)
    assert victim.read_text(encoding="utf-8") == "원본"
    assert mode(victim) == 0o644


def test_open_private_refuses_dangling_symlink(tmp_path):
    link = tmp_path / "log.md"
    link.symlink_to(tmp_path / "would-be-created.md")
    with pytest.raises(OSError, match="symlink"):
        safe_io.open_private(link, append=True)
    assert not (tmp_path / "would-be-created.md").exists()


def test_open_private_works_without_fchmod(tmp_path, monkeypatch):
    monkeypatch.delattr(safe_io.os, "fchmod", raising=False)
    target = tmp_path / "log.md"
    with safe_io.open_private(target, append=False) as fh:
        fh.write("x")
    assert target.read_text(encoding="utf-8") == "x"
    assert mode(target) == 0o600
