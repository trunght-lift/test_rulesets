#!/usr/bin/env python3
"""
Parse output từ OpenHands headless --json mode.
Tìm verdict APPROVE / REJECT trong nội dung agent trả về.
Exit 0 = OK to push, Exit 1 = blocked.
"""
import sys
import json
import re
import ast

APPROVE_PATTERN = re.compile(r'\bAPPROVE\b', re.IGNORECASE)
REJECT_PATTERN  = re.compile(r'\bREJECT\b',  re.IGNORECASE)

def extract_agent_messages_from_json_events(lines):
    """
    Parse JSON events từ output có marker --JSON Event--.
    Trả về list các text từ agent responses.

    Output của OpenHands là list of strings, mỗi phần tử là một dòng.
    Các JSON block nằm giữa hai marker '--JSON Event--' hoặc kết thúc bởi
    'Agent finished' / hết danh sách.
    """
    agent_responses = []
    i = 0
    n = len(lines)

    while i < n:
        line = str(lines[i]).strip()

        if line == "--JSON Event--":
            i += 1
            json_lines = []

            # Gom tất cả các dòng cho đến marker tiếp theo hoặc hết list
            while i < n:
                current = str(lines[i]).strip()
                if current in ("--JSON Event--", "Agent finished", "Agent is working"):
                    break
                json_lines.append(str(lines[i]))
                i += 1

            json_str = "\n".join(json_lines).strip()
            if not json_str:
                continue

            try:
                event = json.loads(json_str)
            except json.JSONDecodeError:
                continue

            if (
                isinstance(event, dict)
                and event.get("source") == "agent"
                and event.get("kind") == "MessageEvent"
            ):
                content_list = event.get("llm_message", {}).get("content", [])
                for item in content_list:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text", "").strip()
                        if text:
                            agent_responses.append(text)
        else:
            i += 1

    return agent_responses

def extract_agent_messages_fallback(raw_text):
    """
    Fallback: tìm toàn bộ message agent trong plain text.
    Dùng khi không parse được JSON events.
    """
    messages = []

    # Tìm trong CONVERSATION SUMMARY block (OpenHands in-terminal display)
    summary_match = re.search(
        r'CONVERSATION SUMMARY.*?─+\n(.*?)(?:\n─{10,}|\Z)',
        raw_text, re.DOTALL
    )
    if summary_match:
        messages.append(summary_match.group(1).strip())
        return messages

    # Tìm trong box Agent (╭─ Agent ─╮ ... ╰─╯)
    box_match = re.search(
        r'╭─.*?Agent.*?─+╮(.*?)╰─+╯',
        raw_text, re.DOTALL
    )
    if box_match:
        # Xóa ANSI codes và ký tự box
        content = box_match.group(1)
        content = re.sub(r'\x1b\[[0-9;]*m', '', content)   # ANSI codes
        content = re.sub(r'^\s*│\s?', '', content, flags=re.MULTILINE)  # border │
        messages.append(content.strip())
        return messages

    # Last resort: tìm đoạn dài nhất chứa APPROVE hoặc REJECT
    candidates = re.findall(
        r'(?:^|\n)((?:[^\n]+\n){0,20}[^\n]*(?:APPROVE|REJECT)[^\n]*(?:\n[^\n]+){0,5})',
        raw_text, re.IGNORECASE
    )
    if candidates:
        # Lấy đoạn dài nhất (nhiều context nhất)
        messages.append(max(candidates, key=len).strip())

    return messages


def _find_verdict(text: str) -> str | None:
    """
    Tìm verdict cuối cùng xuất hiện trong text.
    Trả về 'APPROVE', 'REJECT', hoặc None.
    """
    verdicts = []
    for m in re.finditer(r'\b(APPROVE|REJECT)\b', text, re.IGNORECASE):
        verdicts.append(m.group(1).upper())
    return verdicts[-1] if verdicts else None


def main():
    raw_input = sys.stdin.read()

    # Thử parse như Python list nếu input là repr của list
    try:
        if raw_input.strip().startswith('[') and raw_input.strip().endswith(']'):
            lines = ast.literal_eval(raw_input)
            if not isinstance(lines, list):
                lines = raw_input.splitlines()
        else:
            lines = raw_input.splitlines()
    except (ValueError, SyntaxError):
        lines = raw_input.splitlines()

    # Thử parse JSON events trước
    agent_responses = extract_agent_messages_from_json_events(lines)

    # Fallback: tìm message trong plain text
    if not agent_responses:
        agent_responses = extract_agent_messages_fallback(raw_input)

    if not agent_responses:
        print("[review] Không thể parse output từ OpenHands.", file=sys.stderr)
        print("[review] Có thể format output đã thay đổi hoặc gặp lỗi.", file=sys.stderr)
        print("[review] ⚠️  Cho phép push (không thể verify).", file=sys.stderr)
        sys.exit(0)

    full_text = "\n".join(agent_responses)

    # Tìm response cuối có chứa verdict
    verdict_response = None
    for response in reversed(agent_responses):
        if APPROVE_PATTERN.search(response) or REJECT_PATTERN.search(response):
            verdict_response = response
            break
    if not verdict_response:
        verdict_response = agent_responses[-1]

    # Hiển thị review output
    separator = "=" * 60
    print(f"\n{separator}")
    print("  OpenHands Code Review")
    print(separator)
    print(verdict_response.strip())
    print(f"{separator}\n")

    # Lấy verdict cuối cùng (tránh nhầm khi text đề cập cả hai từ)
    verdict = _find_verdict(full_text)

    if verdict == "REJECT":
        print("[review] ❌  REJECTED — push bị chặn.", file=sys.stderr)
        sys.exit(1)

    if verdict == "APPROVE":
        print("[review] ✅  APPROVED — tiếp tục push.")
        sys.exit(0)

    # Không tìm thấy verdict rõ ràng
    print("[review] ⚠️  Không tìm thấy verdict rõ ràng (APPROVE/REJECT).", file=sys.stderr)
    print("[review] Cho phép push (fail-safe mode).", file=sys.stderr)
    sys.exit(0)