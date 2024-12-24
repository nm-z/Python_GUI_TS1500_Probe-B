import sys
import os
import logging
import time
import serial
from serial.tools import list_ports
from PyQt6.QtCore import QObject, pyqtSignal, QMutex

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
        self._command_lock = QMutex()  # Use QMutex for thread safety
        
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
        
    def connect(self):
        """Connect to Arduino"""
        try:
            # Find Arduino port
            port = self._find_arduino_port()
            if not port:
                self.logger.error("[arduino] No Arduino found")
                return False
                
            # Open serial connection
            self._arduino = serial.Serial(
                port=port,
                baudrate=250000,
                timeout=1
            )
            self.logger.info(f"[arduino] Serial port opened")
            
            # Connection is considered successful once port is opened
            self._connected = True
            self.connection_status.emit(True)
            return True
            
        except Exception as e:
            self.logger.error(f"[arduino] Failed to connect - error={str(e)}")
            return False
            
    def parse_status_response(self, line):
        """Parse the status response from the Arduino"""
        try:
            # Skip initialization messages
            if "initialized" in line.lower():
                return {"status": "initializing"}
                
            # Clean up the response by removing any garbage at the start
            # Find the first occurrence of "POS" and use everything after that
            pos_index = line.find("POS")
            if pos_index == -1:
                return {"error": "Missing POS field"}
            
            line = line[pos_index:]
            self.logger.debug(f'Cleaned status response: {line}')
            
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
                return {"error": f"Missing fields: {missing}"}
                
            # Emit angle update
            self.tilt_updated.emit(values["angle"])
            
            return values
            
        except Exception as e:
            self.logger.error(f'Failed to parse status response: {line} (Error: {str(e)})')
            return {"error": str(e)}

    def clean_response(self, response):
        """Clean up the response string by removing duplicates and invalid data"""
        try:
            self.logger.debug('Cleaning response', extra={'original': response})
            
            # Split into potential responses (in case of duplicates)
            responses = response.split("POS")
            self.logger.debug('Split responses', extra={'parts': responses})
            
            # Take the last complete response
            for resp in reversed(responses):
                if resp.strip():
                    # Reconstruct full response
                    full_resp = "POS" + resp
                    self.logger.debug('Checking response part', extra={'response': full_resp})
                    
                    # Check if it has all required fields
                    if all(field in full_resp for field in ["POS", "ANGLE", "SPEED", "ACCEL", "HOMED", "E_STOP"]):
                        self.logger.debug('Found valid response', extra={'response': full_resp})
                        return full_resp.strip()
                        
            self.logger.warning('No valid response found in data', extra={'original': response})
            return None
        except Exception as e:
            self.logger.error('Error cleaning response', extra={'error': str(e), 'response': response})
            return None

    def send_command(self, command, params=None):
        """Send a command to the Arduino"""
        try:
            if command == "HOME":
                # Send home command
                self._arduino.write(b"HOME\n")
                
                # Wait for "Starting homing sequence..." message
                response = self._arduino.readline().decode('utf-8').strip()
                if "Starting homing sequence" not in response:
                    return f"ERROR: Unexpected response: {response}"
                    
                # Wait for "Homing complete" or error message
                while True:
                    response = self._arduino.readline().decode('utf-8').strip()
                    if "Homing complete" in response:
                        return "Homing complete"
                    elif "ERROR" in response:
                        return response
                    elif "Home switch triggered" in response:
                        # This is an expected intermediate message
                        continue
                    # Keep waiting for valid response
                    
            elif command == "MOVE":
                if params and "steps" in params:
                    self._arduino.write(f"MOVE {params['steps']}\n".encode())
                else:
                    return "ERROR: MOVE requires steps parameter"
            else:
                # Send other commands directly
                self._arduino.write(f"{command}\n".encode())
                
            # Read and return response
            response = self._arduino.readline().decode('utf-8').strip()
            return response
            
        except Exception as e:
            self.logger.error(f"Error sending command {command}: {str(e)}")
            return f"ERROR: {str(e)}"

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
        """Clean up resources"""
        try:
            if hasattr(self, '_arduino') and self._arduino and self._arduino.is_open:
                self._arduino.close()
            if hasattr(self, '_connected'):
                self._connected = False
                try:
                    self.connection_status.emit(False)
                except:
                    pass  # Ignore signal errors during cleanup
        except Exception as e:
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(f"Error during cleanup: {str(e)}")
            
    def __del__(self):
        """Destructor"""
        try:
            self.cleanup()
        except:
            pass  # Ignore errors during deletion

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

    def _find_arduino_port(self):
        """Find the Arduino's serial port"""
        try:
            # Try both ACM0 and ACM1
            for test_port in ['/dev/ttyACM0', '/dev/ttyACM1']:
                try:
                    # Try to open the port
                    test_serial = serial.Serial(
                        port=test_port,
                        baudrate=250000,
                        timeout=1
                    )
                    test_serial.close()
                    return test_port
                except:
                    continue
                    
            self.logger.error("[arduino] No available Arduino ports found")
            return None
            
        except Exception as e:
            self.logger.error(f"[arduino] Error finding Arduino port: {str(e)}")
            return None
