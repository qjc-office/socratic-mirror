from __future__ import annotations
import os
import stat

import pytest
import safe_io


def test_atomic_write_replaces_and_is_private(tmp_path):
    target = tmp_path / "cache" / "extract.txt"
    safe_io.write_atomic(target, "첫째")
    safe_io.write_atomic(target, "둘째")
    assert target.read_text(encoding="utf-8") == "둘째"
    assert stat.S_IMODE(os.stat(target).st_mode) == 0o600
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
