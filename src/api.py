import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.agent.agent import ReActAgent
from src.core.openai_provider import OpenAIProvider

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
    
    return {"mode": "baseline", "response": response.get("content")}

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
            "description": "Calculates estimated budget. Arguments: 'days' (integer) number of days, 'people' (integer) number of people, 'base_fare' (float) flight or hotel cost per day/per person, 'location_multiplier' (float) from 1.0 to 3.0 based on cost of living."
        }
    ]
    
    agent = ReActAgent(llm=provider, tools=tools)
    final_answer = agent.run(request.message)
    
    return {"mode": "agent", "response": final_answer}

# Chạy bằng uvicorn src.api:app --reload
