import os
import sys
from dotenv import load_dotenv

# Mở stream force utf-8 để Windows cmd hiện tiếng việt không lỗi
sys.stdout.reconfigure(encoding='utf-8')

from src.agent.agent import ReActAgent
from src.core.openai_provider import OpenAIProvider

def run_cmd_demo():
    load_dotenv()
    
    print("="*60)
    print("ECOTRACE ESG ADVISOR AGENT - CLI DEMO")
    print("="*60)
    print("Bạn có thể đặt câu hỏi về điểm ESG của công ty, hoặc tính toán carbon footprint. Gõ 'exit' hoặc 'quit' để thoát.\n")
    
    provider = OpenAIProvider()
    
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

    while True:
        try:
            user_input = input("\nNgười dùng: ")
            if user_input.strip().lower() in ['exit', 'quit']:
                print("Tạm biệt!")
                break
            
            if not user_input.strip():
                continue
                
            # print("\nAgent dang thao tac (Check logs/ de xem chi tiet tele metrics)...")
            
            # Khởi chạy Agent loop
            agent_result = agent.run(user_input)
            
            answer = agent_result.get("answer", "No answer found.")
            metrics = agent_result.get("metrics", {})
            
            print(f"\nESG Advisor:\n{answer}")
            print(f"\n[📈 Metrics] Tokens: {metrics.get('total_tokens', 0)} | Cost: ${metrics.get('estimated_cost_usd', 0)}")
            print("-" * 60)
            
        except KeyboardInterrupt:
            print("\nTạm biệt!")
            break
        except Exception as e:
            print(f"\nDa xay ra loi: {str(e)}")

if __name__ == "__main__":
    run_cmd_demo()
