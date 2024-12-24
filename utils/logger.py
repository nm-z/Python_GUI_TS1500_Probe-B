import logging
import os
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QMetaObject, Qt, Q_ARG
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QTextCursor
import colorama
from colorama import Fore, Style
import traceback

class QTextEditLogger(logging.Handler):
    """Custom logging handler that writes to a QTextEdit widget"""
    
    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.widget.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: monospace;
            }
        """)
        self.widget.document().setMaximumBlockCount(1000)  # Limit number of lines
        
    def emit(self, record):
        try:
            msg = self.format(record)
            color = self._get_color_for_level(record.levelno)
            
            # Format with HTML for color
            formatted_msg = f'<div style="color: {color}">{msg}</div>'
            
            # Always use invokeMethod for thread safety
            QMetaObject.invokeMethod(self.widget, 
                                   "append",
                                   Qt.ConnectionType.QueuedConnection,
                                   Q_ARG(str, formatted_msg))
            
            # Move cursor to end
            cursor = self.widget.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.widget.setTextCursor(cursor)
            
        except Exception as e:
            print(f"Error in log handler: {str(e)}")
            
    def _get_color_for_level(self, level):
        """Get color for log level"""
        if level >= logging.ERROR:
            return "#ff0000"  # Red for errors
        elif level >= logging.WARNING:
            return "#ffa500"  # Orange for warnings
        elif level >= logging.INFO:
            return "#00ff00"  # Green for info
        return "#808080"  # Gray for debug

def setup_logger(name, log_dir='logs'):
    """Set up a logger with file and console handlers"""
    try:
        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        
        # Remove any existing handlers
        logger.handlers = []
        
        # Create logs directory if it doesn't exist
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Create file handler
        today = datetime.now().strftime('%Y%m%d')
        log_file = os.path.join(log_dir, f'{name}_{today}.log')
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)  # Changed to DEBUG to show all messages
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Add formatter to handlers
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
        
    except Exception as e:
        print(f"Error setting up logger: {str(e)}")
        return None

def log_hardware_event(logger, component, level, message, **kwargs):
    """Log a hardware event with additional context
    
    Args:
        logger (logging.Logger): Logger instance to use
        component (str): Hardware component (e.g., 'arduino', 'vna')
        level (str): Log level ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        message (str): Main log message
        **kwargs: Additional context to include in log
    """
    try:
        # Format additional context
        context = ', '.join(f"{k}={v}" for k, v in kwargs.items())
        full_message = f"{message} - {context}" if context else message
        
        # Get logging level
        log_level = getattr(logging, level.upper())
        
        # Log message
        logger.log(log_level, f"[{component}] {full_message}")
        
    except Exception as e:
        print(f"Error logging hardware event: {str(e)}")

# Set up GUI logger
gui_logger = setup_logger('gui')

class ColoredFormatter(logging.Formatter):
    """Custom formatter for colored console output"""
    
    COLORS = {
        logging.DEBUG: Fore.WHITE,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT
    }
    
    def format(self, record):
        # Add color to the level name
        color = self.COLORS.get(record.levelno, Fore.WHITE)
        record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
        
        # Add color to the message based on level
        record.msg = f"{color}{record.msg}{Style.RESET_ALL}"
        
        return super().format(record)

def setup_cli_logger(name):
    """Set up a logger for CLI mode"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers
    logger.handlers = []
    
    # Create console handler with color formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)  # Changed to DEBUG to show all messages
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger