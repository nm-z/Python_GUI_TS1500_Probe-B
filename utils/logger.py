import logging
import os
from datetime import datetime
from PyQt6.QtWidgets import QTextEdit, QScrollBar
from PyQt6.QtCore import Qt

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output"""
    
    COLORS = {
        'DEBUG': '\033[0;36m',     # Cyan
        'INFO': '\033[0;32m',      # Green
        'WARNING': '\033[0;33m',   # Yellow
        'ERROR': '\033[0;31m',     # Red
        'CRITICAL': '\033[0;35m',  # Magenta
        'RESET': '\033[0m'         # Reset
    }
    
    def format(self, record):
        # Add color to the level name
        record.levelname = f"{self.COLORS.get(record.levelname, self.COLORS['RESET'])}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

def setup_logger(name, log_file=None, level=logging.INFO):
    """Set up logger with file and console handlers
    
    Args:
        name (str): Logger name
        log_file (str, optional): Path to log file
        level: Logging level
        
    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatters
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if log file specified
    if log_file:
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

# Create log directory
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Create application loggers
timestamp = datetime.now().strftime('%Y%m%d')
gui_logger = setup_logger("gui", os.path.join(log_dir, f"gui_{timestamp}.log"))
hardware_logger = setup_logger("hardware", os.path.join(log_dir, f"hardware_{timestamp}.log"))

# Set logging levels for external libraries
logging.getLogger('PIL').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)

def log_test_results(results, run_number):
    """Log test results to a results file
    
    Args:
        results (dict): Test results data
        run_number (int): Test run number
    """
    results_dir = "data/results"
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"results_{timestamp}_run{run_number}.txt")
    
    try:
        with open(results_file, 'w') as f:
            f.write(f"Test Results - Run {run_number}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Total Execution Time: {results['execution_time']}\n")
            f.write(f"Configuration:\n")
            f.write(f"  Tilt Increment: {results['config']['tilt_increment']}°\n")
            f.write(f"  Minimum Tilt: {results['config']['min_tilt']}°\n")
            f.write(f"  Maximum Tilt: {results['config']['max_tilt']}°\n")
            f.write(f"  Oil Level Time: {results['config']['oil_level_time']}s\n")
            f.write(f"\nData Files:\n")
            f.write(f"  VNA Data: {results['data_files']['vna']}\n")
            f.write(f"  Temperature Data: {results['data_files']['temperature']}\n")
            f.write(f"\nAngles Tested:\n")
            for angle in results['angles_tested']:
                f.write(f"  {angle}°\n")
                
        gui_logger.info(f"Test results saved to {results_file}")
        return results_file
        
    except Exception as e:
        gui_logger.error(f"Error saving test results: {str(e)}")
        return None

def log_hardware_event(component, level, message, **kwargs):
    """Log a hardware-related event with additional context
    
    Args:
        component (str): Hardware component name (e.g., 'arduino', 'vna')
        level (str): Log level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        message (str): Log message
        **kwargs: Additional context (command, response, parameters)
    """
    level_num = getattr(logging, level.upper())
    
    # Format the message with context if provided
    if kwargs:
        context_str = ', '.join(f"{k}={v}" for k, v in kwargs.items())
        message = f"{message} [{context_str}]"
    
    hardware_logger.log(level_num, f"[{component}] {message}")

class QTextEditLogger(logging.Handler):
    """Custom logging handler that writes to a QTextEdit widget"""
    
    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.widget.setReadOnly(True)
        
        # Define colors for different log levels
        self.colors = {
            logging.DEBUG: '#A0A0A0',    # Gray
            logging.INFO: '#FFFFFF',     # White
            logging.WARNING: '#FFA500',  # Orange
            logging.ERROR: '#FF0000',    # Red
            logging.CRITICAL: '#FF00FF'  # Magenta
        }
        
    def emit(self, record):
        """Write the log message to the QTextEdit with appropriate color"""
        msg = self.format(record)
        color = self.colors.get(record.levelno, '#FFFFFF')
        
        # Format message with HTML color
        html_msg = f'<span style="color: {color};">{msg}</span><br>'
        
        # Append message to widget
        self.widget.append(html_msg)
        
        # Auto-scroll to bottom
        scrollbar = self.widget.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

# Make QTextEditLogger available at module level
__all__ = ['ColoredFormatter', 'setup_logger', 'log_test_results', 'log_hardware_event', 'QTextEditLogger', 'gui_logger', 'hardware_logger']