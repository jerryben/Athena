"""Tool registry for Athena's function calling."""

from loguru import logger
from typing import Any, Callable, Dict, List, Optional


class ToolRegistry:
    """Central registry for Athena's tools."""

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, description: str, parameters: dict, handler: Callable):
        """Register a tool with its schema and handler."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": handler,
        }
        logger.info(f"Tool registered: {name}")

    def get_tools(self) -> List[Dict[str, Any]]:
        """Return list of tool schemas for LLM function calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                }
            }
            for tool in self._tools.values()
        ]

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific tool by name."""
        return self._tools.get(name)

    def execute(self, name: str, arguments: dict) -> Any:
        """Execute a tool by name with given arguments."""
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"Tool not found: {name}"}

        try:
            logger.info(f"Executing tool: {name} with args: {arguments}")
            result = tool["handler"](**arguments)
            logger.success(f"Tool {name} executed successfully")
            return {"result": result}
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return {"error": str(e)}


# Global registry instance
registry = ToolRegistry()
