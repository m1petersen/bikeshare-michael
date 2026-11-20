#!/usr/bin/env bash
# PreToolUse hook for Bash: block shell commands that write into data/raw/.
#
# The deny rules in settings.json cover the Edit and Write tools only, and
# check_leakage.sh runs after Edit/Write only, so a Bash `cp` into data/raw/
# went unseen (Exercise 2, fault 4). This runs BEFORE the command; exit 2
# cancels it and sends stderr back to Claude.
#
# It is a pattern match, not a sandbox: a command that writes through an
# interpreter (`python -c "open('data/raw/x','w')"`) or a variable path gets
# past it. tests/test_contract.py (hash + folder contents) is the backstop.
set -uo pipefail

cmd=$(python3 -c \
  'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))')

case "$cmd" in
  *data/raw*) ;;
  *) exit 0 ;;
esac

# Commands that create, change or delete files, followed somewhere by
# data/raw; or output redirected into data/raw.
writes='(^|[;&|[:space:]])(cp|mv|rm|rsync|install|ln|touch|tee|dd|truncate|chmod|unzip|tar|wget|curl)[[:space:]].*data/raw'
inplace='(^|[;&|[:space:]])(sed|perl)[[:space:]]+(-[a-zA-Z]*i|--in-place).*data/raw'
redirect='>>?[[:space:]]*[^[:space:]]*data/raw'
gitwrite='git[[:space:]]+(rm|mv|checkout|restore)[[:space:]].*data/raw'

if printf '%s' "$cmd" | grep -Eq "$writes|$inplace|$redirect|$gitwrite"; then
  echo "Blocked: this command would write to data/raw/, which is immutable." >&2
  echo "Raw data changes are made by a person, outside the agent. Command:" >&2
  echo "  $cmd" >&2
  exit 2
fi
exit 0
