import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.agent.agent import ReActAgent
from src.core.openai_provider import OpenAIProvider
from src.telemetry.logger import logger

# Tải biến môi trường
load_dotenv()

app = FastAPI(title="Travel Planner Agent API")

# Cấu hình CORS để cho phép Next.js localhost call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.post("/chat/baseline")
def chat_baseline(request: ChatRequest):
    """
    UC 1: Chạy mô hình tĩnh (Chatbot thông thường) không có công cụ.
    """
    provider = OpenAIProvider()
    sys_prompt = "You are a helpful travel assistant. Answer questions directly without tools. You should answer simply and concisely. If asked to calculate complex math or do real-time search, guess an estimated answer."
    response = provider.generate(request.message, system_prompt=sys_prompt)
    usage = response.get("usage", {}) or {}
    
    return {
        "mode": "baseline",
        "response": response.get("content"),
        "metrics": {
            "latency_ms": response.get("latency_ms", 0),
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "estimated_cost": round((usage.get("total_tokens", 0) / 1000) * 0.01, 6),
        },
    }

@app.post("/chat/agent")
def chat_agent(request: ChatRequest):
    """
    Kích hoạt ReAct Agent Loop để giải quyết câu hỏi sâu (UC 2, UC 3, UC 4, UC 5).
    """
    provider = OpenAIProvider()
    
    # Định nghĩa cấu trúc tools cho Agent (hàm thực thi thực tế sẽ được đưa vào tools logic)
    tools = [
        {
            "name": "search_web_travel_price",
            "description": "Searches the web for current travel prices such as flight tickets or hotel costs. Arguments: 'query' (string) outlining what to search for, 'location' (string) city/country."
        },
        {
            "name": "estimate_travel_budget",
            "description": "Calculates estimated budget. Arguments: 'days' (integer) number of days, 'people' (integer) number of people, 'base_fare' (float) flight or hotel cost per day/per person."
        },
        {
            "name": "convert_currency_to_vnd",
            "description": "Converts amount from supported currency to VND. Arguments: 'amount' (float), 'currency' (string: USD, EUR, GBP, JPY, CNY, KRW, VND)."
        }
    ]
    
    agent = ReActAgent(llm=provider, tools=tools)
    final_answer = agent.run(request.message)
    
    # Log complete chain of thought for debugging
    logger.log_event("COMPLETE_TRACE", {
        "mode": "agent",
        "trace": final_answer.get("trace", []),
        "metrics_summary": {
            "steps": final_answer.get("metrics", {}).get("steps"),
            "total_tokens": final_answer.get("metrics", {}).get("total_tokens"),
            "latency_ms": final_answer.get("metrics", {}).get("latency_ms"),
        }
    })
    
    return {"mode": "agent", **final_answer}

# Chạy bằng uvicorn src.api:app --reload
