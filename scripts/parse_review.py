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
    
    # Chỉ lấy các message từ agent (bỏ system/user prompt)
    agent_messages = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            # Chỉ parse nếu event là dict
            if isinstance(event, dict):
                text = extract_text(event)
                if text:
                    full_text += "\n" + text
                    last_content = text
                    # Lưu message từ agent
                    if event.get("source") == "agent" or event.get("type") == "observation":
                        agent_messages.append(text)
            else:
                # JSON nhưng không phải dict (array, string, etc.)
                full_text += "\n" + str(event)
                last_content = str(event)
        except (json.JSONDecodeError, TypeError):
            # Dòng plain text (fallback khi không dùng --json)
            full_text += "\n" + line
            last_content = line

    if not full_text.strip():
        print("[review] Không có output từ OpenHands.", file=sys.stderr)
        sys.exit(1)

    # Chỉ in phần kết luận cuối (thường là verdict)
    # Tìm đoạn text có chứa APPROVE/REJECT
    verdict_text = ""
    for msg in reversed(agent_messages):
        if APPROVE_PATTERN.search(msg) or REJECT_PATTERN.search(msg):
            verdict_text = msg
            break
    
    # Nếu không tìm thấy trong agent_messages, lấy last_content
    if not verdict_text:
        verdict_text = last_content

    print("\n" + "="*60)
    print("OpenHands Code Review")
    print("="*60)
    # Chỉ in tối đa 1000 ký tự cuối
    display_text = verdict_text[-1000:] if len(verdict_text) > 1000 else verdict_text
    print(display_text.strip())
    print("="*60 + "\n")

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
