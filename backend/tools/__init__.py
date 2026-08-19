"""Athena AI - Personal Assistant Backend."""

from backend.tools.system_tools import registry as system_tools_registry
from backend.tools.shell_tools import registry as shell_tools_registry

# Tool registries are auto-populated on import
__all__ = ["system_tools_registry", "shell_tools_registry"]
