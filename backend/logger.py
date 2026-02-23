import logging
import sys
import os
from datetime import datetime

def setup_logger(name="AML.BACKEND"):
    """Configures a standardized logger with timestamps and levels."""
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Set to DEBUG to capture everything, handlers can filter
    
    # Check if a handler already exists to avoid double logging
    if logger.handlers:
        return logger

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)  # Default console level
    
    # Create formatter: [2024-02-23 10:00:00] [INFO] [AML.BACKEND]: Message
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger

# Pre-defined loggers for different components
logger_main = setup_logger("AML.API")
logger_db = setup_logger("AML.DB")
logger_agents = setup_logger("AML.AGENTS")
