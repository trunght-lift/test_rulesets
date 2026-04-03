#!/usr/bin/env python3
"""
Parse JSONL output từ OpenHands headless --json mode.
Tìm verdict APPROVE / REJECT trong nội dung agent trả về.
Exit 0 = OK to push, Exit 1 = blocked.
"""
import sys
import json
import re

APPROVE_PATTERN = re.compile(r'\bAPPROVE\b', re.IGNORECASE)
REJECT_PATTERN  = re.compile(r'\bREJECT\b',  re.IGNORECASE)

def extract_text(event: dict) -> str:
    """Lấy text từ các loại event JSONL của OpenHands."""
    # observation content
    if event.get("type") == "observation":
        return event.get("content", "")
    # action message
    if event.get("type") == "action":
        return event.get("message", "") or event.get("content", "")
    return ""

def main():
    lines = sys.stdin.read().strip().splitlines()
    full_text = ""
    last_content = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            text = extract_text(event)
            if text:
                full_text += "\n" + text
                last_content = text
        except json.JSONDecodeError:
            # Dòng plain text (fallback khi không dùng --json)
            full_text += "\n" + line
            last_content = line

    if not full_text.strip():
        print("[review] Không có output từ OpenHands.", file=sys.stderr)
        sys.exit(1)

    # In summary để dev thấy
    print("\n--- OpenHands Code Review ---")
    print(last_content[:2000])  # in phần cuối cùng (thường là verdict)
    print("-----------------------------\n")

    if REJECT_PATTERN.search(full_text):
        print("[review] ❌  REJECTED — push bị chặn.", file=sys.stderr)
        sys.exit(1)

    if APPROVE_PATTERN.search(full_text):
        print("[review] ✅  APPROVED — tiếp tục push.")
        sys.exit(0)

    # Không tìm thấy verdict rõ ràng → cảnh báo nhưng cho qua
    print("[review] ⚠️  Không tìm thấy verdict rõ ràng (APPROVE/REJECT). Cho phép push.", file=sys.stderr)
    sys.exit(0)

if __name__ == "__main__":
    main()
