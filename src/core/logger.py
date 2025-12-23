# src/core/logger.py
"""Logging configuration for the Banking RAG Agent."""

import logging
import logging.config
import os
import sys
from pathlib import Path
from typing import Optional

from config import settings


def setup_logging(log_file: Optional[str] = None, log_level: Optional[str] = None) -> None:
    """
    Configure logging for the application.

    Args:
        log_file: Path to the log file. If None, logs will be written to stderr.
        log_level: Logging level (e.g., 'DEBUG', 'INFO'). If None, uses the value from settings.
    """
    settings = get_settings()
    log_level = log_level or settings.LOG_LEVEL
    log_file = log_file or settings.LOG_FILE

    # Create log directory if it doesn't exist
    if log_file:
        log_path = Path(log_file)
        if not log_path.parent.exists():
            log_path.parent.mkdir(parents=True, exist_ok=True)

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": sys.stderr,
                "level": log_level,
            },
        },
        "loggers": {
            "": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": True,
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }

    # Add file handler if log_file is specified
    if log_file:
        log_config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "json" if settings.ENVIRONMENT == "production" else "default",
            "filename": log_file,
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "level": log_level,
            "encoding": "utf-8",
        }
        log_config["loggers"][""]["handlers"].append("file")

    logging.config.dictConfig(log_config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Name of the logger.

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)


# Initialize root logger when module is imported
setup_logging()
logger = get_logger(__name__)
