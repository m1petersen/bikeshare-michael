#!/usr/bin/env bash
# PostToolUse hook: re-run the whole test suite whenever src/ changes.
# The whole suite, not just tests/test_leakage.py: the row-loss test that
# catches a silent .map() lives in tests/test_contract.py (~1.3 s total).
#
# This runs AFTER the edit has landed, so it cannot prevent the write. What
# exit 2 does is send stderr back to Claude as a system message, so the
# failure is in front of the agent immediately and it cannot carry on as if
# the edit were fine. To make "done" itself conditional on green tests, add
# a Stop hook that runs `make test` and exits 2 on failure (check
# stop_hook_active in the payload to avoid looping).
set -uo pipefail

payload=$(cat)
path=$(printf '%s' "$payload" | python3 -c \
  'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))')

case "$path" in
  *src/*.py) ;;
  *) exit 0 ;;
esac

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
# Hooks run in Claude Code's environment, not an activated venv, so a bare
# `python` may lack pytest and report every edit as a failure.
py=python
[ -x .venv/bin/python ] && py=.venv/bin/python
if ! out=$("$py" -m pytest tests/ -q 2>&1); then
  echo "Tests failed after editing $path:" >&2
  echo "$out" | tail -20 >&2
  exit 2
fi
exit 0
