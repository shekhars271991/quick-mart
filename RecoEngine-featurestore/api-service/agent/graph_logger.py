"""
Dedicated logging configuration for LangGraph workflows.

Separates graph logs from main application logs for easier debugging.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

# Create logs directory
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Log file paths
CHURN_LOG_FILE = LOGS_DIR / "churn_graph.log"
RECO_LOG_FILE = LOGS_DIR / "recommendations_graph.log"


def setup_graph_loggers():
    """Setup dedicated loggers for each graph with file handlers."""
    
    # Common formatter with timestamp and detailed info
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # ============ Churn Prediction Graph Logger ============
    churn_logger = logging.getLogger("graph.churn")
    churn_logger.setLevel(logging.DEBUG)
    churn_logger.propagate = False  # Don't propagate to root logger
    
    # Clear existing handlers
    churn_logger.handlers.clear()
    
    # File handler for churn graph
    churn_file_handler = logging.FileHandler(CHURN_LOG_FILE, mode='a')
    churn_file_handler.setLevel(logging.DEBUG)
    churn_file_handler.setFormatter(formatter)
    churn_logger.addHandler(churn_file_handler)
    
    # Also log to console with a prefix
    churn_console_handler = logging.StreamHandler()
    churn_console_handler.setLevel(logging.INFO)
    churn_console_handler.setFormatter(logging.Formatter(
        '🔮 CHURN | %(message)s'
    ))
    churn_logger.addHandler(churn_console_handler)
    
    # ============ Recommendations Graph Logger ============
    reco_logger = logging.getLogger("graph.reco")
    reco_logger.setLevel(logging.DEBUG)
    reco_logger.propagate = False  # Don't propagate to root logger
    
    # Clear existing handlers
    reco_logger.handlers.clear()
    
    # File handler for recommendations graph
    reco_file_handler = logging.FileHandler(RECO_LOG_FILE, mode='a')
    reco_file_handler.setLevel(logging.DEBUG)
    reco_file_handler.setFormatter(formatter)
    reco_logger.addHandler(reco_file_handler)
    
    # Also log to console with a prefix
    reco_console_handler = logging.StreamHandler()
    reco_console_handler.setLevel(logging.INFO)
    reco_console_handler.setFormatter(logging.Formatter(
        '🎯 RECO  | %(message)s'
    ))
    reco_logger.addHandler(reco_console_handler)
    
    return churn_logger, reco_logger


def get_churn_logger() -> logging.Logger:
    """Get the churn prediction graph logger."""
    return logging.getLogger("graph.churn")


def get_reco_logger() -> logging.Logger:
    """Get the recommendations graph logger."""
    return logging.getLogger("graph.reco")


def log_graph_start(logger: logging.Logger, graph_name: str, user_id: str, **kwargs):
    """Log the start of a graph execution with clear separator."""
    separator = "=" * 60
    logger.info(separator)
    logger.info(f"▶ START: {graph_name} for user {user_id}")
    if kwargs:
        for key, value in kwargs.items():
            logger.info(f"  {key}: {value}")
    logger.info(separator)


def log_graph_end(logger: logging.Logger, graph_name: str, user_id: str, success: bool = True, **kwargs):
    """Log the end of a graph execution with clear separator."""
    separator = "=" * 60
    status = "✅ SUCCESS" if success else "❌ FAILED"
    logger.info(separator)
    logger.info(f"◼ END: {graph_name} for user {user_id} - {status}")
    if kwargs:
        for key, value in kwargs.items():
            logger.info(f"  {key}: {value}")
    logger.info(separator)
    logger.info("")  # Empty line for readability


def log_node(logger: logging.Logger, node_name: str, message: str):
    """Log a node execution step."""
    logger.info(f"[{node_name}] {message}")


def log_node_detail(logger: logging.Logger, node_name: str, message: str):
    """Log detailed node info (DEBUG level - file only)."""
    logger.debug(f"[{node_name}] {message}")


# Initialize loggers on module import
setup_graph_loggers()

