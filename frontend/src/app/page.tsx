"use client";

import { useState, useRef, useEffect } from "react";

// Types
interface Message {
  id: string;
  role: "user" | "agent";
  content: string;
  metrics?: {
    total_tokens: number;
    estimated_cost_usd: number;
  };
  steps?: Array<{
    thought: string;
    action: string;
    observation: string;
  }>;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome-1",
      role: "agent",
      content: "Xin chào! Mình là EcoTrace ESG Advisor. Mình có thể giúp bạn cập nhật tin tức ESG, tra cứu thông tin doanh nghiệp, lấy giá cổ phiếu thị trường hoặc tính toán lượng phát thải Carbon. Mình có thể giúp gì cho bạn hôm nay?"
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim()
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/chat/agent", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: userMessage.content })
      });

      if (!response.ok) {
        throw new Error("Network response was not ok");
      }

      const data = await response.json();

      const agentMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        content: data.response || "Dạ, mình không nhận được phản hồi, bạn thử lại nhé.",
        metrics: data.metrics,
        steps: data.steps
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (error) {
      console.error("Error communicating with agent API:", error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        content: "🚨 Lỗi kết nối: Không thể kết nối tới Backend Agent. Vui lòng đảm bảo FastAPI đang chạy ở cổng 8000."
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0f172a] text-slate-100 flex flex-col items-center p-4 sm:p-8 font-sans selection:bg-[#10b981] selection:text-white">
      {/* Header */}
      <header className="w-full max-w-4xl mb-8 flex flex-col items-center justify-center space-y-2 mt-4 relative z-10">
        <div className="inline-flex items-center justify-center p-3 bg-[#1e293b] rounded-2xl shadow-[0_0_20px_rgba(16,185,129,0.15)] ring-1 ring-white/10 mb-2">
          <svg className="w-8 h-8 text-[#10b981]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-[#10b981] to-[#34d399] text-transparent bg-clip-text">
          EcoTrace Advisor
        </h1>
        <p className="text-sm text-slate-400 font-medium tracking-wide uppercase">Tư vấn ESG & Phân tích Carbon</p>
      </header>

      {/* Chat Container */}
      <main className="w-full max-w-4xl flex-1 bg-[#1e293b]/80 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/5 flex flex-col overflow-hidden relative">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[#10b981] to-transparent opacity-50"></div>

        {/* Messages Layout */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl p-4 shadow-sm backdrop-blur-sm ${msg.role === "user"
                    ? "bg-[#10b981] text-white rounded-br-none"
                    : "bg-slate-800/80 border border-white/5 rounded-bl-none text-slate-200"
                  }`}
              >
                {msg.role === "agent" && (
                  <div className="flex items-center justify-between space-x-2 mb-2">
                    <div className="flex items-center space-x-2">
                      <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse"></span>
                      <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Chuyên gia ESG</span>
                    </div>
                    {msg.metrics && (
                      <div className="flex items-center space-x-3 text-[10px] text-slate-400 bg-black/20 px-2 py-1 rounded-md border border-white/5">
                        <span title="Số Token sử dụng">🪙 {msg.metrics.total_tokens}</span>
                        <span title="Chi phí ước tính (GPT-4o)">💰 ${msg.metrics.estimated_cost_usd}</span>
                      </div>
                    )}
                  </div>
                )}
                <div className="whitespace-pre-wrap leading-relaxed text-sm sm:text-base">
                  {msg.content}
                </div>

                {/* Steps Accordion */}
                {msg.steps && msg.steps.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-white/5">
                    <details className="group">
                      <summary className="flex items-center justify-between cursor-pointer text-xs font-medium text-slate-400 hover:text-[#10b981] transition-colors list-none">
                        <span>🔍 Xem các bước suy luận ({msg.steps.length} bước)</span>
                        <span className="transition group-open:rotate-180">
                          <svg fill="none" height="16" shapeRendering="geometricPrecision" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" viewBox="0 0 24 24" width="16"><path d="M6 9l6 6 6-6"></path></svg>
                        </span>
                      </summary>
                      <div className="mt-3 space-y-3 bg-[#0f172a] rounded-xl p-3 border border-white/5 text-xs text-slate-300 max-h-60 overflow-y-auto custom-scrollbar">
                        {msg.steps.map((step, idx) => (
                          <div key={idx} className="space-y-1">
                            <div className="font-semibold text-purple-400">🤔 Suy nghĩ: <span className="font-normal text-slate-300">{step.thought}</span></div>
                            {step.action && <div className="font-semibold text-blue-400">⚡ Hành động: <span className="font-normal font-mono bg-black/30 px-1 py-0.5 rounded text-blue-200">{step.action}</span></div>}
                            {step.observation && <div className="font-semibold text-amber-400">👁️ Kết quả: <span className="font-normal text-slate-300">{step.observation}</span></div>}
                            {idx < msg.steps!.length - 1 && <hr className="border-white/5 my-2" />}
                          </div>
                        ))}
                      </div>
                    </details>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="max-w-[85%] rounded-2xl rounded-bl-none p-5 bg-slate-800/80 border border-white/5 shadow-sm text-slate-300">
                <div className="flex items-center space-x-3">
                  <span className="relative flex h-3 w-3">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#10b981] opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-[#10b981]"></span>
                  </span>
                  <span className="text-sm font-medium animate-pulse text-slate-400">Đang phân tích dữ liệu...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        <div className="p-4 sm:p-6 bg-[#0f172a]/50 border-t border-white/5">
          <form
            onSubmit={handleSubmit}
            className="relative flex items-center bg-[#1e293b] rounded-2xl ring-1 ring-white/10 focus-within:ring-[#10b981]/50 focus-within:shadow-[0_0_15px_rgba(16,185,129,0.1)] transition-all duration-300 overflow-hidden"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Hỏi về tin tức ESG của Microsoft hoặc yêu cầu tính toán lượng carbon..."
              disabled={loading}
              className="flex-1 bg-transparent border-none py-4 px-6 text-slate-200 placeholder-slate-500 focus:outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="p-3 mr-2 bg-[#10b981] hover:bg-[#059669] text-white rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center group"
            >
              <svg className="w-5 h-5 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </form>

        </div>
      </main>
    </div>
  );
}
