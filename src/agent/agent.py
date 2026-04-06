import os
import re
import json
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

class ReActAgent:
    """
    SKELETON: A ReAct-style Agent that follows the Thought-Action-Observation loop.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        Instructions for the ReAct loop.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        return f"""You are a professional and highly empathetic EcoTrace ESG Advisor. You must use the Thought-Action-Observation loop to answer.

IMPORTANT INSTRUCTIONS:
- ALWAYS respond in the Final Answer using Vietnamese (Tiếng Việt) in an empathetic, positive, and supportive tone.
- You are an expert in Environmental, Social, and Governance (ESG) criteria and carbon footprint analytics.

BOUNDARIES AND FLEXIBILITY (COST OPTIMIZATION):
1. You are highly flexible regarding ESG topics. Help the user enthusiastically if the request contains ANY keyword remotely related to corporate sustainability, carbon metrics, green energy, corporate culture, ethics, or environmental impact.
2. OUT-OF-DOMAIN STRICT RULE: If the topic is 100% UNRELATED to ESG or business sustainability (e.g., Python code, cooking, medical diagnosis, roleplaying a chef, travel booking), you MUST immediately refuse. You MUST format your refusal EXACTLY like this:
Final Answer: Dạ xin lỗi bạn, mình được đào tạo chuyên sâu về tư vấn và đánh giá tác động ESG nên không thể hỗ trợ chủ đề này. Bạn có câu hỏi nào về phát triển bền vững thì cho mình biết nhé!

You have access to the following tools:
{tool_descriptions}

Your output must follow this EXACT plain text format (no markdown blocks like ```json unless requested inside arguments):

Thought: your line of reasoning about what to do next. If a tool fails (Observation says Error), your next Thought should acknowledge the error and output a Final Answer.
Action: tool_name
Action Input: {{"arg1": "value1", "arg2": "value2"}}
Observation: the result of the tool call (you do not write the Observation, the system will provide it!).

When you know the final answer, output:
Final Answer: your final response to the user.

IMPORTANT: You can only output ONE Action at a time. After outputting Action and Action Input, STOP and await the Observation.
"""

    def run(self, user_input: str) -> Dict[str, Any]:
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        session_prompt = f"Question: {user_input}\n"
        steps = 0
        
        # Tracking metrics
        total_prompt_tokens = 0
        total_completion_tokens = 0
        steps_log = []

        while steps < self.max_steps:
            steps += 1
            
            # Generate LLM response: Provide the current trace + the system prompt instruction
            llm_response = self.llm.generate(session_prompt, system_prompt=self.get_system_prompt())
            
            # Track 2: Extract and accumulate Metrics
            result = llm_response.get("content", "")
            usage = llm_response.get("usage", {})
            total_prompt_tokens += usage.get("prompt_tokens", 0)
            total_completion_tokens += usage.get("completion_tokens", 0)
            
            logger.log_event("LLM_METRIC", {
                "step": steps,
                "latency_ms": llm_response.get("latency_ms", 0),
                "usage": usage,
                "provider": llm_response.get("provider", "unknown")
            })
            
            # Current step log template
            current_step_log = {"thought": "", "action": "", "observation": ""}
            
            # Parse result safely
            # Sometimes LLMs wrap their output in extra spaces or add 'Observation:' on their own.
            
            # Parse logic
            thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|\nFinal Answer:|\Z)", result, re.DOTALL | re.IGNORECASE)
            if thought_match:
                current_step_log["thought"] = thought_match.group(1).strip()
            
            # Checking for Final Answer
            final_answer_match = re.search(r"Final Answer:\s*(.*)", result, re.DOTALL | re.IGNORECASE)
            if final_answer_match:
                final_answer = final_answer_match.group(1).strip()
                logger.log_event("FINAL_ANSWER", {"steps": steps, "answer": final_answer})
                
                # Calculate cost (GPT-4o standard: $5/1M input, $15/1M output)
                cost = (total_prompt_tokens / 1000000 * 5.0) + (total_completion_tokens / 1000000 * 15.0)
                if current_step_log["thought"]:
                    steps_log.append(current_step_log)
                    
                return {
                    "answer": final_answer,
                    "metrics": {
                        "total_tokens": total_prompt_tokens + total_completion_tokens,
                        "prompt_tokens": total_prompt_tokens,
                        "completion_tokens": total_completion_tokens,
                        "estimated_cost_usd": float(f"{cost:.6f}")
                    },
                    "steps": steps_log
                }

            # Checking for Action and Action Input
            action_match = re.search(r"Action:\s*([^\n]+)", result, re.IGNORECASE)
            action_input_match = re.search(r"Action Input:\s*(.*?)(\nObservation:|\Z)", result, re.DOTALL | re.IGNORECASE)
            
            if action_match and action_input_match:
                action_name = action_match.group(1).strip()
                action_input_str = action_input_match.group(1).strip()
                
                # Cleanup action input if it's placed inside ```json blocks by LLM hallucination
                action_input_str = action_input_str.strip("`")
                if action_input_str.startswith("json\n"):
                    action_input_str = action_input_str[5:]
                
                current_step_log["action"] = f"{action_name} ({action_input_str})"
                # Attempt to parse json
                try:
                    args = json.loads(action_input_str)
                    observation = self._execute_tool(action_name, args)
                except json.JSONDecodeError:
                    observation = "Error: Invalid JSON format in Action Input. Please try again and provide pure JSON."
                    logger.log_event("PARSE_ERROR", {"raw_input": action_input_str})
            else:
                # If neither Action nor Final Answer is found, prompt the model to use the proper format
                observation = "Error: Could not parse Action or Final Answer. Please follow the correct Thought/Action/Action Input format."
            
            current_step_log["observation"] = observation
            steps_log.append(current_step_log)
            # Append LLM's thought/action + the system's observation to the session prompt
            session_prompt += f"{result}\nObservation: {observation}\n"
            
        logger.log_event("AGENT_END", {"steps": steps, "status": "MAX_STEPS_REACHED"})
        
        cost = (total_prompt_tokens / 1000000 * 5.0) + (total_completion_tokens / 1000000 * 15.0)
        return {
            "answer": "Dạ rất tiếc, tôi chưa thể tìm ra câu trả lời cuối cùng trong số bước cho phép. Bạn có thể thử đặt lại câu hỏi rõ ràng hơn nhé!",
            "metrics": {
                "total_tokens": total_prompt_tokens + total_completion_tokens,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "estimated_cost_usd": float(f"{cost:.6f}")
            },
            "steps": steps_log
        }

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Helper method to execute tools.
        """
        from src.tools.esg_tools import search_real_esg_news, get_stock_price, fetch_company_wikipedia, calculate_carbon_footprint
        
        # Check if the tool exists in our definition
        tool_exists = any(t['name'] == tool_name for t in self.tools)
        if not tool_exists:
            return f"Error: Tool {tool_name} not found. Please use only the tools provided."

        try:
            if tool_name == "search_real_esg_news":
                return search_real_esg_news(company_name=args.get('company_name', ''))
            elif tool_name == "get_stock_price":
                return get_stock_price(ticker_symbol=args.get('ticker_symbol', ''))
            elif tool_name == "fetch_company_wikipedia":
                return fetch_company_wikipedia(company_name=args.get('company_name', ''))
            elif tool_name == "calculate_carbon_footprint":
                return calculate_carbon_footprint(
                    energy_kwh=args.get('energy_kwh', 0.0),
                    fuel_liters=args.get('fuel_liters', 0.0)
                )
            else:
                return f"Error: Tool {tool_name} is known but execution logic is not implemented."
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}. Provide valid arguments."
