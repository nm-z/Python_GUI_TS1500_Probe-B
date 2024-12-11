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

    def connect(self, port='/dev/ttyACM0', baudrate=115200):
        """Connect to Arduino"""
        try:
            if self.arduino and self.arduino.is_open:
                self.arduino.close()
                
            self.arduino = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=1
            )
            
            time.sleep(2)  # Wait for Arduino reset
            self.arduino.reset_input_buffer()
            self.arduino.reset_output_buffer()
            
            # Test connection
            response = self.send_command("TEST")
            if response and not isinstance(response, dict):
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
            
            # Send command
            log_hardware_event('arduino', 'DEBUG', 'Sending command', command=command)
            self.arduino.write(f"{command}\n".encode('utf-8'))
            time.sleep(0.1)
            
            # Read response
            responses = []
            start_time = time.time()
            in_test = False
            
            while (time.time() - start_time) < 2:  # 2 second timeout
                if self.arduino.in_waiting:
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
                            
                time.sleep(0.1)

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
                parts = responses[0].split()
                try:
                    angle = float(parts[3])
                    self.angle_updated_signal.emit(angle)  # Emit angle update signal
                except (IndexError, ValueError) as e:
                    log_hardware_event('arduino', 'ERROR', 'Failed to parse status response', 
                                     response=responses[0], error=str(e))
                    return {"error": "PARSE_ERROR"}
                    
                return {
                    "position": int(parts[1]),
                    "angle": float(parts[3]),
                    "speed": float(parts[5]),
                    "acceleration": float(parts[7]),
                    "homed": parts[9] == "YES",
                    "emergency_stop": parts[11] == "YES"
                }
            elif command == "TEMP":
                if responses[0].startswith("TEMP"):
                    return {"temperature": float(responses[0].split()[1])}
                log_hardware_event('arduino', 'WARNING', 'Invalid temperature response', response=responses[0])
                return {"error": responses[0]}
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