from __future__ import annotations
import io
import os
import stat

import append_log


def test_appends_with_heading_and_redaction(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SOCRATIC_MIRROR_HOME", str(tmp_path / "home"))
    entry = "- 무너진 전제: 혼자 해야 빠르다\n- 메모 API_KEY=abc123"
    assert append_log.main(["--project", "demo"], io.StringIO(entry)) == 0
    log = tmp_path / "home" / "log.md"
    text = log.read_text(encoding="utf-8")
    assert "· demo" in text and "혼자 해야 빠르다" in text and "abc123" not in text
    assert stat.S_IMODE(os.stat(log).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(log.parent).st_mode) == 0o700
    assert str(log) in capsys.readouterr().out


def test_second_entry_appends(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCRATIC_MIRROR_HOME", str(tmp_path))
    append_log.main(["--project", "a"], io.StringIO("첫째"))
    append_log.main(["--project", "b"], io.StringIO("둘째"))
    text = (tmp_path / "log.md").read_text(encoding="utf-8")
    assert text.index("첫째") < text.index("둘째")
    assert text.count("\n## ") == 2


def test_empty_stdin_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCRATIC_MIRROR_HOME", str(tmp_path))
    assert append_log.main(["--project", "a"], io.StringIO("   \n")) == 1
    assert not (tmp_path / "log.md").exists()
