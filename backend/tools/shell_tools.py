"""Shell/command execution tools for Athena."""

import subprocess
from typing import Any, Dict, List

from loguru import logger

from backend.tools.registry import registry

# Allowed commands for security
ALLOWED_COMMANDS = {
    "ls", "cat", "head", "tail", "wc", "grep", "find", "whoami",
    "uname", "df", "free", "top", "htop", "ps", " uptime",
    "du", "date", "cal", "uptime", "which", "whereis",
    "systemctl", "journalctl", "dmesg",
    "docker", "docker-compose", "podman",
    "apt", "apt-get", "pacman", "yum", "dnf", "snap", "flatpak",
    "git", "python", "pip", "node", "npm",
    "curl", "wget", "ping", "netstat", "ss", "ip",
}


def execute_command(command: str, timeout: int = 60) -> Dict[str, Any]:
    """Execute a shell command and return the output."""
    # Security: parse and check command
    try:
        parts = command.strip().split()
        if not parts:
            return {"error": "Empty command"}

        cmd = parts[0]

        # Check if command is allowed
        if cmd not in ALLOWED_COMMANDS:
            return {
                "error": f"Command '{cmd}' is not allowed. Safe commands: {', '.join(sorted(ALLOWED_COMMANDS))}"
            }

        logger.info(f"Executing command: {command}")

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        output = {
            "command": command,
            "return_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip() if result.stderr else None,
        }

        if result.returncode == 0:
            logger.success(f"Command executed successfully: {command}")
        else:
            logger.warning(f"Command failed with code {result.returncode}: {command}")

        return output

    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout} seconds"}
    except Exception as e:
        return {"error": f"Command execution failed: {str(e)}"}


def install_package(package: str, distro: str = "auto") -> Dict[str, Any]:
    """Install a package using the system package manager."""
    # Determine package manager
    managers = {
        "apt": ["apt", "install", "-y"],
        "apt-get": ["apt-get", "install", "-y"],
        "pacman": ["pacman", "-S", "--noconfirm"],
        "yum": ["yum", "install", "-y"],
        "dnf": ["dnf", "install", "-y"],
        "snap": ["snap", "install"],
    }

    if distro == "auto":
        # Try apt first (Ubuntu/Debian)
        check, _, _ = subprocess.run(
            ["which", "apt"], capture_output=True, text=True
        ).returncode, None, None
        if check == 0:
            distro = "apt"
        else:
            distro = "apt"  # fallback

    manager = managers.get(distro)
    if not manager:
        return {"error": f"Unsupported package manager: {distro}"}

    cmd = " ".join(manager + [package])
    return execute_command(cmd)


def uninstall_package(package: str, distro: str = "auto") -> Dict[str, Any]:
    """Uninstall a package using the system package manager."""
    managers = {
        "apt": ["apt", "remove", "-y"],
        "apt-get": ["apt-get", "remove", "-y"],
        "pacman": ["pacman", "-Rsc", "--noconfirm"],
        "yum": ["yum", "remove", "-y"],
        "dnf": ["dnf", "remove", "-y"],
    }

    if distro == "auto":
        check = subprocess.run(
            ["which", "apt"], capture_output=True, text=True
        ).returncode
        distro = "apt" if check == 0 else "apt"

    manager = managers.get(distro)
    if not manager:
        return {"error": f"Unsupported package manager: {distro}"}

    cmd = " ".join(manager + [package])
    return execute_command(cmd)


def docker_command(action: str, image: str = "", container_name: str = "", compose_file: str = "") -> Dict[str, Any]:
    """Execute Docker commands (pull, run, stop, start, etc.)."""
    docker_actions = {
        "pull": lambda: f"docker pull {image}",
        "run": lambda: f"docker run -d --name {container_name} {image}" if container_name else f"docker run -d {image}",
        "stop": lambda: f"docker stop {container_name}",
        "start": lambda: f"docker start {container_name}",
        "rm": lambda: f"docker rm {container_name}",
        "ps": lambda: "docker ps -a",
        "logs": lambda: f"docker logs {container_name}",
        "images": lambda: "docker images",
        "compose-up": lambda: f"docker-compose -f {compose_file} up -d" if compose_file else "docker-compose up -d",
        "compose-down": lambda: f"docker-compose -f {compose_file} down" if compose_file else "docker-compose down",
    }

    cmd_fn = docker_actions.get(action)
    if not cmd_fn:
        return {"error": f"Unknown Docker action: {action}. Available: {list(docker_actions.keys())}"}

    cmd = cmd_fn()
    return execute_command(cmd)


def start_application(app_name: str) -> Dict[str, Any]:
    """Start a desktop application or service."""
    # Try multiple approaches
    checks = [
        f"which {app_name}",
        f"systemctl start {app_name}",
        f"nohup {app_name} &",
    ]

    for cmd in checks:
        result = execute_command(cmd)
        if result.get("return_code") == 0 or "No such file" not in str(result.get("stderr", "")):
            return {
                "application": app_name,
                "status": "started",
                "command_used": cmd,
                "output": result.get("stdout"),
            }

    return {
        "application": app_name,
        "status": "failed",
        "error": "Could not start application. Check if it's installed."
    }


def stop_application(app_name: str) -> Dict[str, Any]:
    """Stop a running application or service."""
    checks = [
        f"pkill {app_name}",
        f"systemctl stop {app_name}",
        f"killall {app_name}",
    ]

    for cmd in checks:
        result = execute_command(cmd)
        if result.get("return_code") == 0:
            return {
                "application": app_name,
                "status": "stopped",
                "command_used": cmd,
            }

    return {
        "application": app_name,
        "status": "failed",
        "error": "Could not stop application."
    }


# Register tools
registry.register(
    name="execute_command",
    description="Execute a shell command and return output. Use for system operations, file operations, and general command execution.",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The shell command to execute"},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default: 60)"},
        },
        "required": ["command"],
    },
    handler=execute_command,
)

registry.register(
    name="install_package",
    description="Install a software package using the system package manager (apt, pacman, etc.)",
    parameters={
        "type": "object",
        "properties": {
            "package": {"type": "string", "description": "Name of the package to install"},
            "distro": {"type": "string", "description": "Package manager to use (auto-detect by default)"},
        },
        "required": ["package"],
    },
    handler=install_package,
)

registry.register(
    name="uninstall_package",
    description="Uninstall a software package using the system package manager",
    parameters={
        "type": "object",
        "properties": {
            "package": {"type": "string", "description": "Name of the package to uninstall"},
            "distro": {"type": "string", "description": "Package manager to use (auto-detect by default)"},
        },
        "required": ["package"],
    },
    handler=uninstall_package,
)

registry.register(
    name="docker_command",
    description="Execute Docker commands: pull, run, stop, start, rm, ps, logs, images, compose-up, compose-down",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["pull", "run", "stop", "start", "rm", "ps", "logs", "images", "compose-up", "compose-down"], "description": "Docker action to perform"},
            "image": {"type": "string", "description": "Docker image name (for pull, run)"},
            "container_name": {"type": "string", "description": "Container name (for run, stop, start, rm, logs)"},
            "compose_file": {"type": "string", "description": "Docker Compose file path (for compose-up, compose-down)"},
        },
        "required": ["action"],
    },
    handler=docker_command,
)

registry.register(
    name="start_application",
    description="Start a desktop application or background service",
    parameters={
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Name of the application to start"},
        },
        "required": ["app_name"],
    },
    handler=start_application,
)

registry.register(
    name="stop_application",
    description="Stop a running desktop application or service",
    parameters={
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Name of the application to stop"},
        },
        "required": ["app_name"],
    },
    handler=stop_application,
)
