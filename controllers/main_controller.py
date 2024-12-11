import time
from datetime import datetime
import os
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication
import yaml

from utils.logger import gui_logger, log_test_results, hardware_logger, log_hardware_event
from utils.config import Config

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
        self.test_running = False
        self.test_paused = False
        self.current_run = 0
        self.current_angle = 0.0
        self.start_time = None
        
        # Initialize connection states
        self.connection_states = {
            'vna': False,
            'tilt': False,
            'temp': False
        }
        
        # Set up data directories
        self.setup_data_directories()
        
        # Start connection status polling
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.poll_connections)
        self.connection_timer.start(5000)  # Poll every 5 seconds
        
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
        key = self.config.get('vna', 'key_event', default='F5')
        app = QApplication.instance()
        
        try:
            # Create and post key press/release events
            key_event = QKeyEvent(QKeyEvent.Type.KeyPress, ord(key), app.keyboardModifiers())
            app.postEvent(app.focusWidget(), key_event)
            
            # Small delay between press and release
            time.sleep(0.1)
            
            key_event = QKeyEvent(QKeyEvent.Type.KeyRelease, ord(key), app.keyboardModifiers())
            app.postEvent(app.focusWidget(), key_event)
            
            log_hardware_event('vna', 'DEBUG', 'VNA key event sent', key=key)
        except Exception as e:
            log_hardware_event('vna', 'ERROR', 'Failed to send VNA key event', key=key, error=str(e))
        
    def start_test(self, parameters):
        """Start test sequence with given parameters
        
        Args:
            parameters (dict): Test parameters including tilt_increment, min_tilt,
                             max_tilt, and oil_level_time
        """
        if self.test_running:
            return
            
        self.test_running = True
        self.test_paused = False
        self.current_run += 1
        self.start_time = datetime.now()
        
        # Update configuration
        self.config.update_test_parameters(parameters)
        
        # Start test sequence
        try:
            # Initial calibration (only on first test)
            if self.current_run == 1:
                gui_logger.info("Performing initial calibration...")
                self.send_command('CALIBRATE')
                time.sleep(2)  # Wait for calibration
                
            # Home the tilt platform and set to 0 degrees
            gui_logger.info("Homing tilt platform...")
            self.send_command('HOME')
            time.sleep(1)  # Wait for homing
            
            # Calculate test angles
            increment = parameters['tilt_increment']
            min_tilt = parameters['min_tilt']
            max_tilt = parameters['max_tilt']
            angles = list(range(int(min_tilt/increment), int(max_tilt/increment) + 1))
            angles = [a * increment for a in angles]
            
            total_angles = len(angles)
            angles_tested = []
            
            # Log test start
            gui_logger.info(f"Starting test run #{self.current_run}")
            gui_logger.info(f"Test parameters: Increment={increment}°, Range={min_tilt}° to {max_tilt}°")
            
            for i, angle in enumerate(angles):
                if not self.test_running or self.test_paused:
                    break
                    
                # Move to angle
                steps = int(angle / 0.0002)  # Convert angle to steps (1 step = 0.0002 degrees)
                gui_logger.info(f"Moving to {angle}°...")
                self.send_command(f'MOVE {steps}')
                self.current_angle = angle
                self.angle_updated.emit(angle)
                
                # Wait for oil to settle
                gui_logger.info(f"Waiting {parameters['oil_level_time']} seconds for oil stabilization...")
                time.sleep(parameters['oil_level_time'])
                
                # Trigger VNA sweep
                gui_logger.info("Triggering VNA sweep...")
                self.send_vna_key_event()
                
                # Read temperature
                gui_logger.info("Reading temperature...")
                temp_response = self.send_command('TEMP')
                
                # Log data files
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                vna_file = f"data/vna/vna_data_{timestamp}_angle{angle:.1f}.dat"
                temp_file = f"data/temperature/temp_data_{timestamp}_angle{angle:.1f}.dat"
                
                # Save temperature data
                with open(temp_file, 'w') as f:
                    f.write(f"Timestamp: {timestamp}\n")
                    f.write(f"Angle: {angle:.1f}\n")
                    f.write(f"Temperature: {temp_response}\n")
                
                angles_tested.append(angle)
                
                # Update progress
                progress = int((i + 1) / total_angles * 100)
                self.progress_updated.emit(progress)
                gui_logger.info(f"Test progress: {progress}%")
                
            # Return to zero
            gui_logger.info("Returning to 0°...")
            self.send_command('MOVE 0')
            self.current_angle = 0.0
            self.angle_updated.emit(0.0)
            
            # Calculate execution time
            execution_time = datetime.now() - self.start_time
            execution_time_str = str(execution_time).split('.')[0]
            
            # Log test results
            results = {
                'run_number': self.current_run,
                'execution_time': execution_time_str,
                'config': parameters,
                'data_files': {
                    'vna': 'data/vna',
                    'temperature': 'data/temperature'
                },
                'angles_tested': angles_tested
            }
            
            results_file = log_test_results(results, self.current_run)
            gui_logger.info(f"Test completed in {execution_time_str}")
            gui_logger.info(f"Results saved to {results_file}")
            
            # Emit test completed signal
            self.test_completed.emit(results)
            
        except Exception as e:
            gui_logger.error(f"Error during test sequence: {str(e)}")
            self.stop_test()
            
    def pause_test(self):
        """Pause the current test"""
        self.test_paused = True
        gui_logger.info("Test paused")
        
    def resume_test(self):
        """Resume the paused test"""
        self.test_paused = False
        gui_logger.info("Test resumed")
        
    def stop_test(self):
        """Stop the current test"""
        self.test_running = False
        self.test_paused = False
        self.send_command('STOP')
        gui_logger.info("Test stopped")
        
    def send_command(self, command):
        """Send command to hardware
        
        Args:
            command (str): Command to send
        
        Returns:
            bool: True if command was sent successfully
        """
        try:
            # Parse command
            cmd_parts = command.split()
            cmd_type = cmd_parts[0].upper()
            
            # Handle different commands
            if cmd_type == 'TEST':
                self.logger.info("Running system self-test...")
                return self._run_self_test()
                
            elif cmd_type == 'STATUS':
                self.logger.info("Checking system status...")
                return self._check_status()
                
            elif cmd_type == 'TEMP':
                self.logger.info("Reading temperature...")
                return self._read_temperature()
                
            elif cmd_type == 'MOVE':
                if len(cmd_parts) != 2:
                    self.logger.error("MOVE command requires steps parameter")
                    return False
                try:
                    steps = int(cmd_parts[1])
                    self.logger.info(f"Moving {steps} steps...")
                    return self._move_motor(steps)
                except ValueError:
                    self.logger.error("Invalid steps value")
                    return False
                    
            elif cmd_type == 'HOME':
                self.logger.info("Homing motor...")
                return self._home_motor()
                
            elif cmd_type == 'STOP':
                self.logger.info("Stopping motor...")
                return self._stop_motor()
                
            elif cmd_type == 'CALIBRATE':
                self.logger.info("Calibrating system...")
                return self._calibrate_system()
                
            elif cmd_type == 'EMERGENCY_STOP':
                self.logger.warning("Emergency stop engaged!")
                return self._emergency_stop()
                
            else:
                self.logger.error(f"Unknown command: {command}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending command: {str(e)}")
            return False
            
    def _run_self_test(self):
        """Run system self-test"""
        try:
            # Test VNA connection
            if not self._check_vna_connection():
                return False
                
            # Test motor movement
            if not self._move_motor(100) or not self._move_motor(-100):
                return False
                
            # Test temperature sensor
            if not self._read_temperature():
                return False
                
            self.logger.info("Self-test completed successfully")
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
            # Simulate temperature reading for now
            # TODO: Replace with actual hardware communication
            import random
            temp = 20.0 + random.uniform(-1.0, 1.0)
            self.logger.info(f"Temperature: {temp:.1f}°C")
            return temp
            
        except Exception as e:
            self.logger.error(f"Temperature read failed: {str(e)}")
            return None
            
    def _move_motor(self, steps):
        """Move stepper motor
        
        Args:
            steps (int): Number of steps to move (positive = clockwise)
        """
        try:
            # Convert steps to degrees for logging
            degrees = steps * 0.0002  # 1 step = ±0.0002 degrees
            self.logger.info(f"Moving motor {steps} steps ({degrees:.4f}°)")
            
            # TODO: Replace with actual motor control
            # For now, simulate movement
            import time
            time.sleep(abs(steps) * 0.001)  # Simulate movement time
            
            return True
            
        except Exception as e:
            self.logger.error(f"Motor movement failed: {str(e)}")
            return False
            
    def _home_motor(self):
        """Home the stepper motor"""
        try:
            self.logger.info("Homing motor...")
            
            # TODO: Replace with actual homing sequence
            # For now, simulate homing
            import time
            time.sleep(2.0)
            
            self.logger.info("Motor homed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Homing failed: {str(e)}")
            return False
            
    def _stop_motor(self):
        """Stop motor movement"""
        try:
            self.logger.info("Stopping motor...")
            # TODO: Replace with actual motor stop command
            return True
            
        except Exception as e:
            self.logger.error(f"Stop failed: {str(e)}")
            return False
            
    def _emergency_stop(self):
        """Emergency stop all movement"""
        try:
            self.logger.warning("EMERGENCY STOP activated")
            # TODO: Replace with actual emergency stop implementation
            self._stop_motor()
            return True
            
        except Exception as e:
            self.logger.error(f"Emergency stop failed: {str(e)}")
            return False
            
    def _calibrate_system(self):
        """Calibrate the system"""
        try:
            self.logger.info("Starting system calibration...")
            
            # Home the motor first
            if not self._home_motor():
                return False
                
            # Move to known positions and verify
            test_angles = [-30, 0, 30]
            for angle in test_angles:
                steps = int(angle / 0.0002)  # Convert angle to steps
                if not self._move_motor(steps):
                    return False
                    
            # Return to zero
            if not self._move_motor(0):
                return False
                
            self.logger.info("Calibration completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Calibration failed: {str(e)}")
            return False
            
    def _check_vna_connection(self):
        """Check VNA connection status"""
        try:
            # TODO: Replace with actual VNA connection check
            # For now, simulate connection
            import random
            connected = random.random() > 0.1  # 90% chance of being connected
            
            if connected:
                self.logger.info("VNA connection verified")
            else:
                self.logger.warning("VNA connection failed")
                
            return connected
            
        except Exception as e:
            self.logger.error(f"VNA connection check failed: {str(e)}")
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
            # TODO: Replace with actual angle reading
            # For now, simulate angle
            import random
            angle = random.uniform(-30.0, 30.0)
            return round(angle, 4)
            
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
        """Poll connection status of all devices"""
        try:
            # Check VNA connection
            vna_status = self.check_vna_connection()
            if vna_status != self.connection_states['vna']:
                self.update_connection_status('vna', vna_status)
                
            # Check tilt sensor connection
            tilt_status = self.check_tilt_connection()
            if tilt_status != self.connection_states['tilt']:
                self.update_connection_status('tilt', tilt_status)
                
            # Check temperature sensor connection
            temp_status = self.check_temp_connection()
            if temp_status != self.connection_states['temp']:
                self.update_connection_status('temp', temp_status)
                
        except Exception as e:
            gui_logger.error(f"Error polling connections: {str(e)}")
            
    def check_vna_connection(self):
        """Check VNA connection status"""
        try:
            # TODO: Implement actual VNA connection check
            return True
        except Exception:
            return False
            
    def check_tilt_connection(self):
        """Check tilt sensor connection status"""
        try:
            response = self.send_command('STATUS')
            return response == "OK"
        except Exception:
            return False
            
    def check_temp_connection(self):
        """Check temperature sensor connection status"""
        try:
            response = self.send_command('TEMP')
            return response != "ERROR"
        except Exception:
            return False
        
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