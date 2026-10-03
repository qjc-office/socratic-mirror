from __future__ import annotations
import pytest
from redact import MASK, redact


# Fake secrets are assembled at runtime so that no secret-shaped literal
# lives in the repository (secret scanners would flag the test file itself).
FAKE = "abcdefghijklmnopqrstuvwxyz0123"
SAMPLES = [
    "sk" + "-ant-api03-" + FAKE,
    "gh" + "p_" + FAKE,
    "github" + "_pat_11" + FAKE,
    "xo" + "xb-1234567890-" + FAKE[:10],
    "AK" + "IA" + "ABCDEFGHIJKLMNOP",
    "ey" + "JhbGciOiJIUzI1NiJ9." + "ey" + "JzdWIiOiIxMjM0NTY3ODkwIn0." + FAKE,
]


@pytest.mark.parametrize("secret", SAMPLES)
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
