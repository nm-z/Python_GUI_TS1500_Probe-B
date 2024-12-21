import sys
import os
import logging
import serial.tools.list_ports
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QProgressBar, QPushButton, QGroupBox,
    QFormLayout, QSpinBox, QDoubleSpinBox, QLabel, QFileDialog, QMessageBox, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon
from utils.logger import gui_logger, QTextEditLogger
from gui.styles import Styles
from .plots_window import PlotsWindow
from .log_viewer import LogViewer
from .settings_dialog import SettingsDialog
import yaml
import time

class InitializationThread(QThread):
    finished = pyqtSignal()
    progress = pyqtSignal(str)

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    def run(self):
        """Run initialization tasks"""
        try:
            # Initialize hardware connections
            self.progress.emit("Initializing hardware connections...")
            if not self.controller.initialize_hardware():
                self.progress.emit("Warning: Failed to initialize hardware")
                self.finished.emit()
                return
            
            # Load configuration
            self.progress.emit("Loading configuration...")
            self.controller.config.load()
            
            # Check system status
            self.progress.emit("Checking system status...")
            if not self.controller.send_command('STATUS'):
                self.progress.emit("Warning: Failed to get system status")
            
            # Run self-test
            self.progress.emit("Running system self-test...")
            if not self.controller.send_command('TEST'):
                self.progress.emit("Warning: Self-test failed")
            
            # Home the motor
            self.progress.emit("Homing motor...")
            if not self.controller.send_command('HOME'):
                self.progress.emit("Warning: Failed to home motor")
            
            # Calibrate system
            self.progress.emit("Calibrating system...")
            if not self.controller.send_command('CALIBRATE'):
                self.progress.emit("Warning: Failed to calibrate system")
            
            self.progress.emit("Initialization complete")
            self.finished.emit()
            
        except Exception as e:
            self.progress.emit(f"Error during initialization: {str(e)}")
            gui_logger.error(f"Initialization error: {str(e)}")
            self.finished.emit()

class MainWindow(QMainWindow):
    def __init__(self, controller):
        """Initialize the main window
        
        Args:
            controller (MainController): Application controller
        """
        super().__init__()
        self.controller = controller
        self.plots_window = None  # Store reference to plots window
        self.test_running = False
        self.init_thread = None
        
        # Set up logger first
        self.logger = gui_logger
        
        # Set up UI components
        self.setup_ui()
        
        # Connect signals after UI is set up
        self.connect_signals()
        
        # Load last configuration
        self.load_last_config()
        
        self.logger.info("MainWindow initialization complete")
        
        self.start_initialization()
        
    def setup_ui(self):
        """Initialize the UI"""
        self.logger.info("Starting UI initialization...")
        
        # Set window properties
        self.setWindowTitle("TS1500 Probe Control")
        self.resize(400, 800)  # Adjusted size for single panel
        
        # Set dark theme by default
        self.dark_mode = True
        theme = Styles.get_theme(self.dark_mode)
        self.setStyleSheet(theme['window'])

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Create toolbar
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)
        settings_action = toolbar.addAction("Settings")
        settings_action.triggered.connect(self.show_settings)

        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(Styles.PROGRESS_STYLE)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - %v/%m")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

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
        self.tilt_increment.setStyleSheet(theme['spinbox'])
        config_layout.addRow("Tilt Increment (°):", self.tilt_increment)

        # Minimum Tilt
        self.min_tilt = QDoubleSpinBox()
        self.min_tilt.setRange(-30.0, 0.0)
        self.min_tilt.setSingleStep(0.1)
        self.min_tilt.setValue(-30.0)
        self.min_tilt.setDecimals(1)
        self.min_tilt.setStyleSheet(theme['spinbox'])
        config_layout.addRow("Minimum Tilt (°):", self.min_tilt)

        # Maximum Tilt
        self.max_tilt = QDoubleSpinBox()
        self.max_tilt.setRange(0.0, 30.0)
        self.max_tilt.setSingleStep(0.1)
        self.max_tilt.setValue(30.0)
        self.max_tilt.setDecimals(1)
        self.max_tilt.setStyleSheet(theme['spinbox'])
        config_layout.addRow("Maximum Tilt (°):", self.max_tilt)

        # Oil Level Time
        self.oil_level_time = QSpinBox()
        self.oil_level_time.setRange(5, 60)
        self.oil_level_time.setSingleStep(1)
        self.oil_level_time.setValue(15)
        self.oil_level_time.setStyleSheet(theme['spinbox'])
        config_layout.addRow("Oil Level Time (s):", self.oil_level_time)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Add control buttons
        button_layout = QHBoxLayout()
        
        # Start button
        self.start_button = QPushButton("Start Test")
        self.start_button.setStyleSheet(theme['button'])
        self.start_button.clicked.connect(self.start_test)
        button_layout.addWidget(self.start_button)
        
        # Pause button
        self.pause_button = QPushButton("Pause")
        self.pause_button.setStyleSheet(theme['button'])
        self.pause_button.clicked.connect(self.pause_test)
        self.pause_button.setEnabled(False)
        button_layout.addWidget(self.pause_button)
        
        # Stop button
        self.stop_button = QPushButton("Stop")
        self.stop_button.setStyleSheet(theme['button'])
        self.stop_button.clicked.connect(self.stop_test)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        # Emergency Stop button
        self.emergency_button = QPushButton("EMERGENCY STOP")
        self.emergency_button.setStyleSheet(Styles.EMERGENCY_BUTTON_STYLE)
        self.emergency_button.clicked.connect(self.emergency_stop)
        button_layout.addWidget(self.emergency_button)
        
        layout.addLayout(button_layout)

        # Add status indicators
        status_group = QGroupBox("Status")
        status_group.setFont(Styles.FONT)
        status_layout = QVBoxLayout()

        # Connection status
        self.connection_status = QLabel("Not Connected")
        self.connection_status.setStyleSheet(f"color: {Styles.ERROR_COLOR};")
        status_layout.addWidget(self.connection_status)

        # Current angle
        self.angle_label = QLabel("Current Angle: 0.0°")
        status_layout.addWidget(self.angle_label)

        # Temperature
        self.temp_label = QLabel("Temperature: --°C")
        status_layout.addWidget(self.temp_label)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Add logger widget
        log_group = QGroupBox("Log")
        log_group.setFont(Styles.FONT)
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(theme['log'])
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # Set up the log handler
        log_handler = QTextEditLogger(self.log_text)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        gui_logger.addHandler(log_handler)

        # Add spacer
        layout.addSpacing(20)

        # Add configuration buttons
        self.save_config_btn = QPushButton("Save Configuration")
        self.load_config_btn = QPushButton("Load Configuration")
        self.reset_config_btn = QPushButton("Reset to Defaults")

        for btn in [self.save_config_btn, self.load_config_btn, self.reset_config_btn]:
            btn.setStyleSheet(theme['button'])
            btn.setMinimumHeight(40)
            layout.addWidget(btn)

        # Connect button signals
        self.save_config_btn.clicked.connect(self.save_config)
        self.load_config_btn.clicked.connect(self.load_config)
        self.reset_config_btn.clicked.connect(self.reset_config)

        # Disable pause and stop buttons initially
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        
    def update_theme(self, is_dark_mode=True):
        """Update application theme
        
        Args:
            is_dark_mode (bool): Whether to use dark mode
        """
        try:
            self.dark_mode = is_dark_mode
            theme = Styles.get_theme(is_dark_mode)
            
            # Update window style
            self.setStyleSheet(theme['window'])
            
            # Update spinboxes
            for spinbox in [self.tilt_increment, self.min_tilt, self.max_tilt, self.oil_level_time]:
                spinbox.setStyleSheet(theme['spinbox'])
            
            # Update buttons
            for btn in [self.start_button, self.pause_button, self.stop_button,
                       self.save_config_btn, self.load_config_btn, self.reset_config_btn]:
                btn.setStyleSheet(theme['button'])
            
            # Emergency button keeps its style
            self.emergency_button.setStyleSheet(Styles.EMERGENCY_BUTTON_STYLE)
            
            # Update log
            self.log_text.setStyleSheet(theme['log'])
            
            # Update plots if they exist
            if hasattr(self, 'plots_window') and self.plots_window:
                self.plots_window.update_theme(is_dark_mode)
            
            gui_logger.info(f"Theme updated to {'dark' if is_dark_mode else 'light'} mode")
            
        except Exception as e:
            gui_logger.error(f"Error updating theme: {str(e)}")
            
    def showEvent(self, event):
        """Handle window show event"""
        super().showEvent(event)
        # Ensure theme is applied when window is shown
        self.update_theme(self.dark_mode)

    def connect_signals(self):
        """Connect controller signals to UI updates"""
        if self.controller:
            # Connect test signals
            self.controller.progress_updated.connect(self.update_progress)
            self.controller.test_completed.connect(self.handle_test_completed)
            
            # Connect data signals
            self.controller.data_collected_signal.connect(self.handle_data_collected)
            
            # Connect connection status signals
            self.controller.connection_status_updated.connect(self.handle_connection_status)
            
            # Connect angle update signal
            self.controller.angle_updated.connect(self.update_angle_display)
            
    def handle_connection_status(self, status_dict):
        """Handle connection status updates"""
        pass
            
    def handle_data_collected(self, data):
        """Handle collected data updates"""
        try:
            if not self.plots_window:
                return
                
            if 'time_point' in data:
                if 'tilt_angle' in data:
                    self.plots_window.update_tilt(data['time_point'], data['tilt_angle'])
                    self.update_angle_display(data['tilt_angle'])
                if 'temperature' in data:
                    self.plots_window.update_temperature(data['time_point'], data['temperature'])
                    self.update_temperature_display(data['temperature'])
                    
        except Exception as e:
            gui_logger.error(f"Error handling data update: {str(e)}")
            
    def update_angle_display(self, angle):
        """Update angle display in UI"""
        try:
            self.angle_label.setText(f"Current Angle: {angle:.1f}°")
        except Exception as e:
            gui_logger.error(f"Error updating angle display: {str(e)}")
            
    def update_temperature_display(self, temperature):
        """Update temperature display in UI"""
        try:
            self.temp_label.setText(f"Temperature: {temperature:.1f}°C")
        except Exception as e:
            gui_logger.error(f"Error updating temperature display: {str(e)}")
            
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
                with open(file_path, 'w') as f:
                    yaml.dump(config, f)
                print("Configuration saved successfully")
            except Exception as e:
                print(f"Error saving configuration: {str(e)}")
                
    def load_config(self, file_path=None):
        """Load configuration from YAML file"""
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Load Configuration", "", "YAML Files (*.yaml);;All Files (*)"
            )
            
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                self.tilt_increment.setValue(config.get('tilt_increment', 1.0))
                self.min_tilt.setValue(config.get('min_tilt', -30.0))
                self.max_tilt.setValue(config.get('max_tilt', 30.0))
                self.oil_level_time.setValue(config.get('oil_level_time', 15))
                
                print("Configuration loaded successfully")
            except Exception as e:
                print(f"Error loading configuration: {str(e)}")
                
    def load_last_config(self):
        """Load the last used configuration"""
        try:
            # Set default values
            self.tilt_increment.setValue(1.0)
            self.min_tilt.setValue(-30.0)
            self.max_tilt.setValue(30.0)
            self.oil_level_time.setValue(15)
        except Exception as e:
            print(f"Error loading last configuration: {str(e)}")
            self.reset_config()
            
    def reset_config(self):
        """Reset configuration to defaults"""
        self.tilt_increment.setValue(1.0)
        self.min_tilt.setValue(-30.0)
        self.max_tilt.setValue(30.0)
        self.oil_level_time.setValue(15)
        print("Configuration reset to defaults")

    def start_test(self):
        """Start a new test with current configuration"""
        try:
            # Initialize plots window if needed
            if not self.plots_window:
                self.plots_window = PlotsWindow()
            self.plots_window.show()
            self.plots_window.clear_plots()
            
            # Get current test parameters
            parameters = {
                'tilt_increment': self.tilt_increment.value(),
                'min_tilt': self.min_tilt.value(),
                'max_tilt': self.max_tilt.value(),
                'oil_level_time': self.oil_level_time.value()
            }
            
            # Validate parameters
            if not self._validate_test_parameters(parameters):
                return
                
            # Disable start button and enable stop/pause
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.pause_button.setEnabled(True)
            
            # Show progress bar
            self.progress_bar.setValue(0)
            self.progress_bar.show()
            
            # Start test with parameters
            if not self.controller.start_test(parameters):
                raise Exception("Failed to start test")
                
            self.test_running = True
            gui_logger.info("Test started successfully")
            
        except Exception as e:
            gui_logger.error(f"Failed to start test: {str(e)}")
            self._handle_test_error()
            if self.plots_window:
                self.plots_window.close()
                self.plots_window = None

    def _validate_test_parameters(self, parameters):
        """Validate test parameters
        
        Args:
            parameters (dict): Test parameters to validate
            
        Returns:
            bool: True if parameters are valid, False otherwise
        """
        try:
            # Check tilt increment
            if parameters['tilt_increment'] <= 0 or parameters['tilt_increment'] > 3.0:
                gui_logger.error("Invalid tilt increment (must be between 0.1 and 3.0)")
                return False
                
            # Check min/max tilt
            if parameters['min_tilt'] >= parameters['max_tilt']:
                gui_logger.error("Minimum tilt must be less than maximum tilt")
                return False
                
            # Check oil level time
            if parameters['oil_level_time'] < 5 or parameters['oil_level_time'] > 60:
                gui_logger.error("Invalid oil level time (must be between 5 and 60 seconds)")
                return False
                
            return True
            
        except Exception as e:
            gui_logger.error(f"Parameter validation error: {str(e)}")
            return False
            
    def _handle_test_error(self):
        """Handle test error and reset UI state"""
        # Reset button states
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        
        # Hide progress bar
        self.progress_bar.hide()
        
        # Reset test state
        self.test_running = False
        
        # Update status
        self.connection_status.setText("Not Connected")
        self.connection_status.setStyleSheet(Styles.STATUS_ERROR_STYLE)

    def pause_test(self):
        """Pause the current test"""
        try:
            if self.controller.pause_test():
                self.pause_button.setText("Resume")
            else:
                self.pause_button.setText("Pause")
                
        except Exception as e:
            print(f"[ERROR] Failed to pause test: {str(e)}")
            
    def stop_test(self):
        """Stop the test and close plots window"""
        if self.plots_window:
            self.plots_window.close()
            self.plots_window = None
        try:
            self.controller.stop_test()
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.pause_button.setText("Pause")
            
        except Exception as e:
            print(f"[ERROR] Failed to stop test: {str(e)}")
            
    def emergency_stop(self):
        """Trigger emergency stop"""
        try:
            self.controller.send_command("EMERGENCY_STOP")
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.pause_button.setText("Pause")
            
        except Exception as e:
            print(f"[ERROR] Failed to execute emergency stop: {str(e)}")
            
    def show_error(self, title, message):
        """Print error message to terminal
        
        Args:
            title (str): Error title
            message (str): Error message
        """
        print(f"[ERROR] {title}: {message}")

    def update_progress(self, value):
        """Update progress bar value and log progress
        
        Args:
            value (Union[int, str]): Progress value (0-100) or status message
        """
        try:
            if isinstance(value, str):
                # If value is a string, it's a status message
                gui_logger.info(value)
                return
                
            # Ensure value is an integer between 0 and 100
            progress = max(0, min(100, int(value)))
            self.progress_bar.setValue(progress)
            
            if progress % 10 == 0:  # Log every 10%
                gui_logger.info(f"Test progress: {progress}%")
                
        except Exception as e:
            gui_logger.error(f"Error updating progress: {str(e)}")

    def handle_test_completed(self, results):
        """Handle test completion
        
        Args:
            results (dict): Test results data
        """
        self.test_running = False
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.progress_bar.setValue(100)
        
        # Log results
        print(f"[SUCCESS] Test completed - Run #{results['run_number']}")
        print(f"[SUCCESS] Total Execution Time: {results['execution_time']}")
        print(f"[SUCCESS] Data saved to: {results['data_files']['vna']}, {results['data_files']['temperature']}")
        
    def resizeEvent(self, event):
        """Handle window resize events
        
        Args:
            event: Resize event
        """
        try:
            super().resizeEvent(event)
            print(f"[DEBUG] Window resized to {self.width()}x{self.height()}")
        except Exception as e:
            import traceback
            print(f"[ERROR] Resize error: {str(e)}")
            print("[ERROR] Traceback:")
            print(traceback.format_exc())
            
    def closeEvent(self, event):
        """Handle window close event - force close regardless of state"""
        try:
            # Force terminate initialization thread if running
            if hasattr(self, 'init_thread') and self.init_thread:
                self.init_thread.terminate()
                self.init_thread = None

            # Force close plots window
            if hasattr(self, 'plots_window') and self.plots_window:
                self.plots_window.close()
                self.plots_window = None

            # Force cleanup controller
            if hasattr(self, 'controller'):
                try:
                    self.controller.force_cleanup()
                except:
                    pass

            # Remove log handlers immediately
            if hasattr(self, 'log_text'):
                for handler in gui_logger.handlers[:]:
                    if isinstance(handler, QTextEditLogger):
                        gui_logger.removeHandler(handler)

        except:
            pass  # Ignore any errors during force close
        finally:
            # Always accept the close event
            event.accept()

    def cleanup(self):
        """Clean up resources before exit"""
        try:
            # Set a flag to prevent new operations
            self._cleanup_in_progress = True

            # Stop initialization thread first
            if hasattr(self, 'init_thread') and self.init_thread:
                try:
                    self.init_thread.quit()
                    # Only wait briefly for thread to finish
                    if not self.init_thread.wait(100):  # 100ms timeout
                        self.init_thread.terminate()
                    self.init_thread = None
                except:
                    pass

            # Close plots window if open
            if hasattr(self, 'plots_window') and self.plots_window:
                try:
                    self.plots_window.close()
                    self.plots_window = None
                except:
                    pass

            # Clean up controller with timeout
            if hasattr(self, 'controller'):
                try:
                    # Use a timer to prevent hanging
                    from PyQt6.QtCore import QTimer
                    cleanup_timer = QTimer()
                    cleanup_timer.setSingleShot(True)
                    cleanup_timer.timeout.connect(lambda: setattr(self, '_cleanup_timeout', True))
                    cleanup_timer.start(500)  # 500ms timeout
                    
                    self.controller.force_cleanup()  # Use force cleanup instead of normal cleanup
                    cleanup_timer.stop()
                except:
                    pass

            # Remove log handlers
            if hasattr(self, 'log_text'):
                try:
                    for handler in gui_logger.handlers[:]:
                        if isinstance(handler, QTextEditLogger):
                            gui_logger.removeHandler(handler)
                except:
                    pass

        except:
            pass  # Ignore all errors during cleanup
        finally:
            # Reset cleanup flag
            self._cleanup_in_progress = False

    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()

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

    def start_initialization(self):
        """Start hardware initialization in a separate thread"""
        if self.init_thread and self.init_thread.isRunning():
            self.logger.warning("Initialization already in progress")
            return
            
        self.init_thread = InitializationThread(self.controller)
        self.init_thread.finished.connect(self.on_initialization_complete)
        self.init_thread.progress.connect(self.update_progress)
        self.init_thread.start()

    def on_initialization_complete(self):
        """Handle initialization completion"""
        try:
            if hasattr(self, 'init_thread') and self.init_thread:
                self.init_thread.quit()
                self.init_thread.wait(1000)  # Wait up to 1 second
                self.init_thread = None
            self.logger.info("Initialization complete")
        except Exception as e:
            self.logger.error(f"Error during initialization completion: {str(e)}")

    def _setup_plots(self):
        """Set up plot window and connections"""
        try:
            # Create plots window
            self.plots_window = PlotsWindow()
            
            # Connect data signals
            self.controller.signals.tilt_angle_updated.connect(self.plots_window.update_tilt)
            self.controller.signals.temperature_updated.connect(self.plots_window.update_temperature)
            
            # Show plots window
            self.plots_window.show()
            
        except Exception as e:
            self.logger.error(f"Error setting up plots: {str(e)}")
            
    def _setup_connections(self):
        """Set up signal connections"""
        try:
            # Connect hardware status signals
            self.controller.signals.hardware_connected.connect(self._on_hardware_connected)
            self.controller.signals.hardware_disconnected.connect(self._on_hardware_disconnected)
            self.controller.signals.hardware_error.connect(self._on_hardware_error)
            
            # Connect test control signals
            self.start_button.clicked.connect(self._on_start_clicked)
            self.stop_button.clicked.connect(self._on_stop_clicked)
            
            # Connect configuration signals
            self.save_config_button.clicked.connect(self._on_save_config)
            self.load_config_button.clicked.connect(self._on_load_config)
            
        except Exception as e:
            self.logger.error(f"Error setting up connections: {str(e)}")
            
    def _on_start_clicked(self):
        """Handle start button click"""
        try:
            if not self.controller.is_test_running():
                # Get test parameters from UI
                parameters = self._get_test_parameters()
                if parameters:
                    # Create plots window if needed
                    if not hasattr(self, 'plots_window') or not self.plots_window.isVisible():
                        self._setup_plots()
                    else:
                        self.plots_window.clear_plots()
                    
                    # Start test
                    if self.controller.start_test(parameters):
                        self.start_button.setText("Pause")
                        self.stop_button.setEnabled(True)
                        self.logger.info("Test started successfully")
                    else:
                        self.logger.error("Failed to start test")
            else:
                # Pause/resume test
                if self.controller.pause_test():
                    self.start_button.setText("Resume" if self.controller.is_test_paused() else "Pause")
                
        except Exception as e:
            self.logger.error(f"Error handling start button: {str(e)}")
            
    def _on_stop_clicked(self):
        """Handle stop button click"""
        try:
            if self.controller.stop_test():
                self.start_button.setText("Start")
                self.stop_button.setEnabled(False)
                self.logger.info("Test stopped successfully")
            else:
                self.logger.error("Failed to stop test")
                
        except Exception as e:
            self.logger.error(f"Error handling stop button: {str(e)}")
            
    def _on_hardware_connected(self):
        """Handle hardware connected event"""
        try:
            self.start_button.setEnabled(True)
            self.status_label.setText("Hardware Connected")
            self.status_label.setStyleSheet("color: green")
            
        except Exception as e:
            self.logger.error(f"Error handling hardware connected: {str(e)}")
            
    def _on_hardware_disconnected(self):
        """Handle hardware disconnected event"""
        try:
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.status_label.setText("Hardware Disconnected")
            self.status_label.setStyleSheet("color: red")
            
        except Exception as e:
            self.logger.error(f"Error handling hardware disconnected: {str(e)}")
            
    def _on_hardware_error(self, error_msg):
        """Handle hardware error event
        
        Args:
            error_msg (str): Error message
        """
        try:
            self.status_label.setText(f"Hardware Error: {error_msg}")
            self.status_label.setStyleSheet("color: red")
            self.logger.error(f"Hardware error: {error_msg}")
            
        except Exception as e:
            self.logger.error(f"Error handling hardware error: {str(e)}")
            