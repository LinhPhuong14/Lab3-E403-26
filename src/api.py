import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.agent.agent import ReActAgent
from src.core.openai_provider import OpenAIProvider

# Tải biến môi trường
load_dotenv()

app = FastAPI(title="EcoTrace ESG Agent API")

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
    sys_prompt = "You are a professional EcoTrace ESG Advisor. Answer questions about Environmental, Social, and Governance compliance. Answer directly without tools if possible. For complex calculations or data fetching, guess an estimated answer if no tools are available. Keep answers concise."
    response = provider.generate(request.message, system_prompt=sys_prompt)
    
    return {"mode": "baseline", "response": response.get("content")}

@app.post("/chat/agent")
def chat_agent(request: ChatRequest):
    """
    Kích hoạt ReAct Agent Loop để giải quyết câu hỏi sâu (UC 2, UC 3, UC 4, UC 5).
    """
    provider = OpenAIProvider()
    
    # Định nghĩa cấu trúc tools cho Agent ESG thực tế (Real Open APIs)
    tools = [
        {
            "name": "search_real_esg_news",
            "description": "Searches the web for latest real-time ESG (Environmental, Social, Governance) news for a company. Arguments: 'company_name' (string) the name of the company."
        },
        {
            "name": "get_stock_price",
            "description": "Fetches current real-time stock price data. Arguments: 'ticker_symbol' (string) the valid Yahoo Finance stock ticker symbol (e.g. AAPL, MSFT, TSLA)."
        },
        {
            "name": "fetch_company_wikipedia",
            "description": "Fetches general background information and corporate history from Wikipedia. Arguments: 'company_name' (string) the name of the company."
        },
        {
            "name": "calculate_carbon_footprint",
            "description": "Calculates the estimated carbon footprint in kg CO2e based on energy and fuel consumption. Arguments: 'energy_kwh' (float) electricity used in kWh, 'fuel_liters' (float) fuel consumed in liters."
        }
    ]
    
    agent = ReActAgent(llm=provider, tools=tools)
    agent_result = agent.run(request.message)
    
    return {
        "mode": "agent", 
        "response": agent_result.get("answer", ""),
        "metrics": agent_result.get("metrics", {}),
        "steps": agent_result.get("steps", [])
    }

# Chạy bằng uvicorn src.api:app --reload
