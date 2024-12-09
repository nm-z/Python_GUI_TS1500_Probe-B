import logging
import sys
import os
from datetime import datetime

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Create a formatter that includes timestamp and level
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create file handler
log_file = os.path.join(logs_dir, f'gui_{datetime.now().strftime("%Y%m%d")}.log')
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

# Create console handler with a higher log level
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.DEBUG)  # Show all logs in console

# Create GUI logger
gui_logger = logging.getLogger('gui')
gui_logger.setLevel(logging.DEBUG)  # Capture all levels
gui_logger.addHandler(file_handler)
gui_logger.addHandler(console_handler)

# Create Hardware logger
hardware_logger = logging.getLogger('hardware')
hardware_logger.setLevel(logging.DEBUG)  # Capture all levels
hardware_logger.addHandler(file_handler)
hardware_logger.addHandler(console_handler)

# Also log to root logger for other modules
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

def log_hardware_event(component, level, message, **kwargs):
    """
    Log a hardware-related event with additional context.
    
    Args:
        component (str): Hardware component name (e.g., 'arduino', 'vna')
        level (str): Log level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        message (str): Log message
        **kwargs: Additional context (command, response, parameters)
    """
    level_num = getattr(logging, level.upper())
    hardware_logger.log(level_num, f"[{component}] {message}")
    if kwargs:
        hardware_logger.log(level_num, f"Context: {kwargs}")

# Ensure matplotlib and other verbose loggers don't spam
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('PIL').setLevel(logging.WARNING) 