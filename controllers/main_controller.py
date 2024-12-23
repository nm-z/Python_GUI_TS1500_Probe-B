import time
from datetime import datetime
import os
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QEvent, QThread
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication
import yaml
import threading
import csv
import logging
import traceback
import sys
from threading import Thread

from utils.logger import gui_logger, hardware_logger, log_hardware_event
from utils.config import Config
from hardware.controller import HardwareController

class DataCollectionThread(QThread):
    """Thread for data collection"""
    data_collected = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.running = False
        self.logger = logging.getLogger('data_collection')
        
    def run(self):
        """Run data collection"""
        self.running = True
        while self.running:
            try:
                data = self._collect_data()
                if data:
                    self.data_collected.emit(data)
            except Exception as e:
                self.logger.error(f"Data collection error: {str(e)}\n{traceback.format_exc()}")
                self.error_occurred.emit(str(e))
                break
            time.sleep(1)  # Collect data every second
            
    def _collect_data(self):
        """Collect a single data point"""
        try:
            if not self.controller._test_running or self.controller._test_paused:
                return None
                
            # Get current data
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            angle = self.controller.current_angle
            temperature = self.controller.hardware.get_temperature() if self.controller.hardware else 0.0
            vna_status = "Ready"  # TODO: Get actual VNA status
            
            return {
                'timestamp': timestamp,
                'run': self.controller.current_run,
                'angle': angle,
                'temperature': temperature,
                'vna_status': vna_status
            }
            
        except Exception as e:
            self.logger.error(f"Error collecting data point: {str(e)}\n{traceback.format_exc()}")
            return None
            
    def stop(self):
        """Stop data collection"""
        self.running = False
        self.wait()

class TestThread(QThread):
    """Thread for running test sequence"""
    progress_updated = pyqtSignal(int)
    test_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.running = False
        self.logger = logging.getLogger('test')
        
    def run(self):
        """Run test sequence"""
        try:
            self.running = True
            self.controller._run_test_routine()
        except Exception as e:
            self.logger.error(f"Test thread error: {str(e)}")
            self.error_occurred.emit(str(e))
        finally:
            self.running = False
            
    def stop(self):
        """Stop test sequence"""
        self.running = False
        self.wait()

class MainController(QObject):
    # Signals for UI updates
    status_updated = pyqtSignal(dict)
    progress_updated = pyqtSignal(int)
    angle_updated = pyqtSignal(float)
    test_completed = pyqtSignal(dict)
    connection_status_updated = pyqtSignal(dict)
    data_collected_signal = pyqtSignal(dict)  # For real-time data updates
    error_occurred = pyqtSignal(str)  # For error notifications
    
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
        self.connection_states = {
            'tilt': False,
            'temp': False
        }
        
        # Set up exception handling
        sys.excepthook = self._handle_exception
        
        # Initialize state
        self.current_run = 0
        self.current_angle = 0.0
        
        # Load configuration
        try:
            self.config = Config()
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {str(e)}")
            self.error_occurred.emit("Failed to load configuration")
            return
            
        # Initialize connection states
        self.connection_states = {
            'vna': False,
            'tilt': False,
            'temp': False
        }
        
        # Set up data directories
        try:
            self.setup_data_directories()
        except Exception as e:
            self.logger.error(f"Failed to set up data directories: {str(e)}")
            self.error_occurred.emit("Failed to set up data directories")
            return
            
        # Initialize VNA settings
        self.vna_trigger_key = self.config.get('vna', 'key', default='F5')
        self.vna_port = self.config.get('vna', 'port', default='COM1')
        
        # Initialize data paths
        self.vna_data_path = self.config.get('data_paths', 'vna', default='data/vna')
        self.temperature_data_path = self.config.get('data_paths', 'temperature', default='data/temperature')
        self.results_path = self.config.get('data_paths', 'results', default='data/results')
        
        # Initialize timers with proper error handling
        try:
            self.connection_timer = QTimer(self)
            self.connection_timer.timeout.connect(self.poll_connections)
            self.connection_timer.start(10000)  # Poll every 10 seconds
        except Exception as e:
            self.logger.error(f"Failed to initialize timers: {str(e)}")
            self.error_occurred.emit("Failed to initialize timers")
            return
            
        # Initialize data collection thread
        self.data_collection_thread = None
        
        # Initialize hardware controller
        try:
            self.hardware = HardwareController()
            self.hardware.connection_status.connect(self._handle_hardware_connection)
            self.hardware.error_occurred.connect(self._handle_hardware_error)
            self.hardware.temperature_updated.connect(self._handle_temperature_update)
            self.hardware.tilt_updated.connect(self._handle_tilt_update)
        except Exception as e:
            self.logger.error(f"Failed to initialize hardware: {str(e)}")
            self.error_occurred.emit("Failed to initialize hardware")
            return
            
    def _handle_exception(self, exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions"""
        if issubclass(exc_type, KeyboardInterrupt):
            # Call the default handler for KeyboardInterrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
            
        self.logger.error("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))
        
    def _handle_hardware_connection(self, connected):
        """Handle hardware connection status changes"""
        try:
            with self._lock:
                self.connection_states['tilt'] = connected
                self.connection_states['temp'] = connected
                self.connection_status_updated.emit(self.connection_states.copy())
                
            if not connected:
                self.logger.warning("Hardware disconnected")
                if self._test_running:
                    self.stop_test()
                    
        except Exception as e:
            self.logger.error(f"Error handling hardware connection: {str(e)}")
            
    def _handle_hardware_error(self, error_msg):
        """Handle hardware errors"""
        self.logger.error(f"Hardware error: {error_msg}")
        self.error_occurred.emit(f"Hardware error: {error_msg}")
        
    def _handle_temperature_update(self, temperature):
        """Handle temperature updates"""
        try:
            if self._test_running and not self._test_paused:
                self.data_collected_signal.emit({
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'temperature': temperature
                })
        except Exception as e:
            self.logger.error(f"Error handling temperature update: {str(e)}")
            
    def _handle_tilt_update(self, tilt):
        """Handle tilt angle updates"""
        try:
            self.current_angle = tilt
            self.angle_updated.emit(tilt)
        except Exception as e:
            self.logger.error(f"Error handling tilt update: {str(e)}")
            
    def _start_data_collection(self):
        """Start collecting data for the test"""
        try:
            with self._lock:
                # Create data directory if needed
                os.makedirs('data', exist_ok=True)
                
                # Create data file with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.data_file = open(f'data/test_{timestamp}.csv', 'w', newline='')
                self.csv_writer = csv.DictWriter(
                    self.data_file,
                    fieldnames=['Timestamp', 'Run', 'Angle', 'Temperature', 'VNA_Status']
                )
                self.csv_writer.writeheader()
                
                # Start data collection thread
                self.data_collection_thread = DataCollectionThread(self)
                self.data_collection_thread.data_collected.connect(self._handle_collected_data)
                self.data_collection_thread.error_occurred.connect(self._handle_collection_error)
                self.data_collection_thread.start()
                
                self.logger.info("Data collection started")
                
        except Exception as e:
            self.logger.error(f"Failed to start data collection: {str(e)}\n{traceback.format_exc()}")
            self._stop_data_collection()
            raise
            
    def _handle_collected_data(self, data):
        """Handle collected data from the thread"""
        try:
            with self._lock:
                self.csv_writer.writerow(data)
                self.data_collected_signal.emit(data)
        except Exception as e:
            self.logger.error(f"Error handling collected data: {str(e)}\n{traceback.format_exc()}")
            
    def _handle_collection_error(self, error_msg):
        """Handle error from data collection thread"""
        self.logger.error(f"Data collection error: {error_msg}")
        self._stop_data_collection()
        self.error_occurred.emit(f"Data collection error: {error_msg}")
        
    def _stop_data_collection(self):
        """Stop collecting data for the test"""
        try:
            # Stop thread
            if self.data_collection_thread:
                self.data_collection_thread.stop()
                self.data_collection_thread = None
            
            # Close data file
            if hasattr(self, 'data_file') and self.data_file:
                try:
                    self.data_file.close()
                except:
                    pass
                self.data_file = None
                self.csv_writer = None
            
            self.logger.info("Data collection stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping data collection: {str(e)}\n{traceback.format_exc()}")
            
    def cleanup(self):
        """Clean up resources"""
        try:
            # Stop data collection
            self._stop_data_collection()
            
            # Stop connection timer
            if self.connection_timer:
                self.connection_timer.stop()
            
            # Clean up hardware
            if self.hardware:
                self.hardware.cleanup()
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}\n{traceback.format_exc()}")
        finally:
            # Ensure critical cleanup
            self._test_running = False
            self._test_paused = False
            
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()

    def setup_data_directories(self):
        """Create necessary data directories"""
        directories = [
            'data/vna',
            'data/temperature',
            'data/results'
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            
    def send_vna_key_event(self):
        """Send key event to trigger VNA sweep with improved error handling and status tracking"""
        try:
            with self._lock:
                self.logger.info("\033[93mVNA: Initiating sweep...\033[0m")
                
                # Update VNA status in data collection
                self.vna_status = "Sweeping"
                
                # Get the application instance
                app = QApplication.instance()
                if not app:
                    raise RuntimeError("No QApplication instance found")
                
                # Handle F5 key properly
                from PyQt6.QtCore import Qt
                key = Qt.Key.Key_F5
                
                # Create and post key press event
                key_event = QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)
                if not app.focusWidget():
                    self.logger.warning("No widget has focus for VNA key event")
                    return False
                
                app.postEvent(app.focusWidget(), key_event)
                time.sleep(0.1)  # Short delay between press and release
                
                # Create and post key release event
                key_event = QKeyEvent(QEvent.Type.KeyRelease, key, Qt.KeyboardModifier.NoModifier)
                app.postEvent(app.focusWidget(), key_event)
                
                # Wait for sweep completion
                sweep_timeout = 30  # 30 seconds timeout
                sweep_start = time.time()
                
                while time.time() - sweep_start < sweep_timeout:
                    # Check for new data file in VNA directory
                    vna_files = os.listdir(self.vna_data_path)
                    latest_file = max(vna_files, key=lambda f: os.path.getmtime(os.path.join(self.vna_data_path, f))) if vna_files else None
                    
                    if latest_file and time.time() - os.path.getmtime(os.path.join(self.vna_data_path, latest_file)) < 5:
                        self.logger.info("\033[93mVNA: Sweep completed successfully\033[0m")
                        self.vna_status = "Complete"
                        return True
                    
                    time.sleep(0.5)  # Check every 500ms
                
                self.logger.error("\033[93mVNA: Sweep timeout\033[0m")
                self.vna_status = "Timeout"
                return False
                
        except Exception as e:
            self.logger.error(f"\033[93mVNA: Failed to send key event: {str(e)}\033[0m")
            self.vna_status = "Error"
            return False
            
        finally:
            # Log VNA event
            try:
                from utils.logger import log_hardware_event
                log_hardware_event('vna', 'DEBUG', f'VNA sweep completed with status: {self.vna_status}')
            except:
                pass

    def _collect_data(self):
        """Collect and save data point with improved error handling"""
        try:
            if not self._test_running or not hasattr(self, 'data_file') or self.data_file.closed:
                self._cleanup_data_collection()
                return
            
            current_time = time.time() - self.test_start_time
            
            # Get measurements with timeouts
            try:
                angle = self.hardware.get_angle(timeout=0.5)
            except:
                angle = None
                
            try:
                temperature = self.hardware.get_temperature(timeout=0.5)
            except:
                temperature = None
            
            # Create data point
            data_point = {
                'time_point': current_time,
                'tilt_angle': angle,
                'temperature': temperature
            }
            
            # Only emit if values have changed
            if self.last_data_point != data_point:
                self.data_collected_signal.emit(data_point)
                self.last_data_point = data_point.copy()
            
            # Save to file
            self._save_data_point(current_time, angle, temperature)
            
        except Exception as e:
            self.logger.error(f"Error collecting data: {str(e)}")
            # Don't stop collection on single error

    def _suppress_logging(self):
        """Context manager to temporarily suppress logging"""
        class SuppressLogging:
            def __enter__(self):
                self.old_level = hardware_logger.level
                hardware_logger.setLevel(logging.ERROR)
                return self
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                hardware_logger.setLevel(self.old_level)
                
        return SuppressLogging()
        
    def _save_data_point(self, time_point, tilt_angle, temperature):
        """Save data point to CSV file
        
        Args:
            time_point (float): Time point in seconds
            tilt_angle (float): Tilt angle in degrees
            temperature (float): Temperature in Celsius
        """
        try:
            if not self.data_file:
                return
                
            # Create data row with matching fieldnames
            row = {
                'Time': f"{time_point:.1f}",
                'Angle': f"{tilt_angle:.1f}" if tilt_angle is not None else "N/A",
                'Temperature': f"{temperature:.1f}" if temperature is not None else "N/A"
            }
            
            # Write to CSV
            self.csv_writer.writerow(row)
            self.data_file.flush()  # Ensure data is written immediately
            
        except Exception as e:
            self.logger.error(f"Error saving data point: {str(e)}")
            
    def _run_test_sequence(self, angle):
        """Run a single test sequence at the given angle
        
        Args:
            angle (float): Target tilt angle in degrees
            
        Returns:
            bool: True if sequence completed successfully, False otherwise
        """
        try:
            # Log start of sequence
            self.logger.info(f"Starting test sequence at {angle:.1f}°")
            
            # Get dwell time from parameters
            dwell_time = self.test_parameters.get('dwell_time', 15)
            
            # 1. Move to target angle
            self.logger.info(f"Moving to {angle:.1f}°")
            if not self.hardware.move_to_angle(angle):
                self.logger.error(f"Failed to move to angle {angle:.1f}°")
                return False
                
            # 2. Wait for movement to complete and system to stabilize
            self.logger.info(f"Waiting {dwell_time}s for system to stabilize...")
            time.sleep(dwell_time)
            
            # 3. Get current tilt angle for verification
            current_angle = self.hardware.get_tilt()
            if current_angle is None:
                self.logger.error("Failed to read current tilt angle")
                return False
                
            # Verify we're at the target angle within tolerance (±0.1°)
            if abs(current_angle - angle) > 0.1:
                self.logger.warning(f"Angle error: target={angle:.1f}°, actual={current_angle:.1f}°")
            
            # 4. Get current temperature
            temperature = self.hardware.get_temperature()
            if temperature is None:
                self.logger.warning("Failed to read temperature")
            
            # 5. Record measurements
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data = {
                'timestamp': timestamp,
                'target_angle': angle,
                'measured_angle': current_angle,
                'temperature': temperature if temperature is not None else "N/A"
            }
            
            # Emit data for real-time updates
            self.data_collected_signal.emit(data)
            
            # Save to CSV if data collection is active
            if hasattr(self, 'csv_writer') and self.csv_writer:
                self.csv_writer.writerow(data)
                self.data_file.flush()
                
            return True
            
        except Exception as e:
            self.logger.error(f"Test sequence failed: {str(e)}")
            return False

    def _generate_test_sequence(self, parameters):
        """Generate and return the test sequence commands
        
        Args:
            parameters (dict): Test parameters
            
        Returns:
            list: List of commands and wait times
        """
        try:
            min_angle = parameters.get('min_tilt', -30.0)
            max_angle = parameters.get('max_tilt', 30.0)
            increment = parameters.get('tilt_increment', 1.0)
            oil_level_time = parameters.get('oil_level_time', 15)
            
            # Calculate test points
            angles = []
            current_angle = min_angle
            while current_angle <= max_angle:
                angles.append(current_angle)
                current_angle += increment
                
            # Generate command sequence
            commands = []
            for angle in angles:
                steps = int(angle / 0.0002)  # Convert angle to steps
                commands.append(f"MOVE {steps} steps ({angle:.1f}°)")
                commands.append(f"Wait 5 seconds for motor movement")
                commands.append(f"Wait {oil_level_time} seconds for oil to level")
                commands.append(f"Take temperature reading")
                commands.append(f"Take tilt reading")
                commands.append(f"Trigger VNA sweep")
                commands.append(f"Wait 10 seconds for VNA sweep")
                commands.append("---")  # Separator between angle sequences
                
            return commands
            
        except Exception as e:
            self.logger.error(f"Error generating test sequence: {str(e)}")
            return []

    def start_test(self, parameters):
        """Start a new test sequence
        
        Args:
            parameters (dict): Test parameters
            
        Returns:
            bool: True if test started successfully, False otherwise
        """
        if self._test_running:
            self.logger.error("Test already in progress")
            return False
            
        if not self._validate_parameters(parameters):
            return False
            
        # Start test in background thread
        self._test_thread = Thread(target=self._run_test, args=(parameters,))
        self._test_thread.daemon = True
        self._test_thread.start()
        return True
        
    def stop_test(self):
        """Stop the current test sequence"""
        if self._test_running:
            self.logger.info("Stopping test sequence...")
            self._test_running = False
            if self._test_thread:
                self._test_thread.join(timeout=5.0)
        else:
            self.logger.warning("No test running to stop")

    def pause_test(self):
        """Pause or resume the current test
        
        Returns:
            bool: True if test paused/resumed successfully, False otherwise
        """
        try:
            with self._lock:
                if not self._test_running:
                    self.logger.warning("No test running")
                    return False
                
                self._test_paused = not self._test_paused
                status = "paused" if self._test_paused else "resumed"
                self.logger.info(f"Test {status}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to pause/resume test: {str(e)}")
            return False

    def is_test_running(self):
        """Check if a test is currently running
        
        Returns:
            bool: True if test is running, False otherwise
        """
        return self._test_running

    def is_test_paused(self):
        """Check if the current test is paused
        
        Returns:
            bool: True if test is paused, False otherwise
        """
        return self._test_paused

    def _run_test_routine(self):
        """Run the test sequence with improved thread safety"""
        try:
            # Get test parameters under lock
            with self._lock:
                if not self._test_running:
                    return
                
                parameters = self.test_parameters.copy()  # Make a thread-safe copy
                if not parameters:
                    raise ValueError("No test parameters set")
                
                min_angle = parameters.get('min_tilt', -30.0)
                max_angle = parameters.get('max_tilt', 30.0)
                increment = parameters.get('tilt_increment', 1.0)
                
                # Initialize progress tracking
                total_steps = int((max_angle - min_angle) / increment) + 1
                current_step = 0
                
                # Store test state locally
                test_id = self.current_run
            
            # Main test loop with periodic state checks
            current_angle = min_angle
            while current_angle <= max_angle:
                # Check if test is still valid
                with self._lock:
                    if not self._test_running or test_id != self.current_run:
                        break
                    
                    if self._test_paused:
                        time.sleep(0.1)  # Short sleep when paused
                        continue
                
                # Run single test sequence
                success = self._run_test_sequence(current_angle)
                if not success:
                    self.logger.error(f"Test sequence failed at angle {current_angle}")
                    break
                
                # Update progress atomically
                with self._lock:
                    if test_id == self.current_run:  # Ensure we're still in the same test
                        current_step += 1
                        progress = int((current_step / total_steps) * 100)
                        self.progress_updated.emit(progress)
                
                # Move to next angle
                current_angle += increment
            
            # Test completion
            with self._lock:
                if test_id == self.current_run:  # Only cleanup if it's still the same test
                    self._test_running = False
                    self._cleanup_data_collection()
                    self.test_completed.emit({'status': 'completed'})
                
        except Exception as e:
            self.logger.error(f"Test routine failed: {str(e)}")
            with self._lock:
                self._test_running = False
                self._cleanup_data_collection()
                self.test_completed.emit({'status': 'failed', 'error': str(e)})

    def _validate_parameters(self, parameters):
        """Validate test parameters according to SBIR requirements
        
        Args:
            parameters (dict): Parameters to validate
            
        Returns:
            bool: True if parameters are valid, False otherwise
        """
        try:
            required_params = ['min_tilt', 'max_tilt', 'tilt_increment', 'dwell_time']
            for param in required_params:
                if param not in parameters:
                    self.logger.error(f"Missing required parameter: {param}")
                    return False
                    
            # Validate tilt increment (1° target, 3° worst case)
            if not (0.1 <= parameters['tilt_increment'] <= 3.0):
                self.logger.error("Tilt increment must be between 0.1° and 3.0°")
                return False
                
            # Validate min/max tilt (±30° range)
            if not (-30.0 <= parameters['min_tilt'] <= 30.0):
                self.logger.error("Minimum tilt must be between -30.0° and 30.0°")
                return False
                
            if not (-30.0 <= parameters['max_tilt'] <= 30.0):
                self.logger.error("Maximum tilt must be between -30.0° and 30.0°")
                return False
                
            if parameters['min_tilt'] >= parameters['max_tilt']:
                self.logger.error("Minimum tilt must be less than maximum tilt")
                return False
                
            # Validate dwell time (for system stabilization)
            if not (5 <= parameters['dwell_time'] <= 60):
                self.logger.error("Dwell time must be between 5 and 60 seconds")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Parameter validation error: {str(e)}")
            return False
        
    def send_command(self, command, retry_count=2, retry_delay=1):
        """Send command to hardware with improved error handling and retry logic
        
        Args:
            command (str): Command to send
            retry_count (int): Number of retries on failure
            retry_delay (float): Delay between retries in seconds
        """
        if not self.hardware_initialized:
            self.logger.error("Hardware not initialized")
            return False
            
        for attempt in range(retry_count + 1):
            try:
                # Parse command
                cmd_parts = command.split()
                cmd_type = cmd_parts[0].upper()
                
                # Handle different commands
                if cmd_type == 'TEST':
                    return self._run_self_test()
                elif cmd_type == 'STATUS':
                    return self._check_status()
                elif cmd_type == 'TEMP':
                    return self._read_temperature()
                elif cmd_type == 'MOVE':
                    if len(cmd_parts) != 2:
                        self.logger.error("MOVE command requires steps parameter")
                        return False
                    try:
                        steps = int(cmd_parts[1])
                        return self._move_motor(steps)
                    except ValueError:
                        self.logger.error("Invalid steps value")
                        return False
                elif cmd_type == 'HOME':
                    return self._home_motor()
                elif cmd_type == 'STOP':
                    return self._stop_motor()
                elif cmd_type == 'CALIBRATE':
                    return self._calibrate_system()
                elif cmd_type == 'EMERGENCY_STOP':
                    return self._emergency_stop()
                else:
                    self.logger.error(f"Unknown command: {command}")
                    return False
                    
            except Exception as e:
                if attempt < retry_count:
                    self.logger.warning(f"Command failed (attempt {attempt + 1}): {str(e)}")
                    time.sleep(retry_delay)
                    continue
                else:
                    self.logger.error(f"Command failed after {retry_count + 1} attempts: {str(e)}")
                    return False
                    
        return False
        
    def _run_self_test(self):
        """Run system self-test"""
        try:
            self.logger.info("=== Running System Self-Test ===")
            
            # Test VNA connection
            self.logger.info("1. Testing VNA connection...")
            if not self._check_vna_connection():
                self.logger.error("VNA connection test failed")
                return False
            self.logger.info("VNA connection OK")
            
            # Test motor movement
            self.logger.info("2. Testing motor movement...")
            if not self._move_motor(100):
                self.logger.error("Forward motor movement failed")
                return False
            time.sleep(1)  # Wait for movement
            
            if not self._move_motor(-100):
                self.logger.error("Reverse motor movement failed")
                return False
            self.logger.info("Motor movement OK")
            
            # Test temperature sensor
            self.logger.info("3. Testing temperature sensor...")
            temp = self._read_temperature()
            if temp is None:
                self.logger.error("Temperature sensor test failed")
                return False
            self.logger.info(f"Temperature sensor OK ({temp:.2f}°C)")
            
            # Test tilt sensor
            self.logger.info("4. Testing tilt sensor...")
            angle = self._get_current_angle()
            if angle is None:
                self.logger.error("Tilt sensor test failed")
                return False
            self.logger.info(f"Tilt sensor OK ({angle:.2f}°)")
            
            self.logger.info("=== Self-test completed successfully ===")
            return True
            
        except Exception as e:
            self.logger.error(f"Self-test failed: {str(e)}")
            return False
            
    def _check_status(self):
        """Check system status"""
        try:
            status = {
                'vna_connected': self._check_vna_connection(),
                'motor_homed': self._check_motor_homed(),
                'temperature': self._read_temperature(),
                'current_angle': self._get_current_angle()
            }
            
            self.logger.info(f"System status: {status}")
            return True
            
        except Exception as e:
            self.logger.error(f"Status check failed: {str(e)}")
            return False
            
    def _read_temperature(self):
        """Read temperature from sensor"""
        try:
            temp = self.hardware.get_temperature()
            if temp is not None:
                self.logger.info(f"Temperature: {temp:.1f}°C")
                return temp
            else:
                self.logger.error("Failed to read temperature")
                return None
        except Exception as e:
            self.logger.error(f"Temperature read failed: {str(e)}")
            return None
            
    def _move_motor(self, steps):
        """Move stepper motor with precise step control
        
        Args:
            steps (int): Number of steps to move (positive = clockwise)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Calculate angle using precise step size (0.0002 degrees per step)
            angle = steps * 0.0002
            self.logger.info(f"\033[95mMOTOR: Moving to {angle:.4f}° ({steps} steps)\033[0m")  # Purple color
            
            # Send movement command
            success = self.hardware.move_to_angle(angle)
            
            if success:
                self.logger.info(f"\033[95mMOTOR: Movement initiated\033[0m")  # Purple color
                return True
            else:
                self.logger.error("\033[95mMOTOR: Failed to initiate movement\033[0m")  # Purple color
                return False
                
        except Exception as e:
            self.logger.error(f"\033[95mMOTOR: Movement failed: {str(e)}\033[0m")  # Purple color
            return False
            
    def _home_motor(self):
        """Home the stepper motor"""
        try:
            self.logger.info("Starting motor homing sequence")
            success = self.hardware.home()
            if success:
                self.logger.info("Motor homed successfully to 0°")
                return True
            else:
                self.logger.error("Failed to home motor")
                return False
        except Exception as e:
            self.logger.error(f"Homing failed: {str(e)}")
            return False
            
    def _stop_motor(self):
        """Stop motor movement"""
        try:
            success = self.hardware.stop()
            if success:
                self.logger.info("Motor stopped")
                return True
            else:
                self.logger.error("Failed to stop motor")
                return False
        except Exception as e:
            self.logger.error(f"Stop failed: {str(e)}")
            return False
            
    def _emergency_stop(self):
        """Emergency stop all movement"""
        try:
            # Set flags first to prevent further operations
            self.test_running = False
            self.test_paused = False
            
            # Try to stop hardware
            try:
                success = self.hardware.emergency_stop()
                if success:
                    self.logger.warning("EMERGENCY STOP activated")
                    return True
                else:
                    self.logger.error("Failed to activate emergency stop")
                    return False
            except Exception as e:
                self.logger.error(f"Hardware emergency stop failed: {str(e)}")
                return False
                
        except Exception as e:
            self.logger.error(f"Emergency stop failed: {str(e)}")
            # Even if hardware command fails, ensure we're in a stopped state
            self.test_running = False
            self.test_paused = False
            return False
        finally:
            # Always ensure we're in a stopped state
            self.test_running = False
            self.test_paused = False
            
            # Try to reset hardware connection
            try:
                self.hardware.reset()
            except Exception as e:
                self.logger.error(f"Failed to reset hardware: {str(e)}")

    def _calibrate_system(self):
        """Calibrate the system"""
        try:
            success = self.hardware.calibrate()
            if success:
                self.logger.info("Calibration completed successfully")
                return True
            else:
                self.logger.error("Failed to calibrate system")
                return False
        except Exception as e:
            self.logger.error(f"Calibration failed: {str(e)}")
            return False
            
    def _check_vna_connection(self):
        """Check VNA connection status"""
        try:
            # TODO: Implement actual VNA connection check
            return True
        except Exception:
            return False
            
    def _check_motor_homed(self):
        """Check if motor is homed"""
        try:
            # TODO: Replace with actual home sensor check
            # For now, assume motor is homed
            return True
            
        except Exception as e:
            self.logger.error(f"Home check failed: {str(e)}")
            return False
            
    def _get_current_angle(self):
        """Get current motor angle"""
        try:
            angle = self.hardware.get_angle()
            if angle is not None:
                return round(angle, 4)
            else:
                self.logger.error("Failed to read angle")
                return None
        except Exception as e:
            self.logger.error(f"Angle read failed: {str(e)}")
            return None
        
    def get_connection_status(self):
        """Get current connection status
        
        Returns:
            dict: Dictionary of connection states
        """
        # TODO: Implement actual connection checking
        return self.connection_states
        
    def update_connection_status(self, device, status):
        """Update connection status for a device
        
        Args:
            device (str): Device name ('vna', 'tilt', or 'temp')
            status (bool): Connection status
        """
        if device in self.connection_states:
            self.connection_states[device] = status
            self.connection_status_updated.emit(self.connection_states)
            
            # Log status change
            status_str = "Connected" if status else "Not Connected"
            gui_logger.info(f"{device.upper()} {status_str}")
            
            # Update hardware logger
            log_hardware_event(device, 'INFO', f"Connection status: {status_str}")
        
    def update_test_parameters(self, parameters):
        """Update test parameters
        
        Args:
            parameters (dict): Dictionary containing test parameters
        """
        try:
            # Validate parameters
            required_params = ['tilt_increment', 'min_tilt', 'max_tilt', 'oil_level_time']
            for param in required_params:
                if param not in parameters:
                    gui_logger.error(f"Missing required parameter: {param}")
                    return False
                    
            # Update configuration
            self.config.update_test_parameters(parameters)
            gui_logger.info("Test parameters updated successfully")
            return True
            
        except Exception as e:
            gui_logger.error(f"Error updating test parameters: {str(e)}")
            return False
        
    def poll_connections(self):
        """Poll hardware connections with improved error handling"""
        try:
            if not hasattr(self, 'hardware') or not self.hardware:
                return
            
            # Update connection status
            self._update_connection_status()
            
            # Check if reconnection is needed
            if not any(self.connection_states.values()):
                self.logger.warning("All hardware disconnected, attempting reconnection...")
                self._start_hardware_initialization()
            
        except Exception as e:
            self.logger.error(f"Error polling connections: {str(e)}")
            self._reset_connection_states()

    def update_settings(self, settings):
        """Update application settings
        
        Args:
            settings (dict): Dictionary containing settings to update
                {
                    'vna': {'key': str, 'port': str},
                    'data_paths': {
                        'vna': str,
                        'temperature': str, 
                        'results': str
                    }
                }
        """
        try:
            # Update VNA settings
            if 'vna' in settings:
                vna_settings = settings['vna']
                if 'key' in vna_settings:
                    self.vna_trigger_key = vna_settings['key']
                if 'port' in vna_settings:
                    self.vna_port = vna_settings['port']
                    
            # Update data paths
            if 'data_paths' in settings:
                paths = settings['data_paths']
                if 'vna' in paths:
                    self.vna_data_path = paths['vna']
                if 'temperature' in paths:
                    self.temperature_data_path = paths['temperature']
                if 'results' in paths:
                    self.results_path = paths['results']
                    
            # Save settings to config file
            self.save_settings()
            
            self.logger.info("Settings updated successfully")
            
        except Exception as e:
            self.logger.error(f"Error updating settings: {str(e)}")
            raise

    def save_settings(self):
        """Save current settings to config file"""
        try:
            config = {
                'vna': {
                    'key': self.vna_trigger_key,
                    'port': self.vna_port
                },
                'data_paths': {
                    'vna': self.vna_data_path,
                    'temperature': self.temperature_data_path,
                    'results': self.results_path
                }
            }
            
            # Save to YAML file
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
                
            self.logger.info(f"Settings saved to {config_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving settings: {str(e)}")
            raise

    def handle_arduino_data(self, data):
        """Handle incoming Arduino serial data
        
        Args:
            data (str): Data received from Arduino
        """
        # Send Arduino data to logger with ARDUINO type
        self.logger.append_message(data, 'ARDUINO')
        
        # Process data for plots if needed
        try:
            # Parse data and update plots if it contains tilt or temperature data
            if 'TILT:' in data:
                angle = float(data.split('TILT:')[1].strip())
                self.data_collected_signal.emit({
                    'time_point': time.time() - self.test_start_time,
                    'tilt_angle': angle
                })
            elif 'TEMP:' in data:
                temp = float(data.split('TEMP:')[1].strip())
                self.data_collected_signal.emit({
                    'time_point': time.time() - self.test_start_time,
                    'temperature': temp
                })
        except (ValueError, IndexError) as e:
            pass  # Silently ignore parsing errors for non-data messages

    def run_web_server(self, host='0.0.0.0', port=5000):
        """Start the web server for remote monitoring
        
        Args:
            host (str): Host address to bind to
            port (int): Port number to listen on
        """
        try:
            from flask import Flask, jsonify
            import threading
            
            app = Flask(__name__)
            
            @app.route('/status')
            def get_status():
                return jsonify({
                    'test_running': self.test_running,
                    'test_paused': self.test_paused,
                    'current_angle': self.current_angle,
                    'connection_states': self.connection_states
                })
            
            @app.route('/temperature')
            def get_temperature():
                temp = self.hardware.get_temperature()
                return jsonify({'temperature': temp})
            
            @app.route('/angle')
            def get_angle():
                angle = self.hardware.get_angle()
                return jsonify({'angle': angle})
            
            def run_server():
                app.run(host=host, port=port)
            
            # Start server in a separate thread
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            self.logger.info(f"Web server started on http://{host}:{port}")
            
        except ImportError:
            self.logger.error("Flask not installed. Web server functionality disabled.")
        except Exception as e:
            self.logger.error(f"Failed to start web server: {str(e)}")

    def connect_hardware(self, max_retries=3):
        """Connect to hardware with retry
        
        Args:
            max_retries (int): Maximum number of connection attempts
        """
        for attempt in range(max_retries):
            try:
                if self.hardware.connect():
                    self.logger.info("Connected to Arduino successfully")
                    return True
                else:
                    self.logger.warning(f"Connection attempt {attempt + 1} failed")
            except Exception as e:
                self.logger.error(f"Connection error: {str(e)}")
            
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry
        
        self.logger.error("Failed to connect to Arduino after multiple attempts")
        return False

    def _start_hardware_initialization(self):
        """Start hardware initialization with retry mechanism"""
        try:
            self.logger.info("Starting hardware initialization...")
            if self.connect():
                self.hardware_initialized = True
                self.logger.info("Hardware initialization complete")
            else:
                self.logger.warning("Hardware initialization failed, will retry periodically")
                self.hardware_initialized = False
        except Exception as e:
            self.logger.error(f"Error during hardware initialization: {str(e)}")
            self.hardware_initialized = False

    def connect(self):
        """Connect to all hardware components
        
        Returns:
            bool: True if all critical components connected successfully
        """
        try:
            with self._lock:
                # Try to connect to Arduino
                if not self.hardware.connect():
                    self.logger.warning("Could not connect to Arduino")
                    self.connection_states['tilt'] = False
                    self.connection_states['temp'] = False
                    return False
                
                # Update connection states
                self.connection_states['tilt'] = True
                self.connection_states['temp'] = True
                
                # Emit connection status update
                self.connection_status_updated.emit(self.connection_states)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error connecting to hardware: {str(e)}")
            return False

    def is_connected(self):
        """Check if hardware is connected
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            with self._lock:
                return self.hardware.is_connected()
        except Exception as e:
            self.logger.error(f"Error checking connection status: {str(e)}")
            return False

    def disconnect(self):
        """Disconnect from hardware safely"""
        try:
            with self._lock:
                if self.hardware:
                    self.hardware.cleanup()
                
                # Update connection states
                self.connection_states['tilt'] = False
                self.connection_states['temp'] = False
                
                # Emit connection status update
                self.connection_status_updated.emit(self.connection_states)
                
        except Exception as e:
            self.logger.error(f"Error disconnecting hardware: {str(e)}")

    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except:
            pass  # Suppress any errors during deletion

    def _run_test(self, parameters):
        """Run the SBIR test sequence
        
        Args:
            parameters (dict): Test parameters
        """
        try:
            self.logger.info("Starting SBIR test sequence...")
            self.test_running = True
            
            # Initialize and calibrate system
            self.logger.info("Calibrating system...")
            response = self.hardware.send_command("CALIBRATE")
            if response and isinstance(response, dict) and response.get('error'):
                raise Exception("Failed to calibrate system")
            
            # Initialize data collection
            test_data = []
            current_tilt = parameters['min_tilt']
            
            # Constants for motor control
            STEPS_PER_DEGREE = 200.0 / 360.0  # 200 steps per revolution
            
            while current_tilt <= parameters['max_tilt'] and self.test_running:
                # Calculate steps needed to reach target angle
                current_angle = self.hardware.get_tilt()
                if current_angle is None:
                    raise Exception("Failed to read current angle")
                    
                steps = int((current_tilt - current_angle) * STEPS_PER_DEGREE)
                
                # Move to target tilt angle
                self.logger.info(f"Moving to tilt angle: {current_tilt}°")
                response = self.hardware.send_command(f"MOVE {steps}")
                if response and isinstance(response, dict) and response.get('error'):
                    raise Exception(f"Failed to move to angle {current_tilt}°")
                
                # Wait for system to stabilize
                self.logger.info(f"Waiting {parameters['dwell_time']} seconds for stabilization...")
                time.sleep(parameters['dwell_time'])
                
                # Take measurements
                tilt = self.hardware.get_tilt()
                if tilt is None:
                    raise Exception("Failed to read tilt angle")
                    
                temp = self.hardware.get_temperature()
                if temp is None:
                    self.logger.warning("Failed to read temperature")
                    temp = 0.0
                    
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Record data point
                data_point = {
                    'timestamp': timestamp,
                    'target_tilt': current_tilt,
                    'measured_tilt': tilt,
                    'temperature': temp
                }
                test_data.append(data_point)
                self.logger.info(f"Recorded data point: {data_point}")
                
                # Move to next tilt angle
                current_tilt += parameters['tilt_increment']
                
            # Test complete
            if self.test_running:
                self.logger.info("Test sequence completed successfully")
                self._save_test_data(test_data)
            else:
                self.logger.info("Test sequence stopped by user")
                
        except Exception as e:
            self.logger.error(f"Error during test sequence: {str(e)}")
            self.test_running = False
            
        finally:
            # Return to zero tilt
            try:
                current_angle = self.hardware.get_tilt()
                if current_angle is not None:
                    steps = int(-current_angle * STEPS_PER_DEGREE)
                    self.hardware.send_command(f"MOVE {steps}")
            except:
                pass
            self.test_running = False

    def _save_test_data(self, test_data):
        """Save test data to CSV file
        
        Args:
            test_data (list): List of test data points
        """
        try:
            # Create timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_run_{timestamp}.csv"
            filepath = os.path.join("data", filename)
            
            # Ensure data directory exists
            os.makedirs("data", exist_ok=True)
            
            # Write data to CSV
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['timestamp', 'target_tilt', 'measured_tilt', 'temperature'])
                writer.writeheader()
                writer.writerows(test_data)
                
            self.logger.info(f"Test data saved to {filepath}")
            
        except Exception as e:
            self.logger.error(f"Error saving test data: {str(e)}")
            
        # Update test runs log
        try:
            runs_file = os.path.join("data", "test_runs.csv")
            run_info = {
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'filename': filename,
                'min_tilt': min(d['target_tilt'] for d in test_data),
                'max_tilt': max(d['target_tilt'] for d in test_data),
                'num_points': len(test_data)
            }
            
            # Create or append to test runs log
            file_exists = os.path.exists(runs_file)
            with open(runs_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['timestamp', 'filename', 'min_tilt', 'max_tilt', 'num_points'])
                if not file_exists:
                    writer.writeheader()
                writer.writerow(run_info)
                
        except Exception as e:
            self.logger.error(f"Error updating test runs log: {str(e)}")

    def update_connection_status(self):
        """Update connection status"""
        try:
            # Get hardware connection status
            hardware_connected = self.hardware.is_connected()
            
            # Update connection states
            self.connection_states['tilt'] = hardware_connected
            self.connection_states['temp'] = hardware_connected
            
            # Emit status update
            self.connection_status_updated.emit(self.connection_states)
            
        except Exception as e:
            self.logger.error(f"Error updating connection status: {str(e)}")
            
    def get_connection_status(self):
        """Get current connection status
        
        Returns:
            dict: Connection status for each component
        """
        return self.connection_states.copy()
        
    def poll_connections(self):
        """Poll hardware connections periodically"""
        try:
            self.update_connection_status()
        except Exception as e:
            self.logger.error(f"Error polling connections: {str(e)}")
            # Reset connection states on error
            self.connection_states = {
                'tilt': False,
                'temp': False
            }
            self.connection_status_updated.emit(self.connection_states)

    def emergency_stop(self):
        """Trigger emergency stop
        
        Returns:
            bool: True if emergency stop successful, False otherwise
        """
        try:
            # Stop any running test
            self.stop_test()
            
            # Send emergency stop command
            response = self.hardware.send_command("EMERGENCY_STOP")
            if response and isinstance(response, dict) and not response.get('error'):
                self.logger.info("Emergency stop triggered")
                return True
            else:
                self.logger.error("Failed to trigger emergency stop")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during emergency stop: {str(e)}")
            return False