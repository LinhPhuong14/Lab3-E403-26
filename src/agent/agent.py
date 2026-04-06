import os
import time
import re
import json
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.tools.travel_search import search_web_travel_price
from src.tools.cost_estimator import estimate_travel_budget
from src.tools.currency_converter import convert_currency_to_vnd

USD_TO_VND_RATE = 26337.0

class ReActAgent:
    """
    SKELETON: A ReAct-style Agent that follows the Thought-Action-Observation loop.
    Includes guardrail for out-of-context detection with retry and timeout.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5, max_retries: int = 5, timeout_seconds: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.history = []
        
        # Guardrail keywords for scope validation
        self.in_scope_keywords = {"giá", "price", "chi phí", "cost", "ngân sách", "budget", "vé", "ticket", "phòng", "hotel", "du lịch", "travel", "bay", "flight", "khách sạn"}
        self.out_of_scope_keywords = {
            "lập trình", "code", "python", "javascript",
            "y tế", "medical", "luật pháp", "law",
            "toán học phức tạp", "complex math", "hack", "hacking",
            "thời tiết", "weather", "chiến sự", "quân sự", "xung đột", "politics", "chính trị"
        }

    def check_out_of_context(self, user_input: str) -> tuple[bool, Optional[str]]:
        """
        Guardrail check: Detect if input is out of context (OOC).
        Returns (is_out_of_context, rejection_reason)
        """
        input_lower = user_input.lower()
        
        # Check for out-of-scope keywords
        for keyword in self.out_of_scope_keywords:
            if keyword in input_lower:
                reason = f"Yêu cầu này nằm ngoài phạm vi. Tôi chỉ hỗ trợ tra cứu giá du lịch và ước tính ngân sách, không hỗ trợ {keyword}."
                return True, reason
        
        # Check if input has any in-scope keywords
        has_in_scope = any(keyword in input_lower for keyword in self.in_scope_keywords)
        
        if not has_in_scope:
            reason = f"Yêu cầu này không rõ ràng là về giá du lịch hoặc ngân sách. Vui lòng hỏi về: giá vé, giá phòng, chi phí du lịch, hoặc lập kế hoạch ngân sách."
            return True, reason
        
        return False, None

    def _json_readable_preview(self, value: Any, max_len: int = 200) -> str:
        """Convert JSON-like strings to readable UTF-8 preview for logs."""
        if isinstance(value, str):
            text = value
            try:
                obj = json.loads(value)
                text = json.dumps(obj, ensure_ascii=False)
            except Exception:
                text = value
            return text[:max_len]

        try:
            return json.dumps(value, ensure_ascii=False)[:max_len]
        except Exception:
            return str(value)[:max_len]

    def _enforce_vnd_answer(self, text: str) -> str:
        """Convert USD amounts in final answer to VND display for user-facing consistency."""
        if not text:
            return text

        def _to_vnd(amount_str: str) -> str:
            amount = float(amount_str.replace(",", ""))
            converted = amount * USD_TO_VND_RATE
            return f"{converted:,.0f} VND"

        # Convert patterns like $123.45
        text = re.sub(
            r"\$\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)",
            lambda m: _to_vnd(m.group(1)),
            text,
        )

        # Convert patterns like 123.45 USD
        text = re.sub(
            r"([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*USD\b",
            lambda m: _to_vnd(m.group(1)),
            text,
            flags=re.IGNORECASE,
        )

        # Remove leftover standalone USD token if any
        text = re.sub(r"\bUSD\b", "VND", text, flags=re.IGNORECASE)
        return text

    def get_system_prompt(self) -> str:
        """
        System prompt for ReAct agent loop with Thought-Action-PAUSE-Observation-Answer format.
        """
        tool_descriptions = "\n".join([f"{t['name']}: {t['description']}" for t in self.tools])
        return f"""Bạn là một Trợ Lý Tìm Giá & Lập Ngân Sách chuyên về khám phá giá cả và ước tính chi phí.

Bạn chạy trong một vòng lặp: Thought → Action → PAUSE → Observation → Answer

CHỈ SỬ DỤNG THOUGHT ĐỂ MÔ TẢ SỰ SUY NGHĨ CỦA BẠN VỀ CÂU HỎI.
CHỈ GỌI MỘT ACTION TẠI MỘT LƯỢT - KHI XONG HÃY DỪNG VÀ CHỜ OBSERVATION.
CHỈ VIẾT ANSWER KHI BẠN CÓ ĐỦ THÔNG TIN ĐỂ TRẢ LỜI.

CÁC CÔNG CỤ CÓ SẴN:

{tool_descriptions}

HƯỚNG DẪN SỬ DỤNG:
- Sử dụng công cụ khi người dùng hỏi về giá, chi phí, hoặc lập kế hoạch ngân sách
- Đừng bịa đặt kết quả công cụ. Nếu công cụ lỗi, hãy nói rõ lỗi
- BẮT BUỘC trả kết quả tiền tệ cuối cùng theo VND cho người dùng
- Nếu có số tiền bằng ngoại tệ, dùng tool convert_currency_to_vnd trước khi đưa ra Answer
- Không dùng cụm từ "Vietnamese dong" trong câu trả lời, chỉ dùng ký hiệu "VND"
- Nếu yêu cầu ngoài phạm vi (lập trình, y tế, luật pháp), từ chối đ礼: "Xin lỗi, tôi chỉ hỗ trợ tra cứu giá cả và ước tính ngân sách"

VÍ DỤ PHIÊN LÀM VIỆC:

Câu hỏi: Chi phí du lịch 3 ngày cho 2 người với giá cơ bản $100/người/ngày là bao nhiêu?

Thought: Người dùng muốn ước tính chi phí du lịch. Tôi cần dùng công cụ estimate_travel_budget với thông tin: 3 ngày, 2 người, $100/người/ngày
Action: estimate_travel_budget
Action Input: {{"days": 3, "people": 2, "base_fare": 100}}
PAUSE

Nếu bạn được gọi lại với:
Observation: {{"days": 3, "people": 2, "base_fare": 100, "total_budget": 600.0, "currency": "USD"}}

Thought: Tôi đã có kết quả theo USD, giờ cần quy đổi sang VND
Action: convert_currency_to_vnd
Action Input: {{"amount": 600, "currency": "USD"}}
PAUSE

Nếu bạn được gọi lại với:
Observation: {{"amount": 600, "currency": "USD", "converted_amount": 15802200, "converted_currency": "VND"}}

Thought: Tôi đã có kết quả quy đổi VND
Answer: Chi phí du lịch 3 ngày cho 2 người với giá cơ bản 100 USD là 15,802,200 VND.

Bây giờ đến lượt bạn:"""

    def run(self, user_input: str) -> Dict[str, Any]:
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name, "max_steps": self.max_steps})
        
        # Guardrail check: Out-of-context detection
        is_ooc, ooc_reason = self.check_out_of_context(user_input)
        if is_ooc:
            logger.log_event("GUARDRAIL_REJECTED", {
                "input": user_input[:100],
                "reason": ooc_reason
            })
            return {
                "response": ooc_reason,
                "trace": [],
                "metrics": {
                    "steps": 0,
                    "latency_ms": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "estimated_cost": 0,
                },
                "guardrail_rejected": True,
            }
        
        # In ReAct, the interaction is usually a single growing text string we append to.
        # But some LLMs handle chat history better. We'll append to a single text prompt for pure ReAct.
        session_prompt = f"Câu hỏi: {user_input}\n"
        steps = 0
        trace: List[Dict[str, Any]] = []
        total_latency_ms = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0

        while steps < self.max_steps:
            steps += 1
            
            # Generate LLM response with timeout and retry mechanism
            step_started_at = time.time()
            llm_response = None
            retry_count = 0
            last_error = "Unknown error"

            # Retry loop with per-attempt timeout budget (timeout_seconds for each attempt).
            for attempt in range(1, self.max_retries + 1):
                retry_count = attempt
                attempt_started_at = time.time()
                try:
                    candidate = self.llm.generate(session_prompt, system_prompt=self.get_system_prompt())
                    attempt_elapsed = time.time() - attempt_started_at

                    if attempt_elapsed > self.timeout_seconds:
                        raise TimeoutError(
                            f"Attempt exceeded {self.timeout_seconds}s (elapsed {attempt_elapsed:.2f}s)"
                        )

                    llm_response = candidate
                    break
                except Exception as e:
                    last_error = str(e)
                    logger.log_event("LLM_RETRY", {
                        "step": steps,
                        "attempt": attempt,
                        "max_retries": self.max_retries,
                        "timeout_per_attempt_seconds": self.timeout_seconds,
                        "error": last_error,
                    })

                    if attempt < self.max_retries:
                        time.sleep(0.5)
            
            if llm_response is None:
                logger.log_event("LLM_TIMEOUT", {
                    "step": steps,
                    "retry_count": retry_count,
                    "timeout_per_attempt_seconds": self.timeout_seconds,
                    "elapsed_seconds": time.time() - step_started_at,
                    "error": last_error,
                })
                return {
                    "response": (
                        f"Xin lỗi, hệ thống đã hết thời gian chờ sau {retry_count} lần thử "
                        f"(mỗi lần {self.timeout_seconds}s). Vui lòng thử lại."
                    ),
                    "trace": trace,
                    "metrics": {
                        "steps": steps,
                        "latency_ms": int((time.time() - step_started_at) * 1000),
                        "prompt_tokens": total_prompt_tokens,
                        "completion_tokens": total_completion_tokens,
                        "total_tokens": total_tokens,
                                "estimated_cost": round((total_tokens / 1000) * 0.01, 6),
                    },
                    "timeout": True,
                }
            
            step_latency_ms = int((time.time() - step_started_at) * 1000)
            
            # Track 2: Extract and dump Telemetry Metrics
            result = llm_response.get("content", "")
            usage = llm_response.get("usage", {}) or {}
            total_latency_ms += llm_response.get("latency_ms", step_latency_ms)
            total_prompt_tokens += int(usage.get("prompt_tokens", 0) or 0)
            total_completion_tokens += int(usage.get("completion_tokens", 0) or 0)
            total_tokens += int(usage.get("total_tokens", 0) or 0)
            
            logger.log_event("LLM_STEP", {
                "step": steps,
                "latency_ms": llm_response.get("latency_ms", 0),
                "usage": llm_response.get("usage", {}),
                "provider": llm_response.get("provider", "unknown"),
                "llm_raw_response": result[:500]  # First 500 chars for debugging
            })

            thought_match = re.search(r"Thought:\s*(.*?)(?:\nAction:|\nAnswer:|\Z)", result, re.DOTALL | re.IGNORECASE)
            current_thought = thought_match.group(1).strip() if thought_match else None
            
            # Parse result safely
            # Sometimes LLMs wrap their output in extra spaces or add 'Observation:' on their own.
            
            # Checking for Answer (final response)
            answer_match = re.search(r"Answer:\s*(.*)", result, re.DOTALL | re.IGNORECASE)
            if answer_match:
                final_answer = self._enforce_vnd_answer(answer_match.group(1).strip())
                trace.append({
                    "step": steps,
                    "type": "final_answer",
                    "content": final_answer,
                })
                logger.log_event("CHAIN_OF_THOUGHT_COMPLETE", {
                    "total_steps": steps,
                    "final_step_type": "final_answer",
                    "answer_preview": final_answer[:200],
                    "total_tokens": total_tokens,
                    "total_latency_ms": total_latency_ms
                })
                return {
                    "response": final_answer,
                    "trace": trace,
                    "metrics": {
                        "steps": steps,
                        "latency_ms": total_latency_ms,
                        "prompt_tokens": total_prompt_tokens,
                        "completion_tokens": total_completion_tokens,
                        "total_tokens": total_tokens,
                        "estimated_cost": round((total_tokens / 1000) * 0.01, 6),
                    },
                }

            # Checking for Action and Action Input.
            # Supports both formats:
            # 1) Action: tool_name: arguments
            # 2) Action: tool_name + Action Input: {...}
            action_inline_match = re.search(r"Action:\s*([a-z_]+)\s*:\s*(.+)", result, re.IGNORECASE)
            action_name_only_match = re.search(r"Action:\s*([a-z_]+)\s*$", result, re.IGNORECASE | re.MULTILINE)
            action_input_match = re.search(
                r"Action Input:\s*(.*?)(?:\n(?:PAUSE|Observation:|Answer:)|\Z)",
                result,
                re.IGNORECASE | re.DOTALL,
            )

            action_name: Optional[str] = None
            action_arg = ""

            if action_inline_match:
                action_name = action_inline_match.group(1).strip().lower()
                action_arg = action_inline_match.group(2).strip()
            elif action_name_only_match:
                action_name = action_name_only_match.group(1).strip().lower()
                if action_input_match:
                    action_arg = action_input_match.group(1).strip()

            if action_name:
                
                # GUARDRAIL: Validate tool exists in available tools BEFORE execution
                declared_tools = {tool["name"].lower(): tool for tool in self.tools}
                
                if action_name not in declared_tools:
                    # Tool not found - return error immediately
                    observation = f"Lỗi: Tool '{action_name}' không tồn tại. Công cụ khả dụng: {', '.join(declared_tools.keys())}"
                    parse_status = "tool_not_found"
                    
                    trace.append({
                        "step": steps,
                        "type": "tool_not_found",
                        "thought": current_thought,
                        "action": action_name,
                        "action_input": action_arg,
                        "observation": observation,
                        "parse_status": parse_status,
                    })
                    
                    logger.log_event("TOOL_NOT_FOUND", {
                        "step": steps,
                        "requested_tool": action_name,
                        "available_tools": list(declared_tools.keys()),
                        "error_message": observation
                    })
                    
                    # Return error immediately instead of continuing loop
                    return {
                        "response": observation,
                        "trace": trace,
                        "metrics": {
                            "steps": steps,
                            "latency_ms": total_latency_ms,
                            "prompt_tokens": total_prompt_tokens,
                            "completion_tokens": total_completion_tokens,
                            "total_tokens": total_tokens,
                            "estimated_cost": round((total_tokens / 1000) * 0.01, 6),
                        },
                    }
                
                # Tool exists - execute it
                try:
                    # Parse action input - could be JSON or simple string
                    parsed_args: Optional[Dict[str, Any]] = None
                    try:
                        # Try to parse as JSON first
                        parsed_args = json.loads(action_arg)
                    except json.JSONDecodeError:
                        # If not JSON, treat as plain text query
                        parsed_args = {"query": action_arg}
                    
                    observation = self._execute_tool(action_name, parsed_args)
                    parse_status = "success"
                except Exception as e:
                    observation = f"Lỗi: Tool execution failed: {str(e)}"
                    parse_status = "execution_error"
                    logger.log_event("TOOL_EXECUTION_ERROR", {
                        "step": steps,
                        "error_type": "execution_error",
                        "tool": action_name,
                        "error": str(e),
                        "action_input": action_arg
                    })
                
                trace.append({
                    "step": steps,
                    "type": "tool_call",
                    "thought": current_thought,
                    "action": action_name,
                    "action_input": parsed_args if parsed_args is not None else action_arg,
                    "observation": observation,
                    "parse_status": parse_status,
                })
                
                logger.log_event("TOOL_EXECUTION", {
                    "step": steps,
                    "action": action_name,
                    "action_input": action_arg,
                    "parse_status": parse_status,
                    "observation_preview": self._json_readable_preview(observation, 200)
                })
            else:
                refusal_markers = ["xin lỗi", "tôi chỉ hỗ trợ", "không thể thực hiện", "không thể hỗ trợ"]
                is_plain_refusal = any(marker in result.lower() for marker in refusal_markers)

                if is_plain_refusal:
                    # More accurate classification: this is a scope/refusal response, not an Action parse issue.
                    observation = result.strip()
                    trace_type = "out_of_scope_refusal"
                    parse_status = "out_of_scope_refusal"

                    logger.log_event("OUT_OF_SCOPE_REFUSAL", {
                        "step": steps,
                        "llm_response_preview": result[:300]
                    })
                else:
                    # Real format error: model attempted ReAct but output schema is invalid.
                    observation = "Lỗi: Không thể phân tích Action. Hỗ trợ 2 định dạng: 'Action: tool_name: arguments' hoặc 'Action: tool_name' + 'Action Input: {...}'."
                    trace_type = "format_error"
                    parse_status = "format_error"

                    logger.log_event("FORMAT_ERROR", {
                        "step": steps,
                        "error_type": "invalid_action_format",
                        "llm_response_preview": result[:300]
                    })

                trace.append({
                    "step": steps,
                    "type": trace_type,
                    "thought": current_thought,
                    "observation": observation,
                    "raw_response": result[:500],
                    "parse_status": parse_status,
                })

                logger.log_event("AGENT_EARLY_STOP", {
                    "step": steps,
                    "reason": "out_of_scope_refusal" if is_plain_refusal else "format_error_no_action",
                    "is_plain_refusal": is_plain_refusal,
                    "raw_response_preview": result[:300]
                })

                return {
                    "response": observation,
                    "trace": trace,
                    "metrics": {
                        "steps": steps,
                        "latency_ms": total_latency_ms,
                        "prompt_tokens": total_prompt_tokens,
                        "completion_tokens": total_completion_tokens,
                        "total_tokens": total_tokens,
                        "estimated_cost": round((total_tokens / 1000) * 0.01, 6),
                    },
                }
            
            # Append LLM's thought/action + the system's observation to the session prompt
            session_prompt += f"{result}\nObservation: {observation}\n"
            
            
        # Max steps reached without final answer
        last_trace = trace[-1] if trace else None
        logger.log_event("AGENT_TIMEOUT", {
            "total_steps": steps,
            "max_steps": self.max_steps,
            "last_step_type": last_trace.get("type") if last_trace else None,
            "last_action": last_trace.get("action") if last_trace else None,
            "reason": "Agent reached max steps without producing Answer",
            "total_tokens": total_tokens,
            "total_latency_ms": total_latency_ms,
            "full_trace_length": len(trace)
        })
        return {
            "response": "Xin lỗi, tôi không thể tìm thấy câu trả lời trong số bước cho phép.",
            "trace": trace,
            "metrics": {
                "steps": steps,
                "latency_ms": total_latency_ms,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_tokens,
                "estimated_cost": round((total_tokens / 1000) * 0.01, 6),
            },
        }

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Helper method to execute tools.
        tool_name should be lowercase (e.g., 'search_web_travel_price')
        """
        tool_name = tool_name.lower()
        
        try:
            if tool_name == "search_web_travel_price":
                if "query" not in args:
                    return "Lỗi: Thiếu tham số 'query'."
                result = search_web_travel_price(
                    query=str(args.get("query", "")),
                    location=str(args.get("location", "")) if args.get("location") is not None else None,
                )
            elif tool_name == "estimate_travel_budget":
                required = ["days", "people", "base_fare"]
                missing = [k for k in required if k not in args]
                if missing:
                    return f"Lỗi: Thiếu tham số: {', '.join(missing)}."

                result = estimate_travel_budget(
                    days=int(args.get("days", 1)),
                    people=int(args.get("people", 1)),
                    base_fare=float(args.get("base_fare", 0)),
                )
            elif tool_name == "convert_currency_to_vnd":
                required = ["amount", "currency"]
                missing = [k for k in required if k not in args]
                if missing:
                    return f"Lỗi: Thiếu tham số: {', '.join(missing)}."

                result = convert_currency_to_vnd(
                    amount=float(args.get("amount", 0)),
                    currency=str(args.get("currency", "USD")),
                )
            else:
                # This shouldn't happen because of pre-validation, but just in case
                return f"Lỗi: Tool '{tool_name}' không được hỗ trợ."
        except ValueError as ve:
            logger.log_event("TOOL_ERROR", {
                "tool_name": tool_name,
                "error_type": "value_error",
                "args": args,
                "error": str(ve)
            })
            return f"Lỗi: Tham số không hợp lệ: {str(ve)}"
        except Exception as exc:
            logger.log_event("TOOL_ERROR", {
                "tool_name": tool_name,
                "error_type": "execution_error",
                "args": args,
                "error": str(exc)
            })
            return f"Lỗi: Thực thi tool thất bại: {str(exc)}"

        logger.log_event("TOOL_CALL_SUCCESS", {
            "tool_name": tool_name,
            "args": args,
            "result_preview": self._json_readable_preview(result, 200)
        })
        return result
