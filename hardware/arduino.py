from PyQt6.QtCore import QObject, pyqtSignal
import serial
import time
from utils.logger import hardware_logger, log_hardware_event

class ArduinoController(QObject):
    # Define signals
    angle_updated_signal = pyqtSignal(float)
    
    def __init__(self):
        super().__init__()
        self.arduino = None
        self.arduino_connected = False
        
    @staticmethod
    def find_arduino_port():
        """Find the Arduino Due Native port"""
        import serial.tools.list_ports
        
        # First try to find Arduino Due Native port
        for port in serial.tools.list_ports.comports():
            if "Arduino Due" in port.description and "Native" in port.description:
                return port.device
                
        # If native port not found, try programming port as fallback
        for port in serial.tools.list_ports.comports():
            if "Arduino Due" in port.description and "Programming" in port.description:
                return port.device
                
        # Last resort: try ttyACM ports
        for port in serial.tools.list_ports.comports():
            if "ttyACM" in port.device:
                return port.device
                
        return None  # No suitable port found
        
    def connect(self, port=None, baudrate=250000):
        """Connect to Arduino"""
        if port is None:
            port = self.find_arduino_port()
            
        try:
            if self.arduino and self.arduino.is_open:
                self.arduino.close()
                
            log_hardware_event('arduino', 'INFO', f'Attempting to connect to {port} at {baudrate} baud')
            self.arduino = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=1,
                write_timeout=1,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            log_hardware_event('arduino', 'INFO', 'Serial port opened, waiting for reset...')
            time.sleep(3)  # Due needs more time to reset
            
            # Clear any startup messages
            self.arduino.reset_input_buffer()
            self.arduino.reset_output_buffer()
            
            # Send initial newline to clear any partial commands
            self.arduino.write(b'\n')
            time.sleep(0.1)
            self.arduino.reset_input_buffer()
            
            # Wait for initialization messages and READY signal
            start_time = time.time()
            ready_received = False
            init_messages = []
            
            while (time.time() - start_time) < 5:  # 5 second timeout
                if self.arduino.in_waiting:
                    try:
                        line = self.arduino.readline().decode('utf-8').strip()
                        if line:
                            log_hardware_event('arduino', 'DEBUG', 'Init message received', message=line)
                            init_messages.append(line)
                            if line == "READY":
                                ready_received = True
                                break
                    except UnicodeDecodeError:
                        log_hardware_event('arduino', 'WARNING', 'Received non-text data during init')
                time.sleep(0.1)
            
            if not ready_received:
                log_hardware_event('arduino', 'ERROR', 'Never received READY signal', init_messages=init_messages)
                return False
            
            log_hardware_event('arduino', 'INFO', 'READY signal received, testing connection...')
            
            # Now test the connection with a simple command
            response = self.send_command("STATUS")
            log_hardware_event('arduino', 'DEBUG', 'Status response', response=response)
            
            if response and isinstance(response, dict) and 'error' not in response:
                self.arduino_connected = True
                log_hardware_event('arduino', 'INFO', 'Connected successfully', port=port, baudrate=baudrate)
                return True
                
            log_hardware_event('arduino', 'WARNING', 'Connection test failed', port=port, response=response)
            return False
            
        except Exception as e:
            log_hardware_event('arduino', 'ERROR', 'Failed to connect', port=port, error=str(e))
            self.arduino_connected = False
            return False

    def send_command(self, command):
        """Send command to Arduino and read response"""
        if not self.arduino or not self.arduino.is_open:
            log_hardware_event('arduino', 'WARNING', 'Cannot send command - not connected', command=command)
            return None
            
        try:
            # Clear input buffer
            self.arduino.reset_input_buffer()
            
            # Send command with newline
            log_hardware_event('arduino', 'DEBUG', 'Sending command', command=command)
            self.arduino.write(f"{command}\n".encode('utf-8'))
            self.arduino.flush()  # Ensure command is sent
            time.sleep(0.1)  # Give Arduino time to process
            
            # Read response
            responses = []
            start_time = time.time()
            in_test = False
            
            while (time.time() - start_time) < 2:  # 2 second timeout
                if self.arduino.in_waiting:
                    try:
                        line = self.arduino.readline().decode('utf-8').strip()
                        if line:
                            log_hardware_event('arduino', 'DEBUG', 'Received response', response=line)
                            
                            # Handle special cases
                            if line == "START_TEST":
                                in_test = True
                                continue
                            elif line == "END_TEST":
                                in_test = False
                                break
                            elif line.startswith("ERROR"):
                                log_hardware_event('arduino', 'ERROR', 'Error response received', error=line)
                                return {"error": line}
                            
                            responses.append(line)
                            
                            # If not in a TEST command, break after first response
                            if not in_test and command != "TEST":
                                break
                    except UnicodeDecodeError:
                        log_hardware_event('arduino', 'WARNING', 'Received non-text data')
                        continue
                        
                time.sleep(0.05)  # Shorter sleep to be more responsive

            if not responses:
                log_hardware_event('arduino', 'WARNING', 'No response received', command=command)
                return {"error": "NO_RESPONSE"}
                
            # Parse responses based on command
            if command == "TEST":
                result = {}
                for response in responses:
                    if ":" in response:
                        key, value = response.split(":", 1)
                        result[key.strip()] = value.strip()
                return result
            elif command == "STATUS":
                # Parse status response: POS X ANGLE Y SPEED Z ACCEL W HOMED H E_STOP E
                try:
                    parts = responses[0].split()
                    if len(parts) >= 12:  # Make sure we have all parts
                        angle = float(parts[3])
                        self.angle_updated_signal.emit(angle)  # Emit angle update signal
                        return {
                            "position": int(parts[1]),
                            "angle": angle,
                            "speed": float(parts[5]),
                            "acceleration": float(parts[7]),
                            "homed": parts[9] == "YES",
                            "emergency_stop": parts[11] == "YES"
                        }
                    else:
                        log_hardware_event('arduino', 'ERROR', 'Invalid status response format', response=responses[0])
                        return {"error": "INVALID_FORMAT"}
                except (IndexError, ValueError) as e:
                    log_hardware_event('arduino', 'ERROR', 'Failed to parse status response', 
                                     response=responses[0], error=str(e))
                    return {"error": "PARSE_ERROR"}
            elif command == "TEMP":
                try:
                    if responses[0].startswith("TEMP "):
                        return {"temperature": float(responses[0].split()[1])}
                    log_hardware_event('arduino', 'WARNING', 'Invalid temperature response', response=responses[0])
                    return {"error": responses[0]}
                except (IndexError, ValueError) as e:
                    log_hardware_event('arduino', 'ERROR', 'Failed to parse temperature', 
                                     response=responses[0], error=str(e))
                    return {"error": "PARSE_ERROR"}
            else:
                return responses[0] if responses else None
            
        except Exception as e:
            log_hardware_event('arduino', 'ERROR', 'Command error', command=command, error=str(e))
            return {"error": str(e)}

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
        """Safely disconnect from Arduino"""
        try:
            if self.arduino and self.arduino.is_open:
                self.arduino.close()
            self.arduino_connected = False
            log_hardware_event('arduino', 'INFO', 'Disconnected')
        except Exception as e:
            log_hardware_event('arduino', 'ERROR', 'Error disconnecting', error=str(e))

    def get_tilt(self):
        """Get current tilt data"""
        response = self.send_command("STATUS")
        if response and not isinstance(response, dict):
            return {
                'x': response['angle'],
                'y': 0  # Only using single axis tilt for now
            }
        return None