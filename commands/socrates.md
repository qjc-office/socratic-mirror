---
description: Socratic self-interrogation over your Claude Code history (questions only)
argument-hint: "[close|triad] [--days N] [--all-projects]"
allowed-tools: ["Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_history.py:*)", "Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/append_log.py:*)", "Read", "Skill", "Agent"]
---

Invoke the `socratic-mirror:socratic-inquiry` skill with the Skill tool, passing these arguments unchanged: $ARGUMENTS

The plugin scripts live in `${CLAUDE_PLUGIN_ROOT}/scripts`. When the skill runs a script, call it exactly as `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py ...` (unquoted, this exact prefix) so the pre-approved permission matches.

Then follow that skill exactly. Do not answer, advise, or comfort outside what the skill allows.
