from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QGroupBox
from PyQt6.QtCore import Qt
from .styles import Styles

class StatusIndicators(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Initialize the status indicators UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Styles.MARGINS, Styles.MARGINS, 
                                Styles.MARGINS, Styles.MARGINS)
        layout.setSpacing(Styles.SPACING)

        # Status Group
        status_group = QGroupBox("Status")
        status_group.setFont(Styles.HEADER_FONT)
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(Styles.MARGINS, Styles.MARGINS * 2, 
                                      Styles.MARGINS, Styles.MARGINS)
        status_layout.setSpacing(Styles.SPACING)

        # Connection status
        conn_layout = QHBoxLayout()
        conn_label = QLabel("Connection:")
        conn_label.setFont(Styles.BODY_FONT)
        self.conn_status = QLabel("Disconnected")
        self.conn_status.setFont(Styles.BODY_FONT)
        self.conn_status.setStyleSheet(f"color: {Styles.COLORS['error']}")
        conn_layout.addWidget(conn_label)
        conn_layout.addWidget(self.conn_status)
        conn_layout.addStretch()

        # Test progress
        progress_layout = QHBoxLayout()
        progress_label = QLabel("Progress:")
        progress_label.setFont(Styles.BODY_FONT)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setFont(Styles.SMALL_FONT)
        self.progress_bar.setStyleSheet(Styles.PROGRESS_STYLE)
        progress_layout.addWidget(progress_label)
        progress_layout.addWidget(self.progress_bar)

        # Current phase
        phase_layout = QHBoxLayout()
        phase_label = QLabel("Phase:")
        phase_label.setFont(Styles.BODY_FONT)
        self.phase_status = QLabel("Idle")
        self.phase_status.setFont(Styles.BODY_FONT)
        phase_layout.addWidget(phase_label)
        phase_layout.addWidget(self.phase_status)
        phase_layout.addStretch()

        # Add all layouts to status group
        status_layout.addLayout(conn_layout)
        status_layout.addLayout(progress_layout)
        status_layout.addLayout(phase_layout)
        status_group.setLayout(status_layout)

        # Add status group to main layout
        layout.addWidget(status_group)

    def update_connection_status(self, connected):
        """Update the connection status indicator"""
        if connected:
            self.conn_status.setText("Connected")
            self.conn_status.setStyleSheet(f"color: {Styles.COLORS['success']}")
        else:
            self.conn_status.setText("Disconnected")
            self.conn_status.setStyleSheet(f"color: {Styles.COLORS['error']}")

    def update_test_progress(self, progress, phase=None):
        """Update the test progress indicators"""
        self.progress_bar.setValue(int(progress))
        if phase:
            self.phase_status.setText(phase)

    def update_status(self, time_point, tilt_angle, fill_level):
        """Update status from collected data"""
        # Update progress based on time or other metrics if needed
        # For now, we'll just update the phase to show we're collecting data
        self.phase_status.setText(f"Collecting Data (Tilt: {tilt_angle:.1f}°, Fill: {fill_level:.1f}%)")

    def set_test_status(self, status):
        """Set the test status phase"""
        self.phase_status.setText(status)
