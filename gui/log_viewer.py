from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PyQt6.QtGui import QTextCharFormat, QColor, QFont
from PyQt6.QtCore import Qt
from .styles import Styles

class LogViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create text edit for log display
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Ubuntu", 10))
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #121212;
                color: #FFFFFF;
                border: none;
            }
        """)
        layout.addWidget(self.text_edit)
        
        # Set up text formats for different message types
        self.formats = {
            'ERROR': self.create_format('#FF0000'),  # Red
            'WARNING': self.create_format('#FFA500'),  # Orange
            'SUCCESS': self.create_format('#00FF00'),  # Green
            'INFO': self.create_format('#FFFFFF'),  # White
            'DATA': self.create_format('#47A8E5'),  # Light blue
        }
        
    def create_format(self, color):
        """Create a text format with the specified color"""
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        fmt.setFont(QFont("Ubuntu", 10))
        return fmt
        
    def append_message(self, message, msg_type='INFO'):
        """Append a message to the log with the specified type
        
        Args:
            message (str): The message to append
            msg_type (str): Message type ('ERROR', 'WARNING', 'SUCCESS', 'INFO', 'DATA')
        """
        # Only process Arduino serial data
        if msg_type == 'ARDUINO':
            cursor = self.text_edit.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(f"{message}\n", self.formats.get('DATA', self.formats['INFO']))
            self.text_edit.setTextCursor(cursor)
            self.text_edit.ensureCursorVisible()
            
    def clear(self):
        """Clear the log display"""
        self.text_edit.clear()
