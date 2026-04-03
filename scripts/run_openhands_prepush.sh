#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

TMP_DIFF="$(mktemp)"
TMP_TASK="$(mktemp)"
TMP_OUT="$(mktemp)"

cleanup() {
  rm -f "$TMP_DIFF" "$TMP_TASK" "$TMP_OUT"
}
trap cleanup EXIT

if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
  git diff '@{u}...HEAD' > "$TMP_DIFF"
else
  git diff HEAD~1..HEAD > "$TMP_DIFF" 2>/dev/null || true
fi

if [ ! -s "$TMP_DIFF" ]; then
  echo "[pre-push] No diff to review. Allowing push."
  exit 0
fi

cat scripts/openhands_prepush_task.txt > "$TMP_TASK"
{
  echo
  echo "Git diff to review:"
  echo
  cat "$TMP_DIFF"
} >> "$TMP_TASK"

echo "[pre-push] Running OpenHands headless review..."

openhands --headless --json -f "$TMP_TASK" > "$TMP_OUT"

tail -n 40 "$TMP_OUT" || true

DECISION="$(grep -E '^(ALLOW_PUSH|BLOCK_PUSH)$' "$TMP_OUT" | tail -n 1 | tr -d '\r')"

case "$DECISION" in
  BLOCK_PUSH)
    echo "[pre-push] OpenHands found blocking issues. Push rejected."
    exit 1
    ;;
  ALLOW_PUSH)
    echo "[pre-push] OpenHands approved. Push allowed."
    exit 0
    ;;
  *)
    echo "[pre-push] No clear ALLOW_PUSH/BLOCK_PUSH verdict. Push rejected."
    exit 1
    ;;
esac