#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"

cmd="$(printf '%s' "$input" | python3 - <<'PY'
import json, sys

raw = sys.stdin.read()
try:
    data = json.loads(raw)
except Exception:
    print("")
    raise SystemExit(0)

command = data.get("tool_input", {}).get("command", "")
print(command)
PY
)"

if [ -z "$cmd" ]; then
  exit 0
fi

trimmed="$(printf '%s' "$cmd" | sed 's/^[[:space:]]*//')"

case "$trimmed" in
  rm\ -rf*|sudo\ *|git\ reset\ --hard*|git\ clean\ -fd*)
    echo '{"decision":"deny","reason":"Dangerous command blocked during pre-push review."}'
    exit 2
    ;;
esac

exit 0