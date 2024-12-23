import logging
import serial
import time
import os
from serial.tools import list_ports
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread
from PyQt6.QtWidgets import QApplication
from utils.logger import hardware_logger, log_hardware_event

class HardwareController(QObject):
    """Controller for hardware interactions"""
    
    # Define signals
    connection_status = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    temperature_updated = pyqtSignal(float)
    tilt_updated = pyqtSignal(float)
    status_updated = pyqtSignal(dict)
    
    def __init__(self, logger=None):
        super().__init__()
        
        # Set up logging
        self.logger = logger or logging.getLogger('hardware')
        
        # Initialize state
        self._arduino = None
        self._connected = False
        self._last_status = {}
        
        # Try to connect
        self.connect()
        
    @staticmethod
    def find_arduino_port():
        """Find the Arduino Due Native port"""
        # First try to find Arduino Due Native port
        for port in list_ports.comports():
            if "Arduino Due" in port.description and "Native" in port.description:
                return port.device
                
        # If native port not found, try programming port as fallback
        for port in list_ports.comports():
            if "Arduino Due" in port.description and "Programming" in port.description:
                return port.device
                
        # Last resort: try ttyACM ports
        for port in list_ports.comports():
            if "ttyACM" in port.device:
                return port.device
                
        return None  # No suitable port found
        
    def connect(self, port=None, baudrate=250000):
        """Connect to Arduino"""
        try:
            if port is None:
                # Try both ACM0 and ACM1
                for test_port in ['/dev/ttyACM0', '/dev/ttyACM1']:
                    try:
                        # Try to open the port
                        test_serial = serial.Serial(
                            port=test_port,
                            baudrate=baudrate,
                            timeout=1,
                            write_timeout=1,
                            bytesize=serial.EIGHTBITS,
                            parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE
                        )
                        test_serial.close()
                        port = test_port
                        break
                    except:
                        continue
                        
                if not port:
                    self.logger.error("[arduino] No available Arduino ports found")
                    return False
                    
            if self._arduino and self._arduino.is_open:
                self._arduino.close()
                
            self.logger.info(f"[arduino] Attempting to connect to {port} at {baudrate} baud")
            self._arduino = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=1,
                write_timeout=1,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            self.logger.info("[arduino] Serial port opened")
            
            # Clear any remaining startup messages
            self._arduino.reset_input_buffer()
            self._arduino.reset_output_buffer()
            
            self._connected = True
            self.connection_status.emit(True)
            self.logger.info(f"[arduino] Connected successfully - port={port}, baudrate={baudrate}")
            return True
                
        except Exception as e:
            self.logger.error(f"[arduino] Failed to connect - error={str(e)}")
            self._connected = False
            self.connection_status.emit(False)
            return False
            
    def parse_status_response(self, line):
        """Parse the status response from the Arduino"""
        try:
            # Clean up the response by removing any garbage at the start
            # Find the first occurrence of "POS" and use everything after that
            pos_index = line.find("POS")
            if pos_index == -1:
                raise ValueError("Missing POS field")
            
            line = line[pos_index:]
            log_hardware_event('arduino', 'DEBUG', f'Cleaned status response: {line}')
            
            # Extract values using string operations
            parts = line.split()
            values = {}
            
            # Find position of each field
            for i in range(len(parts) - 1):
                if parts[i] == "POS":
                    values["position"] = int(parts[i + 1])
                elif parts[i] == "ANGLE":
                    values["angle"] = float(parts[i + 1])
                elif parts[i] == "SPEED":
                    values["speed"] = float(parts[i + 1])
                elif parts[i] == "ACCEL":
                    values["acceleration"] = float(parts[i + 1])
                elif parts[i] == "HOMED":
                    values["homed"] = parts[i + 1] == "YES"
                elif parts[i] == "E_STOP":
                    values["emergency_stop"] = parts[i + 1] == "YES"
                    
            # Check if we have all required fields
            required_fields = ["position", "angle", "speed", "acceleration", "homed", "emergency_stop"]
            if not all(field in values for field in required_fields):
                missing = [field for field in required_fields if field not in values]
                raise ValueError(f"Missing fields: {missing}")
                
            # Emit angle update
            self.tilt_updated.emit(values["angle"])
            
            return values
            
        except Exception as e:
            log_hardware_event('arduino', 'ERROR', f'Failed to parse status response: {line} (Error: {str(e)})')
            return {"error": "PARSE_ERROR"}

    def clean_response(self, response):
        """Clean up the response string by removing duplicates and invalid data"""
        try:
            log_hardware_event('arduino', 'DEBUG', 'Cleaning response', original=response)
            
            # Split into potential responses (in case of duplicates)
            responses = response.split("POS")
            log_hardware_event('arduino', 'DEBUG', 'Split responses', parts=responses)
            
            # Take the last complete response
            for resp in reversed(responses):
                if resp.strip():
                    # Reconstruct full response
                    full_resp = "POS" + resp
                    log_hardware_event('arduino', 'DEBUG', 'Checking response part', response=full_resp)
                    
                    # Check if it has all required fields
                    if all(field in full_resp for field in ["POS", "ANGLE", "SPEED", "ACCEL", "HOMED", "E_STOP"]):
                        log_hardware_event('arduino', 'DEBUG', 'Found valid response', response=full_resp)
                        return full_resp.strip()
                        
            log_hardware_event('arduino', 'WARNING', 'No valid response found in data', original=response)
            return None
        except Exception as e:
            log_hardware_event('arduino', 'ERROR', 'Error cleaning response', error=str(e), response=response)
            return None

    def send_command(self, command):
        """Send command to Arduino and read response"""
        if not self._arduino or not self._arduino.is_open:
            log_hardware_event('arduino', 'WARNING', 'Cannot send command - not connected', command=command)
            return None
        
        try:
            # Clear input buffer
            self._arduino.reset_input_buffer()
            
            # Send command with newline
            log_hardware_event('arduino', 'DEBUG', f'Sending command: {command}')
            self._arduino.write(f"{command}\n".encode('utf-8'))
            self._arduino.flush()  # Ensure command is sent
            time.sleep(0.2)  # Give Arduino more time to process and respond
            
            # Read response with timeout
            start_time = time.time()
            response = None
            
            while (time.time() - start_time) < 2:  # 2 second timeout
                try:
                    if self._arduino.in_waiting:
                        line = self._arduino.readline().decode('utf-8').strip()
                        if line:
                            log_hardware_event('arduino', 'DEBUG', f'Received response: {line}')
                            
                            # Handle special cases
                            if line == "START_TEST":
                                continue
                            elif line == "END_TEST":
                                break
                            elif line.startswith("ERROR"):
                                log_hardware_event('arduino', 'ERROR', f'Error response: {line}')
                                return {"error": line}
                                
                            # For STATUS command, try to clean up the response
                            if command == "STATUS" and "POS" in line:
                                response = line
                                break
                            elif command != "STATUS":
                                response = line
                                break
                except UnicodeDecodeError:
                    log_hardware_event('arduino', 'WARNING', 'Received non-text data')
                    continue
                    
                time.sleep(0.01)  # Short sleep to prevent CPU spinning
                
            if not response:
                log_hardware_event('arduino', 'WARNING', 'No response received', command=command)
                return {"error": "NO_RESPONSE"}
                
            # Parse response based on command
            if command == "STATUS":
                return self.parse_status_response(response)
            elif command == "TEMP":
                try:
                    if response.startswith("TEMP "):
                        temp = float(response.split()[1])
                        self.temperature_updated.emit(temp)
                        return {"temperature": temp}
                    log_hardware_event('arduino', 'WARNING', f'Invalid temperature response: {response}')
                    return {"error": response}
                except (IndexError, ValueError) as e:
                    log_hardware_event('arduino', 'ERROR', f'Failed to parse temperature: {response} (Error: {str(e)})')
                    return {"error": "PARSE_ERROR"}
            elif command == "TILT":
                try:
                    if response.startswith("TILT "):
                        angle = float(response.split()[1])
                        self.tilt_updated.emit(angle)
                        return {"angle": angle}
                    log_hardware_event('arduino', 'WARNING', f'Invalid tilt response: {response}')
                    return {"error": response}
                except (IndexError, ValueError) as e:
                    log_hardware_event('arduino', 'ERROR', f'Failed to parse tilt: {response} (Error: {str(e)})')
                    return {"error": "PARSE_ERROR"}
            elif command == "EMERGENCY_STOP":
                if response == "Emergency stop engaged" or response == "Emergency stop released":
                    return True
                return False
                
            return response
            
        except Exception as e:
            log_hardware_event('arduino', 'ERROR', 'Command failed', command=command, error=str(e))
            return {"error": str(e)}
            
    def is_connected(self):
        """Check if Arduino is connected and responding"""
        if not self._arduino or not self._arduino.is_open:
            return False
        
        # Return the internal connection state
        return self._connected
            
    def disconnect(self):
        """Disconnect from hardware"""
        try:
            if self._arduino and self._arduino.is_open:
                self._arduino.close()
            self._arduino = None
            self._connected = False
            self.connection_status.emit(False)
            self.logger.info("[arduino] Disconnected")
        except Exception as e:
            self.logger.error(f"[arduino] Error disconnecting - error={str(e)}")
            
    def cleanup(self):
        """Cleanup resources"""
        try:
            if self._arduino and self._arduino.is_open:
                try:
                    self._arduino.reset_input_buffer()
                    self._arduino.reset_output_buffer()
                    self._arduino.close()
                except:
                    pass  # Ignore errors during cleanup
            self._arduino = None
            self._connected = False
            try:
                if not QApplication.instance().closingDown():
                    self.connection_status.emit(False)
                    self.logger.info("[arduino] Disconnected")
            except:
                pass  # Ignore signal errors during cleanup
        except Exception as e:
            try:
                self.logger.error(f"[arduino] Error during cleanup - error={str(e)}")
            except:
                pass  # Ignore logging errors during cleanup
            
    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            self.cleanup()
        except:
            pass  # Ignore errors during cleanup

    def get_tilt(self):
        """Get the current tilt angle
        
        Returns:
            float: Current tilt angle in degrees, or None if error
        """
        try:
            response = self.send_command("TILT")
            if response and isinstance(response, dict) and 'angle' in response:
                return response['angle']
            return None
        except Exception as e:
            self.logger.error(f"[arduino] Error reading tilt: {str(e)}")
            return None
            
    def get_temperature(self):
        """Get the current temperature
        
        Returns:
            float: Current temperature in Celsius, or None if error
        """
        try:
            response = self.send_command("TEMP")
            if response and isinstance(response, dict) and 'temperature' in response:
                return response['temperature']
            return None
        except Exception as e:
            self.logger.error(f"[arduino] Error reading temperature: {str(e)}")
            return None
