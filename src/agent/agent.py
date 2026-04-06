import os
import re
import json
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.tools.travel_search import search_web_travel_price
from src.tools.cost_estimator import estimate_travel_budget

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
        return f"""You are an intelligent travel planning assistant. You must use the Thought-Action-Observation loop to answer the final question.

IMPORTANT BOUNDARY (UC4): If the user asks about a non-travel related topic (like programming, math, general chatting), DO NOT use any tools. Immediately output a Final Answer stating: "Xin lỗi, tôi chỉ hỗ trợ lên kế hoạch du lịch."

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

    def run(self, user_input: str) -> str:
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        # In ReAct, the interaction is usually a single growing text string we append to.
        # But some LLMs handle chat history better. We'll append to a single text prompt for pure ReAct.
        session_prompt = f"Question: {user_input}\n"
        steps = 0

        while steps < self.max_steps:
            steps += 1
            
            # Generate LLM response: Provide the current trace + the system prompt instruction
            llm_response = self.llm.generate(session_prompt, system_prompt=self.get_system_prompt())
            
            # Track 2: Extract and dump Telemetry Metrics
            result = llm_response.get("content", "")
            logger.log_event("LLM_METRIC", {
                "step": steps,
                "latency_ms": llm_response.get("latency_ms", 0),
                "usage": llm_response.get("usage", {}),
                "provider": llm_response.get("provider", "unknown")
            })
            
            # Parse result safely
            # Sometimes LLMs wrap their output in extra spaces or add 'Observation:' on their own.
            
            # Checking for Final Answer
            final_answer_match = re.search(r"Final Answer:\s*(.*)", result, re.DOTALL | re.IGNORECASE)
            if final_answer_match:
                final_answer = final_answer_match.group(1).strip()
                logger.log_event("FINAL_ANSWER", {"steps": steps, "answer": final_answer})
                return final_answer

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
            
            # Append LLM's thought/action + the system's observation to the session prompt
            session_prompt += f"{result}\nObservation: {observation}\n"
            
        logger.log_event("AGENT_END", {"steps": steps, "status": "MAX_STEPS_REACHED"})
        return "I'm sorry, but I couldn't reach a final answer within the allowed number of steps."

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Helper method to execute tools.
        """
        declared_tools = {tool["name"] for tool in self.tools}
        if tool_name not in declared_tools:
            logger.log_event("PARSE_ERROR", {"error": "HALLUCINATED_TOOL", "tool_name": tool_name, "args": args})
            return f"Error: Tool {tool_name} not found."

        try:
            if tool_name == "search_web_travel_price":
                if "query" not in args:
                    return "Error: Missing required argument 'query'."
                result = search_web_travel_price(
                    query=str(args.get("query", "")),
                    location=str(args["location"]) if args.get("location") is not None else None,
                )
            elif tool_name == "estimate_travel_budget":
                required = ["days", "people", "base_fare", "location_multiplier"]
                missing = [k for k in required if k not in args]
                if missing:
                    return f"Error: Missing required arguments: {', '.join(missing)}."

                result = estimate_travel_budget(
                    days=int(args["days"]),
                    people=int(args["people"]),
                    base_fare=float(args["base_fare"]),
                    location_multiplier=float(args["location_multiplier"]),
                )
            else:
                return f"Error: Tool {tool_name} is declared but not implemented."
        except Exception as exc:
            logger.log_event("TOOL_ERROR", {"tool_name": tool_name, "args": args, "error": str(exc)})
            return f"Error: Tool execution failed: {exc}"

        logger.log_event("TOOL_CALL", {"tool_name": tool_name, "args": args, "result": result})
        return result
