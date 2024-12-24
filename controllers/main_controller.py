import sys
import os
import logging
import time
import threading
from datetime import datetime
import csv
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from hardware.controller import HardwareController
from utils.config import Config

class MainController(QObject):
    # Signals for UI updates
    status_updated = pyqtSignal(dict)
    progress_updated = pyqtSignal(int)
    angle_updated = pyqtSignal(float)
    test_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, hardware_controller):
        """Initialize the controller
        
        Args:
            hardware_controller (HardwareController): The hardware controller instance
        """
        super().__init__()
        self.logger = logging.getLogger('gui')
        self.hardware = hardware_controller
        self._lock = threading.Lock()
        self._test_running = False
        self._test_paused = False
        self._test_thread = None