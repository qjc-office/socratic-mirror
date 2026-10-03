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
