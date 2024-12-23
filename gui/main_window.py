import logging
import traceback
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QProgressBar, QPushButton, QGroupBox,
    QFormLayout, QSpinBox, QDoubleSpinBox, QLabel, QFileDialog, QMessageBox, QTextEdit,
    QStatusBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QProcess, QMetaObject, Q_ARG, QObject, QEvent, QSettings
from PyQt6.QtGui import QAction, QWindow, QColor
from utils.logger import QTextEditLogger
from hardware.controller import HardwareController
from controllers.main_controller import MainController

class WindowEventFilter(QObject):
    """Event filter to track window events"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger('gui')
        
    def eventFilter(self, obj, event):
        """Filter window events"""
        try:
            # Log specific events for debugging
            if event.type() == QEvent.Type.WindowStateChange:
                state = obj.windowState()
                state_str = "Normal"
                if state & Qt.WindowState.WindowMaximized:
                    state_str = "Maximized"
                elif state & Qt.WindowState.WindowMinimized:
                    state_str = "Minimized"
                elif state & Qt.WindowState.WindowFullScreen:
                    state_str = "FullScreen"
                self.logger.debug(f"Window state changed: {state_str}")
            
        except Exception as e:
            self.logger.error(f"Error in event filter: {str(e)}\n{traceback.format_exc()}")
            
        return super().eventFilter(obj, event)

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
        self.start_pos.setRange(-30, 30)  # Match SBIR requirements
        params_layout.addRow("Start Position (°):", self.start_pos)
        
        self.end_pos = QSpinBox()
        self.end_pos.setRange(-30, 30)  # Match SBIR requirements
        params_layout.addRow("End Position (°):", self.end_pos)
        
        self.step_size = QDoubleSpinBox()
        self.step_size.setRange(0.1, 3.0)  # Match SBIR requirements
        self.step_size.setSingleStep(0.1)
        self.step_size.setValue(1.0)
        params_layout.addRow("Step Size (°):", self.step_size)
        
        self.dwell_time = QSpinBox()
        self.dwell_time.setRange(5, 60)  # Match SBIR requirements
        self.dwell_time.setValue(15)
        params_layout.addRow("Dwell Time (s):", self.dwell_time)
        
        control_layout.addLayout(params_layout)
        
        # Add control buttons
        self.start_button = QPushButton("Start")
        self.start_button.setEnabled(True)  # Enable by default
        control_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)  # Disabled until test starts
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
        
        # Set up log handler
        log_handler = QTextEditLogger(self.log_text)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logging.getLogger('gui').addHandler(log_handler)
        logging.getLogger('hardware').addHandler(log_handler)
        
        log_group.setLayout(log_layout)
        self.main_splitter.addWidget(log_group)
        
        # Set initial splitter sizes
        self.main_splitter.setSizes([200, 600])
        
        # Connect signals
        self._connect_signals()
        
        self.logger.info("Application initialized successfully")
        
    def closeEvent(self, event):
        """Handle window close event"""
        if hasattr(self, 'hardware'):
            self.hardware.cleanup()
        event.accept()
        
    def _connect_signals(self):
        """Connect signals"""
        # Connect hardware signals
        self.hardware.connection_status.connect(self._handle_connection_status)
        self.hardware.error_occurred.connect(self._handle_error)
        self.hardware.temperature_updated.connect(self._handle_temperature)
        self.hardware.tilt_updated.connect(self._handle_tilt)
        
        # Connect button signals
        self.start_button.clicked.connect(self._handle_start)
        self.stop_button.clicked.connect(self._handle_stop)
        self.emergency_button.clicked.connect(self._handle_emergency)
        
    def _handle_connection_status(self, connected):
        """Handle hardware connection status changes"""
        if connected:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.emergency_button.setEnabled(True)
        else:
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.emergency_button.setEnabled(False)
            
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

