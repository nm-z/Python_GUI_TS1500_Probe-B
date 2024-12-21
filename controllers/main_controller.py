import time
from datetime import datetime
import os
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication
import yaml
import threading
import csv
import logging

from utils.logger import gui_logger, log_test_results, hardware_logger, log_hardware_event
from utils.config import Config
from hardware.controller import HardwareController

class MainController(QObject):
    # Signals for UI updates
    status_updated = pyqtSignal(dict)
    progress_updated = pyqtSignal(int)
    angle_updated = pyqtSignal(float)
    test_completed = pyqtSignal(dict)
    connection_status_updated = pyqtSignal(dict)
    data_collected_signal = pyqtSignal(dict)  # For real-time data updates
    
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.logger = gui_logger
        self._test_running = False
        self._test_paused = False
        self.current_run = 0
        self.current_angle = 0.0
        
        # Initialize hardware controller with retry mechanism
        self.hardware = HardwareController()
        self.hardware_initialized = False
        
        # Initialize connection states
        self.connection_states = {
            'vna': False,
            'tilt': False,
            'temp': False
        }
        
        # Set up data directories
        self.setup_data_directories()
        
        # Initialize VNA settings
        self.vna_trigger_key = self.config.get('vna', 'key', default='F5')
        self.vna_port = self.config.get('vna', 'port', default='COM1')
        
        # Initialize data paths
        self.vna_data_path = self.config.get('data_paths', 'vna', default='data/vna')
        self.temperature_data_path = self.config.get('data_paths', 'temperature', default='data/temperature')
        self.results_path = self.config.get('data_paths', 'results', default='data/results')
        
        # Start hardware initialization in a separate thread with retry
        self._start_hardware_initialization()
        
        # Start connection status polling with reduced frequency
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.poll_connections)
        self.connection_timer.start(10000)  # Poll every 10 seconds
        
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
        """Send key event to trigger VNA sweep"""
        try:
            self.logger.info(f"\033[93mVNA: Initiating sweep...\033[0m")
            
            # Handle F5 key properly
            from PyQt6.QtCore import Qt
            key = Qt.Key.Key_F5
            
            app = QApplication.instance()
            # Create and post key press/release events with proper key code
            key_event = QKeyEvent(QKeyEvent.Type.KeyPress, key, app.keyboardModifiers())
            app.postEvent(app.focusWidget(), key_event)
            
            time.sleep(0.1)
            
            key_event = QKeyEvent(QKeyEvent.Type.KeyRelease, key, app.keyboardModifiers())
            app.postEvent(app.focusWidget(), key_event)
            
            self.logger.info(f"\033[93mVNA: Sweep completed\033[0m")
            log_hardware_event('vna', 'DEBUG', 'VNA key event sent')
        except Exception as e:
            self.logger.error(f"\033[93mVNA: Failed to send key event: {str(e)}\033[0m")
            log_hardware_event('vna', 'ERROR', 'Failed to send VNA key event', error=str(e))
        
    def _collect_data(self):
        """Collect data continuously for graph updates"""
        try:
            if not self.hardware.is_connected():
                return
                
            # Get current time point
            current_time = time.time() - self.test_start_time
            
            # Collect data every second
            if int(current_time) == current_time:
                with self._suppress_logging():
                    tilt_angle = self.hardware.get_tilt_angle()
                    temperature = self.hardware.get_temperature()
                
                if tilt_angle is not None:
                    self.angle_updated.emit(tilt_angle)
                    self.data_collected_signal.emit({
                        'time_point': current_time,
                        'tilt_angle': tilt_angle
                    })
                    
                if temperature is not None:
                    self.data_collected_signal.emit({
                        'time_point': current_time,
                        'temperature': temperature
                    })
                
        except Exception as e:
            pass  # Silently ignore data collection errors
        
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
        """Run a single test sequence at the given angle"""
        try:
            # 1. Move motor to position
            self.logger.info(f"\033[95mMOTOR: Moving to {angle:.4f}° ({int(angle / 0.0002)} steps)\033[0m")
            if not self._move_motor(int(angle / 0.0002)):
                raise Exception("Failed to move motor")
            
            # 2. Wait for motor movement to complete
            self.logger.info("\033[37mWaiting 5s for motor movement...\033[0m")
            time.sleep(5)
            
            # 3. Wait for oil to level
            oil_level_time = self.test_parameters.get('oil_level_time', 15)
            self.logger.info(f"\033[37mWaiting {oil_level_time}s for oil to level...\033[0m")
            time.sleep(oil_level_time)
            
            # 4. Take measurements after oil has leveled
            # Get temperature reading
            with self._suppress_logging():
                temperature = self.hardware.get_temperature()
            if temperature is not None:
                self.logger.info(f"\033[92mTemperature at {angle:.1f}°: {temperature:.1f}°C\033[0m")
                # Update graph with temperature
                current_time = time.time() - self.test_start_time
                self.data_collected_signal.emit({
                    'time_point': current_time,
                    'temperature': temperature
                })
            
            # Get current tilt angle for verification
            with self._suppress_logging():
                actual_angle = self.hardware.get_tilt_angle()
            if actual_angle is not None:
                self.logger.info(f"\033[92mVerified tilt at {actual_angle:.1f}°\033[0m")
                # Update graph with tilt angle
                self.data_collected_signal.emit({
                    'time_point': current_time,
                    'tilt_angle': actual_angle
                })
            
            # Start VNA sweep
            self.logger.info(f"\033[93mVNA: Starting sweep at {angle:.1f}°...\033[0m")
            self.send_vna_key_event()
            
            # 5. Wait for VNA sweep to complete
            self.logger.info("\033[37mWaiting 10s for VNA sweep...\033[0m")
            time.sleep(10)
            
            # Save data point
            self._save_data_point(current_time, actual_angle or angle, temperature)
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
        """Start a new test with the given parameters"""
        try:
            # First validate hardware connection
            if not self.hardware.is_connected():
                self.logger.error("Cannot start test: Hardware not connected")
                return False
            
            # Check if test is already running
            if self._test_running:
                self.logger.error("Cannot start test: Test already running")
                return False
            
            # Show test sequence dialog first
            from gui.test_parameters_dialog import show_test_sequence
            if not show_test_sequence(None, parameters):
                self.logger.info("Test cancelled by user")
                return False
            
            # If user accepted, start the test
            self.logger.info("\033[95mInitializing test...\033[0m")
            
            # Store test parameters and initialize test state
            self.test_parameters = parameters
            self._test_running = True
            self._test_paused = False
            self._current_angle = None
            self.test_start_time = time.time()
            
            # Start continuous data collection
            self._start_data_collection()
            
            # Emit signal to open plots window
            self.test_started = True  # Flag to indicate test has started
            self.status_updated.emit({'test_started': True})
            
            # Start test sequence in a separate thread
            self.test_thread = threading.Thread(target=self._run_test_routine)
            self.test_thread.start()
            
            self.logger.info("\033[95mTest started\033[0m")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start test: {str(e)}")
            self._test_running = False
            return False

    def _run_test_routine(self):
        """Run the complete test routine"""
        try:
            min_angle = self.test_parameters.get('min_tilt', -30.0)
            max_angle = self.test_parameters.get('max_tilt', 30.0)
            increment = self.test_parameters.get('tilt_increment', 1.0)
            
            # Calculate test points
            angles = []
            current_angle = min_angle
            while current_angle <= max_angle:
                angles.append(current_angle)
                current_angle += increment
            
            # Run test sequence for each angle
            total_points = len(angles)
            for i, angle in enumerate(angles):
                if not self._test_running:  # Check for stop condition
                    break
                    
                if self._test_paused:  # Handle pause
                    while self._test_paused and self._test_running:
                        time.sleep(0.1)
                    if not self._test_running:  # Check if stopped during pause
                        break
                
                # Run test sequence for this angle
                if not self._run_test_sequence(angle):
                    self.logger.error(f"Failed at angle {angle:.1f}°")
                    break
                
                # Update progress
                progress = int((i + 1) * 100 / total_points)
                self.progress_updated.emit(progress)
            
            # Test completed
            self.test_completed.emit({
                'run_number': self.current_run,
                'execution_time': time.time() - self.test_start_time,
                'data_files': {
                    'vna': self.vna_data_path,
                    'temperature': self.temperature_data_path
                }
            })
            
        except Exception as e:
            self.logger.error(f"Test routine failed: {str(e)}")
        finally:
            self._test_running = False
            if self.data_file:
                self.data_file.close()
                self.data_file = None

    def _validate_parameters(self, parameters):
        """Validate test parameters
        
        Args:
            parameters (dict): Parameters to validate
            
        Returns:
            bool: True if parameters are valid, False otherwise
        """
        try:
            required_params = ['tilt_increment', 'min_tilt', 'max_tilt', 'oil_level_time']
            for param in required_params:
                if param not in parameters:
                    self.logger.error(f"Missing required parameter: {param}")
                    return False
                    
            # Validate tilt increment
            if not (0.1 <= parameters['tilt_increment'] <= 3.0):
                self.logger.error("Tilt increment must be between 0.1 and 3.0 degrees")
                return False
                
            # Validate min/max tilt
            if not (-30.0 <= parameters['min_tilt'] <= 0.0):
                self.logger.error("Minimum tilt must be between -30.0 and 0.0 degrees")
                return False
                
            if not (0.0 <= parameters['max_tilt'] <= 30.0):
                self.logger.error("Maximum tilt must be between 0.0 and 30.0 degrees")
                return False
                
            if parameters['min_tilt'] >= parameters['max_tilt']:
                self.logger.error("Minimum tilt must be less than maximum tilt")
                return False
                
            # Validate oil level time
            if not (5 <= parameters['oil_level_time'] <= 60):
                self.logger.error("Oil level time must be between 5 and 60 seconds")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Parameter validation error: {str(e)}")
            return False
        
    def stop_test(self):
        """Stop the test"""
        try:
            if not hasattr(self, '_test_running') or not self._test_running:
                return
                
            # Stop data collection
            if hasattr(self, 'data_timer') and self.data_timer:
                self.data_timer.stop()
                self.data_timer = None
            
            # Close data file
            if hasattr(self, 'data_file') and self.data_file:
                self.data_file.close()
                self.data_file = None
            
            self._test_running = False
            self.logger.info("Test stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping test: {str(e)}")
            
    def cleanup(self):
        """Clean up resources before exit"""
        try:
            # Stop test if running
            self.stop_test()
            
            # Stop all timers first
            for timer_attr in ['connection_timer', 'data_timer']:
                if hasattr(self, timer_attr):
                    timer = getattr(self, timer_attr)
                    if timer is not None:
                        timer.stop()
                        setattr(self, timer_attr, None)
            
            # Stop all threads
            for thread_attr in ['test_thread', 'init_thread']:
                if hasattr(self, thread_attr):
                    thread = getattr(self, thread_attr)
                    if thread is not None and thread.is_alive():
                        thread.join(timeout=0.5)
            
            # Disconnect hardware
            if hasattr(self, 'hardware') and self.hardware:
                try:
                    self.hardware.disconnect()
                except:
                    pass
                self.hardware = None
            
            self.hardware_initialized = False
            
        except Exception as e:
            pass  # Silently ignore cleanup errors
        finally:
            # Force stop all remaining threads
            for thread in threading.enumerate():
                if thread != threading.current_thread() and thread.is_alive():
                    try:
                        thread.join(timeout=0.1)
                    except:
                        pass

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
        """Poll connection status of all components"""
        if not hasattr(self, 'hardware') or not self.hardware_initialized:
            return
        
        try:
            # Skip connection polling during test
            if hasattr(self, '_test_running') and self._test_running:
                return
            
            # Only check hardware connection during initialization
            if not hasattr(self, '_connection_initialized'):
                response = self.hardware.send_command("STATUS", timeout=0.5)
                arduino_ok = response and response.startswith("POS ")
                
                new_states = {
                    'vna': arduino_ok,
                    'tilt': arduino_ok,
                    'temp': arduino_ok
                }
                
                if new_states != self.connection_states:
                    self.connection_states = new_states
                    self.connection_status_updated.emit(new_states)
                
                self._connection_initialized = True
            
        except Exception:
            pass  # Silently ignore connection polling errors

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
        """Start hardware initialization in a separate thread with retry"""
        def init_with_retry():
            max_retries = 2  # Reduced retries
            retry_delay = 2  # Reduced delay
            
            for attempt in range(max_retries):
                if not self._test_running:  # Fixed attribute name
                    return
                    
                try:
                    if self.hardware.connect():
                        self.hardware_initialized = True
                        self.logger.info("Hardware initialization successful")
                        self.poll_connections()  # Update connection status immediately
                        return
                    else:
                        self.logger.warning(f"Hardware initialization attempt {attempt + 1} failed")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            try:
                                self.hardware.disconnect()
                            except:
                                pass
                except Exception as e:
                    self.logger.error(f"Hardware initialization error: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        try:
                            self.hardware.disconnect()
                        except:
                            pass
                            
            self.logger.error("Hardware initialization failed after all retries")
            self.connection_states = {
                'vna': False,
                'tilt': False,
                'temp': False
            }
            self.connection_status_updated.emit(self.connection_states)
            
        self.init_thread = threading.Thread(target=init_with_retry, daemon=True)
        self.init_thread.start()
        
    def initialize_hardware(self):
        """Initialize hardware with improved error handling"""
        try:
            if hasattr(self, 'hardware') and self.hardware.is_connected():
                self.hardware.disconnect()
                
            self.hardware = HardwareController()
            
            # Try to connect multiple times
            for attempt in range(3):
                if attempt > 0:
                    self.logger.info(f"Retrying connection (attempt {attempt + 1}/3)")
                    time.sleep(2)  # Wait between attempts
                    
                if self.hardware.connect():
                    self.hardware_initialized = True
                    self.update_status("Hardware initialized successfully")
                    return True
                    
            self.hardware_initialized = False
            self.update_status("Failed to initialize hardware after 3 attempts")
            return False
            
        except Exception as e:
            self.logger.error(f"Hardware initialization error: {str(e)}")
            self.hardware_initialized = False
            self.update_status(f"Hardware initialization failed: {str(e)}")
            return False

    def update_status(self, message):
        """Update status message
        
        Args:
            message (str): Status message to display
        """
        self.logger.info(message)
        self.status_updated.emit({'message': message})

    def is_test_running(self):
        """Check if test is running
        
        Returns:
            bool: True if test is running, False otherwise
        """
        return self.test_running
        
    def is_test_paused(self):
        """Check if test is paused
        
        Returns:
            bool: True if test is paused, False otherwise
        """
        return self.test_paused
        
    def pause_test(self):
        """Pause/resume the current test
        
        Returns:
            bool: True if test was paused/resumed successfully, False otherwise
        """
        try:
            if not self.test_running:
                return False
                
            self.test_paused = not self.test_paused
            
            if self.test_paused:
                # Stop data collection
                if hasattr(self, 'data_timer'):
                    self.data_timer.stop()
                self.logger.info("Test paused")
            else:
                # Resume data collection
                if hasattr(self, 'data_timer'):
                    self.data_timer.start()
                self.logger.info("Test resumed")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error pausing/resuming test: {str(e)}")
            return False

    def is_connected(self):
        """Check if hardware is connected"""
        return self.hardware and self.hardware.is_connected()

    def _start_data_collection(self):
        """Start data collection timer"""
        try:
            # Create data file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.data_file = open(f"data/test_run_{timestamp}.csv", 'w', newline='')
            self.csv_writer = csv.DictWriter(self.data_file, fieldnames=['Time', 'Tilt_Angle', 'Temperature'])
            self.csv_writer.writeheader()
            
            # Start data collection timer with higher frequency
            self.data_timer = QTimer()
            self.data_timer.timeout.connect(self._collect_data)
            self.data_timer.start(100)  # Collect data every 100ms
            
            self.test_start_time = time.time()
            self.logger.info("Data collection started")
            
        except Exception as e:
            self.logger.error(f"Error starting data collection: {str(e)}")
            raise