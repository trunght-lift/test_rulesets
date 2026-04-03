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

def main():
    raw_input = sys.stdin.read().strip()
    
    # Thử parse như Python list (nếu output bị wrap bởi debug code cũ)
    try:
        lines = ast.literal_eval(raw_input)
        if not isinstance(lines, list):
            lines = raw_input.splitlines()
    except (ValueError, SyntaxError):
        lines = raw_input.splitlines()
    
    agent_responses = []
    full_text = ""
    
    # Parse từng dòng, tìm JSON events từ agent
    i = 0
    while i < len(lines):
        line = str(lines[i]).strip()
        
        # Tìm marker "--JSON Event--"
        if line == "--JSON Event--":
            # Đọc các dòng tiếp theo cho đến khi hết JSON object
            json_lines = []
            i += 1
            brace_count = 0
            started = False
            
            while i < len(lines):
                current = str(lines[i])
                json_lines.append(current)
                
                # Đếm dấu ngoặc để biết khi nào JSON object kết thúc
                for char in current:
                    if char == '{':
                        brace_count += 1
                        started = True
                    elif char == '}':
                        brace_count -= 1
                
                i += 1
                
                # Kết thúc JSON object
                if started and brace_count == 0:
                    break
            
            # Parse JSON
            try:
                json_str = '\n'.join(json_lines)
                event = json.loads(json_str)
                
                # Chỉ lấy message từ agent
                if event.get("source") == "agent" and event.get("kind") == "MessageEvent":
                    llm_msg = event.get("llm_message", {})
                    content_list = llm_msg.get("content", [])
                    
                    for content_item in content_list:
                        if content_item.get("type") == "text":
                            text = content_item.get("text", "")
                            if text:
                                agent_responses.append(text)
                                full_text += "\n" + text
            except (json.JSONDecodeError, ValueError):
                # Bỏ qua JSON không hợp lệ
                pass
        
        i += 1
    
    if not agent_responses:
        print("[review] Không có response từ agent.", file=sys.stderr)
        sys.exit(1)
    
    # Lấy response cuối cùng từ agent (thường là verdict)
    final_response = agent_responses[-1]
    
    print("\n" + "="*60)
    print("OpenHands Code Review")
    print("="*60)
    print(final_response.strip())
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
