import sys
import os
import logging
import serial.tools.list_ports
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QProgressBar, QPushButton, QGroupBox,
    QFormLayout, QSpinBox, QDoubleSpinBox, QLabel, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from .styles import Styles
from .real_time_plots import RealTimePlots
from .log_viewer import LogViewer
from .settings_dialog import SettingsDialog
from .status_indicators import StatusIndicators
from utils.logger import gui_logger

class MainWindow(QMainWindow):
    def __init__(self, controller):
        """Initialize the main window
        
        Args:
            controller (MainController): Application controller
        """
        super().__init__()
        self.controller = controller
        
        # Initialize components before UI setup
        self.logger = LogViewer()
        self.plots = RealTimePlots()
        self.status_indicators = StatusIndicators()
        
        # Initialize connection states
        self.arduino_connected = False
        self.vna_connected = False
        self.tilt_connected = False
        self.temp_connected = False
        
        # Set up UI components
        self.setup_ui()
        
        # Connect signals after UI is set up
        self.connect_signals()
        
        # Connect to hardware
        self.controller.connect_hardware()
        
        # Load last configuration
        self.load_last_config()
        
    def setup_ui(self):
        """Initialize the UI"""
        # Set window properties
        self.setWindowTitle("TS1500 Probe Control")
        self.resize(1200, 800)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create toolbar
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)
        settings_action = toolbar.addAction("Settings")
        settings_action.triggered.connect(self.show_settings)

        # Create main content widget and layout
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        layout.addWidget(content_widget)

        # Create main horizontal splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(4)
        self.main_splitter.setStyleSheet(Styles.DIVIDER_STYLE)
        self.main_splitter.splitterMoved.connect(self.handle_splitter_moved)
        content_layout.addWidget(self.main_splitter)

        # Add left panel (configuration)
        self.left_panel = QWidget()
        self.left_panel.setMinimumWidth(250)
        self.left_panel.setMaximumWidth(400)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)

        # Add configuration group
        config_group = QGroupBox("Test Configuration")
        config_group.setFont(Styles.FONT)
        config_layout = QFormLayout()
        config_layout.setSpacing(10)

        # Tilt Increment
        self.tilt_increment = QDoubleSpinBox()
        self.tilt_increment.setRange(0.1, 3.0)
        self.tilt_increment.setSingleStep(0.1)
        self.tilt_increment.setValue(1.0)
        self.tilt_increment.setDecimals(1)
        self.tilt_increment.setStyleSheet(Styles.SPINBOX_STYLE)
        config_layout.addRow("Tilt Increment (°):", self.tilt_increment)

        # Minimum Tilt
        self.min_tilt = QDoubleSpinBox()
        self.min_tilt.setRange(-30.0, 0.0)
        self.min_tilt.setSingleStep(0.1)
        self.min_tilt.setValue(-30.0)
        self.min_tilt.setDecimals(1)
        self.min_tilt.setStyleSheet(Styles.SPINBOX_STYLE)
        config_layout.addRow("Minimum Tilt (°):", self.min_tilt)

        # Maximum Tilt
        self.max_tilt = QDoubleSpinBox()
        self.max_tilt.setRange(0.0, 30.0)
        self.max_tilt.setSingleStep(0.1)
        self.max_tilt.setValue(30.0)
        self.max_tilt.setDecimals(1)
        self.max_tilt.setStyleSheet(Styles.SPINBOX_STYLE)
        config_layout.addRow("Maximum Tilt (°):", self.max_tilt)

        # Oil Level Time
        self.oil_level_time = QSpinBox()
        self.oil_level_time.setRange(5, 60)
        self.oil_level_time.setValue(15)
        self.oil_level_time.setStyleSheet(Styles.SPINBOX_STYLE)
        config_layout.addRow("Oil Level Time (s):", self.oil_level_time)

        config_group.setLayout(config_layout)
        left_layout.addWidget(config_group)

        # Add configuration buttons vertically
        self.save_config_btn = QPushButton("Save Configuration")
        self.load_config_btn = QPushButton("Load Configuration")
        self.reset_config_btn = QPushButton("Reset to Defaults")

        for btn in [self.save_config_btn, self.load_config_btn, self.reset_config_btn]:
            btn.setStyleSheet(Styles.BUTTON_STYLE)
            btn.setMinimumHeight(40)
            left_layout.addWidget(btn)

        # Add spacer
        left_layout.addSpacing(20)

        # Add test control buttons vertically
        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)
        
        # Start button
        self.start_button = QPushButton("Run Routine")
        self.start_button.setIcon(QIcon("icons/start.png"))
        self.start_button.setStyleSheet(Styles.BUTTON_STYLE)
        self.start_button.clicked.connect(self.start_test)
        button_layout.addWidget(self.start_button)
        
        # Pause button
        self.pause_button = QPushButton("Pause")
        self.pause_button.setIcon(QIcon("icons/pause.png"))
        self.pause_button.setStyleSheet(Styles.BUTTON_STYLE)
        self.pause_button.clicked.connect(self.pause_test)
        self.pause_button.setEnabled(False)
        button_layout.addWidget(self.pause_button)
        
        # Stop button
        self.stop_button = QPushButton("Stop")
        self.stop_button.setIcon(QIcon("icons/stop.png"))
        self.stop_button.setStyleSheet(Styles.BUTTON_STYLE)
        self.stop_button.clicked.connect(self.stop_test)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        # Emergency Stop button
        self.emergency_button = QPushButton("EMERGENCY STOP")
        self.emergency_button.setIcon(QIcon("icons/stop.png"))
        self.emergency_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #FF0000;
                color: white;
                border: 2px solid #AA0000;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Ubuntu';
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #AA0000;
            }}
            QPushButton:pressed {{
                background-color: #880000;
            }}
        """)
        self.emergency_button.clicked.connect(self.emergency_stop)
        button_layout.addWidget(self.emergency_button)
        
        # Add spacer to push buttons to top
        button_layout.addStretch()
        
        # Add button layout to main layout
        left_layout.addLayout(button_layout)

        # Add stretch at the bottom to push everything up
        left_layout.addStretch()

        # Add left panel to splitter
        self.main_splitter.addWidget(self.left_panel)

        # Create right side widget with vertical layout
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Create right panel with vertical splitter
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.right_splitter.setHandleWidth(4)
        self.right_splitter.setStyleSheet(Styles.DIVIDER_STYLE)
        self.right_splitter.splitterMoved.connect(self.handle_splitter_moved)
        right_layout.addWidget(self.right_splitter)

        # Add plots
        self.plots = RealTimePlots()
        self.right_splitter.addWidget(self.plots)

        # Add logger
        self.logger = LogViewer()
        self.right_splitter.addWidget(self.logger)

        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(Styles.PROGRESS_STYLE)
        self.progress_bar.hide()
        right_layout.addWidget(self.progress_bar)

        # Add right widget to splitter
        self.main_splitter.addWidget(right_widget)

        # Set initial sizes
        self.main_splitter.setSizes([300, 900])  # 25% left, 75% right
        self.right_splitter.setSizes([600, 200])  # 75% plots, 25% logger

        # Connect button signals
        self.save_config_btn.clicked.connect(self.save_config)
        self.load_config_btn.clicked.connect(self.load_config)
        self.reset_config_btn.clicked.connect(self.reset_config)
        self.start_button.clicked.connect(self.start_test)
        self.pause_button.clicked.connect(self.pause_test)
        self.stop_button.clicked.connect(self.stop_test)

        # Disable pause and stop buttons initially
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)

    def connect_signals(self):
        """Connect controller signals to UI updates"""
        if self.controller:
            # Connect test signals
            self.controller.progress_updated.connect(self.update_progress)
            self.controller.test_completed.connect(self.handle_test_completed)
            self.controller.angle_updated.connect(lambda angle: self.plots.update_tilt(angle))
            
            # Connect data signals
            self.controller.data_collected_signal.connect(self.handle_data_collected)
            
            # Connect Arduino initialization messages
            if hasattr(self.controller.hardware, 'initialization_message'):
                self.controller.hardware.initialization_message.connect(self.handle_initialization_message)
                
            # Connect Arduino connection status signal
            if hasattr(self.controller.hardware, 'connection_status_changed'):
                self.controller.hardware.connection_status_changed.connect(self.status_indicators.update_connection_status)
    
    def handle_initialization_message(self, message):
        """Handle messages from the Arduino"""
        if message:
            self.logger.append_message(message)
            self.logger.verticalScrollBar().setValue(self.logger.verticalScrollBar().maximum())  # Auto-scroll to bottom

    def handle_connection_status(self, is_connected):
        """Handle connection status updates"""
        self.status_indicators.update_connection_status(is_connected)

    def update_connection_status(self):
        """Update connection status indicators"""
        if hasattr(self, 'arduino_connected'):
            self.status_indicators.update_connection_status(self.arduino_connected)

    def handle_data_collected(self, data):
        """Handle collected data updates"""
        if 'time_point' in data:
            if 'tilt_angle' in data:
                self.plots.update_tilt(data['tilt_angle'])
            if 'temperature' in data:
                self.plots.update_temperature(data['time_point'], data['temperature'])

    def handle_splitter_moved(self, pos, index):
        """Handle splitter movement and snapping"""
        splitter = self.sender()
        if not isinstance(splitter, QSplitter):
            return
            
        # Get splitter geometry
        width = splitter.width()
        height = splitter.height()
        
        # Get current sizes
        sizes = list(splitter.sizes())  # Convert to list for modification
        
        # Calculate snap thresholds (10% of total size)
        snap_threshold = int(width * 0.1) if splitter.orientation() == Qt.Orientation.Horizontal else int(height * 0.1)
        
        # Handle horizontal splitter (main splitter)
        if splitter == self.main_splitter:
            # Left panel has minimum and maximum widths
            if sizes[0] < self.left_panel.minimumWidth():
                sizes[0] = self.left_panel.minimumWidth()
                sizes[1] = width - sizes[0]
            elif sizes[0] > self.left_panel.maximumWidth():
                sizes[0] = self.left_panel.maximumWidth()
                sizes[1] = width - sizes[0]
                
            # Snap to edges
            if sizes[0] < snap_threshold:
                sizes[0] = 0
                sizes[1] = width
            elif sizes[1] < snap_threshold:
                sizes[0] = width
                sizes[1] = 0
                
        # Handle vertical splitter (right splitter)
        elif splitter == self.right_splitter:
            # Ensure minimum heights for plots and logger
            min_plot_height = int(height * 0.3)  # 30% minimum for plots
            min_logger_height = int(height * 0.2)  # 20% minimum for logger
            
            if sizes[0] < min_plot_height:
                sizes[0] = min_plot_height
                sizes[1] = height - sizes[0]
            elif sizes[1] < min_logger_height:
                sizes[1] = min_logger_height
                sizes[0] = height - sizes[1]
                
        # Convert sizes to integers and apply
        sizes = [int(size) for size in sizes]
        splitter.setSizes(sizes)

    def save_config(self):
        """Save current configuration to YAML file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration", "", "YAML Files (*.yaml);;All Files (*)"
        )
        
        if file_path:
            config = {
                'tilt_increment': self.tilt_increment.value(),
                'min_tilt': self.min_tilt.value(),
                'max_tilt': self.max_tilt.value(),
                'oil_level_time': self.oil_level_time.value()
            }
            
            try:
                self.controller.save_config(file_path, config)
                self.logger.append_message("Configuration saved successfully", 'SUCCESS')
            except Exception as e:
                self.logger.append_message(f"Error saving configuration: {str(e)}", 'ERROR')
                
    def load_config(self, file_path=None):
        """Load configuration from YAML file"""
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Load Configuration", "", "YAML Files (*.yaml);;All Files (*)"
            )
            
        if file_path and os.path.exists(file_path):
            try:
                config = self.controller.load_config(file_path)
                
                self.tilt_increment.setValue(config.get('tilt_increment', 1.0))
                self.min_tilt.setValue(config.get('min_tilt', -30.0))
                self.max_tilt.setValue(config.get('max_tilt', 30.0))
                self.oil_level_time.setValue(config.get('oil_level_time', 15))
                
                self.logger.append_message("Configuration loaded successfully", 'SUCCESS')
            except Exception as e:
                self.logger.append_message(f"Error loading configuration: {str(e)}", 'ERROR')
                
    def load_last_config(self):
        """Load the last used configuration"""
        try:
            config = self.controller.load_last_config()
            if config:
                self.update_gui_from_config(config)
        except Exception:
            # Silently handle configuration loading errors
            pass

    def reset_config(self):
        """Reset configuration to defaults"""
        self.tilt_increment.setValue(1.0)
        self.min_tilt.setValue(-30.0)
        self.max_tilt.setValue(30.0)
        self.oil_level_time.setValue(15)
        self.logger.append_message("Configuration reset to defaults", 'INFO')

    def start_test(self):
        """Start the test sequence"""
        try:
            # Collect parameters from UI
            parameters = {
                'tilt_increment': self.tilt_increment.value(),
                'min_tilt': self.min_tilt.value(),
                'max_tilt': self.max_tilt.value(),
                'oil_level_time': self.oil_level_time.value()
            }
            
            self.controller.start_test(parameters)
            self.start_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            
        except Exception as e:
            print(f"Error starting test: {str(e)}", file=sys.stderr)
            
    def pause_test(self):
        """Pause the current test"""
        try:
            if self.controller.pause_test():
                self.pause_button.setText("Resume")
            else:
                self.pause_button.setText("Pause")
                
        except Exception as e:
            print(f"Error pausing test: {str(e)}", file=sys.stderr)
            
    def stop_test(self):
        """Stop the current test"""
        try:
            self.controller.stop_test()
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.pause_button.setText("Pause")
            
        except Exception as e:
            print(f"Error stopping test: {str(e)}", file=sys.stderr)
            
    def emergency_stop(self):
        """Trigger emergency stop"""
        try:
            self.controller.send_command("EMERGENCY_STOP")
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.pause_button.setText("Pause")
            
        except Exception as e:
            print(f"Error executing emergency stop: {str(e)}", file=sys.stderr)
            
    def show_error(self, title, message):
        """Print error to terminal instead of showing dialog
        
        Args:
            title (str): Error title
            message (str): Error message
        """
        print(f"Error - {title}: {message}", file=sys.stderr)

    def update_progress(self, value):
        """Update progress bar value"""
        self.progress_bar.setValue(value)
        
    def handle_test_completed(self, results):
        """Handle test completion"""
        self.test_running = False
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.progress_bar.setValue(100)
        
    def resizeEvent(self, event):
        """Handle window resize event"""
        super().resizeEvent(event)
        
        # Update window size
        new_size = event.size()
        self.resize(new_size)
        
    def update_splitter_sizes(self, main_sizes, right_sizes):
        """Update splitter sizes"""
        self.main_splitter.setSizes(main_sizes)
        self.right_splitter.setSizes(right_sizes)
        
    def closeEvent(self, event):
        """Handle window close event"""
        try:
            # Stop any running test
            if hasattr(self, 'test_running') and self.test_running:
                self.controller.stop_test()
                
            # Disconnect hardware
            if hasattr(self.controller, 'hardware'):
                self.controller.hardware.disconnect()
                
            # Stop timers
            if hasattr(self.controller, 'connection_timer'):
                self.controller.connection_timer.stop()
                
            # Accept the close event
            event.accept()
            
        except Exception as e:
            print(f"Error during cleanup: {str(e)}", file=sys.stderr)
            event.accept()  # Accept the close event even if there's an error

    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self)
        dialog.settings_updated.connect(self.apply_settings)
        dialog.exec()
        
    def apply_settings(self, settings):
        """Apply updated settings"""
        # Update theme
        is_dark_mode = settings['theme']['dark_mode']
        self.plots.update_theme(is_dark_mode)
        self.logger.update_theme(is_dark_mode)
        
        # Update font size
        font = Styles.FONT
        font.setPointSize(settings['theme']['font_size'])
        self.setFont(font)
        
        # Update all widgets that need font size changes
        for widget in self.findChildren(QWidget):
            widget.setFont(font)

    def handle_hardware_event(self, event):
        """Handle hardware events"""
        if event.get('source') == 'arduino':
            message = event.get('message', '')
            if isinstance(message, str):
                self.logger.append_message(message)
            else:
                self.logger.append_message(str(message))