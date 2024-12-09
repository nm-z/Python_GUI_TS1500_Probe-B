import threading
import logging
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QIcon
from models.data_model import DataModel
from hardware.arduino import ArduinoController
from utils.logger import gui_logger
from utils.time_sync import get_ntp_time
from utils.backup import backup_data
import os
import time
import serial.tools.list_ports
import subprocess

class HardwareError(Exception):
    """Exception raised for hardware-related errors."""
    pass

class CriticalError(Exception):
    """Exception raised for critical errors that require test termination."""
    pass

class GUILogHandler(logging.Handler):
    def __init__(self, log_viewer):
        super().__init__()
        self.log_viewer = log_viewer
        self.setLevel(logging.INFO)
        
    def emit(self, record):
        msg = self.format(record)
        self.log_viewer.append_log(msg, record.levelname)

class MainController(QObject):
    # Define signals
    status_updated_signal = pyqtSignal(dict)
    test_progress_signal = pyqtSignal(dict)
    test_completed_signal = pyqtSignal(dict)
    test_started_signal = pyqtSignal()
    test_paused_signal = pyqtSignal()
    test_stopped_signal = pyqtSignal()
    test_error_signal = pyqtSignal(str, str)  # title, message
    diagnostic_progress_signal = pyqtSignal(int, str)  # progress, message
    data_collected_signal = pyqtSignal(dict)  # data update signal
    
    def __init__(self):
        super().__init__()
        self.arduino = None
        self._is_connected = False
        self.data_model = DataModel()
        self.test_parameters = {}
        self.is_running = False
        self.is_paused = False
        self.test_thread = None
        self.logger = gui_logger
        
        # Create necessary data directories
        self._init_data_directories()
        
        # Initialize with default test parameters
        self.test_parameters = {
            'run_number': 1,
            'total_runs': 1,
            'step_size': 1,  # Default step size
            'current_angle': 0,
            'sweep_key': 'F11'  # Default sweep key, can be changed by user
        }

    def _init_data_directories(self):
        """Initialize data directories"""
        try:
            # Create data directories if they don't exist
            data_dirs = ['data', 'logs']
            base_dir = os.path.dirname(os.path.dirname(__file__))
            
            for dir_name in data_dirs:
                dir_path = os.path.join(base_dir, dir_name)
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                    self.logger.info(f"Created directory: {dir_path}")
                    
        except Exception as e:
            self.logger.error(f"Error initializing data directories: {e}")

    def trigger_sweep(self):
        """Trigger VNA sweep using configured key press"""
        try:
            from utils.keyboard_control import trigger_vna_sweep
            if trigger_vna_sweep(self.test_parameters.get('sweep_key', 'F11')):
                self.logger.info(f"VNA sweep triggered using {self.test_parameters['sweep_key']}")
                return True
            else:
                self.test_error_signal.emit("Sweep Error", "Failed to trigger VNA sweep")
                return False
        except Exception as e:
            self.test_error_signal.emit("Sweep Error", str(e))
            return False

    def update_sweep_key(self, key):
        """Update the key used to trigger VNA sweeps"""
        self.test_parameters['sweep_key'] = key
        self.logger.info(f"Sweep key updated to: {key}")

    def is_connected(self):
        """Check if hardware is connected"""
        return self._is_connected

    def connect_hardware(self, port):
        """Connect to Arduino hardware"""
        try:
            self.arduino = ArduinoController(port)
            self._is_connected = True
            self.update_status()
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to hardware: {e}")
            return False

    def disconnect_hardware(self):
        """Disconnect from hardware"""
        try:
            if self.arduino:
                self.arduino.disconnect()
            self._is_connected = False
            self.update_status()
        except Exception as e:
            self.logger.error(f"Error disconnecting hardware: {e}")

    def update_status(self):
        """Update system status"""
        status = {
            'ready': self._is_connected,
            'connected': self._is_connected,
        }
        self.status_updated_signal.emit(status)

    def update_test_parameters(self, parameters):
        """Update test parameters and validate them"""
        try:
            # Validate parameters
            required_params = ['start_angle', 'end_angle', 'step_size', 'dwell_time', 'num_runs']
            for param in required_params:
                if param not in parameters:
                    self.logger.error(f"Missing required parameter: {param}")
                    return False
            
            # Validate numeric values
            if not (isinstance(parameters['start_angle'], (int, float)) and 
                   isinstance(parameters['end_angle'], (int, float)) and
                   isinstance(parameters['step_size'], (int, float)) and
                   isinstance(parameters['dwell_time'], (int, float)) and
                   isinstance(parameters['num_runs'], int)):
                self.logger.error("Invalid parameter types")
                return False
            
            # Validate ranges
            if not (0 <= parameters['start_angle'] <= 90 and
                   0 <= parameters['end_angle'] <= 90 and
                   0 < parameters['step_size'] <= 90 and
                   parameters['dwell_time'] > 0 and
                   parameters['num_runs'] > 0):
                self.logger.error("Parameters out of valid range")
                return False
            
            # Update parameters
            self.test_parameters.update(parameters)
            self.logger.info("Test parameters updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating test parameters: {e}")
            return False