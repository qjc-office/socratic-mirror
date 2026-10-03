from __future__ import annotations
from conftest import user
from extract_history import MAX_UTTERANCE, clean_line, extract_text, parse_line
from redact import MASK


def test_plain_string_content():
    assert extract_text(user("나는 혼자 해야 빨라")) == "나는 혼자 해야 빨라"


def test_text_blocks_kept_tool_result_dropped():
    rec = user([{"type": "tool_result", "content": "ls output"},
                {"type": "text", "text": "이거 왜 안 돼?"}])
    assert extract_text(rec) == "이거 왜 안 돼?"


def test_tool_result_only_is_none():
    assert extract_text(user([{"type": "tool_result", "content": "x"}])) is None


def test_meta_sidechain_compact_dropped():
    assert extract_text(user("a", isMeta=True)) is None
    assert extract_text(user("a", isSidechain=True)) is None
    assert extract_text(user("a", isCompactSummary=True)) is None


def test_non_user_types_dropped():
    rec = user("a")
    rec["type"] = "assistant"
    assert extract_text(rec) is None


def test_tag_blocks_stripped():
    text = "<command-name>/effort</command-name>\n<command-message>effort</command-message>"
    assert extract_text(user(text)) is None
    mixed = "<system-reminder>hook said hi</system-reminder>진짜 질문은 이거야"
    assert extract_text(user(mixed)) == "진짜 질문은 이거야"


def test_interrupt_marker_dropped():
    assert extract_text(user("[Request interrupted by user]")) is None


def test_long_paste_truncated_and_redacted():
    paste = "로그:\n" + ("x" * 2000) + " token=" + "sk" + "-ant-api03-" + "abcdefghijklmnopqrstuvwx"
    line = clean_line(paste)
    assert len(line) <= MAX_UTTERANCE + 1
    assert line.endswith("…")
    assert "\n" not in line and "⏎" in line
    short = clean_line("API_KEY=abc123 끝")
    assert "abc123" not in short and MASK in short


def test_malformed_lines_counted_not_fatal():
    assert parse_line("{not json") is None
    assert parse_line("[1, 2]") is None
    assert parse_line("") is None
    assert parse_line('{"type": "user"}') == {"type": "user"}


def test_odd_message_shapes_do_not_crash():
    assert extract_text({"type": "user", "message": "plain string"}) is None
    assert extract_text({"type": "user", "message": {"content": [{"type": "text", "text": 42}]}}) is None
    assert extract_text({"type": "user", "message": {"content": [{"type": "text", "text": None},
                                                                  {"type": "text", "text": "살아남음"}]}}) == "살아남음"
