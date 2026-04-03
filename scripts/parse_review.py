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
    """
    agent_responses = []
    i = 0
    
    while i < len(lines):
        line = str(lines[i]).strip()
        
        # Tìm marker "--JSON Event--"
        if line == "--JSON Event--":
            i += 1
            json_buffer = []
            
            while i < len(lines):
                current_line = str(lines[i])
                json_buffer.append(current_line)
                
                try:
                    json_str = '\n'.join(json_buffer)
                    event = json.loads(json_str)
                    
                    # Parse thành công, xử lý event
                    if isinstance(event, dict):
                        if event.get("source") == "agent" and event.get("kind") == "MessageEvent":
                            llm_msg = event.get("llm_message", {})
                            content_list = llm_msg.get("content", [])
                            
                            for content_item in content_list:
                                if isinstance(content_item, dict) and content_item.get("type") == "text":
                                    text = content_item.get("text", "")
                                    if text:
                                        agent_responses.append(text)
                    
                    i += 1
                    break
                    
                except json.JSONDecodeError:
                    i += 1
                    continue
        else:
            i += 1
    
    return agent_responses

def extract_agent_messages_fallback(raw_text):
    """
    Fallback: tìm verdict trực tiếp trong plain text.
    Dùng khi không parse được JSON events.
    """
    # Tìm các đoạn text có APPROVE hoặc REJECT
    matches = []
    for match in re.finditer(r'(.{0,200}(?:APPROVE|REJECT).{0,200})', raw_text, re.IGNORECASE | re.DOTALL):
        matches.append(match.group(1))
    return matches

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
    
    # Fallback: tìm verdict trong plain text
    if not agent_responses:
        agent_responses = extract_agent_messages_fallback(raw_input)
    
    if not agent_responses:
        print("[review] Không thể parse output từ OpenHands.", file=sys.stderr)
        print("[review] Có thể format output đã thay đổi hoặc gặp lỗi.", file=sys.stderr)
        print("[review] Để debug, chạy lại với: DEBUG=1 git push", file=sys.stderr)
        # Fail-safe: cho phép push nếu không parse được (tránh block dev)
        print("[review] ⚠️  Cho phép push (không thể verify).", file=sys.stderr)
        sys.exit(0)
    
    # Tìm response có verdict (APPROVE/REJECT), ưu tiên response cuối
    verdict_response = None
    full_text = "\n".join(agent_responses)
    
    for response in reversed(agent_responses):
        if APPROVE_PATTERN.search(response) or REJECT_PATTERN.search(response):
            verdict_response = response
            break
    
    # Nếu không tìm thấy verdict trong responses, tìm trong toàn bộ text
    if not verdict_response:
        verdict_response = agent_responses[-1] if agent_responses else ""
    
    # Hiển thị verdict
    if verdict_response:
        print("\n" + "="*60)
        print("OpenHands Code Review")
        print("="*60)
        # Chỉ hiển thị tối đa 500 ký tự để tránh spam
        display_text = verdict_response.strip()
        if len(display_text) > 500:
            display_text = display_text[:500] + "\n... (truncated)"
        print(display_text)
        print("="*60 + "\n")

    # Kiểm tra verdict trong toàn bộ output
    if REJECT_PATTERN.search(full_text):
        print("[review] ❌  REJECTED — push bị chặn.", file=sys.stderr)
        sys.exit(1)

    if APPROVE_PATTERN.search(full_text):
        print("[review] ✅  APPROVED — tiếp tục push.")
        sys.exit(0)

    # Không tìm thấy verdict rõ ràng → cảnh báo nhưng cho qua (fail-safe)
    print("[review] ⚠️  Không tìm thấy verdict rõ ràng (APPROVE/REJECT).", file=sys.stderr)
    print("[review] Cho phép push (fail-safe mode).", file=sys.stderr)
    sys.exit(0)

if __name__ == "__main__":
    main()
