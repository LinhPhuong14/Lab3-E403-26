# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyen Phuong Linh
- **Student ID**: 2A202600193
- **Date**: 06/04/2026

---

## I. Technical Contribution (15 Points)

*Khởi tạo kiến trúc Core ReAct và phát triển định hướng ESG.*

- **Modules Implemented**: 
  - `src/tools/esg_tools.py` (Real APIs Zero-config Deployment)
  - `src/agent/agent.py` (Parser, Cost Metrics, Prompt Bounds)
  - `frontend/src/app/page.tsx` (Glassmorphism & Telemetry Tracking UI)
- **Code Highlights**:
  - Tích hợp thành công Web Crawling APIs thực (`duckduckgo_search` tab `news()`, `requests` gọi public Yahoo Finance và Wikipedia) thay vì dùng Mockup Data tĩnh.
  - Sửa đổi cơ chế trả về của ReAct Agent từ chuỗi văn bản thuần túy sang mảng Dictionary cấu trúc chuẩn: ghi nhận số Tokens, chi phí quy đổi USD theo cấu hình GPT-4o và Logs `steps` (ReAct chains) chi tiết.
- **Documentation**: Các Tools được hệ thống linh hoạt định tuyến thông qua block `_execute_tool()` bằng Python thuần chay (không dùng LangChain), cho phép quản lý vòng đời Prompt và Action một cách tường minh nhất.

---

## II. Debugging Case Study (10 Points)

*Phân tích vòng lặp lỗi Parsing Error điển hình (Infinite ReAct Loop).*

- **Problem Description**: LLM bị mắc kẹt văng lỗi `Max steps reached` (vòng lặp 5 lần) liên tục kèm theo log "Could not parse Action or Final Answer" khi người dùng hỏi các câu cạm bẫy lách luật (Ví dụ: "Bắt LLM đóng vai đầu bếp nấu món ăn").
- **Log Source**: `Observation: Error: Could not parse Action or Final Answer. Please follow the correct Thought/Action/Action Input format.`
- **Diagnosis**: 
  - Regex Parser của hệ thống quy định chữ chốt hạ phải bắt đầu bằng đoạn text `Final Answer: ...`.
  - Mặc dù hệ thống đã được cài đặt lệnh "Strict Bounds" (ép từ chối câu hỏi ngoài luồng), nhưng do Prompt mỏng nên LLM chỉ nói vỏn vẹn *"Dạ xin lỗi bạn, mình được đào tạo..."* (thiếu cụm `Final Answer:` ở đầu chuỗi). Hệ thống Regex không tóm được mỏ neo này, ném lỗi ngược lại cho LLM, khiến AI loay hoay lặp lại câu xin lỗi.
- **Solution**: Cập nhật lại System Prompt bằng quy tắc bắt buộc khuôn dạng chặt chẽ: `You MUST format your refusal EXACTLY like this: \nFinal Answer: Dạ xin lỗi...`.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Suy ngẫm về sức mạnh Suy luận và Điểm yếu Hệ thống.*

1.  **Reasoning**: Vòng lặp `Thought` thực sự ép Model phải lên kế hoạch (Planning) và chia nhỏ vấn đề (Decomposition). So với Chatbot trả lời một lèo dễ dẫn đến "Ảo giác" (Hallucination), thiết kế ReAct giúp Agent tự nhẩm trong đầu: *"Để tính giá trị tác động ESG của Tesla tới cổ phiếu, mình phải truy vấn Wikipedia trước, lấy News và sau đó tra cứu Market Price"*. 
2.  **Reliability**: Agent sẽ hoàn toàn mất kiểm soát và trả lời chậm hơn hẳn một Chatbot bình thường nếu kết nối mạng của Tool bị Time-out hoặc bộ máy tìm kiếm (Searching Logic) gặp từ khóa quá yếu, LLM sẽ tiêu tốn quá nhiều Token để mò mẫm dữ kiện thay vì trả lời theo Training Data gốc của nó.
3.  **Observation**: Feedback là lõi cốt tử! Khi Agent của tôi tìm kiếm `Apple ESG Report`, Search Engine vô tình mang về kết quả "Green Apple Award". Nhờ có Observation, bước Thought tiếp theo của AI đã soi chiếu lại và tự phán đoán "Data này vô dụng", từ đó kiên quyết từ chối bịa chuyện, khẳng định lại tinh thần chịu trách nhiệm giải trình.

---

## IV. Future Improvements (5 Points)

*Hệ thống quy mô Production-level.*

- **Scalability**: Khi số lượng Tool mở rộng vượt qua 10-20 API, việc nhồi Description mọi Tool vào System Prompt sẽ khiến chi phí Token vọt lên tới nóc. Giải pháp là ứng dụng **Vector Database** (Qdrant, ChromaDB) để thực hiện "RAG Tool Retrieval" – chỉ bốc 3 Tools được nghi ngờ là đúng nhất truyền vào LLM theo từng query.
- **Safety**: Xây dựng kiến trúc **Multi-Agent (LangGraph/AutoGen)**. Bổ sung một nút "Supervisor QA (Quality Assurance)". Trước khi đẩy Final Answer ra UI cho người dùng, QA Agent sẽ đánh giá độ "Độc hại" hoặc "An Toàn" của câu trả lời.
- **Performance**: Ứng dụng Semantic Caching bằng **Redis** hoặc MongoDB. Nếu User B hỏi lại câu hỏi mà User A mới hỏi 3 phút trước (hoặc yêu cầu lấy API chứng khoán cũ), hệ thống móc bộ đệm trả lời ngay dưới 100ms mà không cần gọi OpenAI hay truy vấn Yahoo Finance.
