#!/usr/bin/env bash
# Cài pre-push hook vào .git/hooks/
set -e

HOOK_SRC="$(cd "$(dirname "$0")/.." && pwd)/.githooks/pre-push"
HOOK_DST="$(cd "$(dirname "$0")/.." && pwd)/.git/hooks/pre-push"

cp "$HOOK_SRC" "$HOOK_DST"
chmod +x "$HOOK_DST"
echo "✅ pre-push hook đã được cài vào .git/hooks/pre-push"
