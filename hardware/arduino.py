from PyQt6.QtCore import QObject, pyqtSignal
import serial
import time
from utils.logger import hardware_logger, log_hardware_event
import os
from serial.tools import list_ports
import logging

class ArduinoController(QObject):
    # Define signals
    angle_updated_signal = pyqtSignal(float)
    
    def __init__(self, port=None, baudrate=9600, timeout=1):
        """Initialize the Arduino controller"""
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.connected = False
        self.logger = logging.getLogger('hardware')
        
        # Set up logging
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/hardware.log')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.force_cleanup()
        
    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
        return False  # Don't suppress exceptions
    
    def find_arduino_port(self):
        """Find the Arduino port by checking available serial ports"""
        try:
            # List all available ports
            ports = list(list_ports.comports())
            
            # First try user-specified port if provided
            if self.port:
                for port in ports:
                    if port.device == self.port:
                        self.logger.info(f"Found Arduino on specified port {self.port}")
                        return self.port
                        
            # Otherwise try to find an Arduino port
            for port in ports:
                if "Arduino" in port.description or "ACM" in port.device:
                    self.logger.info(f"Found potential Arduino port on {port.device}")
                    return port.device
                    
            self.logger.error("No Arduino ports found")
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding Arduino port: {str(e)}")
            return None
        
    def connect(self, port=None, baudrate=9600):
        """Connect to the Arduino"""
        try:
            # Use provided port or find one
            if port:
                self.port = port
            else:
                self.port = self.find_arduino_port()
            
            if not self.port:
                self.logger.error("No Arduino port available")
                return False
            
            # Check port permissions
            try:
                stat = os.stat(self.port)
                self.logger.info(f"Port owner: {stat.st_uid}, group: {stat.st_gid}, mode: {oct(stat.st_mode)}")
                
                # Check if we have read/write access
                if not os.access(self.port, os.R_OK | os.W_OK):
                    self.logger.error(f"Insufficient permissions for port {self.port}")
                    return False
                
            except OSError as e:
                self.logger.error(f"Error checking port permissions: {str(e)}")
                return False
            
            # Try to connect with retries
            max_retries = 3
            retry_delay = 1
            
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        self.logger.info(f"Retry attempt {attempt + 1}/{max_retries}")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    
                    self.serial = serial.Serial(
                        port=self.port,
                        baudrate=baudrate,
                        timeout=self.timeout
                    )
                    
                    # Wait for Arduino to reset
                    time.sleep(2)
                    
                    # Test connection
                    self.serial.write(b"PING\n")
                    response = self.serial.readline().decode().strip()
                    
                    if response == "PONG":
                        self.connected = True
                        self.logger.info(f"Successfully connected to Arduino on {self.port}")
                        return True
                    else:
                        self.logger.warning(f"Invalid response from Arduino: {response}")
                        self.serial.close()
                    
                except serial.SerialException as e:
                    self.logger.error(f"Serial connection error: {str(e)}")
                    if self.serial:
                        self.serial.close()
                    
            self.logger.error(f"Failed to connect after {max_retries} attempts")
            return False
            
        except Exception as e:
            self.logger.error(f"Connection error: {str(e)}")
            return False

    def send_command(self, command, max_retries=2):
        """Send a command to the Arduino and get the response"""
        if not self.connected:
            self.logger.error("Not connected to Arduino")
            return None
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Clear any pending data
                self.serial.reset_input_buffer()
                self.serial.reset_output_buffer()
                
                # Send command with newline
                cmd = f"{command}\n".encode()
                self.serial.write(cmd)
                self.serial.flush()
                
                # Wait for response
                response = self.serial.readline().decode().strip()
                
                if response:
                    return response
                else:
                    retry_count += 1
                    if retry_count < max_retries:
                        self.logger.warning(f"No valid response, retrying... ({retry_count}/{max_retries})")
                        time.sleep(0.5)
                    else:
                        self.logger.error(f"No valid response received after {max_retries} attempts")
                        return None
                    
            except serial.SerialException as e:
                self.logger.error(f"Serial communication error: {str(e)}")
                return None
            except Exception as e:
                self.logger.error(f"Error sending command: {str(e)}")
                return None
                
        return None
    
    def read_line(self, timeout=1.0):
        """Read a line from the Arduino with timeout"""
        if not self.connected:
            self.logger.error("Not connected to Arduino")
            return None
        
        try:
            start_time = time.time()
            while (time.time() - start_time) < timeout:
                if self.serial.in_waiting:
                    return self.serial.readline().decode().strip()
                time.sleep(0.1)
            return None
        except Exception as e:
            self.logger.error(f"Error reading line: {str(e)}")
            return None

    def is_connected(self):
        """Check if Arduino is connected and responding"""
        if not self.arduino or not self.arduino.is_open:
            return False
        try:
            # Send test command
            response = self.send_command("STATUS")
            return response is not None and not isinstance(response, dict)
        except Exception as e:
            log_hardware_event('arduino', 'ERROR', 'Connection check failed', error=str(e))
            return False

    def disconnect(self):
        """Disconnect from the Arduino"""
        try:
            if self.serial and self.serial.is_open:
                self.serial.close()
            self.connected = False
            self.logger.info("Disconnected from Arduino")
            return True
        except Exception as e:
            self.logger.error(f"Error disconnecting: {str(e)}")
            return False
        
    def cleanup(self):
        """Clean up resources"""
        try:
            self.disconnect()
            self.logger.info("Cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
        
    def force_cleanup(self):
        """Force cleanup of resources even if errors occur"""
        try:
            if self.serial:
                try:
                    self.serial.close()
                except:
                    pass
            self.connected = False
            self.logger.info("Force cleanup completed")
        except:
            pass

    def get_tilt(self):
        """Get the current tilt angle"""
        try:
            response = self.send_command("TILT")
            if response and response.startswith("TILT:"):
                tilt_str = response.split(":")[1].strip()
                try:
                    return float(tilt_str)
                except ValueError:
                    self.logger.error(f"Invalid tilt value: {tilt_str}")
                    return None
            else:
                self.logger.error(f"Invalid tilt response: {response}")
                return None
        except Exception as e:
            self.logger.error(f"Tilt read error: {str(e)}")
            return None
        
    def get_temperature(self):
        """Get the current temperature"""
        try:
            response = self.send_command("TEMP")
            if response and response.startswith("TEMP:"):
                temp_str = response.split(":")[1].strip()
                try:
                    return float(temp_str)
                except ValueError:
                    self.logger.error(f"Invalid temperature value: {temp_str}")
                    return None
            else:
                self.logger.error(f"Invalid temperature response: {response}")
                return None
        except Exception as e:
            self.logger.error(f"Temperature read error: {str(e)}")
            return None
        
    def emergency_stop(self):
        """Send emergency stop command"""
        try:
            response = self.send_command("STOP")
            if response == "STOPPED":
                self.logger.info("Emergency stop successful")
                return True
            else:
                self.logger.error(f"Emergency stop failed: {response}")
                return False
        except Exception as e:
            self.logger.error(f"Emergency stop error: {str(e)}")
            return False