import os
import json
from src.api import chat_baseline, chat_agent, ChatRequest
import sys

# Mở stream force utf-8 để Windows cmd hiện tiếng việt không lỗi
sys.stdout.reconfigure(encoding='utf-8')

print("[TEST 1] CHAY CHATBOT TINH (UC 1)")
print("Nguoi dung: Thoi tiet o Da Lat thuong the nao?")
res1 = chat_baseline(ChatRequest(message="Thoi tiet o Da Lat thuong the nao?"))
print("Bot tra loi: ", res1["response"])
print("-" * 50)

print("\n[TEST 2] CHAY TINH TOAN BANG RE-ACT AGENT (UC 2)")
print("Nguoi dung: Tinh du toan du lich cho 2 nguoi di Thai Lan 3 ngay. Gia su base_fare la 150. Tu goi tool tinh toan nhe.")
res2 = chat_agent(ChatRequest(message="Tinh du toan du lich cho 2 nguoi di Thai Lan 3 ngay. Gia su base_fare la 150. Nho goi tool nhe."))
print("Agent tra loi: ", res2["response"])
print("-" * 50)

print("\n[TEST 3] CHAY EDGE CASE - CAU HOI MA CODE (UC 4)")
print("Nguoi dung: Huong dan toi viet vong lap For trong Python")
res3 = chat_agent(ChatRequest(message="Huong dan toi viet vong lap For trong Python"))
print("Agent tra loi: ", res3["response"])
print("-" * 50)

print("\n[TEST 4] BAY HALLUCINATION TOOL (UC 5)")
print("Nguoi dung: Hay dung tool auto_book_hotel de dat khach san ngay lap tuc.")
res4 = chat_agent(ChatRequest(message="Hay dung tool auto_book_hotel de dat khach san ngay lap tuc."))
print("Agent tra loi: ", res4["response"])
print("-" * 50)
