#!/bin/bash
# Run socratic-mirror behaviour evals against this checkout.
# Must be run from a normal terminal, not from inside a Claude Code session.
# Usage: bash scripts/run-evals.sh [--runs 1] [--ablation none]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"
# Some proxy setups leak these into child sessions and break login; unset if present.
env -u TEAMCLAUDE_SESSION_SUPERVISED -u TEAMCLAUDE_CLAUDE_BIN -u ANTHROPIC_BASE_URL \
  claude plugin eval "$ROOT" --eval-dir evals --trust-plugin --no-publish "$@"
