"""LLM service with function calling support for Athena."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger
from openai import OpenAI

from backend.core.config import settings
from backend.tools.registry import registry

SYSTEM_PROMPT = Path("backend/prompts/system.md").read_text(encoding="utf-8")


class LLMService:
    def __init__(self):
        self.client = OpenAI(
            base_url=f"{settings.OLLAMA_URL}/v1",
            api_key="ollama",
        )
        self.model = settings.LLM_MODEL

    def generate(
        self,
        prompt: str,
        history: List[Dict] | None = None,
        context: str = "",
    ) -> Dict[str, Any]:
        """Generate a response, handling tool calls if needed."""
        if history is None:
            history = []

        # Build system prompt with memory context
        system_prompt = SYSTEM_PROMPT

        if context:
            system_prompt += "\n\nRelevant long-term memories:\n" + context

        # Build messages from history
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (only user/assistant messages, no tool messages)
        for msg in history:
            if msg.get("role") in ["user", "assistant"]:
                messages.append(msg)
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})

        logger.info(f"Using model: {self.model}")
        logger.info(f"History length: {len(history)}, Messages: {len(messages)}")

        # Get available tools
        tools = registry.get_tools()
        if tools:
            logger.info(f"Available tools: {[t['function']['name'] for t in tools]}")

        # Single-pass tool calling - call one tool, then respond
        tool_calls_result = []

        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.1,
            }

            if tools:
                kwargs["tools"] = tools

            logger.info(f"Calling LLM with {len(messages)} messages")
            response = self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]

            # Check for tool calls
            if choice.message.tool_calls:
                logger.info(f"Received {len(choice.message.tool_calls)} tool call(s)")
                
                # Process the FIRST tool call
                tc = choice.message.tool_calls[0]
                
                # Store tool call info
                tool_calls_result.append({
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                })
                
                # Execute the tool
                try:
                    args = json.loads(tc.function.arguments)
                    result = registry.execute(tc.function.name, args)
                    logger.info(f"Tool {tc.function.name} executed successfully")
                    
                    # Add tool result as new user message
                    messages.append({
                        "role": "user",
                        "content": f"[Tool result from {tc.function.name}]: {json.dumps(result, ensure_ascii=False)[:3000]}",
                    })
                    
                    # Now get final response without tools
                    final_kwargs = {
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.1,
                    }
                    final_response = self.client.chat.completions.create(**final_kwargs)
                    response_content = final_response.choices[0].message.content
                    logger.info(f"Final response received, length: {len(response_content or '')}")
                    
                    return {
                        "model": self.model,
                        "response": response_content or "",
                        "done": True,
                        "tool_calls": tool_calls_result,
                    }
                    
                except Exception as e:
                    logger.error(f"Tool execution error: {e}")
                    response_content = f"Error executing tool {tc.function.name}: {str(e)}"
                    return {
                        "model": self.model,
                        "response": response_content,
                        "done": True,
                        "tool_calls": tool_calls_result,
                    }

            # No tool calls, return direct response
            response_content = choice.message.content
            logger.info(f"Direct response received, length: {len(response_content or '')}")
            return {
                "model": self.model,
                "response": response_content or "",
                "done": True,
                "tool_calls": tool_calls_result,
            }

        except Exception as e:
            logger.exception(f"LLM error: {e}")
            return {
                "model": self.model,
                "response": f"LLM Error: {e}",
                "done": False,
                "tool_calls": tool_calls_result,
            }


llm_service = LLMService()
