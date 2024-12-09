from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QGroupBox
from PyQt6.QtCore import Qt
from .styles import Styles

class ControlPanel(QWidget):
    def __init__(self, connection_callback, start_test_callback, stop_test_callback):
        super().__init__()
        self.connection_callback = connection_callback
        self.start_test_callback = start_test_callback
        self.stop_test_callback = stop_test_callback
        self.init_ui()

    def init_ui(self):
        """Initialize the control panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Styles.MARGINS, Styles.MARGINS, 
                                Styles.MARGINS, Styles.MARGINS)
        layout.setSpacing(Styles.SPACING)

        # Connection Group
        connection_group = QGroupBox("Connection")
        connection_group.setFont(Styles.HEADER_FONT)
        connection_layout = QHBoxLayout()
        connection_layout.setContentsMargins(Styles.MARGINS, Styles.MARGINS * 2, 
                                           Styles.MARGINS, Styles.MARGINS)
        connection_layout.setSpacing(Styles.SPACING)

        # Port selection
        port_layout = QHBoxLayout()
        port_label = QLabel("Port:")
        port_label.setFont(Styles.BODY_FONT)
        self.port_combo = QComboBox()
        self.port_combo.setFont(Styles.BODY_FONT)
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_combo)

        # Refresh ports button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setFont(Styles.BODY_FONT)
        port_layout.addWidget(self.refresh_btn)

        # Add port layout to connection layout
        connection_layout.addLayout(port_layout)
        connection_group.setLayout(connection_layout)

        # Add connection group to main layout
        layout.addWidget(connection_group)

        # ... rest of the existing code remains the same ...
