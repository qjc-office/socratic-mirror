from __future__ import annotations
import pytest
from redact import MASK, redact


@pytest.mark.parametrize("secret", [
    "sk-ant-api03-abcdefghijklmnopqrstuvwx",
    "ghp_abcdefghijklmnopqrstuvwxyz0123",
    "github_pat_11ABCDEFG0123456789_abcdefghij",
    "xoxb-1234567890-abcdefghij",
    "AKIAABCDEFGHIJKLMNOP",
    "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijklmnop",
])
def test_token_patterns_masked(secret):
    out = redact(f"키는 {secret} 입니다")
    assert secret not in out
    assert MASK in out


def test_uppercase_assignment_value_masked():
    out = redact('OPENAI_API_KEY=abc123def DB_PASSWORD: "hunter2"')
    assert "abc123def" not in out and "hunter2" not in out
    assert "OPENAI_API_KEY=" in out and "DB_PASSWORD" in out


def test_lowercase_assignment_with_equals_masked():
    assert "s3cr3t" not in redact("api_key=s3cr3t")


def test_plain_prose_untouched():
    text = "핵심 key: 고객이 먼저다. 토큰 비용은 신경 안 써도 돼."
    assert redact(text) == text


def test_words_containing_sk_dash_untouched():
    text = "task-management-dashboard-v2 와 risk-assessment-checklist-final"
    assert redact(text) == text
