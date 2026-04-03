#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"

if echo "$input" | grep -E '"command".*(rm -rf|git reset --hard|git clean -fd|sudo )' >/dev/null 2>&1; then
  echo '{"decision":"deny","reason":"Dangerous command blocked during pre-push review."}'
  exit 2
fi

exit 0
