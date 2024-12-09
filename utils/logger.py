import logging
import sys
import os
from datetime import datetime

def setup_logging():
    """Set up logging with handlers added only once"""
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Create a formatter that includes timestamp and level
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Set up GUI logger
    gui_logger = logging.getLogger('gui')
    if not gui_logger.handlers:  # Only add handlers if none exist
        # Create file handler
        log_file = os.path.join(logs_dir, f'gui_{datetime.now().strftime("%Y%m%d")}.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.DEBUG)
        
        # Add handlers
        gui_logger.addHandler(file_handler)
        gui_logger.addHandler(console_handler)
        gui_logger.setLevel(logging.DEBUG)

    # Set up hardware logger
    hardware_logger = logging.getLogger('hardware')
    if not hardware_logger.handlers:  # Only add handlers if none exist
        hardware_logger.addHandler(file_handler)
        hardware_logger.addHandler(console_handler)
        hardware_logger.setLevel(logging.DEBUG)

    # Configure root logger
    root_logger = logging.getLogger()
    if not root_logger.handlers:  # Only add handlers if none exist
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    # Prevent other loggers from being too verbose
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)

    return gui_logger, hardware_logger

# Initialize loggers
gui_logger, hardware_logger = setup_logging()

def log_hardware_event(component, level, message, **kwargs):
    """Log a hardware-related event with additional context"""
    level_num = getattr(logging, level.upper())
    hardware_logger.log(level_num, f"[{component}] {message}")
    if kwargs:
        hardware_logger.log(level_num, f"Context: {kwargs}") 