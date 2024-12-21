from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QPushButton,
    QDialogButtonBox, QMessageBox, QFileDialog, QHBoxLayout, QSpinBox, QDoubleSpinBox, QTextEdit
)
from PyQt6.QtCore import QDir, Qt

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

class TestSequenceDialog(QDialog):
    def __init__(self, sequence_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Planned Test Sequence")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Add text display
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setText(sequence_text)
        layout.addWidget(self.text_display)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Test")
        self.start_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
def show_test_sequence(parent, parameters):
    """Show test sequence dialog and return whether to proceed
    
    Args:
        parent: Parent widget
        parameters (dict): Test parameters
        
    Returns:
        bool: True if user clicked Start, False if cancelled
    """
    try:
        # Calculate test points
        min_angle = parameters.get('min_tilt', -30.0)
        max_angle = parameters.get('max_tilt', 30.0)
        increment = parameters.get('tilt_increment', 1.0)
        oil_level_time = parameters.get('oil_level_time', 15)
        
        # Generate sequence text
        sequence_text = "=== Planned Test Sequence ===\n\n"
        
        # Calculate points
        angles = []
        current_angle = min_angle
        while current_angle <= max_angle:
            angles.append(current_angle)
            current_angle += increment
            
        sequence_text += f"Total test points: {len(angles)}\n"
        sequence_text += "-" * 40 + "\n\n"
        
        # Add each point's sequence
        for i, angle in enumerate(angles, 1):
            steps = int(angle / 0.0002)
            sequence_text += f"Point {i}:\n"
            sequence_text += f"1. MOVE {steps} steps ({angle:.1f}°)\n"
            sequence_text += f"2. Wait 5 seconds for motor movement\n"
            sequence_text += f"3. Wait {oil_level_time} seconds for oil to level\n"
            sequence_text += f"4. Take temperature reading\n"
            sequence_text += f"5. Take tilt reading\n"
            sequence_text += f"6. Trigger VNA sweep\n"
            sequence_text += f"7. Wait 10 seconds for VNA sweep\n"
            sequence_text += "-" * 40 + "\n\n"
            
        # Calculate estimated time
        points_count = len(angles)
        time_per_point = 5 + oil_level_time + 10  # motor + oil level + VNA
        total_time = points_count * time_per_point
        hours = total_time // 3600
        minutes = (total_time % 3600) // 60
        seconds = total_time % 60
        
        sequence_text += f"\nEstimated total time: {int(hours)}h {int(minutes)}m {int(seconds)}s\n"
        
        # Show dialog
        dialog = TestSequenceDialog(sequence_text, parent)
        result = dialog.exec()
        
        return result == QDialog.DialogCode.Accepted
        
    except Exception as e:
        print(f"Error showing test sequence: {str(e)}")
        return False 