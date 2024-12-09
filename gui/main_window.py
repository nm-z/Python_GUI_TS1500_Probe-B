import sys
import os
import logging
import serial.tools.list_ports
from PyQt6.QtWidgets import QMainWindow, QApplication
from hardware.arduino import ArduinoController
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QToolBar, QFileDialog, QMessageBox, QDialog, QLabel,
    QToolButton, QMenu, QComboBox, QSpinBox, QDoubleSpinBox, QDialogButtonBox,
    QGroupBox, QGridLayout, QTabWidget, QProgressBar, QListWidget, QPushButton,
    QLineEdit, QScrollArea, QDateTimeEdit, QCheckBox, QFormLayout, QProgressDialog
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QAction
import platform
import subprocess
from .components import RealTimePlots, LogViewer, StatusIndicators, TiltIndicator
from .styles import Styles
from datetime import datetime
from utils.logger import gui_logger
import time

# Define simple fonts
HEADER_FONT = QFont()
HEADER_FONT.setFamily("Ubuntu")
HEADER_FONT.setPointSize(12)
HEADER_FONT.setWeight(QFont.Weight.Bold)

BODY_FONT = QFont()
BODY_FONT.setFamily("Ubuntu")
BODY_FONT.setPointSize(10)

def open_file(file_path):
    """Cross-platform file opening"""
    try:
        if platform.system() == "Darwin":       # macOS
            subprocess.call(('open', file_path))
        elif platform.system() == "Windows":    # Windows
            os.startfile(file_path)
        else:                                   # Linux variants
            subprocess.call(('xdg-open', file_path))
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Failed to open file: {e}")

class HardwareConfigurationDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hardware Configuration")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Hardware Configuration Settings Go Here"))
        self.setLayout(layout)

class TestParametersDialog(QDialog):
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Test Parameters")
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Create form layout for parameters
        form_layout = QFormLayout()
        
        # Add parameter inputs
        self.start_angle = QDoubleSpinBox()
        self.start_angle.setRange(-90, 90)
        self.start_angle.setValue(0)
        form_layout.addRow("Start Angle (��):", self.start_angle)
        
        self.end_angle = QDoubleSpinBox()
        self.end_angle.setRange(-90, 90)
        self.end_angle.setValue(45)
        form_layout.addRow("End Angle (°):", self.end_angle)
        
        self.step_size = QDoubleSpinBox()
        self.step_size.setRange(0.1, 10)
        self.step_size.setValue(1)
        form_layout.addRow("Step Size (°):", self.step_size)
        
        self.dwell_time = QDoubleSpinBox()
        self.dwell_time.setRange(0, 60)
        self.dwell_time.setValue(5)
        form_layout.addRow("Dwell Time (s):", self.dwell_time)
        
        self.num_runs = QSpinBox()
        self.num_runs.setRange(1, 10)
        self.num_runs.setValue(1)
        form_layout.addRow("Number of Runs:", self.num_runs)
        
        layout.addLayout(form_layout)
        
        # Add button box with StandardButton
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
    def get_parameters(self):
        return {
            'start_angle': self.start_angle.value(),
            'end_angle': self.end_angle.value(),
            'step_size': self.step_size.value(),
            'dwell_time': self.dwell_time.value(),
            'num_runs': self.num_runs.value()
        }

class BackupManagementDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Backup Management")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Backup Management Settings Go Here"))
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self, controller):
        """Initialize MainWindow"""
        super().__init__()
        print("Starting MainWindow initialization...")
        
        self.controller = controller
        self.test_parameters = {}
        self.test_start_time = None
        self.is_paused = False
        
        print("Initializing components...")
        # Initialize components
        self.real_time_plots = RealTimePlots()
        
        # Set up icons first
        print("Setting up icons...")
        self.setup_icons()
        
        print("Starting UI initialization...")
        # Initialize the UI
        self.init_ui()
        
        # Connect signals
        self.connect_signals()

    def setup_icons(self):
        """Set up icons for the application"""
        self.icons = {}
        icon_names = [
            'issue', 'components', 'help', 'reset', 'sync', 'upload',
            'backup', 'params', 'hardware', 'plots', 'tilt', 'logs',
            'stop', 'pause', 'export', 'start', 'save', 'open'
        ]
        
        # Get the absolute path to the icons directory
        icons_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'icons')
        print(f"Setting up icons from: {icons_dir}")
        
        for name in icon_names:
            icon_path = os.path.join(icons_dir, f'{name}.png')
            if os.path.exists(icon_path):
                self.icons[name] = QIcon(icon_path)
                print(f"Successfully loaded icon: {name}")
            else:
                print(f"Warning: Icon not found: {icon_path}")
                # Set a default icon or placeholder
                self.icons[name] = QIcon()

    def init_ui(self):
        """Initialize the UI"""
        self.setWindowTitle("TS1500 Probe Test Control")
        self.setMinimumSize(1024, 768)
        
        # Create toolbar
        self.create_toolbar()
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel for controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Status section
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout()
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        status_group.setLayout(status_layout)
        left_layout.addWidget(status_group)
        
        # Test Controls
        controls_group = QGroupBox("Test Controls")
        controls_layout = QVBoxLayout()
        
        # Control buttons with icons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Test")
        self.start_button.setIcon(self.icons['start'])
        self.pause_button = QPushButton("Pause Test")
        self.pause_button.setIcon(self.icons['pause'])
        self.stop_button = QPushButton("Stop Test")
        self.stop_button.setIcon(self.icons['stop'])
        self.configure_button = QPushButton("Configure Test")
        self.configure_button.setIcon(self.icons['params'])
        
        for button in [self.start_button, self.pause_button, 
                      self.stop_button, self.configure_button]:
            button_layout.addWidget(button)
            button.setFont(Styles.BODY_FONT)
        
        controls_layout.addLayout(button_layout)
        
        # Progress information
        progress_layout = QGridLayout()
        
        # Run progress
        progress_layout.addWidget(QLabel("Run:"), 0, 0)
        self.run_label = QLabel("1/1")
        progress_layout.addWidget(self.run_label, 0, 1)
        
        # Current angle
        progress_layout.addWidget(QLabel("Current Angle:"), 1, 0)
        self.angle_label = QLabel("0°")
        progress_layout.addWidget(self.angle_label, 1, 1)
        
        # Progress bar
        progress_layout.addWidget(QLabel("Progress:"), 2, 0)
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar, 2, 1)
        
        # Execution time
        progress_layout.addWidget(QLabel("Execution Time:"), 3, 0)
        self.time_label = QLabel("00:00:00")
        progress_layout.addWidget(self.time_label, 3, 1)
        
        controls_layout.addLayout(progress_layout)
        controls_group.setLayout(controls_layout)
        left_layout.addWidget(controls_group)
        
        # Error list
        error_group = QGroupBox("Errors")
        error_layout = QVBoxLayout()
        self.error_list = QListWidget()
        self.error_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {Styles.COLORS['background_alt']};
                border: 1px solid {Styles.COLORS['border']};
                border-radius: {Styles.BORDER_RADIUS}px;
            }}
        """)
        error_layout.addWidget(self.error_list)
        error_group.setLayout(error_layout)
        left_layout.addWidget(error_group)
        
        # Add left panel to splitter
        splitter.addWidget(left_panel)
        
        # Right panel for data 
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Data display tabs
        tabs = QTabWidget()
        
        # Initialize components
        self.real_time_plots = RealTimePlots()
        
        # Add tabs
        tabs.addTab(self.real_time_plots, "Real-time Plots")
        
        right_layout.addWidget(tabs)
        splitter.addWidget(right_panel)
        
        # Set splitter sizes (40% left, 60% right)
        splitter.setSizes([400, 600])
        
        # Initialize status bar
        self.init_status_bar()
        
        # Apply base style
        self.setStyleSheet(Styles.BASE_STYLE)

        # Connect signals
        self.start_button.clicked.connect(self.start_test)
        self.pause_button.clicked.connect(self.pause_test)
        self.stop_button.clicked.connect(self.stop_test)
        self.configure_button.clicked.connect(self.configure_test)
        
        # Initialize button states
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        
        # Start update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_execution_time)
        self.test_start_time = None

    def create_toolbar(self):
        """Create the main toolbar"""
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setStyleSheet("""
            QToolBar {
                background: #2b2b2b;
                border-bottom: 1px solid #3d3d3d;
                padding: 2px;
            }
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 4px;
                margin: 1px;
            }
            QToolButton:hover {
                background: #3d3d3d;
                border: 1px solid #4d4d4d;
            }
            QToolButton:pressed {
                background: #404040;
            }
        """)

        # File Menu
        file_button = QToolButton()
        file_button.setIcon(self.icons['components'])  # Using components icon for file menu
        file_button.setText("File")
        file_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        file_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        file_menu = QMenu()
        
        new_test_action = QAction(self.icons['start'], "New Test", self)
        new_test_action.setStatusTip("Create a new test")
        new_test_action.triggered.connect(self.new_test)
        file_menu.addAction(new_test_action)
        
        load_config_action = QAction(self.icons['open'], "Load Config", self)
        load_config_action.setStatusTip("Load configuration from file")
        load_config_action.triggered.connect(self.load_config)
        file_menu.addAction(load_config_action)
        
        save_config_action = QAction(self.icons['save'], "Save Config", self)
        save_config_action.setStatusTip("Save configuration to file")
        save_config_action.triggered.connect(self.save_config)
        file_menu.addAction(save_config_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(self.icons['stop'], "Exit", self)
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        file_button.setMenu(file_menu)
        toolbar.addWidget(file_button)
        
        # Settings Menu
        settings_button = QToolButton()
        settings_button.setIcon(self.icons['params'])
        settings_button.setText("Settings")
        settings_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        settings_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        settings_menu = QMenu()
        
        hardware_config_action = QAction(self.icons['hardware'], "Hardware Config", self)
        hardware_config_action.setStatusTip("Configure hardware settings")
        hardware_config_action.triggered.connect(self.configure_hardware)
        settings_menu.addAction(hardware_config_action)
        
        test_params_action = QAction(self.icons['params'], "Test Parameters", self)
        test_params_action.setStatusTip("Configure test parameters")
        test_params_action.triggered.connect(self.configure_test)
        settings_menu.addAction(test_params_action)
        
        settings_button.setMenu(settings_menu)
        toolbar.addWidget(settings_button)
        
        # Tools Menu
        tools_button = QToolButton()
        tools_button.setIcon(self.icons['sync'])  # Using sync icon for tools
        tools_button.setText("Tools")
        tools_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        tools_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        tools_menu = QMenu()
        
        backup_action = QAction(self.icons['backup'], "Backup", self)
        backup_action.setStatusTip("Manage backups")
        backup_action.triggered.connect(self.manage_backups)
        tools_menu.addAction(backup_action)
        
        upload_action = QAction(self.icons['upload'], "Upload Firmware", self)
        upload_action.setStatusTip("Upload firmware to device")
        upload_action.triggered.connect(self.upload_firmware)
        tools_menu.addAction(upload_action)
        
        tools_button.setMenu(tools_menu)
        toolbar.addWidget(tools_button)
        
        # Help Menu
        help_button = QToolButton()
        help_button.setIcon(self.icons['help'])
        help_button.setText("Help")
        help_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        help_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        help_menu = QMenu()
        
        components_action = QAction(self.icons['components'], "Components", self)
        components_action.setStatusTip("View components overview")
        components_action.triggered.connect(self.show_components)
        help_menu.addAction(components_action)
        
        issue_action = QAction(self.icons['issue'], "Report Issue", self)
        issue_action.setStatusTip("Report an issue")
        issue_action.triggered.connect(self.report_issue)
        help_menu.addAction(issue_action)
        
        help_button.setMenu(help_menu)
        toolbar.addWidget(help_button)

    def start_test(self):
        """Start the test"""
        if self.controller:
            self.controller.start_test()

    def pause_test(self):
        """Pause/resume the test"""
        if self.controller:
            self.controller.pause_test()

    def stop_test(self):
        """Stop the test"""
        if self.controller:
            self.controller.stop_test()

    def configure_test(self):
        """Configure test parameters"""
        try:
            dialog = TestParametersDialog(self.controller)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                parameters = dialog.get_parameters()
                if self.controller and self.controller.update_test_parameters(parameters):
                    self.test_parameters = parameters
                    self.update_parameter_display()
                    self.statusBar().showMessage("Test parameters updated successfully", 3000)
                else:
                    error_msg = "Failed to update test parameters"
                    print(error_msg)
                    self.statusBar().showMessage(error_msg, 3000)
        except Exception as e:
            error_msg = f"Error configuring test: {str(e)}"
            print(error_msg)
            self.statusBar().showMessage(error_msg, 3000)

    def update_parameter_display(self):
        """Update the display of current test parameters"""
        self.run_label.setText(
            f"{self.test_parameters.get('run_number', 1)}/"
            f"{self.test_parameters.get('total_runs', 1)}"
        )

    def update_progress(self, progress_data):
        """Update test progress in the UI"""
        try:
            # Update run number
            if 'current_run' in progress_data and 'total_runs' in progress_data:
                self.run_label.setText(f"{progress_data['current_run']}/{progress_data['total_runs']}")
            
            # Update current angle
            if 'current_angle' in progress_data:
                self.angle_label.setText(f"{progress_data['current_angle']}°")
                if hasattr(self, 'tilt_indicator'):
                    self.tilt_indicator.set_angle(progress_data['current_angle'])
            
            # Update progress bar
            if 'completion_percentage' in progress_data:
                self.progress_bar.setValue(int(progress_data['completion_percentage']))
            
            # Update status message
            if 'status' in progress_data:
                self.status_label.setText(progress_data['status'])
            
            # Log progress
            gui_logger.debug(f"Test progress updated: {progress_data}")
            
        except Exception as e:
            gui_logger.error(f"Error updating progress: {e}")
            self.show_error("Progress Update Error", str(e))

    def update_execution_time(self):
        """Update the execution time display"""
        if self.test_start_time:
            elapsed = datetime.now() - self.test_start_time
            self.time_label.setText(str(elapsed).split('.')[0])

    def on_test_started(self):
        """Handle test started signal"""
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.configure_button.setEnabled(False)
        self.status_label.setText("Test Running")
        self.test_start_time = datetime.now()
        self.update_timer.start(1000)
        self.error_list.clear()

    def on_test_paused(self):
        """Handle test paused signal"""
        self.pause_button.setText(
            "Resume Test" if self.pause_button.text() == "Pause Test"
            else "Pause Test"
        )
        self.status_label.setText("Test Paused")

    def on_test_stopped(self):
        """Handle test stopped signal"""
        self.reset_ui_state()
        self.status_label.setText("Test Stopped")

    def on_test_completed(self, summary):
        """Handle test completed signal"""
        self.reset_ui_state()
        self.status_label.setText("Test Completed")
        
        # Show completion dialog
        msg = (f"Test completed in {summary['execution_time']}\n"
               f"Completed angles: {summary['completed_angles']}/"
               f"{summary['total_angles']}")
        
        if summary['anomalies']:
            msg += "\n\nAnomalies detected:"
            for anomaly in summary['anomalies']:
                msg += f"\n- {anomaly}"
        
        print(msg)

    def on_test_error(self, error_msg):
        """Handle test error signal"""
        try:
            self.error_list.addItem(error_msg)
            self.error_list.scrollToBottom()
            if hasattr(self, 'status_label'):
                self.status_label.setText("Error Detected")
            print(f"Error occurred: {error_msg}")
        except Exception as e:
            print(f"Error handling test error: {str(e)}")

    def reset_ui_state(self):
        """Reset UI to initial state"""
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.configure_button.setEnabled(True)
        self.pause_button.setText("Pause Test")
        self.update_timer.stop()
        self.test_start_time = None
        self.time_label.setText("00:00:00")

    def connect_signals(self):
        """Connect signals to slots"""
        if self.controller:
            # Connect all controller signals
            self.controller.data_collected_signal.connect(self.real_time_plots.update_data)
            self.controller.test_started_signal.connect(self.on_test_started)
            self.controller.test_paused_signal.connect(self.on_test_paused)
            self.controller.test_stopped_signal.connect(self.on_test_stopped)
            self.controller.test_completed_signal.connect(self.on_test_completed)
            self.controller.test_error_signal.connect(self.on_test_error)
            self.controller.status_updated_signal.connect(self.update_status_indicators)
            
            # Connect button signals
            self.start_button.clicked.connect(self.start_test)
            self.pause_button.clicked.connect(self.pause_test)
            self.stop_button.clicked.connect(self.stop_test)
            self.configure_button.clicked.connect(self.configure_test)
            
            # Initial status update
            self.controller.update_status()

    def closeEvent(self, event):
        """Handle application close event"""
        try:
            if self.controller and self.controller.is_running:
                reply = QMessageBox.question(
                    self,
                    'Confirm Exit',
                    "A test is currently running. Are you sure you want to exit?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    event.ignore()
                    return
            
            # Stop any running test
            if self.controller:
                self.controller.stop_test()
            
            event.accept()
        except Exception as e:
            print(f"Error while closing application: {str(e)}")
            event.accept()

    def configure_hardware(self):
        """Configure hardware settings"""
        try:
            dialog = HardwareConfigDialog(self.controller, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                settings = dialog.get_settings()
                # Connect to hardware with new settings
                if settings['serial_port']:
                    print(f"Attempting to connect to Arduino on {settings['serial_port']}")
                    if self.controller.connect_hardware(settings['serial_port']):
                        # Verify connection with test commands
                        if self.controller.verify_connection():
                            print(f"Successfully connected and verified Arduino on {settings['serial_port']}")
                            self.update_arduino_status(True)
                            self.statusBar().showMessage("Hardware connected and verified", 3000)
                            return True
                        else:
                            error_msg = f"Connected but failed to verify Arduino on {settings['serial_port']}"
                            print(error_msg)
                            self.controller.disconnect_hardware()
                            self.statusBar().showMessage(error_msg, 3000)
                            return False
                    else:
                        error_msg = "Failed to connect to hardware"
                        print(error_msg)
                        self.statusBar().showMessage(error_msg, 3000)
                        return False
                        
                # Connect to VNA if IP is provided
                if settings['vna_ip']:
                    if self.controller.connect_vna(settings['vna_ip'], settings['vna_port']):
                        self.statusBar().showMessage("VNA connected successfully", 3000)
                    else:
                        self.statusBar().showMessage("Failed to connect to VNA", 3000)
                        
        except Exception as e:
            error_msg = f"Failed to configure hardware: {str(e)}"
            print(error_msg)
            self.statusBar().showMessage(error_msg, 3000)
            return False

    def configure_test_parameters(self):
        """Show test parameters dialog"""
        try:
            dialog = TestParametersDialog(self.controller)
            if dialog.exec() == QDialog.Accepted:
                self.test_parameters = dialog.get_parameters()
                if self.controller:
                    self.controller.update_test_parameters(self.test_parameters)
                self.statusBar().showMessage("Test parameters updated")
        except Exception as e:
            print(f"Failed to show test parameters: {str(e)}")

    def manage_backups(self):
        """Show backup management dialog"""
        try:
            dialog = BackupManagementDialog()
            dialog.exec()
            self.statusBar().showMessage("Backup management updated")
        except Exception as e:
            print(f"Failed to show backup management: {str(e)}")

    def upload_firmware(self):
        """Upload firmware to Arduino"""
        try:
            if not self.controller.is_connected():
                print("Error: Arduino not connected. Please connect to Arduino first.")
                self.statusBar().showMessage("Error: Arduino not connected", 3000)
                return
                
            self.controller.upload_firmware()
            print("Firmware uploaded successfully")
            self.statusBar().showMessage("Firmware uploaded successfully", 3000)
        except Exception as e:
            error_msg = f"Failed to upload firmware: {str(e)}"
            print(error_msg)
            self.statusBar().showMessage(error_msg, 3000)

    def sync_time(self):
        """Synchronize system time"""
        try:
            self.controller.sync_time()
            print("Time synchronized successfully")
            self.statusBar().showMessage("Time synchronized")
        except Exception as e:
            print(f"Failed to sync time: {str(e)}")

    def reset_to_defaults(self):
        """Reset settings to defaults"""
        reply = QMessageBox.question(
            self,
            'Reset to Defaults',
            "Are you sure you want to reset all settings to default values?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.controller.reset_to_defaults()
                print("Settings reset to defaults")
                self.statusBar().showMessage("Settings reset to defaults")
            except Exception as e:
                print(f"Failed to reset settings: {str(e)}")

    def open_user_guide(self):
        """Show the user guide"""
        try:
            guide_path = os.path.join(os.path.dirname(__file__), '..', 'README.md')
            if os.path.exists(guide_path):
                if platform.system() == "Windows":
                    os.startfile(guide_path)
                elif platform.system() == "Darwin":
                    subprocess.call(('open', guide_path))
                else:
                    subprocess.call(('xdg-open', guide_path))
                self.statusBar().showMessage("User guide opened")
            else:
                print("User guide not found")
        except Exception as e:
            print(f"Failed to open user guide: {str(e)}")

    def open_components_overview(self):
        """Show components overview"""
        try:
            components_path = os.path.join(os.path.dirname(__file__), '..', 'components.md')
            if os.path.exists(components_path):
                if platform.system() == "Windows":
                    os.startfile(components_path)
                elif platform.system() == "Darwin":
                    subprocess.call(('open', components_path))
                else:
                    subprocess.call(('xdg-open', components_path))
                self.statusBar().showMessage("Components overview opened")
            else:
                print("Components overview not found.")
                self.statusBar().showMessage("Components Overview not found.")
        except Exception as e:
            print(f"Failed to open components overview: {str(e)}")

    def report_issue(self):
        """Open email client to report issue"""
        import webbrowser
        subject = "TS1500 Probe Issue Report"
        body = "Please describe the issue:"
        webbrowser.open(f'mailto:natezmcpherson@gmail.com?subject={subject}&body={body}')

    def load_config(self):
        """Load configuration from file"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Load Configuration", "", "Config Files (*.yaml *.json)"
            )
            if file_path:
                self.controller.load_config(file_path)
                print("Configuration loaded successfully")
                
                # Update UI with new configuration
                config = self.controller.get_current_config()
                self.update_ui_from_config(config)
                
        except Exception as e:
            print(f"Failed to load configuration: {str(e)}")

    def save_config(self):
        """Save configuration to file"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Configuration", "", "Config Files (*.yaml *.json)"
            )
            if file_path:
                # Get current UI state
                config = {
                    'test_parameters': self.test_parameters,
                    'hardware_settings': self.controller.get_hardware_settings(),
                    'data_paths': {
                        'vna_data': self.controller.get_vna_data_path(),
                        'temperature_data': self.controller.get_temperature_data_path()
                    },
                    'display_settings': {
                        'plot_update_interval': self.real_time_plots.update_interval,
                        'temperature_units': 'celsius',
                        'angle_precision': 2
                    }
                }
                
                # Save to file
                self.controller.save_config(file_path, config)
                print("Configuration saved successfully")
                
        except Exception as e:
            print(f"Failed to save configuration: {str(e)}")

    def export_data(self):
        """Export test data"""
        try:
            file_path, selected_filter = QFileDialog.getSaveFileName(
                self, "Export Data", "", 
                "CSV Files (*.csv);;Excel Files (*.xlsx)"
            )
            if file_path:
                # Determine export format
                export_format = 'csv' if selected_filter == 'CSV Files (*.csv)' else 'excel'
                
                # Get export options
                dialog = ExportOptionsDialog(self)
                if dialog.exec():
                    options = dialog.get_options()
                    
                    # Show progress dialog
                    progress = QProgressDialog("Exporting data...", "Cancel", 0, 100, self)
                    progress.setWindowModality(Qt.WindowModal)
                    
                    def update_progress(value):
                        progress.setValue(value)
                    
                    # Connect progress signal
                    self.controller.export_progress_signal.connect(update_progress)
                    
                    # Export data
                    self.controller.export_data(file_path, export_format, options)
                    print("Data exported successfully")
                    
        except Exception as e:
            print(f"Failed to export data: {str(e)}")

    def update_ui_from_config(self, config):
        """Update UI elements from configuration"""
        try:
            # Update test parameters
            if 'test_parameters' in config:
                self.test_parameters = config['test_parameters']
                self.update_parameter_display()
            
            # Update plot settings
            if 'display_settings' in config:
                display_settings = config['display_settings']
                if 'plot_update_interval' in display_settings:
                    self.real_time_plots.update_interval = display_settings['plot_update_interval']
            
            # Update status
            self.update_status_indicators({
                'ready': True,
                'connected': self.controller.is_connected(),
                'vna_connected': self.controller.is_vna_connected()
            })
            
        except Exception as e:
            print(f"Some settings could not be updated: {str(e)}")

    def calibrate_sensors(self):
        """Calibrate system sensors"""
        try:
            if not self.controller.is_connected():
                print("Please connect to hardware first")
                return
                
            reply = QMessageBox.question(
                self,
                "Calibrate Sensors",
                "This will start the sensor calibration process. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.controller.calibrate_sensors()
                print("Sensor calibration completed")
        except Exception as e:
            print(f"Calibration failed: {str(e)}")

    def run_diagnostics(self):
        """Run system diagnostics"""
        try:
            if not self.controller.is_connected():
                print("Please connect to hardware first")
                return
                
            progress = QProgressDialog("Running diagnostics...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            
            def update_progress(value, message):
                progress.setValue(value)
                progress.setLabelText(message)
            
            # Connect progress signal
            self.controller.diagnostic_progress_signal.connect(update_progress)
            
            # Run diagnostics
            results = self.controller.run_diagnostics()
            
            # Show results
            if results:
                dialog = DiagnosticsResultDialog(results, self)
                dialog.exec()
            else:
                print("All systems operating normally")
                
        except Exception as e:
            print(f"Diagnostics failed: {str(e)}")
        finally:
            progress.close()

    def show_about(self):
        """Show about dialog"""
        print(
            "TS1500 Probe Test Control\n\n"
            "Version 1.0.0\n\n"
            "A control system for automated probe testing."
        )

    def show_logs(self):
        """Show the log viewer"""
        try:
            self.log_viewer.show()
            self.log_viewer.raise_()
            self.statusBar().showMessage("Log viewer opened")
        except Exception as e:
            print(f"Failed to show logs: {str(e)}")

    def show_real_time_plots(self):
        """Show real-time plots"""
        try:
            self.real_time_plots.show()
            self.real_time_plots.raise_()
            self.statusBar().showMessage("Real-time plots opened")
        except Exception as e:
            print(f"Failed to show plots: {str(e)}")

    def show_tilt_indicator(self):
        """Show the tilt indicator"""
        try:
            if not hasattr(self, 'tilt_indicator'):
                self.tilt_indicator = TiltIndicator()
            self.tilt_indicator.show()
            self.tilt_indicator.raise_()
            self.statusBar().showMessage("Tilt indicator opened")
        except Exception as e:
            print(f"Failed to show tilt indicator: {str(e)}")

    def show_hardware_config(self):
        """Show hardware configuration dialog"""
        self.hardware_config_dialog = HardwareConfigurationDialog()
        self.hardware_config_dialog.show()
        self.statusBar().showMessage("Hardware Configuration opened.")

    def show_test_parameters(self):
        """Show test parameters dialog"""
        self.test_parameters_dialog = TestParametersDialog()
        self.test_parameters_dialog.show()
        self.statusBar().showMessage("Test Parameters Configuration opened.")

    def show_backup_settings(self):
        """Show backup management dialog"""
        self.backup_management_dialog = BackupManagementDialog()
        self.backup_management_dialog.show()
        self.statusBar().showMessage("Backup Management opened.")

    def show_components(self):
        """Show components overview"""
        components_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'components.md')
        if os.path.exists(components_path):
            open_file(components_path)
            self.statusBar().showMessage("Components Overview opened.")
        else:
            print("Components overview not found.")
            self.statusBar().showMessage("Components Overview not found.")

    def init_status_bar(self):
        """Initialize the status bar with multiple sections"""
        status_bar = self.statusBar()
        
        # Set status bar style
        status_bar.setStyleSheet(f"""
            QStatusBar {{
                background: {Styles.COLORS['background']};
                color: {Styles.COLORS['foreground']};
                border-top: 1px solid {Styles.COLORS['border']};
            }}
            QLabel {{
                padding: 3px;
                border-right: 1px solid {Styles.COLORS['border']};
            }}
        """)
        
        # Initialize status labels
        self.time_sync_label = QLabel("Time Sync: Not Synced")
        self.arduino_status = QLabel("Arduino: Not Connected")
        self.tilt_status_label = QLabel("Tilt Sensor: Not Connected")
        self.temp_status_label = QLabel("Temperature: Not Connected")
        self.motor_status_label = QLabel("Motor: Not Connected")
        
        # Set initial error style for disconnected state
        self.arduino_status.setStyleSheet(f"color: {Styles.COLORS['error']};")
        
        # Create a single list of status widgets to ensure no duplicates
        status_widgets = [
            self.time_sync_label,
            QLabel(" | "),  # Separator
            self.arduino_status,
            QLabel(" | "),  # Separator
            self.tilt_status_label,
            QLabel(" | "),  # Separator
            self.temp_status_label,
            QLabel(" | "),  # Separator
            self.motor_status_label
        ]
        
        # Add widgets to status bar in sequence
        for widget in status_widgets:
            status_bar.addPermanentWidget(widget)

    def update_status_indicators(self, status):
        """Update status indicators with proper colors"""
        # Update Ready status
        if status.get('ready', False):
            self.status_label.setText("Ready")
            self.status_label.setStyleSheet("color: #44ff44;")  # Green
        else:
            self.status_label.setText("Not Ready")
            self.status_label.setStyleSheet("color: #666666;")  # Grey
            
        # Update Arduino status
        if status.get('connected', False):
            self.arduino_status.setText("Arduino: Connected")
            self.arduino_status.setStyleSheet("color: #44ff44;")  # Green
        else:
            self.arduino_status.setText("Arduino: Not Connected") 
            self.arduino_status.setStyleSheet("color: #ff4444;")  # Red
            
        # Show any error message
        if status.get('error'):
            self.error_list.addItem(status['error'])
            self.error_list.scrollToBottom()

    def update_arduino_status(self, connected):
        """Update Arduino connection status"""
        if connected:
            self.arduino_status.setText("Arduino: Connected")
            self.arduino_status.setStyleSheet("color: #00ff00;")  # Green
        else:
            self.arduino_status.setText("Arduino: Not Connected")
            self.arduino_status.setStyleSheet("color: #ff4444;")  # Red

    def update_vna_status(self, connected):
        """Update VNA connection status"""
        if connected:
            self.vna_status.setText("VNA: Connected")
            self.vna_status.setStyleSheet("color: #00ff00;")  # Green
        else:
            self.vna_status.setText("VNA: Not Connected")
            self.vna_status.setStyleSheet("color: #ff4444;")  # Red

    def new_test(self):
        """Create a new test"""
        # Reset all test parameters
        self.run_label.setText("1/1")
        self.angle_label.setText("0°")
        self.progress_bar.setValue(0)
        self.time_label.setText("00:00:00")
        self.error_list.clear()
        self.real_time_plots.clear_data()
        self.tilt_indicator.set_angle(0)
        
        # Reset test state
        self.test_start_time = None
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        
        # Show configuration dialog
        self.configure_test()

    def show_documentation(self):
        """Show the documentation"""
        try:
            docs_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'index.html')
            if os.path.exists(docs_path):
                if platform.system() == "Windows":
                    os.startfile(docs_path)
                elif platform.system() == "Darwin":
                    subprocess.call(('open', docs_path))
                else:
                    subprocess.call(('xdg-open', docs_path))
                self.statusBar().showMessage("Documentation opened", 3000)
            else:
                print("Documentation not found")
        except Exception as e:
            print(f"Failed to open documentation: {str(e)}")

    def show_error(self, title, message):
        """Show error message in the GUI and log it"""
        gui_logger.error(f"{title}: {message}")
        self.statusBar().showMessage(f"Error: {message}", 5000)  # Show for 5 seconds
        
        # Add to error list if it exists
        if hasattr(self, 'error_list'):
            self.error_list.addItem(f"{title}: {message}")
            self.error_list.scrollToBottom()
        
        # Update status label if it exists
        if hasattr(self, 'status_label'):
            self.status_label.setText("Error")
            self.status_label.setStyleSheet("color: #ff4444;")  # Red

    def connect_hardware(self):
        """Connect to hardware"""
        try:
            ports = self.controller.get_available_ports()
            if not ports:
                print("No serial ports found")
                return
            
            # Try to connect to the first available port
            if self.controller.connect_to_arduino(ports[0]):
                print(f"Successfully connected to hardware on {ports[0]}")
            else:
                print("Failed to connect to hardware")
        except Exception as e:
            print(f"Error connecting to hardware: {str(e)}")

    def connect_to_hardware(self):
        """Attempt to connect to Arduino hardware"""
        try:
            # Default to /dev/ttyACM0 for Arduino Due
            port = '/dev/ttyACM0'
            print(f"Attempting to connect to Arduino on {port}")
            
            # Try to connect
            if self.controller.connect_hardware(port):
                # Start a timer to check connection status after a short delay
                QTimer.singleShot(1000, self.verify_connection)
                self.statusBar().showMessage(f"Connecting to Arduino on {port}...", 3000)
                return True
            else:
                error_msg = "Failed to connect to Arduino"
                print(error_msg)
                self.statusBar().showMessage(error_msg, 3000)
                return False
                
        except Exception as e:
            error_msg = f"Error connecting to hardware: {str(e)}"
            print(error_msg)
            self.statusBar().showMessage(error_msg, 3000)
            return False

    def verify_connection(self):
        """Verify Arduino connection status"""
        try:
            if self.controller.verify_connection():
                print("Successfully connected and verified Arduino")
                self.update_arduino_status(True)
                self.statusBar().showMessage("Connected to Arduino", 3000)
            else:
                print("Failed to verify Arduino connection")
                self.controller.disconnect_hardware()
                self.update_arduino_status(False)
                self.statusBar().showMessage("Failed to verify Arduino connection", 3000)
        except Exception as e:
            print(f"Error verifying connection: {str(e)}")
            self.controller.disconnect_hardware()
            self.update_arduino_status(False)
            self.statusBar().showMessage(f"Connection verification error: {str(e)}", 3000)

    def update_tilt_visualization(self, angle):
        """Update tilt visualization with new angle"""
        if hasattr(self, 'tilt_indicator'):
            self.tilt_indicator.set_angle(angle)
            self.angle_label.setText(f"{angle:.1f}°")

class HardwareConfigDialog(QDialog):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Hardware Configuration")
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Show Arduino status
        status_group = QGroupBox("Arduino Status")
        status_layout = QVBoxLayout()
        self.status_label = QLabel("Arduino Due should be connected to /dev/ttyACM0")
        status_layout.addWidget(self.status_label)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_settings(self):
        """Get the current settings"""
        return {
            'serial_port': '/dev/ttyACM0',  # Always use ttyACM0
        }

class ExportOptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Options")
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Data selection
        self.temp_check = QCheckBox("Temperature Data")
        self.temp_check.setChecked(True)
        self.vna_check = QCheckBox("VNA Data")
        self.vna_check.setChecked(True)
        
        layout.addWidget(self.temp_check)
        layout.addWidget(self.vna_check)
        
        # Time range
        time_group = QGroupBox("Time Range")
        time_layout = QFormLayout()
        self.start_time = QDateTimeEdit()
        self.start_time.setDateTime(datetime.now().replace(hour=0, minute=0))
        self.end_time = QDateTimeEdit()
        self.end_time.setDateTime(datetime.now())
        time_layout.addRow("Start:", self.start_time)
        time_layout.addRow("End:", self.end_time)
        time_group.setLayout(time_layout)
        layout.addWidget(time_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_options(self):
        """Get the selected export options"""
        return {
            'include_temperature': self.temp_check.isChecked(),
            'include_vna': self.vna_check.isChecked(),
            'start_time': self.start_time.dateTime().toPyDateTime(),
            'end_time': self.end_time.dateTime().toPyDateTime()
        }

class DiagnosticsResultDialog(QDialog):
    def __init__(self, results, parent=None):
        super().__init__(parent)
        self.results = results
        self.setWindowTitle("Diagnostics Results")
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Results display
        scroll = QScrollArea()
        content = QWidget()
        content_layout = QVBoxLayout()
        
        for component, status in self.results.items():
            group = QGroupBox(component)
            group_layout = QVBoxLayout()
            
            status_label = QLabel(f"Status: {status['status']}")
            status_label.setStyleSheet(
                f"color: {'#44ff44' if status['status'] == 'OK' else '#ff4444'}"
            )
            group_layout.addWidget(status_label)
            
            if 'details' in status:
                details = QLabel(status['details'])
                details.setWordWrap(True)
                group_layout.addWidget(details)
            
            group.setLayout(group_layout)
            content_layout.addWidget(group)
        
        content.setLayout(content_layout)
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        
        self.setLayout(layout)