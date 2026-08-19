"""System monitoring tools for Athena."""

import os
import platform
import subprocess
from typing import Any, Dict, List

from loguru import logger

from backend.tools.registry import registry


def _run_cmd(cmd: List[str], timeout: int = 10) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def get_system_info() -> Dict[str, Any]:
    """Get basic system information."""
    return {
        "hostname": platform.node(),
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "user": os.getenv("USER", "unknown"),
    }


def get_disk_usage() -> Dict[str, Any]:
    """Get disk usage statistics."""
    try:
        result = subprocess.run(
            ["df", "-h"],
            capture_output=True,
            text=True,
            check=True,
        )
        return {"output": result.stdout}
    except Exception as e:
        return {"error": str(e)}


def get_memory_usage() -> Dict[str, Any]:
    """Get memory usage statistics."""
    try:
        result = subprocess.run(
            ["free", "-h"],
            capture_output=True,
            text=True,
            check=True,
        )
        return {"output": result.stdout}
    except Exception as e:
        return {"error": str(e)}


def get_cpu_load() -> Dict[str, Any]:
    """Get CPU load averages."""
    try:
        loads = os.getloadavg()
        return {
            "load_1min": loads[0],
            "load_5min": loads[1],
            "load_15min": loads[2],
            "cpu_count": os.cpu_count(),
        }
    except Exception as e:
        return {"error": str(e)}


def list_processes() -> Dict[str, Any]:
    """List running processes."""
    try:
        result = subprocess.run(
            ["ps", "aux", "--sort=-%mem"],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = result.stdout.split("\n")
        # Return header + top 20 processes
        return {"output": "\n".join(lines[:21])}
    except Exception as e:
        return {"error": str(e)}


def search_files(path: str = "/", pattern: str = "", max_results: int = 20) -> Dict[str, Any]:
    """Search for files by name pattern."""
    try:
        cmd = ["find", path, "-name", f"*{pattern}*", "-type f", "-maxdepth", "3"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        files = [f for f in result.stdout.split("\n") if f.strip()][:max_results]
        return {"files": files, "count": len(files)}
    except Exception as e:
        return {"error": str(e)}


def check_service(service_name: str) -> Dict[str, Any]:
    """Check if a systemd service is running."""
    try:
        rc, stdout, stderr = _run_cmd(["systemctl", "is-active", service_name])
        return {
            "service": service_name,
            "status": stdout.strip() if rc == 0 else "inactive",
            "error": stderr if rc != 0 else None,
        }
    except Exception as e:
        return {"error": str(e)}


# Register tools
registry.register(
    name="get_system_info",
    description="Get basic system information including OS, hostname, CPU count",
    parameters={
        "type": "object",
        "properties": {},
    },
    handler=get_system_info,
)

registry.register(
    name="get_disk_usage",
    description="Get disk usage statistics for all mounted filesystems",
    parameters={
        "type": "object",
        "properties": {},
    },
    handler=get_disk_usage,
)

registry.register(
    name="get_memory_usage",
    description="Get RAM and swap memory usage statistics",
    parameters={
        "type": "object",
        "properties": {},
    },
    handler=get_memory_usage,
)

registry.register(
    name="get_cpu_load",
    description="Get CPU load averages for 1, 5, and 15 minutes",
    parameters={
        "type": "object",
        "properties": {},
    },
    handler=get_cpu_load,
)

registry.register(
    name="list_processes",
    description="List top 20 running processes sorted by memory usage",
    parameters={
        "type": "object",
        "properties": {},
    },
    handler=list_processes,
)

registry.register(
    name="search_files",
    description="Search for files by name pattern in a directory",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory to search in (default: /)"},
            "pattern": {"type": "string", "description": "Filename pattern to search for"},
            "max_results": {"type": "integer", "description": "Maximum results to return (default: 20)"},
        },
        "required": ["pattern"],
    },
    handler=search_files,
)

registry.register(
    name="check_service",
    description="Check if a systemd service is active/running",
    parameters={
        "type": "object",
        "properties": {
            "service_name": {"type": "string", "description": "Name of the systemd service"},
        },
        "required": ["service_name"],
    },
    handler=check_service,
)
