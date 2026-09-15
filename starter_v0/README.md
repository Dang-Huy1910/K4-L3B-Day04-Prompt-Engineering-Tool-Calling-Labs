# IT Helpdesk Agent — Day04 Implementation Guide

Hướng dẫn chi tiết cài đặt, cấu hình, kiểm thử tự động, chạy đánh giá (eval) và giao diện người dùng (UI) cho bài lab Day04.

## 1. Cài đặt môi trường

```bash
cd starter_v0
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest streamlit
```

Cấu hình API Key trong file `starter_v0/.env` (tuyệt đối không commit file này):

```env
# Chọn một trong các provider:
OPENROUTER_API_KEY=your_key_here
# Hoặc:
# GEMINI_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here
# ANTHROPIC_API_KEY=your_key_here

# Tuỳ chọn cho tra cứu web ngoài (Tavily):
# TAVILY_API_KEY=your_tavily_key
```

## 2. Kiểm tra kết nối (Preflight)

Kiểm tra khả năng gọi công cụ có cấu trúc trước khi chạy eval:

```bash
.venv/bin/python scripts/preflight_provider.py --provider gemini --model gemini-3.6-flash
# Hoặc với OpenRouter:
# .venv/bin/python scripts/preflight_provider.py --provider openrouter --model openai/gpt-4o-mini
```

## 3. Chạy kiểm thử tự động (Unit Tests)

Bộ kiểm thử độc lập không phụ thuộc network, không gây side-effect (mock Tavily, tmp_path cho ticket, SHA256 integrity cố định):

```bash
.venv/bin/python -m compileall agent.py chat.py app.py providers tools scripts tests conversation.py
.venv/bin/pytest tests -v
```

## 4. Chạy các bộ Evaluation

Tất cả lệnh chạy đều chốt tham số `--provider` và `--model` nhất quán:

```bash
# 1. Base Evaluation (v0 - baseline nguyên bản)
.venv/bin/python run_eval.py --provider gemini --model gemini-3.6-flash --version v0 --suite base --eval-cases data/eval_base.json

# 2. Base Evaluation (v1 - cải tiến tool declaration & argument contract)
.venv/bin/python run_eval.py --provider gemini --model gemini-3.6-flash --version v1 --suite base --eval-cases data/eval_base.json

# 3. Base Evaluation (v2 - cải tiến multi-turn, disambiguation & confirmation)
.venv/bin/python run_eval.py --provider gemini --model gemini-3.6-flash --version v2 --suite base --eval-cases data/eval_base.json

# 4. Base Evaluation (v3 - cải tiến safety, trust boundaries & trace tuning)
.venv/bin/python run_eval.py --provider gemini --model gemini-3.6-flash --version v3 --suite base --eval-cases data/eval_base.json

# 5. Group Evaluation (10 case nhóm: 5 single-turn + 5 multi-turn)
.venv/bin/python run_eval.py --provider gemini --model gemini-3.6-flash --version v3 --suite group --eval-cases data/eval_group.json

# 6. Adversarial Evaluation (12 attack cases về prompt injection, role spoof, data exfiltration)
.venv/bin/python run_eval.py --provider gemini --model gemini-3.6-flash --version v3 --suite adversarial --eval-cases data/eval_adversarial.json

# 7. Helpdesk Extension (10 cases policy, confirmed tickets, external search)
.venv/bin/python run_eval.py --provider gemini --model gemini-3.6-flash --version v3 --suite extension --eval-cases data/eval_helpdesk_extension.json

# 8. Bonus Tool Evaluation (5 cases cho công cụ check_warranty)
.venv/bin/python run_eval.py --provider gemini --model gemini-3.6-flash --version v3 --suite bonus --eval-cases data/eval_bonus.json
```

## 5. Phân tích kết quả chạy (Run Analysis)

Chuyển đổi kết quả chạy JSON thành bảng CSV để phân tích nguyên nhân lỗi:

```bash
.venv/bin/python scripts/parse_runs.py runs/ --output analysis/all_runs_analysis.csv
```

## 6. Giao diện Chat (Local Streamlit UI) & CLI

Chạy giao diện web nội bộ Streamlit hiển thị chi tiết tool calls, JSON arguments, kết quả/lỗi, artifact version và xuất transcript:

```bash
.venv/bin/streamlit run app.py
```

Chạy qua giao diện dòng lệnh (CLI):

```bash
.venv/bin/python chat.py --provider gemini --model gemini-3.6-flash --version v3
```

## 7. Sinh Transcript tương tác mẫu (Reproducible)

Sinh tự động 5 kịch bản tương tác thực tế với mô hình theo đúng `conversation.py`:

```bash
.venv/bin/python scripts/generate_transcripts.py --provider gemini --model gemini-3.6-flash --version v3
```

## 8. Cấu trúc thư mục bằng chứng (Evidence Map)

- `artifacts/`: `system_prompt.md`, `tools.yaml`, `REPORT.md`, `version_log.csv`.
- `artifacts/versions/`: Snapshot các phiên bản `v0/`, `v1/`, `v2/`, `v3/` đối chiếu hash.
- `runs/`: Toàn bộ file kết quả chạy thật của các suite.
- `transcripts/`: Các file JSON ghi lại lịch sử đối thoại nhiều lượt và tool trace.
- `analysis/`: Bảng CSV phân tích failure và so sánh trước/sau.
- `helpdesk_data/`: Dữ liệu giả lập (`assets.json`, `users.json`, `service_status.json`, `warranties.json`, `knowledge_base/`).
- `tools/check_warranty/`: Bonus tool mới ngoài luồng cơ bản với hợp đồng và tài liệu đầy đủ.

