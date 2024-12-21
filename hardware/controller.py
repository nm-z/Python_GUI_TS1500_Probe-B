import serial
import time
import logging
from utils.logger import hardware_logger
import os
import stat
import subprocess
import fcntl
import threading

class HardwareController:
    def __init__(self, port=None, baudrate=250000):
        """Initialize hardware controller
        
        Args:
            port (str): Serial port to use. If None, will auto-detect
            baudrate (int): Baud rate for serial communication
        """
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.logger = hardware_logger
        self.initialized = False
        self._lock = threading.Lock()
        self._port_lock_fd = None
        
    def _detect_arduino_port(self):
        """Auto-detect Arduino Due port
        
        Returns:
            str: Port name if found, None otherwise
        """
        try:
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            self.logger.debug(f"Available ports: {[p.device for p in ports]}")
            
            # First try to find Arduino Due Native port
            for port in ports:
                if "Arduino Due" in port.description and "Native" in port.description:
                    self.logger.info(f"Found Arduino Due native port on {port.device}")
                    return port.device
                    
            # If native port not found, try programming port as fallback
            for port in ports:
                if "Arduino Due" in port.description and "Programming" in port.description:
                    self.logger.info(f"Found Arduino Due programming port on {port.device}")
                    return port.device
                    
            # Last resort: try ttyACM ports
            for port in ports:
                if "ttyACM" in port.device:
                    self.logger.info(f"Found potential Arduino port on {port.device}")
                    return port.device
                    
            self.logger.error("No Arduino Due ports found")
            self.logger.debug("Available ports details:")
            for port in ports:
                self.logger.debug(f"  {port.device}: {port.description} ({port.hwid})")
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error detecting Arduino port: {str(e)}")
            return None
        
    def _check_port_permissions(self, port):
        """Check if we have permission to access the port"""
        try:
            # First check if port exists
            if not os.path.exists(port):
                self.logger.error(f"Port {port} does not exist")
                return False
                
            # Check if we have read/write access
            mode = os.stat(port).st_mode
            if not (mode & stat.S_IRWXU):
                self.logger.error(f"Insufficient permissions for port {port}")
                # Try to fix permissions
                try:
                    os.chmod(port, 0o666)
                    self.logger.info(f"Updated permissions for port {port}")
                    return True
                except Exception as e:
                    self.logger.error(f"Failed to update permissions: {str(e)}")
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Error checking port permissions: {str(e)}")
            return False
            
    def _acquire_port_lock(self, port):
        """Acquire exclusive lock on port using flock"""
        try:
            # First check if port exists
            if not os.path.exists(port):
                self.logger.error(f"Port {port} does not exist")
                return False
                
            # Create lock file path
            lock_path = f"/var/lock/LCK..{os.path.basename(port)}"
            
            # Try to acquire lock
            try:
                self._port_lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
                fcntl.flock(self._port_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except (IOError, OSError) as e:
                if self._port_lock_fd:
                    try:
                        os.close(self._port_lock_fd)
                    except:
                        pass
                    self._port_lock_fd = None
                return False
                
        except Exception as e:
            self.logger.error(f"Error acquiring port lock: {str(e)}")
            return False
            
    def _release_port_lock(self):
        """Release port lock with improved cleanup"""
        if self._port_lock_fd is not None:
            try:
                # Release flock
                fcntl.flock(self._port_lock_fd, fcntl.LOCK_UN)
                
                # Close file descriptor
                os.close(self._port_lock_fd)
                
                # Try to remove lock file
                lock_path = f"/var/lock/LCK..{os.path.basename(self.port)}"
                if os.path.exists(lock_path):
                    try:
                        os.unlink(lock_path)
                    except:
                        pass
                        
            except Exception as e:
                self.logger.error(f"Error releasing port lock: {str(e)}")
            finally:
                self._port_lock_fd = None

    def _release_port(self, port):
        """Try to release a busy port"""
        try:
            # Check permissions first
            if not self._check_port_permissions(port):
                return False
                
            # First try to acquire lock
            if self._acquire_port_lock(port):
                return True
                
            # If lock failed, try to kill processes using the port
            try:
                # Try to find and kill processes using the port
                lsof_output = subprocess.run(['lsof', port], capture_output=True, text=True)
                if lsof_output.returncode == 0:
                    # Extract PIDs
                    pids = set()
                    for line in lsof_output.stdout.splitlines()[1:]:  # Skip header
                        try:
                            pids.add(int(line.split()[1]))
                        except (IndexError, ValueError):
                            continue
                    
                    # Kill processes
                    for pid in pids:
                        try:
                            subprocess.run(['kill', '-9', str(pid)], timeout=1)
                        except subprocess.TimeoutExpired:
                            continue
                
                time.sleep(0.5)  # Short wait after killing processes
                
                # Try to acquire lock again
                if self._acquire_port_lock(port):
                    return True
                    
                # If still failed, try to reset USB device
                port_path = os.path.realpath(port)
                usb_path = os.path.dirname(os.path.dirname(port_path))
                if os.path.exists(os.path.join(usb_path, "authorized")):
                    # Reset USB device
                    with open(os.path.join(usb_path, "authorized"), 'w') as f:
                        f.write('0')
                    time.sleep(0.1)
                    with open(os.path.join(usb_path, "authorized"), 'w') as f:
                        f.write('1')
                    time.sleep(1)
                    
                    # Final attempt to acquire lock
                    return self._acquire_port_lock(port)
                    
            except subprocess.TimeoutExpired:
                self.logger.error("Timeout while trying to kill processes")
            except Exception as e:
                self.logger.error(f"Error during port release: {str(e)}")
                
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to release port: {str(e)}")
            return False
            
    def is_connected(self):
        """Check if hardware is connected
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            # Basic connection check
            if not (hasattr(self, 'serial') and self.serial is not None and self.serial.is_open):
                return False
                
            # Try a simple write/read test
            try:
                self.serial.write(b'\n')  # Send a newline
                self.serial.flush()
                time.sleep(0.1)
                self.serial.reset_input_buffer()  # Clear any response
                return True
            except:
                return False
                
        except:
            return False
        
    def connect(self):
        """Connect to Arduino with improved port handling"""
        with self._lock:  # Thread safety
            try:
                # First disconnect if already connected
                if self.serial and self.serial.is_open:
                    self.disconnect()
                
                # Auto-detect port if not specified
                if not self.port:
                    self.port = self._detect_arduino_port()
                    if not self.port:
                        raise Exception("No Arduino Due found")
                        
                self.logger.info(f"Attempting to connect to Arduino on {self.port}")
                
                # Debug port permissions
                try:
                    import stat
                    mode = os.stat(self.port).st_mode
                    self.logger.info(f"Port permissions: {stat.filemode(mode)}")
                except Exception as e:
                    self.logger.error(f"Error checking port permissions: {str(e)}")

                # Try direct connection first without lock
                try:
                    self.logger.info("Attempting direct connection...")
                    self.serial = serial.Serial(
                        port=self.port,
                        baudrate=self.baudrate,
                        timeout=1,
                        write_timeout=1,
                        exclusive=False,  # Try without exclusive access first
                        rtscts=False,
                        dsrdtr=False,
                        xonxoff=False
                    )
                    self.logger.info("Direct connection successful")
                except Exception as e:
                    self.logger.error(f"Direct connection failed: {str(e)}")
                    # If direct connection fails, try with port release
                    if not self._release_port(self.port):
                        raise Exception(f"Could not acquire port {self.port}")
                    
                    try:
                        self.serial = serial.Serial(
                            port=self.port,
                            baudrate=self.baudrate,
                            timeout=1,
                            write_timeout=1,
                            exclusive=True,
                            rtscts=False,
                            dsrdtr=False,
                            xonxoff=False
                        )
                    except serial.SerialException as e:
                        self._release_port_lock()
                        raise Exception(f"Failed to open port: {str(e)}")
                    
                # Wait for Arduino initialization
                time.sleep(2)  # Initial wait for Arduino reset
                
                # Clear buffers
                self.serial.reset_input_buffer()
                self.serial.reset_output_buffer()
                
                # Send multiple newlines to ensure synchronization
                for _ in range(3):
                    self.serial.write(b'\n')
                    self.serial.flush()
                    time.sleep(0.1)
                
                # If we got this far with an open connection, consider it initialized
                if self.serial and self.serial.is_open:
                    self.initialized = True
                    self.logger.info("Connection established")
                    return True
                
                raise Exception("Failed to establish connection")
                
            except Exception as e:
                self.logger.error(f"Failed to connect to Arduino: {str(e)}")
                self.disconnect()
                return False

    def disconnect(self):
        """Disconnect from Arduino with improved cleanup"""
        try:
            # Use a timeout for acquiring the lock
            if self._lock.acquire(timeout=0.5):  # 500ms timeout
                try:
                    if self.serial:
                        if self.serial.is_open:
                            try:
                                self.send_command("STOP", timeout=0.5)
                            except:
                                pass
                            try:
                                self.serial.reset_input_buffer()
                                self.serial.reset_output_buffer()
                                self.serial.close()
                            except:
                                pass
                        self.serial = None

                    # Release port lock
                    self._release_port_lock()

                    # Reset state
                    self.initialized = False
                    self.logger.info("Disconnected from Arduino")
                finally:
                    self._lock.release()
            else:
                # If lock acquisition times out, force cleanup
                self.force_cleanup()
        except:
            # If any error occurs, force cleanup
            self.force_cleanup()

    def __del__(self):
        """Ensure cleanup on destruction"""
        try:
            self.force_cleanup()  # Use force cleanup instead of normal disconnect
        except:
            pass
        
    def send_command(self, command, timeout=1.0, retry_count=1):
        """Send command to Arduino with improved reliability
        
        Args:
            command (str): Command to send
            timeout (float): Timeout in seconds
            retry_count (int): Number of retries on failure
        """
        with self._lock:  # Thread safety
            if not self.serial or not self.serial.is_open:
                raise Exception("Not connected to Arduino")
                
            for attempt in range(retry_count + 1):
                try:
                    # Clear buffers
                    self.serial.reset_input_buffer()
                    self.serial.reset_output_buffer()
                    
                    # Send command
                    self.logger.debug(f"Sending command: '{command}' (attempt {attempt + 1})")
                    self.serial.write(f"{command}\n".encode())
                    self.serial.flush()
                    
                    # Wait for response
                    start_time = time.time()
                    response = None
                    response_lines = []
                    
                    while (time.time() - start_time) < timeout:
                        if self.serial.in_waiting:
                            line = self.serial.readline().decode().strip()
                            if line:
                                self.logger.debug(f"Arduino response: '{line}'")
                                response_lines.append(line)
                                
                                # Check for command-specific responses
                                if command == "TEMP" and line.startswith("TEMP "):
                                    response = line
                                    break
                                elif command == "TILT" and line.startswith("TILT "):
                                    response = line
                                    break
                                elif command == "STATUS" and line.startswith("POS "):
                                    response = line
                                    break
                                elif command.startswith("MOVE") and "Movement started" in line:
                                    response = line
                                    break
                                elif line.startswith("ERROR:"):
                                    response = line
                                    break
                                    
                        time.sleep(0.01)
                        
                    if response:
                        return response
                        
                    if attempt < retry_count:
                        self.logger.warning(f"No valid response, retrying... ({attempt + 1}/{retry_count})")
                        continue
                        
                    self.logger.error("No valid response received. All lines:")
                    for line in response_lines:
                        self.logger.error(f"  {line}")
                    raise Exception("No valid response received from Arduino")
                    
                except Exception as e:
                    if attempt < retry_count:
                        self.logger.warning(f"Command failed (attempt {attempt + 1}): {str(e)}")
                        time.sleep(0.5)
                        continue
                    raise
                    
            return None
            
    def get_temperature(self):
        """Get temperature reading
        
        Returns:
            float: Temperature in Celsius
        """
        try:
            self.logger.info("Reading temperature...")
            response = self.send_command("TEMP")
            self.logger.debug(f"Temperature response: '{response}'")
            
            if response.startswith("ERROR:"):
                raise Exception(f"Error getting temperature: {response}")
                
            # Parse temperature from response (format: "TEMP <value>")
            parts = response.split()
            if len(parts) == 2 and parts[0] == "TEMP":
                try:
                    temp = float(parts[1])
                    self.logger.info(f"Temperature: {temp:.2f}°C")
                    return temp
                except ValueError:
                    raise Exception(f"Invalid temperature value: {parts[1]}")
            
            raise Exception(f"Invalid temperature response format: '{response}'")
            
        except Exception as e:
            self.logger.error(f"Error reading temperature: {str(e)}")
            return None
            
    def get_angle(self):
        """Get current tilt angle
        
        Returns:
            float: Current angle in degrees
        """
        try:
            self.logger.info("Reading tilt angle...")
            response = self.send_command("TILT")
            self.logger.debug(f"Tilt response: '{response}'")
            
            if response.startswith("ERROR:"):
                raise Exception(f"Error getting angle: {response}")
                
            # Parse angle from response (format: "TILT <value>")
            parts = response.split()
            if len(parts) == 2 and parts[0] == "TILT":
                try:
                    angle = float(parts[1])
                    self.logger.info(f"Current angle: {angle:.2f}°")
                    return angle
                except ValueError:
                    raise Exception(f"Invalid angle value: {parts[1]}")
            
            raise Exception(f"Invalid tilt response format: '{response}'")
            
        except Exception as e:
            self.logger.error(f"Error reading angle: {str(e)}")
            return None
            
    def move_to_angle(self, angle):
        """Move to specified angle with high precision
        
        Args:
            angle (float): Target angle in degrees
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert angle to steps using precise conversion (1 step = ±0.0002 degrees)
            steps = int(angle / 0.0002)  # More precise conversion
            
            # Send move command
            response = self.send_command(f"MOVE {steps}")
            
            # Check for successful movement start
            if response and "Movement started" in response:
                self.logger.info(f"Motor movement initiated: {steps} steps ({angle:.4f}°)")
                return True
                
            if "ERROR" in response:
                raise Exception(f"Error moving to angle: {response}")
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error moving to angle {angle}: {str(e)}")
            return False
            
    def home(self):
        """Home the system
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = self.send_command("HOME")
            if "ERROR" in response:
                raise Exception(f"Error homing: {response}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error homing: {str(e)}")
            return False
            
    def stop(self):
        """Stop all movement
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = self.send_command("STOP")
            if "ERROR" in response:
                raise Exception(f"Error stopping: {response}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping: {str(e)}")
            return False
            
    def calibrate(self):
        """Calibrate the system
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = self.send_command("CALIBRATE")
            if "ERROR" in response:
                raise Exception(f"Error calibrating: {response}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error calibrating: {str(e)}")
            return False
            
    def emergency_stop(self):
        """Trigger emergency stop
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = self.send_command("EMERGENCY_STOP")
            if "ERROR" in response:
                raise Exception(f"Error triggering emergency stop: {response}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error triggering emergency stop: {str(e)}")
            return False
            
    def cleanup(self):
        """Clean up hardware resources"""
        try:
            self.logger.info("Starting hardware cleanup")
            
            # Stop any running test first
            try:
                if hasattr(self, '_test_running') and self._test_running:
                    self.stop_test()
            except:
                pass
            
            # Close serial connection if it exists
            try:
                if hasattr(self, 'serial') and self.serial:
                    if self.serial.is_open:
                        self.serial.close()
                    self.serial = None
            except:
                pass
            
            # Release port lock
            try:
                if hasattr(self, '_port_lock_fd') and self._port_lock_fd is not None:
                    try:
                        fcntl.flock(self._port_lock_fd, fcntl.LOCK_UN)
                    except:
                        pass
                    try:
                        os.close(self._port_lock_fd)
                    except:
                        pass
                    self._port_lock_fd = None
                    
                    # Try to remove lock file
                    if hasattr(self, 'port') and self.port:
                        lock_path = f"/var/lock/LCK..{os.path.basename(self.port)}"
                        if os.path.exists(lock_path):
                            try:
                                os.unlink(lock_path)
                            except:
                                pass
            except:
                pass
            
            # Reset all state flags
            self.initialized = False
            if hasattr(self, '_test_running'):
                self._test_running = False
            if hasattr(self, '_connected'):
                self._connected = False
                
        except Exception as e:
            self.logger.error(f"Error during hardware cleanup: {str(e)}")
        finally:
            # Always reset critical attributes
            self.serial = None
            self._port_lock_fd = None
            self.initialized = False

    def force_cleanup(self):
        """Force cleanup of hardware resources without waiting for locks"""
        try:
            # Force close serial connection without waiting for lock
            if hasattr(self, 'serial') and self.serial:
                try:
                    if self.serial.is_open:
                        self.serial.close()
                except:
                    pass
                self.serial = None

            # Force release port lock without waiting
            if hasattr(self, '_port_lock_fd') and self._port_lock_fd is not None:
                try:
                    os.close(self._port_lock_fd)
                except:
                    pass
                self._port_lock_fd = None

            # Reset all state flags immediately
            self.initialized = False
            if hasattr(self, '_test_running'):
                self._test_running = False
            if hasattr(self, '_connected'):
                self._connected = False

        except:
            pass  # Ignore any errors during force cleanup

    # Add alias for get_tilt_angle
    def get_tilt_angle(self):
        """Alias for get_angle()"""
        return self.get_angle()