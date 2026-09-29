"""Logging configuration for the Celebrity Wiki Agent.

This module sets up structured logging to both console and file.
Log files are written to the logs/ directory.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

from app.config import LOGS_DIR


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Set up logging for the application.
    
    Creates a logger that writes to both console and a timestamped log file.
    
    Args:
        level: The logging level (default: INFO)
        
    Returns:
        The configured root logger
    """
    # Ensure logs directory exists
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create timestamped log filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"agent_{timestamp}.log"
    
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # Log everything to file
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger("celebrity_agent")
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Also capture langchain logs
    langchain_logger = logging.getLogger("langchain")
    langchain_logger.setLevel(logging.WARNING)
    
    root_logger.info(f"Logging initialized. Log file: {log_file}")
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger with the given name.
    
    Args:
        name: The name for the logger (e.g., 'llm', 'tools', 'graph')
        
    Returns:
        A logger instance
    """
    return logging.getLogger(f"celebrity_agent.{name}")
