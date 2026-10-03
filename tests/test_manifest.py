from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(name):
    return json.loads((ROOT / ".claude-plugin" / name).read_text(encoding="utf-8"))


def test_plugin_manifest_fields():
    p = load("plugin.json")
    assert p["name"] == "socratic-mirror"
    assert isinstance(p["author"], dict) and p["author"]["name"]
    assert p["license"] == "MIT"
    assert p["version"] == "0.1.0"


def test_marketplace_points_to_repo_root():
    m = load("marketplace.json")
    assert m["name"] == "socratic-mirror"
    assert isinstance(m["owner"], dict)
    [plugin] = m["plugins"]
    assert plugin["name"] == "socratic-mirror"
    assert plugin["source"] == "./"
    assert plugin["version"] == load("plugin.json")["version"]
