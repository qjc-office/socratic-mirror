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


@pytest.mark.parametrize("secret", SAMPLES,
                         ids=["openai", "github", "github-pat", "slack", "aws", "jwt"])
def test_token_patterns_masked(secret):
    out = redact(f"키는 {secret} 입니다")
    assert secret not in out
    assert MASK in out


def test_uppercase_assignment_value_masked():
    out = redact('OPENAI_API_KEY=abc123def DB_PASSWORD: "hunter2"')
    assert "abc123def" not in out and "hunter2" not in out
    assert out.startswith("OPENAI_API_KEY=")
    second = redact('DB_PASSWORD: "hunter2"')
    assert second.startswith("DB_PASSWORD") and "hunter2" not in second


def test_lowercase_assignment_with_equals_masked():
    assert "s3cr3t" not in redact("api_key=s3cr3t")


def test_plain_prose_untouched():
    text = "핵심 key: 고객이 먼저다. 토큰 비용은 신경 안 써도 돼."
    assert redact(text) == text


def test_words_containing_sk_dash_untouched():
    text = "task-management-dashboard-v2 와 risk-assessment-checklist-final"
    assert redact(text) == text


def test_bare_secret_word_assignments_masked():
    out = redact("TOKEN=SYNTHETIC_VALUE_1 SECRET: SYNTHETIC_VALUE_2 password=SYNTHETIC_VALUE_3")
    assert "SYNTHETIC_VALUE" not in out


def test_bearer_header_masked():
    bearer = "Bear" + "er " + "abcdefghijklmnopqrstuvwxyz012345"
    out = redact("Authorization: " + bearer)
    assert "abcdefghijklmnopqrstuvwxyz012345" not in out


def test_structured_and_spaced_assignments_masked():
    samples = ['{"API_KEY":"FAKE_VALUE_1"}', "{'password': 'FAKE_VALUE_2'}",
               "api_key = FAKE_VALUE_3", "client_secret: FAKE_VALUE_4", "password: FAKE_VALUE_5"]
    for text in samples:
        assert "FAKE_VALUE" not in redact(text), text


def test_prose_with_colon_still_untouched():
    for text in ("핵심 key: 고객이 먼저다", "토큰 token: 비용 얘기", "Secret: 그건 비밀이야"):
        assert redact(text) == text, text


def test_camel_case_colon_keys_masked():
    for text in ("apiKey: FAKE_VALUE_6", "clientSecret: FAKE_VALUE_7", "authToken: FAKE_VALUE_8"):
        assert "FAKE_VALUE" not in redact(text), text


def test_escaped_quote_inside_json_value_masked():
    out = redact('{"password":"prefix\\"synthetic-private-value"}')
    assert "synthetic-private-value" not in out


def test_nested_colon_keys_masked():
    for text in ("config: {apiKey: demo_value}", "credentials:\n  password: demo_value",
                 "tokens:\n  client_secret: demo_value"):
        assert "demo_value" not in redact(text), text


def test_yaml_doubled_single_quote_masked():
    assert "secret-suffix" not in redact("password: 'prefix''secret-suffix'")


def test_unquoted_value_with_spaces_masked_to_line_end():
    out = redact("password: correct horse battery staple\n다음 줄은 그대로")
    assert "horse" not in out and "staple" not in out and "다음 줄은 그대로" in out
