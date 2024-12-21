from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor
from .styles import Styles

class LogViewer(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setStyleSheet(Styles.LOGGER_STYLE)
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)  # Prevent line wrapping
        
    def append_message(self, message):
        """Append a message to the log viewer
        
        Args:
            message (str): Message to append
        """
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.insertPlainText(message + '\n')
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.ensureCursorVisible()
