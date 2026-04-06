# EcoTrace ESG Advisor (Agentic AI)

EcoTrace ESG Advisor là một trợ lý ảo siêu thông minh (Agentic AI) giúp tra cứu, tổng hợp luồng tin tức và đánh giá tính tuân thủ ESG (Môi trường, Xã hội, Quản trị) của các tập đoàn một cách hoàn toàn tự động dựa trên Kiến trúc ReAct (Reasoning & Acting).

---

## 🚀 HƯỚNG DẪN CHẠY DỰ ÁN (HOW TO RUN)

Dự án này là một hệ thống Full-Stack, bạn cần chạy song song cả **Backend** (Xử lý AI) và **Frontend** (Giao diện người dùng).

### Bước 1: Khởi động Backend (FastAPI & Agent)
Backend chịu trách nhiệm chạy luồng suy luận ReAct và gọi các Tool (DuckDuckGo, Yahoo Finance, Wikipedia).

1. Mở Terminal mới tại thư mục gốc của dự án (`lab3-Team26`).
2. Kích hoạt môi trường ảo (nếu có) và cài đặt thư viện:
   ```bash
   pip install -r requirements.txt
   ```
3. Cấu hình API Key: Đảm bảo bạn đã copy file `.env.example` thành `.env` và điền `OPENAI_API_KEY`.
4. Khởi chạy Server Backend:
   ```bash
   python -m uvicorn src.api:app --reload
   ```
   *Backend sẽ chạy tại: `http://localhost:8000`*

### Bước 2: Khởi động Frontend (Next.js & Tailwind)
Frontend cung cấp giao diện Chat xịn xò (Glassmorphism UI) để tương tác trực quan với Agent, xem cost và các log tư duy (Thoughts).

1. Mở Terminal thứ hai.
2. Di chuyển vào thư mục frontend:
   ```bash
   cd frontend
   ```
3. Cài đặt các gói Node.js:
   ```bash
   npm install
   ```
4. Khởi chạy Server Frontend:
   ```bash
   npm run dev
   ```
   *Frontend sẽ giao tiếp với bạn tại: `http://localhost:3000`*

👉 **Trải nghiệm:** Hãy mở trình duyệt, vào `http://localhost:3000` và chat thử: *"Tìm tin tức ESG của Apple hôm nay và cho tôi biết giá cổ phiếu AAPL của họ hiện bao nhiêu?"*

---

## 🛠️ Cấu Trúc Dự Án
- `src/agent/agent.py`: Nơi chứa "Bộ não" ReAct Agent, Parser JSON và Logic phòng thủ chống ảo giác (Anti-Hallucination).
- `src/api.py`: FastAPI server định nghĩa endpoints.
- `src/tools/esg_tools.py`: Các công cụ thực tế như DDGS News, Wikipedia, Yahoo Finance.
- `frontend/src/app/page.tsx`: Giao diện React/Next.js cho chatbot UI.
- `logs/`: Nơi chứa logs hoạt động chi tiết hệ thống theo thời gian (chuẩn ISO timestamp).

---

## 🏠 (Tùy chọn) Chạy bằng Model Local (CPU)
Nếu bạn không có thẻ tín dụng để dùng OpenAI, bạn có thể chạy mô hình mã nguồn mở bằng thư viện `llama-cpp-python`.

1. Tải mô hình [Phi-3-mini-4k-instruct-GGUF](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf).
2. Đặt vào thư mục `models/` ở gốc dự án.
3. Trong file `.env`, điều chỉnh:
   ```env
   DEFAULT_PROVIDER=local
   LOCAL_MODEL_PATH=./models/Phi-3-mini-4k-instruct-q4.gguf
   ```
