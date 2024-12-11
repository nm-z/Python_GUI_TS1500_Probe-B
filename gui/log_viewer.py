from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QScrollBar
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor
from .styles import Styles

class LogViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Initialize the log viewer UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create text edit for log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(Styles.FONT)
        self.log_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Styles.COLORS['background']};
                color: {Styles.COLORS['foreground']};
                border: none;
                font-family: 'Ubuntu';
                font-weight: bold;
            }}
        """)
        
        layout.addWidget(self.log_display)
        
        # Create text formats for different message types
        self.formats = {
            'INFO': QTextCharFormat(),
            'ERROR': QTextCharFormat(),
            'WARNING': QTextCharFormat(),
            'SUCCESS': QTextCharFormat(),
            'EXECUTION_TIME': QTextCharFormat(),
            'CONNECTION': QTextCharFormat()
        }
        
        # Set colors for different message types
        self.formats['INFO'].setForeground(QColor(Styles.COLORS['foreground']))
        self.formats['ERROR'].setForeground(QColor(Styles.COLORS['error']))
        self.formats['WARNING'].setForeground(QColor(Styles.COLORS['warning']))
        self.formats['SUCCESS'].setForeground(QColor(Styles.COLORS['success']))
        self.formats['EXECUTION_TIME'].setForeground(QColor(Styles.COLORS['accent']))
        self.formats['CONNECTION'].setForeground(QColor(Styles.COLORS['divider']))
        
    @pyqtSlot(str, str)
    def append_message(self, message, level='INFO'):
        """Append a message to the log with appropriate formatting
        
        Args:
            message (str): Message to append
            level (str): Message level (INFO, ERROR, WARNING, SUCCESS)
        """
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Format timestamp
        timestamp = QTextCharFormat()
        timestamp.setForeground(QColor(Styles.COLORS['border']))
        cursor.insertText(f"{message[:19]} - ", timestamp)
        
        # Get appropriate format for message type
        format = self.formats.get(level, self.formats['INFO'])
        
        # Insert message with format
        cursor.insertText(f"{message[21:]}\n", format)
        
        # Ensure latest message is visible
        self.log_display.setTextCursor(cursor)
        self.log_display.ensureCursorVisible()
        
    def append_execution_time(self, time_str):
        """Append execution time message with special formatting
        
        Args:
            time_str (str): Execution time string
        """
        self.append_message(f"Total Execution Time: {time_str}", 'EXECUTION_TIME')
        
    def append_connection_status(self, device, status):
        """Append connection status message with special formatting
        
        Args:
            device (str): Device name
            status (bool): Connection status
        """
        status_str = "Connected" if status else "Not Connected"
        self.append_message(f"{device.upper()} {status_str}", 'CONNECTION')
        
    def append_data_saved(self, filepath):
        """Append data saved confirmation with special formatting
        
        Args:
            filepath (str): Path where data was saved
        """
        self.append_message(f"Data saved to: {filepath}", 'SUCCESS')
