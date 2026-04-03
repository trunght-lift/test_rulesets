#!/usr/bin/env bash
set -euo pipefail

cd "$OPENHANDS_PROJECT_DIR"

if [ -f package.json ]; then
  npm run lint >/dev/null 2>&1 || {
    echo '{"decision":"deny","reason":"Lint failed. Agent must not finish yet."}'
    exit 2
  }
fi

if [ -f pyproject.toml ] || [ -f requirements.txt ]; then
  python3 -m pytest -q >/dev/null 2>&1 || {
    echo '{"decision":"deny","reason":"Tests failed. Agent must not finish yet."}'
    exit 2
  }
fi

exit 0
