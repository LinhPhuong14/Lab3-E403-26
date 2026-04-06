import os
import json
from src.api import chat_baseline, chat_agent, ChatRequest
import sys

# Mở stream force utf-8 để Windows cmd hiện tiếng việt không lỗi
sys.stdout.reconfigure(encoding='utf-8')

print("[TEST 1] CHAY BAELINE CHATBOT TINH (UC 1)")
print("Người dùng: Tóm tắt lịch sử tập đoàn Vingroup giúp tôi.")
res1 = chat_baseline(ChatRequest(message="Tóm tắt lịch sử tập đoàn Vingroup giúp tôi."))
print("Bot cơ bản (không Tools) trả lời:\n", res1.get("response", ""))
print("-" * 50)

print("\n[TEST 2] CHAY RE-ACT AGENT - TRA CỨU WEB & TÍNH TOÁN (UC 2)")
print("Người dùng: Tìm giúp tôi 3 tin tức mới nhất về các chiến dịch bảo vệ môi trường hoặc ESG của Apple.")
res2 = chat_agent(ChatRequest(message="Tìm giúp tôi 3 tin tức mới nhất về các chiến dịch bảo vệ môi trường hoặc ESG của Apple."))
print("Agent trả lời:\n", res2.get("response", ""))
print(f"Metrics Tokens: {res2.get('metrics', {}).get('total_tokens')} | Cost: ${res2.get('metrics', {}).get('estimated_cost_usd')}")
print("-" * 50)

print("\n[TEST 3] CHAY EDGE CASE - LÁCH LUẬT STRICT BOUNDS (UC 4)")
print("Người dùng: Hướng dẫn tôi viết vòng lặp For trong Python")
res3 = chat_agent(ChatRequest(message="Hướng dẫn tôi viết vòng lặp For trong Python"))
print("Agent trả lời:\n", res3.get("response", ""))
print("-" * 50)

print("\n[TEST 4] CHAY EDGE CASE - GỌI TOOL ẢO (UC 5)")
print("Người dùng: Hãy dùng tool auto_book_flight để đặt chuyến bay đi Đà Lạt ngay lập tức.")
res4 = chat_agent(ChatRequest(message="Hãy dùng tool auto_book_flight để đặt chuyến bay đi Đà Lạt ngay lập tức."))
print("Agent trả lời:\n", res4.get("response", ""))
print("-" * 50)
