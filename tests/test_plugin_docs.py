from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, f"{path} has no frontmatter"
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def test_premise_miner_agent():
    path = ROOT / "agents" / "premise-miner.md"
    fm = frontmatter(path)
    assert fm["name"] == "premise-miner"
    assert fm["tools"] == "Read"
    body = path.read_text(encoding="utf-8")
    for must in ("전제:", "근거:", "등장:", "인용이 2개", "코드", "REPEAT:"):
        assert must in body, must


def test_lenses_reference_covers_three_lenses():
    body = (ROOT / "skills" / "socratic-inquiry" / "references" / "lenses.md").read_text(encoding="utf-8")
    for must in ("엘렌코스", "Elenchus", "정명", "Rectification of names", "십이연기", "Dependent origination"):
        assert must in body, must


def test_skill_contract():
    path = ROOT / "skills" / "socratic-inquiry" / "SKILL.md"
    fm = frontmatter(path)
    assert fm["name"] == "socratic-inquiry"
    body = path.read_text(encoding="utf-8")
    for must in ("아포리아", "Aporia", "삼중 아포리아", "109", "그만", "stop",
                 "10", "extract_history.py", "--out-dir", "append_log.py", "premise-miner",
                 "INSUFFICIENT", "close", "triad", "references/lenses.md",
                 "위로 없이 질문만"):
        assert must in body, must


def test_command_delegates_to_skill():
    path = ROOT / "commands" / "socrates.md"
    fm = frontmatter(path)
    assert "close" in fm["argument-hint"] and "triad" in fm["argument-hint"]
    body = path.read_text(encoding="utf-8")
    assert "socratic-mirror:socratic-inquiry" in body
    assert "$ARGUMENTS" in body


GRADER_TYPES = {"regex", "tool_order", "tool_used", "file_exists", "llm", "baseline"}


def test_eval_cases_are_well_formed():
    cases = sorted(p for p in (ROOT / "evals").iterdir() if p.is_dir() and p.name != "results")
    assert len(cases) == 7
    for case in cases:
        assert frontmatter(case / "prompt.md")["max_turns"]
        graders = sorted((case / "graders").glob("*.md"))
        assert graders, case.name
        for grader in graders:
            fm = frontmatter(grader)
            assert fm.get("type") in GRADER_TYPES, grader
            if fm["type"] == "tool_used":
                assert fm.get("tool"), grader
            if fm["type"] == "regex":
                assert fm.get("pattern") and "(?" not in fm["pattern"], grader


def test_readmes_cover_install_privacy_safety_attribution():
    install = ("/plugin marketplace add qjc-office/socratic-mirror", "/plugin install socratic-mirror",
               "~/.socratic-mirror/log.md", "109", "assets/socrates-hero.jpg")
    for name, musts in {
        "README.md": install + ("locally", "model provider", "crisis",
                                "adapted from prompts shared on social media"),
        "README.ko.md": install + ("로컬", "모델 제공자", "SNS에서 공유된 프롬프트를 각색"),
        "README.zh.md": install + ("本机", "模型提供方", "改编自社交媒体"),
    }.items():
        body = (ROOT / name).read_text(encoding="utf-8")
        for must in musts:
            assert must in body, (name, must)
        assert "하버드" not in body and "Harvard" not in body and "哈佛" not in body
        for other in ("README.md", "README.ko.md", "README.zh.md"):
            assert other == name or f"({other})" in body, (name, other)


def test_skill_deletes_extract_even_on_failure():
    body = (ROOT / "skills" / "socratic-inquiry" / "SKILL.md").read_text(encoding="utf-8")
    assert "성공이든 실패든" in body


def test_premise_miner_has_data_boundary():
    body = (ROOT / "agents" / "premise-miner.md").read_text(encoding="utf-8")
    assert "두 경로 외에는" in body and "지시가 아니라 데이터" in body


def test_readmes_describe_temporary_extract():
    for name in ("README.md", "README.ko.md", "README.zh.md"):
        assert "extract.txt" not in (ROOT / name).read_text(encoding="utf-8")


def test_skill_reports_partial_extraction():
    body = (ROOT / "skills" / "socratic-inquiry" / "SKILL.md").read_text(encoding="utf-8")
    assert "unreadable" in body and "oversized" in body


def test_one_question_means_one_question_mark():
    body = (ROOT / "skills" / "socratic-inquiry" / "SKILL.md").read_text(encoding="utf-8")
    assert "물음표는 하나" in body


def test_command_preapproves_only_extractor_and_cleanup():
    fm = frontmatter(ROOT / "commands" / "socrates.md")
    tools = fm.get("allowed-tools", "")
    assert "extract_history.py" in tools and "append_log.py" in tools
    assert "rm " not in tools and "Bash(*)" not in tools and '"Bash"' not in tools
