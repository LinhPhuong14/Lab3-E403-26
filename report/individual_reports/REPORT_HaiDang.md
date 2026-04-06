# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Hải Đăng
- **Student ID**: 2A202600157
- **Date**: 6/4/2026
---

## I. Technical Contribution (15 Points)

Triển khai tầng API để cung cấp cả hai chế độ: chatbot baseline và ReAct agent, cho phép so sánh trực tiếp giữa cách trả lời tĩnh của LLM và cơ chế suy luận có sử dụng tool.

- **Modules Implementated**: src/api.py
- **Code Highlights**: @app.post("/chat/baseline")
def chat_baseline(request: ChatRequest):
    provider = OpenAIProvider()
    sys_prompt = "You are a professional EcoTrace ESG Advisor..."
    
    response = provider.generate(
        request.message, 
        system_prompt=sys_prompt
    )
    
    return {"mode": "baseline", "response": response.get("content")}
- **Documentation**: ReAct Agent xử lý câu hỏi thông qua vòng lặp lặp lại Thought → Action → Observation.
Ở mỗi bước, LLM quyết định có gọi tool hay không dựa trên danh sách tools[], sau đó nhận kết quả (observation) và cập nhật lại quá trình suy luận.
Vòng lặp tiếp tục cho đến khi agent tạo ra final answer, đồng thời trả về kèm các bước trung gian và metrics.

---

## II. Debugging Case Study (10 Points)

Phân tích lỗi sử dụng tool sai định dạng dẫn đến vòng lặp ReAct.

- **Problem Description**: Agent bị mắc kẹt trong vòng lặp khi liên tục gọi tool với input không hợp lệ, không tạo được Final Answer và lặp lại nhiều bước suy luận.
- **Log Source**: Observation: Error: missing required argument 'company_name'
- **Diagnosis**: Tool schema chưa đủ rõ ràng nên LLM không biết format input chính xác
- **Solution**: Làm rõ description của tool.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

Suy ngẫm về khả năng reasoning và trade-off hệ thống.

1.  **Reasoning**: ReAct buộc LLM phải suy nghĩ theo từng bước thông qua Thought, giúp decomposition rõ ràng và có định hướng sử dụng tool. Thay vì trả lời một lần như chatbot, agent sẽ xác định: cần dữ liệu gì → gọi tool nào → tổng hợp lại → tăng độ chính xác.
2.  **Reliability**: Agent kém ổn định hơn chatbot khi: Tool trả lỗi / timeout, Input format sai, Search trả về dữ liệu nhiễu
3.  **Observation**: Observation đóng vai trò feedback loop quan trọng. Kết quả từ tool ảnh hưởng trực tiếp đến bước Thought tiếp theo:
-Nếu dữ liệu đúng → tiếp tục reasoning
-Nếu dữ liệu sai / nhiễu → agent điều chỉnh hoặc bỏ qua
---

## IV. Future Improvements (5 Points)

Định hướng nâng cấp hệ thống lên production-level.

- **Scalability**: Khi số lượng tool tăng, cần tránh nhồi toàn bộ vào prompt. Chỉ inject top-k tools liên quan vào mỗi query hoặc Tool retrieval bằng Vector DB 
- **Safety**: Thêm lớp validation + guardrails trước khi execute tool
- **Performance**: Cache kết quả tool / LLM (Redis), Giảm số bước ReAct, Tối ưu prompt để giảm token usage
---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.
