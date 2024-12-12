from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QTextCharFormat, QColor
from PyQt6.QtCore import Qt
from .styles import Styles

class LogViewer(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the log viewer UI"""
        self.setReadOnly(True)
        self.setStyleSheet(Styles.LOGGER_STYLE)
        self.setFont(Styles.FONT)
        
        # Define message colors
        self.colors = {
            'ERROR': QColor('#FF073A'),    # Red
            'WARNING': QColor('#FFA500'),   # Orange
            'SUCCESS': QColor('#0FFF50'),   # Green
            'INFO': QColor('white'),        # White
            'DEBUG': QColor('#808080')      # Gray
        }
        
    def append_message(self, message, level='INFO'):
        """Append a colored message to the log
        
        Args:
            message (str): Message to append
            level (str): Message level (ERROR, WARNING, SUCCESS, INFO, DEBUG)
        """
        # Create text format with color
        text_format = QTextCharFormat()
        text_format.setForeground(self.colors.get(level.upper(), QColor('white')))
        text_format.setFont(Styles.FONT)
        
        # Get current cursor
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        
        # Set the format and insert text
        cursor.setCharFormat(text_format)
        cursor.insertText(f"[{level.upper()}] {message}\n")
        
        # Scroll to bottom
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        
    def clear_log(self):
        """Clear all log messages"""
        self.clear()
        
    def update_theme(self, is_dark_mode):
        """Update logger colors based on theme"""
        if is_dark_mode:
            self.colors['INFO'] = QColor('white')
            self.setStyleSheet(Styles.LOGGER_STYLE)
        else:
            self.colors['INFO'] = QColor('black')
            self.setStyleSheet(f"""
                QTextEdit {{
                    background-color: white;
                    color: black;
                    border: 2px solid {Styles.PRIMARY};
                    border-radius: 5px;
                    padding: 5px;
                    {Styles.FONT_STYLE}
                }}
            """)
