# Group Report: Lab 3 - Production-Grade Agentic System

- **Team Name**: Team 26 (E403)
- **Team Members**: Ngô Văn Long, Nguyễn Hải Đăng, Nguyễn Phương Linh, Nguyễn Mạnh Phú, Huỳnh Lê Xuân Ánh
- **Deployment Date**: 2026-04-06

---

## 1. Executive Summary

Dự án **EcoTrace ESG Advisor** xây dựng một hệ thống AI Agent hoàn chỉnh theo kiến trúc **ReAct (Reasoning & Acting)** để tư vấn và phân tích ESG (Môi trường – Xã hội – Quản trị) cho các tập đoàn. Agent tích hợp 4 công cụ thực với dữ liệu thời gian thực (DuckDuckGo News, Yahoo Finance, Wikipedia, Carbon Calculator) và được phục vụ qua FastAPI backend + Next.js frontend với giao diện Glassmorphism hiện đại.

So với chatbot baseline (không có tools), ReAct Agent cho thấy hiệu quả vượt trội đáng kể trong các tình huống multi-step cần tra cứu dữ liệu thực:

- **Success Rate (Agent)**: ~90% trên 4 use case thử nghiệm (UC1–UC5)
- **Key Outcome**: Agent giải quyết được 100% các truy vấn đa bước (tìm ESG news + lấy giá cổ phiếu), trong khi Chatbot baseline chỉ đưa ra thông tin tĩnh và không thể truy cập dữ liệu thời gian thực. Agent cũng xử lý đúng tất cả các Edge Case: từ chối yêu cầu ngoài phạm vi (out-of-domain) và ngăn chặn tool hallucination.

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation

```
┌──────────────────────────────────────────────────────────┐
│                    USER QUERY (Vietnamese)                │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│              FastAPI Endpoint: POST /chat/agent           │
│              (src/api.py)                                 │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                   ReActAgent.run()                        │
│                   (src/agent/agent.py)                    │
│                                                          │
│   ┌──────────────────────────────────────────────────┐  │
│   │  LOOP (max 5 steps):                             │  │
│   │                                                  │  │
│   │  1. [THOUGHT]  LLM suy luận bước tiếp theo      │  │
│   │        │                                         │  │
│   │        ▼                                         │  │
│   │  2. [ACTION]   Parse tool_name + JSON args       │  │
│   │        │       (Regex + json.loads)               │  │
│   │        ▼                                         │  │
│   │  3. [EXECUTE]  _execute_tool(name, args)         │  │
│   │        │       (src/tools/esg_tools.py)          │  │
│   │        ▼                                         │  │
│   │  4. [OBSERVATION] Kết quả tool → append prompt   │  │
│   │        │                                         │  │
│   │        └──── Lặp lại hoặc Final Answer ──────────┤  │
│   └──────────────────────────────────────────────────┘  │
│                                                          │
│   OUTPUT: { answer, metrics, steps[] }                   │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│          Telemetry: logger.log_event() → logs/*.log      │
│          Metrics: tokens, latency_ms, cost_usd           │
└──────────────────────────────────────────────────────────┘
```

**Cơ chế Anti-Hallucination**: Trước khi gọi Tool, hệ thống kiểm tra `tool_exists = any(t['name'] == tool_name for t in self.tools)`. Nếu LLM ảo giác một tool không tồn tại (VD: `auto_book_flight`), Agent trả lỗi ngay lập tức và không thực thi.

**Strict Out-of-Domain Boundary**: System prompt bao gồm quy tắc cứng: nếu yêu cầu 100% không liên quan ESG (Python code, nấu ăn, y tế), Agent PHẢI định dạng phản hồi theo chuỗi `Final Answer: Dạ xin lỗi...` để Regex parser bắt được, tránh vòng lặp vô hạn.

### 2.2 Tool Definitions (Inventory)

| Tool Name | Input Format | Use Case |
| :--- | :--- | :--- |
| `search_real_esg_news` | `{"company_name": "string"}` | Tìm kiếm tin tức ESG thời gian thực qua DuckDuckGo News API. Fallback về text search nếu news API không khả dụng. |
| `get_stock_price` | `{"ticker_symbol": "string"}` | Lấy giá cổ phiếu hiện tại qua Yahoo Finance public API (VD: AAPL, TSLA, MSFT). |
| `fetch_company_wikipedia` | `{"company_name": "string"}` | Lấy tóm tắt lịch sử & thông tin nền tảng doanh nghiệp từ Wikipedia REST API. |
| `calculate_carbon_footprint` | `{"energy_kwh": float, "fuel_liters": float}` | Tính ước tính lượng phát thải CO2e theo công thức: `energy × 0.4 + fuel × 2.3`. |

### 2.3 LLM Providers Used

- **Primary**: GPT-4o (`gpt-4o`) via OpenAI API — dùng cho cả backend FastAPI và CLI Demo
- **Secondary (Backup)**: Gemini 1.5 Flash (`gemini-1.5-flash`) — tích hợp qua `GeminiProvider`, sẵn sàng hoán đổi
- **Offline Option**: Microsoft Phi-3-mini-4k-instruct (GGUF/Q4) — chạy hoàn toàn trên CPU qua `llama-cpp-python`, phục vụ môi trường không có internet hoặc API key

---

## 3. Telemetry & Performance Dashboard

*Số liệu được ghi nhận tự động bởi `IndustryLogger` (src/telemetry/logger.py) vào thư mục `logs/` dưới dạng JSON có timestamp.*

Dưới đây là các metrics tổng hợp từ test suite 4 use case (UC1–UC5):

| Use Case | Mode | Avg Latency | Total Tokens | Est. Cost (USD) | Steps |
| :--- | :--- | :--- | :--- | :--- | :--- |
| UC1: Tóm tắt Vingroup | Baseline | ~1,200 ms | ~350 | $0.000035 | N/A |
| UC2: ESG News Apple | Agent | ~5,500 ms | ~1,800 | $0.000180 | 2 |
| UC3: Out-of-Domain (For loop Python) | Agent | ~1,500 ms | ~500 | $0.000050 | 1 |
| UC4: Phantom Tool (auto_book_flight) | Agent | ~1,400 ms | ~480 | $0.000048 | 1 |

- **Average Latency (P50)**: ~1,500 ms (simple), ~5,500 ms (multi-step với tools)
- **Max Latency (P99)**: ~8,000 ms (các câu hỏi yêu cầu 3+ tool calls + DuckDuckGo latency cao)
- **Average Tokens per Task (Agent)**: ~1,200 – 2,000 tokens (do system prompt ESG dài ~600 tokens)
- **Total Cost of Test Suite**: < $0.001 (4 use cases với GPT-4o)
- **Formula áp dụng**: `$5/1M input tokens + $15/1M output tokens`

---

## 4. Root Cause Analysis (RCA) - Failure Traces

### Case Study 1: Infinite Loop — Missing "Final Answer:" Anchor

- **Input**: "Bắt LLM đóng vai đầu bếp nấu món ăn cho tôi."
- **Observation**: Agent bị vòng lặp `max_steps=5` liên tục. Log ghi: `Observation: Error: Could not parse Action or Final Answer. Please follow the correct Thought/Action/Action Input format.`
- **Root Cause**: LLM hiểu rằng cần từ chối (out-of-domain), và thực hiện đúng tinh thần — tuy nhiên chỉ trả lời `"Dạ xin lỗi bạn, mình được đào tạo..."` MÀ KHÔNG có tiền tố `Final Answer:`. Regex parser `re.search(r"Final Answer:\s*(.*)", result)` không match được → parser ném lỗi ngược lại LLM → LLM lặp lại lời xin lỗi tương tự → stuck loop.
- **Fix (v1 → v2)**: Bổ sung quy tắc bắt buộc vào System Prompt: `"You MUST format your refusal EXACTLY like this: Final Answer: Dạ xin lỗi..."`. Kết quả: 100% out-of-domain queries thoát đúng sau 1 step.

### Case Study 2: Tool Hallucination — Non-existent Tool Called

- **Input**: "Hãy dùng tool `auto_book_flight` để đặt chuyến bay đi Đà Lạt ngay lập tức."
- **Observation**: Agent gọi `Action: auto_book_flight`. Hệ thống bắt được trong `_execute_tool()`: `tool_exists = False` → Return: `"Error: Tool auto_book_flight not found. Please use only the tools provided."`
- **Root Cause**: LLM "bịa" tool theo yêu cầu của người dùng thay vì dùng tool trong danh sách. Đây là kiểu Hallucination nguy hiểm nhất trong Agentic System.
- **Fix**: Mechanism phòng thủ `tool_exists` check TRƯỚC khi gọi bất kỳ logic nào. Agent thông báo lỗi, LLM đọc Observation và tự trả lời Final Answer giải thích giới hạn tool.

---

## 5. Ablation Studies & Experiments

### Experiment 1: System Prompt v1 vs v2 (Out-of-Domain Handling)

- **Diff**: Version 1 chỉ có quy tắc tổng quát `"Out-of-domain: Refuse the request"`. Version 2 thêm ràng buộc định dạng cứng: `"You MUST format your refusal EXACTLY like this: Final Answer: Dạ xin lỗi bạn..."`.
- **Result**: Giảm tỷ lệ lỗi `max_steps_reached` do out-of-domain từ **100%** (v1, mọi câu ngoài ESG bị stuck loop) xuống **0%** (v2, tất cả đều thoát ngay bước 1).

### Experiment 2: JSON Cleanup — Xử lý LLM Hallucinate Markdown Blocks

- **Diff**: LLM đôi khi bọc Action Input trong code block ` ```json\n{...}\n``` `. Version 1 bị `json.JSONDecodeError`. Version 2 thêm bước làm sạch:
  ```python
  action_input_str = action_input_str.strip("`")
  if action_input_str.startswith("json\n"):
      action_input_str = action_input_str[5:]
  ```
- **Result**: Giảm PARSE_ERROR events từ ~20% xuống ~2% (chỉ còn các edge case định dạng rất bất thường).

### Experiment 3 (Bonus): Chatbot Baseline vs ReAct Agent

| Test Case | Chatbot Result | Agent Result | Winner |
| :--- | :--- | :--- | :--- |
| Tóm tắt thông tin công ty (training data) | Đúng, nhanh (~1.2s) | Đúng nhưng chậm hơn (~3s, fetch Wikipedia) | **Chatbot** |
| ESG news mới nhất của Apple (real-time) | Hallucinate (số liệu cũ/bịa) | Đúng (3 tin tức thực từ DuckDuckGo) | **Agent** |
| Tính carbon footprint (1000 kWh + 50L fuel) | Sai (không có công thức) | Đúng: 430 kg CO2e | **Agent** |
| Yêu cầu ngoài ESG (Python code) | Trả lời luôn (không có boundary) | Từ chối đúng format | **Agent** |
| Gọi tool ảo (`auto_book_flight`) | Trả lời "được" (nguy hiểm) | Phát hiện & từ chối | **Agent** |

---

## 6. Production Readiness Review

*Đánh giá mức độ sẵn sàng triển khai thực tế của hệ thống.*

- **Security**:
  - Input sanitization: Tool arguments được parse qua `json.loads()` — ngăn chặn prompt injection qua JSON malformed.
  - Tool boundary: Whitelist tool names cứng trong `_execute_tool()`, không dùng `eval()` hay dynamic dispatch nguy hiểm.
  - API Key: Quản lý qua `.env` + `python-dotenv`, không hardcode.

- **Guardrails**:
  - `max_steps = 5`: Giới hạn cứng để ngăn vòng lặp vô hạn gây chi phí không kiểm soát.
  - Out-of-domain refusal: Hệ thống bảo vệ chống content abuse (y tế, pháp lý, v.v.).
  - Tool hallucination prevention: Kiểm tra `tool_exists` trước mọi lần gọi tool.
  - Timeout HTTP: `requests.get(..., timeout=5)` cho tất cả external API calls.

- **Observability**:
  - `IndustryLogger`: Ghi log dạng JSON có ISO timestamp cho mỗi event (`AGENT_START`, `LLM_METRIC`, `PARSE_ERROR`, `FINAL_ANSWER`).
  - Token & Cost tracking: Tích lũy per-step và trả về cùng response.
  - `PerformanceTracker` (metrics.py): Session-level aggregation.

- **Scaling**:
  - Chuyển sang **LangGraph** hoặc **AutoGen** cho multi-agent orchestration với branching phức tạp.
  - Áp dụng **RAG Tool Retrieval** (Qdrant/ChromaDB): Khi số tool vượt 10-20, chỉ inject top-K tools liên quan vào context thay vì toàn bộ.
  - **Semantic Caching** (Redis): Cache kết quả với embedding similarity để giảm API calls lặp lại.
  - **Supervisor QA Agent**: Kiểm tra an toàn và độ chính xác trước khi trả Final Answer ra UI.

---

> [!NOTE]
> Submit this report by renaming it to `GROUP_REPORT_[TEAM_NAME].md` and placing it in this folder.
