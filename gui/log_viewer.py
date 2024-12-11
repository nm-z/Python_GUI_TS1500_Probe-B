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
                color: #FFFFFF;  /* Pure white text */
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
        self.formats['INFO'].setForeground(QColor('#FFFFFF'))  # Pure white for info
        self.formats['ERROR'].setForeground(QColor('#FF4444'))  # Bright red for errors
        self.formats['WARNING'].setForeground(QColor('#FFAA00'))  # Bright orange for warnings
        self.formats['SUCCESS'].setForeground(QColor('#44FF44'))  # Bright green for success
        self.formats['EXECUTION_TIME'].setForeground(QColor('#47A8E5'))  # Light blue for execution time
        self.formats['CONNECTION'].setForeground(QColor('#47A8E5'))  # Light blue for connection status
        
    @pyqtSlot(str, str)
    def append_message(self, message, level='INFO'):
        """Append a message to the log with appropriate formatting
        
        Args:
            message (str): Message to append
            level (str): Message level (INFO, ERROR, WARNING, SUCCESS)
        """
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Check if message has timestamp format (YYYY-MM-DD HH:MM:SS)
        if len(message) > 19 and message[4] == '-' and message[7] == '-' and message[10] == ' ' and message[13] == ':' and message[16] == ':':
            # Format timestamp with light gray color
            timestamp = QTextCharFormat()
            timestamp.setForeground(QColor('#CCCCCC'))  # Light gray for better visibility
            cursor.insertText(f"{message[:19]} - ", timestamp)
            message_text = message[21:]
        else:
            message_text = message
            
        # Get appropriate format for message type
        format = self.formats.get(level, self.formats['INFO'])
        
        # Insert message with format
        cursor.insertText(f"{message_text}\n", format)
        
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
