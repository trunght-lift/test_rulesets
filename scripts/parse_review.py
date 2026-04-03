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
    
    agent_responses = []
    full_text = ""
    
    # Tìm các JSON event blocks
    i = 0
    while i < len(lines):
        line = str(lines[i]).strip()
        
        # Tìm marker "--JSON Event--"
        if line == "--JSON Event--":
            i += 1
            # Collect lines cho đến khi có JSON hợp lệ
            json_buffer = []
            
            while i < len(lines):
                current_line = str(lines[i])
                json_buffer.append(current_line)
                
                # Thử parse JSON sau mỗi dòng
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
                                        full_text += "\n" + text
                    
                    # JSON đã parse xong, break khỏi inner loop
                    i += 1
                    break
                    
                except json.JSONDecodeError:
                    # Chưa đủ dữ liệu, tiếp tục đọc
                    i += 1
                    continue
        else:
            i += 1
    
    if not agent_responses:
        print("[review] Không có response từ agent.", file=sys.stderr)
        print("[review] Có thể OpenHands chưa hoàn thành hoặc gặp lỗi.", file=sys.stderr)
        print("[review] Kiểm tra log tại .openhands-review.log", file=sys.stderr)
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
