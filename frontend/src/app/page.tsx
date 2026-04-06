"use client";

import { FormEvent, useMemo, useState } from "react";

type ChatRole = "user" | "assistant";

type ChatMessage = {
  role: ChatRole;
  content: string;
};

const SUGGESTED_PROMPTS = [
  "Khí hậu ở Đà Lạt vào mùa đông như thế nào?",
  "Dự tính chi phí cho 2 người đi Bangkok 3 ngày, 150$/ngày, hệ số 1.1",
  "Tìm giá phòng ở Phú Quốc rồi tính tổng chi phí 4 người đi 5 ngày, hệ số 1.5",
];

const AGENT_ENDPOINT = process.env.NEXT_PUBLIC_AGENT_ENDPOINT ?? "http://localhost:8000/chat/agent";

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Chào bạn. Tôi là Travel Planner Agent. Hãy đặt câu hỏi về chi phí, lịch trình hoặc tìm giá du lịch.",
    },
  ]);
  const [prompt, setPrompt] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSend = useMemo(() => prompt.trim().length > 0 && !isLoading, [prompt, isLoading]);

  async function sendMessage(rawPrompt: string) {
    const cleanPrompt = rawPrompt.trim();
    if (!cleanPrompt || isLoading) {
      return;
    }

    setError(null);
    setPrompt("");
    setIsLoading(true);
    setMessages((prev) => [...prev, { role: "user", content: cleanPrompt }]);

    try {
      const response = await fetch(AGENT_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: cleanPrompt }),
      });

      if (!response.ok) {
        throw new Error(`Backend error: ${response.status}`);
      }

      const payload = await response.json();
      const answer =
        payload?.response ??
        payload?.answer ??
        payload?.output ??
        payload?.message ??
        "Không nhận được phản hồi hợp lệ.";

      setMessages((prev) => [...prev, { role: "assistant", content: String(answer) }]);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Không kết nối được backend.";
      setError(message);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Tôi gặp lỗi kết nối backend. Vui lòng kiểm tra API Python đang chạy tại localhost:8000.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage(prompt);
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#fbe8d2_0%,#f5efe6_40%,#e6f1f6_100%)] text-slate-900">
      <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-4 py-6 md:px-8 md:py-10">
        <header className="mb-6 rounded-2xl border border-white/60 bg-white/70 p-5 backdrop-blur">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Lab 03</p>
          <h1 className="mt-2 text-2xl font-bold md:text-3xl">Trợ Lý Lập Kế Hoạch Du Lịch</h1>
          <p className="mt-2 text-sm text-slate-600">Nhập câu hỏi để nhận tư vấn hành trình và ước tính chi phí chuyến đi.</p>
        </header>

        <section className="mb-4 flex flex-wrap gap-2">
          {SUGGESTED_PROMPTS.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => {
                setPrompt(item);
              }}
              className="rounded-full border border-slate-300 bg-white/80 px-3 py-2 text-xs font-medium text-slate-700 transition hover:border-slate-400 hover:bg-white"
            >
              {item}
            </button>
          ))}
        </section>

        <section className="flex-1 overflow-hidden rounded-2xl border border-white/60 bg-white/80 shadow-sm backdrop-blur">
          <div className="h-[56vh] overflow-y-auto p-4 md:p-6">
            <div className="space-y-3">
              {messages.map((msg, index) => (
                <article
                  key={`${msg.role}-${index}`}
                  className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-relaxed md:text-base ${
                    msg.role === "user"
                      ? "ml-auto bg-slate-900 text-white"
                      : "mr-auto border border-slate-200 bg-slate-50 text-slate-800"
                  }`}
                >
                  <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider opacity-70">
                    {msg.role === "user" ? "Bạn" : "Trợ lý"}
                  </p>
                  <p>{msg.content}</p>
                </article>
              ))}

              {isLoading && (
                <article className="mr-auto max-w-[88%] rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider">Trợ lý</p>
                  <p>Đang suy luận và gọi công cụ...</p>
                </article>
              )}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="border-t border-slate-200 bg-white p-3 md:p-4">
            <div className="flex gap-2">
              <input
                value={prompt}
                onChange={(event) => {
                  setPrompt(event.target.value);
                }}
                placeholder="Nhập câu hỏi du lịch của bạn..."
                className="flex-1 rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none ring-0 transition placeholder:text-slate-400 focus:border-slate-900"
              />
              <button
                type="submit"
                disabled={!canSend}
                className="rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                Gửi
              </button>
            </div>
            {error && <p className="mt-2 text-xs text-red-700">Lỗi: {error}</p>}
          </form>
        </section>
      </main>
    </div>
  );
}
