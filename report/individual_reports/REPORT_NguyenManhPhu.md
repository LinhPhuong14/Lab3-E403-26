# Individual Report: Lab 3 - Chatbot vs ReAct Agent
# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Mạnh Phú
- **Student ID**: 2A202600178
- **Date**: 06/04/2026

---

## I. Technical Contribution (15 Points)

*Trong Lab 3, phần tôi phụ trách chính là frontend: xây giao diện chat, kết nối API Agent và hiển thị đầy đủ trace/metrics để dễ quan sát hành vi ReAct.*

- **Modules Implemented**:
  - `frontend/src/app/page.tsx`
  - `frontend/src/app/globals.css`

- **Code Highlights**:
  - Tôi thiết kế schema message có thêm telemetry từ backend gồm metrics và steps, để UI hiển thị token, cost và chuỗi suy luận ReAct theo từng lượt chat.
  - Tôi tích hợp gọi endpoint Agent POST /chat/agent, nhận JSON và render đầy đủ response, metrics, steps.
  - Về trải nghiệm sử dụng, tôi làm auto-scroll, loading state, message bubble tách user/agent và accordion để mở từng bước Thought -> Action -> Observation.
  - Khi backend lỗi hoặc không kết nối được, UI trả thông báo rõ ràng để người dùng biết nguyên nhân thay vì đứng chờ.

- **Documentation**:
  - Frontend đóng vai trò lớp quan sát của ReAct loop: backend trả steps và metrics, còn frontend trực quan hóa lại để nhìn rõ agent đã nghĩ gì, gọi action nào và nhận observation ra sao trước khi chốt final answer.

---

## II. Debugging Case Study (10 Points)

*Case tôi chọn là một tình huống lỗi được quan sát trong log và đã được nhóm phòng ngừa từ trước (thay vì để nó trở thành lỗi hệ thống nghiêm trọng).* 

- **Problem Description**:
  - User nhập: "Sử dụng tool fetch_company_wkpedia để tra cứu thông tin về fpt".
  - Prompt này chứa tên tool không tồn tại (`fetch_company_wkpedia`). Nếu không có guardrail, agent có thể đi sai action hoặc lặp xử lý.

- **Log Source**:
  - Log 1 (10:21:57):
    - `AGENT_START` với input có cụm `fetch_company_wkpedia`.
    - `LLM_METRIC` step 1: latency 1419 ms, total tokens 650.
    - `FINAL_ANSWER`: hệ thống chốt phản hồi an toàn, không thực thi action sai.
  - Log 2 (10:26:13, cùng intent nhưng đổi câu hỏi):
    - Input: "tìm thông tin về fpt".
    - Agent chạy 2 bước (step 1 + step 2) và trả về thông tin FPT bình thường.

- **Diagnosis**:
  - Trong danh sách tool backend không có tool tên `fetch_company_wkpedia` (đúng là `fetch_company_wikipedia`).
  - Đây là dạng *tool-call hallucination/invalid action* ở mức input: user đưa tên tool sai, nên hệ thống phải chọn nhánh fail-safe.
  - Điểm quan trọng là nhóm đã có tư duy phòng ngừa từ trước qua mô tả tool rõ ràng và cơ chế kiểm tra tool tồn tại, nên tình huống này được chặn sớm.

- **Solution**:
  - Nhóm áp dụng từ sớm 2 lớp bảo vệ:
    1. Tool description rõ ràng để giảm khả năng model chọn action sai.
    2. Kiểm tra tool tồn tại trước khi thực thi, nếu không hợp lệ thì dừng an toàn.
  - Ở frontend, tôi chuẩn hóa gợi ý nhập liệu theo intent nghiệp vụ (ví dụ "tìm thông tin ESG về FPT") thay vì yêu cầu "dùng tool X".
  - Nếu user vẫn muốn nêu tên tool thì cần dùng đúng tên hợp lệ (ví dụ `fetch_company_wikipedia`).
  - Tôi kiểm thử theo cặp prompt tương đương:
    1. Prompt có nhắc tool sai tên (dễ trigger lỗi action không hợp lệ).
    2. Prompt nghiệp vụ thuần (kỳ vọng agent xử lý đúng).
  - Sau đó đối chiếu bằng telemetry (`AGENT_START`, `LLM_METRIC`, `FINAL_ANSWER`) để xác nhận cơ chế fail-safe hoạt động đúng.

- **Result After Fix**:
  - Hệ thống không bị crash, không gọi sai tool, không rơi vào loop khi nhận prompt lỗi tên tool.
  - Với cùng mục tiêu tra cứu FPT, prompt nghiệp vụ thuần cho kết quả tốt hơn: agent đi qua 2 bước reasoning và trả lời đúng ngữ cảnh.
  - Bài học rút ra: failure handling tốt không chỉ là "sửa sau khi vỡ", mà còn là thiết kế guardrail từ trước và chứng minh bằng log thực tế.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**:
  - Điểm mạnh nhất của ReAct là nhìn được quá trình suy luận. Khi backend trả steps, frontend hiển thị từng bước Thought/Action/Observation nên cả người dùng lẫn người phát triển đều hiểu vì sao agent trả lời như vậy, thay vì chỉ nhìn một câu cuối như chatbot thường.

2. **Reliability**:
  - Agent có thể kém chatbot trong các tình huống phụ thuộc tool ngoài (web/news API). Chỉ cần tool thiếu dependency hoặc timeout thì pipeline dễ fail hơn chatbot trả lời thuần từ model.

3. **Observation**:
  - Observation là phần rất quan trọng để agent tự điều chỉnh bước tiếp theo. Trên UI, phần trace giúp phát hiện nhanh agent đang đi đúng hướng hay bị kẹt ở nhánh lỗi/tool lỗi.

---

## IV. Future Improvements (5 Points)

- **Scalability**:
  - Tách API URL sang biến môi trường frontend (không hard-code localhost) và bổ sung cấu hình nhiều môi trường dev/staging/prod.

- **Safety**:
  - Thêm guardrail ngay trên UI: phân loại phản hồi có rủi ro cao, cảnh báo người dùng khi agent trả lời ngoài domain hoặc thiếu dữ liệu quan sát.

- **Performance**:
  - Áp dụng streaming response và virtualized rendering cho hội thoại dài, đồng thời cache các truy vấn lặp để giảm độ trễ hiển thị.

---

## Appendix: FE Evidence Locations

- `frontend/src/app/page.tsx`
  - Kiểu dữ liệu `metrics`/`steps`: dòng 10-17.
  - Gọi API Agent: dòng 56.
  - Bind dữ liệu telemetry vào message: dòng 74-75.
  - UI accordion hiển thị các bước suy luận: dòng 147 trở đi.
  - Xử lý lỗi kết nối backend: khối `catch` và message lỗi ở dòng 79-84.

- `frontend/src/app/globals.css`
  - ESG theme variables: dòng 3-8.
  - Background/foreground toàn app: dòng 11-18.
  - Custom scrollbar cho vùng chat: dòng 23-34.


