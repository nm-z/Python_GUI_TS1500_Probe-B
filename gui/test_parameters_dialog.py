from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QPushButton,
    QDialogButtonBox, QMessageBox, QFileDialog
)
from PyQt6.QtCore import QDir

class TestParametersDialog(QDialog):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Test Parameters")

        layout = QFormLayout()

        self.total_runs_edit = QLineEdit("1")
        layout.addRow(QLabel("Total Runs:"), self.total_runs_edit)

        self.run_number_edit = QLineEdit("1")
        layout.addRow(QLabel("Run Number:"), self.run_number_edit)

        self.min_tilt_edit = QLineEdit("-15")
        layout.addRow(QLabel("Min Tilt (°):"), self.min_tilt_edit)

        self.max_tilt_edit = QLineEdit("15")
        layout.addRow(QLabel("Max Tilt (°):"), self.max_tilt_edit)

        self.step_size_edit = QLineEdit("1")
        layout.addRow(QLabel("Step Size (°):"), self.step_size_edit)

        self.log_path_edit = QLineEdit()
        self.log_path_edit.setPlaceholderText("Path to save logs")
        layout.addRow(QLabel("Log Path:"), self.log_path_edit)

        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_log_path)
        layout.addRow(self.browse_button)

        self.pause_duration_edit = QLineEdit("0")
        layout.addRow(QLabel("Pause Between Runs (s):"), self.pause_duration_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept_parameters)
        button_box.rejected.connect(self.reject)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addWidget(button_box)
        self.setLayout(main_layout)

    def browse_log_path(self):
        """Opens a dialog to select the log path."""
        directory = QFileDialog.getExistingDirectory(self, "Select Log Path", QDir.homePath())
        if directory:
            self.log_path_edit.setText(directory)

    def accept_parameters(self):
        """Validates and accepts the parameters."""
        try:
            total_runs = int(self.total_runs_edit.text())
            run_number = int(self.run_number_edit.text())
            min_tilt = int(self.min_tilt_edit.text())
            max_tilt = int(self.max_tilt_edit.text())
            step_size = int(self.step_size_edit.text())
            pause_duration = int(self.pause_duration_edit.text())
            log_path = self.log_path_edit.text()

            if total_runs <= 0:
                raise ValueError("Total Runs must be greater than 0.")
            if not (1 <= run_number <= total_runs):
                raise ValueError("Run Number must be between 1 and Total Runs.")
            if min_tilt >= max_tilt:
                raise ValueError("Min Tilt must be less than Max Tilt.")
            if step_size <= 0:
                raise ValueError("Step Size must be greater than 0.")
            if pause_duration < 0:
                raise ValueError("Pause Duration cannot be negative.")
            if not log_path:
                raise ValueError("Log Path is required.")

            self.accept()

        except ValueError as e:
            QMessageBox.warning(self, "Validation Error", str(e))

    def get_parameters(self):
        """
        Returns the parameters entered by the user.
        """
        return {
            'total_runs': int(self.total_runs_edit.text()),
            'run_number': int(self.run_number_edit.text()),
            'min_tilt': int(self.min_tilt_edit.text()),
            'max_tilt': int(self.max_tilt_edit.text()),
            'step_size': int(self.step_size_edit.text()),
            'log_path': self.log_path_edit.text(),
            'pause_duration': int(self.pause_duration_edit.text()),
        } 