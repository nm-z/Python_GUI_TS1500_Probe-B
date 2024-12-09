from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QGroupBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor
from .styles import Styles

class LogViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Initialize the log viewer UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Styles.MARGINS, Styles.MARGINS, 
                                Styles.MARGINS, Styles.MARGINS)
        layout.setSpacing(Styles.SPACING)

        # Log Group
        log_group = QGroupBox("System Log")
        log_group.setFont(Styles.HEADER_FONT)
        log_layout = QVBoxLayout()
        log_layout.setContentsMargins(Styles.MARGINS, Styles.MARGINS * 2, 
                                   Styles.MARGINS, Styles.MARGINS)
        log_layout.setSpacing(Styles.SPACING)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(Styles.SMALL_FONT)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Styles.COLORS['background_alt']};
                color: {Styles.COLORS['foreground']};
                border: 1px solid {Styles.COLORS['border']};
                border-radius: 2px;
            }}
        """)

        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

    def append_log(self, message, level="INFO"):
        """Append a message to the log with color based on level"""
        color = {
            "ERROR": Styles.COLORS['error'],
            "WARNING": Styles.COLORS['warning'],
            "SUCCESS": Styles.COLORS['success'],
            "INFO": Styles.COLORS['foreground']
        }.get(level.upper(), Styles.COLORS['foreground'])

        self.log_text.moveCursor(QTextCursor.End)
        self.log_text.insertHtml(
            f'<span style="color: {color};">[{level.upper()}] {message}</span><br>'
        )
        self.log_text.moveCursor(QTextCursor.End)

    def clear_log(self):
        """Clear the log text area"""
        self.log_text.clear()
