# utils/logging_setup.py
"""
Configure loguru for production use:
  - Coloured console output
  - Rotating file log (one per run)
  - Separate error log
"""

import sys
import os
from loguru import logger


def setup_logging(log_dir: str = "logs", debug: bool = False) -> None:
    os.makedirs(log_dir, exist_ok=True)

    # Remove default handler
    logger.remove()

    # Console — human readable
    level = "DEBUG" if debug else "INFO"
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> — <level>{message}</level>"
        ),
        colorize=True,
    )

    # Rotating file log
    logger.add(
        os.path.join(log_dir, "tina_{time:YYYY-MM-DD}.log"),
        rotation="00:00",       # new file each day
        retention="14 days",
        level="DEBUG",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} — {message}",
    )

    # Separate error log
    logger.add(
        os.path.join(log_dir, "tina_errors.log"),
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
    )

    logger.debug("Logging configured (debug={})", debug)
