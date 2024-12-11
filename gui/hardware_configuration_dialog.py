from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QMessageBox
)
from PyQt6.QtCore import pyqtSlot

class HardwareConfigurationDialog(QDialog):
    def __init__(self, controller, main_window, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.main_window = main_window
        self.setWindowTitle("Hardware Configuration")

        layout = QVBoxLayout()

        self.serial_port_edit = QLineEdit()
        self.serial_port_edit.setPlaceholderText("/dev/ttyUSB0")
        layout.addWidget(QLabel("Serial Port:"))
        layout.addWidget(self.serial_port_edit)

        # Buttons
        button_layout = QHBoxLayout()
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_button)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    @pyqtSlot()
    def test_connection(self):
        """Tests the connection to the specified serial port."""
        serial_port = self.serial_port_edit.text()
        if not serial_port:
            QMessageBox.warning(self, "No Serial Port", "Please enter a serial port.")
            return

        if self.controller.connect_hardware(serial_port):
            QMessageBox.information(self, "Connection Successful", f"Successfully connected to {serial_port}")
            self.main_window.update_status('arduino', True)
        else:
            QMessageBox.critical(self, "Connection Failed", f"Failed to connect to {serial_port}")
            self.main_window.update_status('arduino', False)

    def get_settings(self):
        """
        Returns the hardware settings entered by the user.
        """
        return {
            'serial_port': self.serial_port_edit.text()
        } 