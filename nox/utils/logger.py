# nox/utils/logger.py
"""
Central logger for NOX Core.
Safe for multiple imports / reloads.
"""

import logging
import os
from typing import Optional

# Module-level logger instance
logger = logging.getLogger("nox.core")

def setup_logger(level: Optional[str] = None) -> None:
    """
    Configure the logger (idempotent - can be called multiple times safely).
    """
    if logger.handlers:
        return  # already configured

    # Determine log level
    level_name = level or os.getenv("NOX_LOG_LEVEL", "INFO" if os.getenv("NOX_ENV", "development").lower() != "production" else "WARNING")
    try:
        logger.setLevel(level_name.upper())
    except ValueError:
        logger.setLevel(logging.INFO)
        logger.warning(f"Invalid log level '{level_name}' - falling back to INFO")

    # Handler & formatter
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    logger.info(f"Logger initialized at level {logger.level}")

# Auto-configure when module is imported (optional but convenient)
setup_logger()