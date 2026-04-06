# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Huỳnh Lê Xuân Ánh
- **Student ID**: 2A202600083
- **Date**: 06/04/2026

---

## I. Technical Contribution (15 Points)

Vẽ flowchart và hoàn thành report nhóm

- **Modules Implementated**: tests/cli_demo.py, tests/test_be1.py
- **Code Highlights**: 
* CLI Demo for ReAct Agent:
Xây dựng giao diện dòng lệnh cho người dùng tương tác trực tiếp với Agent
* Tích hợp nhiều tools: `search_real_esg_news`, `get_stock_price`, `fetch_company_wikipedia`, `calculate_carbon_footprint`
* Hiển thị Metrics (Token + Cost)
* Test Script so sánh Chatbot vs Agent
- **Documentation**:
* cli_demo.py đóng vai trò là entry point để chạy vòng lặp ReAct:
Nhận input người dùng
Gọi agent.run()
Agent thực hiện chu trình: Thought → Action → Observation → Thought → Final Answer
* test_be1.py giúp kiểm thử:
So sánh trực tiếp giữa Chatbot (không tool) và ReAct Agent
Đánh giá behavior trong các tình huống khác nhau (normal + edge cases)
---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: Agent có thể cố gắng gọi các tool không tồn tại (ví dụ: auto_book_flight) khi người dùng yêu cầu hành động ngoài phạm vi.
- **Log Source**: dùng prompt res4 = chat_agent(ChatRequest(message="Hãy dùng tool auto_book_flight..."))
- **Diagnosis**: 
LLM bị “hallucination” tool name do:
* Prompt không giới hạn chặt danh sách tool hợp lệ
* Model suy đoán rằng có thể tồn tại tool tương ứng
* Ngoài ra, Agent chưa validate tool trước khi gọi
- **Solution**: 
* Giới hạn danh sách tool rõ ràng trong prompt
* Thêm cơ chế:
       Validate tool name trước khi execute
       Fallback: trả lời tự nhiên nếu tool không tồn tại
* Điều chỉnh system prompt để nhấn mạnh
---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1.  **Reasoning**: `Thought` giúp Agent xử lý các bài toán nhiều bước, cần suy luận hoặc cần dữ liệu bên ngoài tốt hơn Chatbot.
2.  **Reliability**: Agent có thể perform kém hơn trong các trường hợp câu hỏi đơn giản, tool không cần thiết nhưng vẫn bị gọi, overthinking, prompt không tốt
3.  **Observation**: Observation giúp cập nhật thông tin mới cho Agent, giúp cho Agent điều chỉnh và cải thiện kết quả qua từng bước

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**: 
* Sử dụng async queue cho tool calls
* Tách agent thành microservices
* Cache kết quả tool để giảm chi phí
- **Safety**: 
* Thêm “Supervisor LLM” để kiểm tra: Tool usage, Output an toàn
* Validate input/output nghiêm ngặt
- **Performance**: 
* Sử dụng Vector Database để: Truy xuất tool thông minh hơn, Giảm số lần gọi LLM
* Tối ưu prompt để giảm token usage

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.