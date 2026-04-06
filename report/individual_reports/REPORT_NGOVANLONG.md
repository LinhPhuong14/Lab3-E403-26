# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Ngô Văn Long
- **Student ID**: 2A202600129
- **Date**: 2026-04-06

---

## I. Technical Contribution (15 Points)

*Mô tả chi tiết đóng góp kỹ thuật cụ thể vào codebase.*

### Modules Implemented

- **`src/tools/esg_tools.py`** — Định nghĩa và triển khai toàn bộ 4 Tool thực (Real API, Zero-config):
  - `search_real_esg_news(company_name)`: Tìm kiếm tin tức ESG thời gian thực qua DuckDuckGo News API, có fallback về text search nếu news API không khả dụng.
  - `get_stock_price(ticker_symbol)`: Lấy giá cổ phiếu hiện tại qua Yahoo Finance public API (`query1.finance.yahoo.com/v8/finance/chart/`).
  - `fetch_company_wikipedia(company_name)`: Lấy tóm tắt thông tin doanh nghiệp từ Wikipedia REST API (`/api/rest_v1/page/summary/`).
  - `calculate_carbon_footprint(energy_kwh, fuel_liters)`: Tính phát thải CO2e theo công thức: `CO2 = (energy_kwh × 0.4) + (fuel_liters × 2.3)`.

- **`src/agent/agent.py`** — Triển khai ReAct loop đầy đủ, bao gồm:
  - Regex parser hai lớp cho `Thought`, `Action`, `Action Input`, `Final Answer`.
  - Cost tracking theo chuẩn GPT-4o pricing: `$5/1M input + $15/1M output tokens`.
  - Trả về structured response: `{ answer, metrics: {total_tokens, prompt_tokens, completion_tokens, estimated_cost_usd}, steps: [{thought, action, observation}] }`.

- **`src/api.py`** — FastAPI backend với hai endpoint:
  - `POST /chat/baseline`: Chatbot tĩnh, không có tool.
  - `POST /chat/agent`: Khởi tạo `ReActAgent` với 4 tools và chạy full ReAct loop.

- **`frontend/src/app/page.tsx`** — Next.js chat UI với Glassmorphism design, hiển thị token usage, estimated cost, và collapsible ReAct steps accordion.

### Code Highlights

**1. Anti-Hallucination Tool Guard** (`src/agent/agent.py`, dòng 165–167):
```python
# Kiểm tra tool có tồn tại trong whitelist không TRƯỚC khi thực thi
tool_exists = any(t['name'] == tool_name for t in self.tools)
if not tool_exists:
    return f"Error: Tool {tool_name} not found. Please use only the tools provided."
```

**2. JSON Markdown Cleanup** (`src/agent/agent.py`, dòng 123–125):
```python
# LLM đôi khi bọc JSON trong ```json ... ``` — cần làm sạch trước khi parse
action_input_str = action_input_str.strip("`")
if action_input_str.startswith("json\n"):
    action_input_str = action_input_str[5:]
```

**3. DuckDuckGo Fallback Logic** (`src/tools/esg_tools.py`, dòng 10–13):
```python
results = DDGS().news(f"{company_name} ESG OR sustainability OR environment", max_results=3)
if not results:
    # Fallback về text search nếu News API tạm thời không khả dụng
    results = DDGS().text(f"{company_name} ESG initiatives issues", max_results=3)
```

**4. Carbon Footprint Calculator** (`src/tools/esg_tools.py`, dòng 66–68):
```python
energy_co2 = float(energy_kwh) * 0.4   # Hệ số phát thải điện: 0.4 kg CO2e/kWh
fuel_co2 = float(fuel_liters) * 2.3     # Hệ số phát thải nhiên liệu: 2.3 kg CO2e/L
total_co2 = energy_co2 + fuel_co2
```

### Documentation

Luồng dữ liệu qua ReAct loop hoạt động như sau:

1. `api.py` nhận HTTP request → khởi tạo `OpenAIProvider` và `ReActAgent` với danh sách tools dạng `List[Dict]`.
2. `ReActAgent.run()` tích lũy `session_prompt` theo từng vòng: `Question → Thought → Action → Action Input → Observation → Thought → ...`.
3. Mỗi bước, `llm.generate(session_prompt, system_prompt=...)` gọi OpenAI API, parse response bằng Regex.
4. Tool được dispatch qua `_execute_tool()` → gọi function trong `esg_tools.py` → trả `observation` dạng string.
5. `logger.log_event()` ghi JSON event vào `logs/log_YYYYMMDD_HHMMSS.log` sau mỗi bước.

---

## II. Debugging Case Study (10 Points)

*Phân tích chi tiết một sự cố xảy ra trong quá trình phát triển.*

### Vấn đề: Infinite Loop do thiếu "Final Answer:" Anchor trong Out-of-Domain Refusal

**Problem Description**:

Khi người dùng đặt câu hỏi hoàn toàn ngoài phạm vi ESG (VD: *"Hướng dẫn tôi viết vòng lặp For trong Python"*), Agent bị stuck ở `MAX_STEPS_REACHED` (5 bước). Mỗi bước đều ghi một lỗi giống nhau.

**Log Source** (từ `logs/log_*.log`):

```json
{"timestamp": "2026-04-06T08:45:12.100Z", "event": "LLM_METRIC", "data": {"step": 1, "latency_ms": 1320, "usage": {"prompt_tokens": 645, "completion_tokens": 48}}}
{"timestamp": "2026-04-06T08:45:12.101Z", "event": "PARSE_ERROR", "data": {"raw_input": ""}}
{"timestamp": "2026-04-06T08:45:13.501Z", "event": "LLM_METRIC", "data": {"step": 2, "latency_ms": 1200, "usage": {"prompt_tokens": 720, "completion_tokens": 48}}}
{"timestamp": "2026-04-06T08:45:13.502Z", "event": "PARSE_ERROR", "data": {"raw_input": ""}}
...
{"timestamp": "2026-04-06T08:45:18.001Z", "event": "AGENT_END", "data": {"steps": 5, "status": "MAX_STEPS_REACHED"}}
```

**Phần LLM generate ra** (trích từ session log):
```
Dạ xin lỗi bạn, mình được đào tạo chuyên sâu về tư vấn ESG nên không thể hỗ trợ chủ đề này.
```

**Diagnosis**:

Vấn đề nằm ở **3 điểm tương tác**:

1. **Model Side**: LLM hiểu đúng cần từ chối (out-of-domain), nhưng output ra câu xin lỗi thuần túy mà **không có tiền tố `Final Answer:`** — vì System Prompt v1 chỉ nói "refuse" mà không chỉ định định dạng bắt buộc.

2. **Parser Side** (`agent.py` dòng 93): Regex `re.search(r"Final Answer:\s*(.*)", result)` không match → không có Final Answer.

3. **Fallback Logic** (`agent.py` dòng 135–138): Cũng không có Action/Action Input → parser trả `observation = "Error: Could not parse..."`. Chuỗi lỗi này được append vào `session_prompt`, ép LLM phải tiếp tục lặp lại câu xin lỗi trong 5 bước.

**Root Cause**: Xung đột giữa ý định của LLM (từ chối đúng) và kỳ vọng của parser (cần keyword `Final Answer:`). Thiếu contract định dạng chặt chẽ trong prompt.

**Solution**:

Cập nhật System Prompt (v1 → v2) thêm quy tắc **bắt buộc format cứng** cho out-of-domain refusal:

```
OUT-OF-DOMAIN STRICT RULE: If the topic is 100% UNRELATED to ESG...
You MUST format your refusal EXACTLY like this:
Final Answer: Dạ xin lỗi bạn, mình được đào tạo chuyên sâu về tư vấn
và đánh giá tác động ESG nên không thể hỗ trợ chủ đề này.
Bạn có câu hỏi nào về phát triển bền vững thì cho mình biết nhé!
```

Kết quả: 100% out-of-domain queries thoát sạch sau đúng **1 step**, không còn stuck loop.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Phản tư sâu về sự khác biệt căn bản giữa LLM Chatbot và ReAct Agent dựa trên kết quả thực nghiệm.*

### 1. Reasoning

Block `Thought` trong ReAct thực sự ép model phải thực hiện **"Chain-of-Thought Planning"** — một việc mà Chatbot hoàn toàn bỏ qua. Khi được hỏi *"Tìm 3 tin tức ESG gần nhất của Apple và cho biết giá cổ phiếu AAPL"*, Chatbot baseline trả lời ngay bằng dữ liệu training cũ (không real-time, tiềm năng hallucinate). Agent thay vào đó tự cấu trúc kế hoạch:

> *"Thought: Câu hỏi yêu cầu 2 loại thông tin riêng biệt. Trước tiên tôi sẽ tìm tin tức ESG của Apple, sau đó lấy giá AAPL. Bắt đầu bước 1."*

Đây là biểu hiện rõ ràng của **Task Decomposition** — khả năng chia nhỏ bài toán phức tạp. Với Chatbot một lèo không có Thought, model không có "khoảng trống suy nghĩ" để lập kế hoạch trước khi hành động.

### 2. Reliability

Agent thực sự **kém hơn Chatbot** trong một số tình huống cụ thể:

- **Câu hỏi đơn giản về kiến thức tĩnh**: Hỏi "ESG là viết tắt của gì?" — Chatbot trả lời < 1s. Agent mất 1.5–2s chỉ để LLM nhận ra không cần dùng tool và output `Final Answer` thẳng. Chi phí token cao hơn do system prompt dài (~600 tokens overhead/request).
- **Tool API timeout**: Khi DuckDuckGo hoặc Yahoo Finance chậm (> 5s timeout), Agent trả về lỗi và LLM phải xử lý gracefully trong Thought tiếp theo, gây tổng latency có thể lên đến 10–12 giây — khó chấp nhận với UX thực tế.
- **Context window**: Mỗi vòng lặp append toàn bộ Thought/Action/Observation vào `session_prompt`. Sau 3–4 steps, prompt có thể đạt 3,000–4,000 tokens, tăng cost đáng kể.

### 3. Observation

Feedback loop từ môi trường (Observation) chính là **điểm mấu chốt** tạo ra hành vi "có trách nhiệm" của Agent. Minh chứng thực tế từ lab:

Khi tìm kiếm `Apple ESG Report`, DuckDuckGo trả về một kết quả không liên quan về "Green Apple Award". Thay vì bịa ra câu trả lời dựa trên dữ liệu nhiễu đó (như Chatbot sẽ làm), Thought tiếp theo của Agent đọc Observation và nhận xét:

> *"Thought: Kết quả tìm kiếm không chứa thông tin ESG chính thức của công ty Apple Inc. Tôi sẽ thử từ khóa hẹp hơn..."*

Agent tự nhận thức được chất lượng dữ liệu và điều chỉnh strategy. Đây là hành vi **self-correction** mà Chatbot không có — vì Chatbot không nhận feedback từ bên ngoài mà chỉ dựa vào training weights nội tại.

---

## IV. Future Improvements (5 Points)

*Đề xuất nâng cấp hệ thống lên tầm Production-level.*

### Scalability: RAG Tool Retrieval với Vector Database

Hệ thống hiện tại nhồi toàn bộ description của 4 tools vào System Prompt mỗi request. Khi số lượng tool mở rộng lên 20–50 API (ví dụ: thêm SEC filing lookup, GHG Protocol calculator, ESG rating APIs của MSCI/Sustainalytics), chi phí token sẽ vọt lên không kiểm soát.

**Giải pháp**: Xây dựng **Tool Registry** lưu trong Vector DB (Qdrant hoặc ChromaDB). Mỗi request, embed câu hỏi của user → tìm top-K tools liên quan nhất bằng cosine similarity → chỉ inject K tools đó vào prompt. Kết hợp với LangGraph để quản lý workflow phức tạp hơn.

### Safety: Multi-Agent Supervisor Architecture

Hệ thống hiện tại không có lớp kiểm duyệt output. Một số Final Answer có thể chứa thông tin sai (nếu DuckDuckGo trả về tin giả mạo) hoặc có nội dung nhạy cảm.

**Giải pháp**: Bổ sung **Supervisor QA Agent** (AutoGen/LangGraph node) chạy song song với main agent. Trước khi trả kết quả về UI, Supervisor đánh giá:
- Tính nhất quán với dữ liệu Observation
- Mức độ "confidence" (có tool được gọi thành công không?)
- Phát hiện nội dung độc hại hoặc off-topic thoát qua guardrails

### Performance: Semantic Caching & Async Tool Execution

**Semantic Caching (Redis + Embedding)**: Lưu cache kết quả với embedding key thay vì exact string match. Câu hỏi "Tin tức ESG Apple" và "ESG news của Apple hôm nay" có cosine similarity cao → hit cache, trả kết quả < 100ms mà không cần gọi OpenAI hay DuckDuckGo.

**Async Tool Execution**: Khi một bước Thought yêu cầu nhiều tool song song (VD: "vừa lấy ESG news vừa lấy stock price của Apple"), hệ thống hiện tại thực hiện tuần tự. Nâng cấp lên `asyncio.gather()` hoặc `concurrent.futures.ThreadPoolExecutor` để gọi đồng thời, giảm latency 40–60%.

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.
