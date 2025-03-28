#!/usr/bin/env python3
"""
Logger Utility

This module provides a centralized logging configuration.
"""

import logging
import os
import sys
from datetime import datetime

# ANSI color codes for colored terminal output
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output for terminal."""
    
    COLORS = {
        logging.DEBUG: Colors.BLUE,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.PURPLE
    }
    
    def format(self, record):
        if hasattr(sys, 'ps1'):  # Check if running in interactive mode
            level_color = self.COLORS.get(record.levelno, Colors.RESET)
            record.levelname = f"{level_color}{record.levelname}{Colors.RESET}"
            record.msg = f"{level_color}{record.msg}{Colors.RESET}"
        return super().format(record)

def setup_logger(name=None, log_file=None, level=logging.INFO, console=True):
    """
    Set up a logger with file and console handlers.
    
    Args:
        name: Logger name (or root logger if None)
        log_file: Path to log file (no file logging if None)
        level: Logging level
        console: Whether to log to console
        
    Returns:
        Configured logger
    """
    # Get or create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear any existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Create formatters
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_formatter = ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Add file handler if log_file is specified
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Add console handler if console is True
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    return logger

def get_default_log_file():
    """Generate a default log file name based on current date/time."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logs_dir = "logs"
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    return os.path.join(logs_dir, f"thermal_control_{timestamp}.log")