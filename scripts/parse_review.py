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
    agent_responses = []
    last_thought = ""      # thought của ActionEvent cuối
    last_observation = ""  # kết quả tool cuối
    i = 0
    n = len(lines)

    while i < n:
        line = str(lines[i]).strip()

        if line == "--JSON Event--":
            i += 1
            json_lines = []
            while i < n:
                current = str(lines[i]).strip()
                if current in ("--JSON Event--", "Agent finished", "Agent is working"):
                    break
                safe_line = str(lines[i]).replace('\n', '\\n').replace('\r', '\\r')
                json_lines.append(safe_line)
                i += 1

            json_str = "\n".join(json_lines).strip()
            if not json_str:
                continue

            try:
                event = json.loads(json_str)
            except json.JSONDecodeError:
                continue

            kind   = event.get("kind", "")
            source = event.get("source", "")

            # Final message từ agent (happy path)
            if kind == "MessageEvent" and source == "agent":
                for item in event.get("llm_message", {}).get("content", []):
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text", "").strip()
                        if text:
                            agent_responses.append(text)

            # Agent dùng tool: lưu thought để fallback nếu crash
            elif kind == "ActionEvent" and source == "agent":
                thoughts = event.get("thought", [])
                for t in thoughts:
                    if isinstance(t, dict) and t.get("type") == "text":
                        last_thought = t.get("text", "").strip()

            # Kết quả tool: lưu để fallback
            elif kind == "ObservationEvent":
                obs = event.get("observation", {})
                content = obs.get("content", [])
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        last_observation = c.get("text", "").strip()

            # Agent crash: log để debug
            elif kind == "ConversationErrorEvent":
                detail = event.get("detail", "")
                print(f"[review] ⚠️  Agent gặp lỗi: {detail[:120]}", file=sys.stderr)

        else:
            i += 1

    # Nếu agent crash trước khi gửi MessageEvent,
    # thử dùng observation cuối (kết quả py_compile, file view...) làm context
    if not agent_responses and last_observation:
        agent_responses.append(f"[Agent crashed. Last observation]\n{last_observation}")

    return agent_responses


def extract_agent_messages_fallback(raw_text):
    """
    Fallback: tìm toàn bộ message agent trong plain text.
    Dùng khi không parse được JSON events.
    """
    messages = []

    # Tìm trong CONVERSATION SUMMARY block
    summary_match = re.search(
        r'CONVERSATION SUMMARY.*?─+\n(.*?)(?:\n─{10,}|\Z)',
        raw_text, re.DOTALL
    )
    if summary_match:
        messages.append(summary_match.group(1).strip())
        return messages

    # Tìm trong box Agent (╭─ Agent ─╮ ... ╰─╯)
    box_match = re.search(r'╭─.*?Agent.*?─+╮(.*?)╰─+╯', raw_text, re.DOTALL)
    if box_match:
        content = box_match.group(1)
        content = re.sub(r'\x1b\[[0-9;]*m', '', content)
        content = re.sub(r'^\s*│\s?', '', content, flags=re.MULTILINE)
        messages.append(content.strip())
        return messages

    # Last resort: đoạn dài nhất chứa APPROVE hoặc REJECT
    candidates = re.findall(
        r'(?:^|\n)((?:[^\n]+\n){0,20}[^\n]*(?:APPROVE|REJECT)[^\n]*(?:\n[^\n]+){0,5})',
        raw_text, re.IGNORECASE
    )
    if candidates:
        messages.append(max(candidates, key=len).strip())

    return messages


def _find_verdict(text):
    """Trả về verdict cuối cùng xuất hiện: 'APPROVE', 'REJECT', hoặc None."""
    verdicts = [m.group(1).upper() for m in re.finditer(r'\b(APPROVE|REJECT)\b', text, re.IGNORECASE)]
    return verdicts[-1] if verdicts else None


def main():
    raw_input = sys.stdin.read()

    # Parse input: list repr hoặc plain text
    try:
        stripped = raw_input.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            lines = ast.literal_eval(stripped)
            if not isinstance(lines, list):
                lines = raw_input.splitlines()
        else:
            lines = raw_input.splitlines()
    except (ValueError, SyntaxError):
        lines = raw_input.splitlines()

    # Parse JSON events
    agent_responses = extract_agent_messages_from_json_events(lines)

    # Fallback nếu không parse được
    if not agent_responses:
        agent_responses = extract_agent_messages_fallback(raw_input)

    if not agent_responses:
        print("[review] ❓ Không thể parse output từ OpenHands.", file=sys.stderr)
        print("[review]    Có thể format output đã thay đổi hoặc agent gặp lỗi.", file=sys.stderr)
        print("[review] ⚠️  Cho phép push (không thể verify).", file=sys.stderr)
        sys.exit(0)

    full_text = "\n".join(agent_responses)

    # Tìm response cuối có chứa verdict để hiển thị
    verdict_response = next(
        (r for r in reversed(agent_responses) if APPROVE_PATTERN.search(r) or REJECT_PATTERN.search(r)),
        agent_responses[-1]
    )

    # In review output ra stdout
    sep = "=" * 60
    print(f"\n{sep}")
    print("  OpenHands Code Review")
    print(sep)
    print(verdict_response.strip())
    print(f"{sep}\n")

    # Lấy verdict cuối cùng
    verdict = _find_verdict(full_text)

    if verdict == "REJECT":
        print("[review] ❌  REJECTED — push bị chặn.", file=sys.stderr)
        sys.exit(1)

    if verdict == "APPROVE":
        print("[review] ✅  APPROVED — tiếp tục push.")
        sys.exit(0)

    print("[review] ⚠️  Không tìm thấy verdict rõ ràng (APPROVE/REJECT).", file=sys.stderr)
    print("[review]    Cho phép push (fail-safe mode).", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()