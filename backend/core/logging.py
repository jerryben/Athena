from pathlib import Path
from loguru import logger
import sys

# Create logs directory
Path("logs").mkdir(exist_ok=True)

# Remove default logger
logger.remove()

# Console logging
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
           "<level>{level: <8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
           "<level>{message}</level>",
)

# File logging
logger.add(
    "logs/athena.log",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    level="DEBUG",
)

__all__ = ["logger"]