import sys
import os
import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTextEdit, QDialog, QMessageBox, QMenuBar, QMenu, QStatusBar
)
from PyQt6.QtCore import Qt, QTimer
from hardware.controller import HardwareController
from controllers.main_controller import MainController
from utils.config import Config

class TestFunctionalityDialog(QDialog):
    """Test Functionality Dialog"""
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.logger = logging.getLogger('gui')
        self.setup_ui()
        
        self.setWindowTitle("Test Functionality")
        self.setModal(False)
        
        layout = QVBoxLayout()
        
        # Motor control buttons
        motor_group = QGroupBox("Motor Control")
        motor_layout = QHBoxLayout()
        
        self.plus_one_btn = QPushButton("+1°")
        self.minus_one_btn = QPushButton("-1°")
        
        motor_layout.addWidget(self.minus_one_btn)
        motor_layout.addWidget(self.plus_one_btn)
        motor_group.setLayout(motor_layout)
        layout.addWidget(motor_group)
        
        # VNA sweep button
        self.sweep_btn = QPushButton("Sweep VNA in 5s")
        layout.addWidget(self.sweep_btn)
        
        self.setLayout(layout)
        
        # Connect signals
        self.plus_one_btn.clicked.connect(self._move_plus_one)
        self.minus_one_btn.clicked.connect(self._move_minus_one)
        self.sweep_btn.clicked.connect(self._sweep_vna)
        
    def _move_plus_one(self):
        """Move motor +1 degree"""
        try:
            self.controller.move_motor(1)
            self.logger.info("Moving motor +1 degree")
        except Exception as e:
            self.logger.error(f"Error moving motor: {str(e)}")
            
    def _move_minus_one(self):
        """Move motor -1 degree"""
        try:
            self.controller.move_motor(-1)
            self.logger.info("Moving motor -1 degree")
        except Exception as e:
            self.logger.error(f"Error moving motor: {str(e)}")
            
    def _sweep_vna(self):
        """Trigger VNA sweep"""
        try:
            self.logger.warning("Please click into the VNA.J window to focus it")
            QTimer.singleShot(5000, self._do_sweep)
        except Exception as e:
            self.logger.error(f"Error triggering VNA sweep: {str(e)}")
            
    def _do_sweep(self):
        """Execute VNA sweep after delay"""
        try:
            self.controller.trigger_vna_sweep()
            self.logger.info("VNA sweep triggered")
        except Exception as e:
            self.logger.error(f"Error during VNA sweep: {str(e)}")

class MainWindow(QMainWindow):
    """Main application window"""
    def __init__(self):
        """Main application window"""
        super().__init__()
        
        # Set up logging
        self.logger = logging.getLogger('gui')
        
        # Initialize hardware controller in main thread
        self.hardware = HardwareController()
        self.controller = MainController(self.hardware)
        
        # Set up UI
        self.setWindowTitle("TS1500 Probe Control")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Create main splitter
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.layout.addWidget(self.main_splitter)
        
        # Create control panel
        control_panel = QGroupBox("Control Panel")
        control_layout = QVBoxLayout()
        
        # Add test parameters
        params_layout = QFormLayout()
        
        self.start_pos = QSpinBox()
        self.start_pos.setRange(-30, 30)
        self.start_pos.setValue(-17)  # Default value
        params_layout.addRow("Start Position (°):", self.start_pos)
        
        self.end_pos = QSpinBox()
        self.end_pos.setRange(-30, 30)
        self.end_pos.setValue(17)  # Default value
        params_layout.addRow("End Position (°):", self.end_pos)
        
        self.step_size = QDoubleSpinBox()
        self.step_size.setRange(0.1, 3.0)
        self.step_size.setSingleStep(0.1)
        self.step_size.setValue(1.0)  # Default value
        params_layout.addRow("Step Size (°):", self.step_size)
        
        self.dwell_time = QSpinBox()
        self.dwell_time.setRange(5, 60)
        self.dwell_time.setValue(15)  # Default value
        params_layout.addRow("Dwell Time (s):", self.dwell_time)
        
        control_layout.addLayout(params_layout)
        
        # Add control buttons
        self.start_button = QPushButton("Start Test")
        self.start_button.setEnabled(True)
        control_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)
        
        self.emergency_button = QPushButton("EMERGENCY STOP")
        self.emergency_button.setStyleSheet("""
            QPushButton {
                background-color: red;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: darkred;
            }
            QPushButton:pressed {
                background-color: #800000;
            }
        """)
        control_layout.addWidget(self.emergency_button)
        
        control_panel.setLayout(control_layout)
        self.main_splitter.addWidget(control_panel)
        
        # Create log viewer
        log_group = QGroupBox("Log Output")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        # Set up log handler with modified behavior
        log_handler = QTextEditLogger(self.log_text)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger('gui').addHandler(log_handler)
        logging.getLogger('hardware').addHandler(log_handler)
        
        log_group.setLayout(log_layout)
        self.main_splitter.addWidget(log_group)
        
        # Set initial splitter sizes
        self.main_splitter.setSizes([200, 600])
        
        # Connect signals
        self._connect_signals()
        
        self.logger.info("Application initialized successfully")
        
    def _create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # Test Components menu
        test_menu = menubar.addMenu('Test Components')
        test_action = QAction('Test Functionality', self)
        test_action.triggered.connect(self._show_test_dialog)
        test_menu.addAction(test_action)
        
    def _show_test_dialog(self):
        """Show the test functionality dialog"""
        if not hasattr(self, 'test_dialog'):
            self.test_dialog = TestFunctionalityDialog(self.controller, self)
        self.test_dialog.show()
        
    def closeEvent(self, event):
        """Handle window close event"""
        if hasattr(self, 'hardware'):
            self.hardware.cleanup()
        event.accept()
        
    def _connect_signals(self):
        """Connect signals"""
        # Connect hardware signals
        self.hardware.error_occurred.connect(self._handle_error)
        self.hardware.temperature_updated.connect(self._handle_temperature)
        self.hardware.tilt_updated.connect(self._handle_tilt)
        
        # Connect button signals
        self.start_button.clicked.connect(self._handle_start)
        self.stop_button.clicked.connect(self._handle_stop)
        self.emergency_button.clicked.connect(self._handle_emergency)
        
    def _handle_error(self, error_msg):
        """Handle hardware errors"""
        self.logger.error(f"Hardware error: {error_msg}")
        
    def _handle_temperature(self, temperature):
        """Handle temperature updates"""
        pass  # Let the logger handle this
        
    def _handle_tilt(self, tilt):
        """Handle tilt updates"""
        pass  # Let the logger handle this
        
    def _handle_start(self):
        """Handle Start button click"""
        try:
            # Collect test parameters from GUI
            parameters = {
                'min_tilt': float(self.start_pos.value()),
                'max_tilt': float(self.end_pos.value()),
                'tilt_increment': float(self.step_size.value()),
                'dwell_time': float(self.dwell_time.value())
            }
            
            # Start test
            if self.controller.start_test(parameters):
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                self.logger.info("Test started with parameters:")
                for key, value in parameters.items():
                    self.logger.info(f"  {key}: {value}")
            
        except ValueError as e:
            self.logger.error("Invalid parameter value. Please check all inputs are valid numbers.")
        except Exception as e:
            self.logger.error(f"Error starting test: {str(e)}")
            
    def _handle_stop(self):
        """Handle Stop button click"""
        try:
            self.controller.stop_test()
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.logger.info("Test stopped by user")
        except Exception as e:
            self.logger.error(f"Error stopping test: {str(e)}")
            
    def _handle_emergency(self):
        """Handle emergency stop button click"""
        try:
            if self.controller.emergency_stop():
                self.logger.warning("Emergency stop triggered")
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
            else:
                self.logger.error("Emergency stop failed")
                
        except Exception as e:
            self.logger.error(f"Error during emergency stop: {str(e)}")

