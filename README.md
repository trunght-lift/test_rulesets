# test_rulesets

## OpenHands Code Review Hook

Tự động review code bằng OpenHands AI trước khi push.

### Setup

```bash
# 1. Cài OpenHands CLI
pip install openhands-ai
# hoặc dùng pipx (khuyến nghị)
pipx install openhands-ai

# 2. Tạo .env từ example
cp .env.example .env
# Điền LLM_API_KEY vào .env

# 3. Cài pre-push hook
bash scripts/install-hooks.sh
```

### Flow hoạt động

```
git push
  └─ .git/hooks/pre-push
       ├─ git diff → build prompt
       ├─ openhands --headless --json --always-approve -t "<diff+prompt>"
       └─ python3 scripts/parse_review.py  ← parse JSONL stdout
            ├─ tìm "APPROVE" → exit 0 (push tiếp)
            └─ tìm "REJECT"  → exit 1 (push bị chặn)
```

### Cấu hình

Chỉnh sửa `.env`:
```bash
LLM_API_KEY=sk-ant-...
LLM_MODEL=anthropic/claude-sonnet-4-5
```

Hỗ trợ các provider: Anthropic, OpenAI, Google, Azure, v.v.

### Test thử

```bash
# Tạo commit test
echo "test" >> main.py
git add main.py
git commit -m "test review"

# Push sẽ trigger review
git push
```