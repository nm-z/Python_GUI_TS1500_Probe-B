from PyQt5.QtCore import QObject, pyqtSignal
import serial
import time
import logging
from utils.logger import hardware_logger

class ArduinoController(QObject):
    # Define signals
    angle_updated_signal = pyqtSignal(float)
    
    def __init__(self):
        super().__init__()
        self.arduino = None
        self.arduino_connected = False
        self.logger = logging.getLogger(__name__)

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
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Arduino: {e}")
            self.arduino_connected = False
            return False

    def send_command(self, command):
        """Send command to Arduino and read response"""
        if not self.arduino or not self.arduino.is_open:
            return None
            
        try:
            # Clear input buffer
            self.arduino.reset_input_buffer()
            
            # Send command
            print(f"\n→ Sending: {command}")
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
                        print(f"← Received: {line}")
                        
                        # Handle special cases
                        if line == "START_TEST":
                            in_test = True
                            continue
                        elif line == "END_TEST":
                            in_test = False
                            break
                        elif line.startswith("ERROR"):
                            return {"error": line}
                        
                        responses.append(line)
                        
                        # If not in a TEST command, break after first response
                        if not in_test and command != "TEST":
                            break
                            
                time.sleep(0.1)

            if not responses:
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
                except (IndexError, ValueError):
                    pass
                    
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
                return {"error": responses[0]}
            else:
                return responses[0] if responses else None
            
        except Exception as e:
            print(f"Error sending command: {e}")
            return {"error": str(e)}

    def is_connected(self):
        """Check if Arduino is connected and responding"""
        if not self.arduino or not self.arduino.is_open:
            return False
        try:
            # Send test command
            response = self.send_command("STATUS")
            return response is not None and not isinstance(response, dict)
        except:
            return False

    def disconnect(self):
        """Safely disconnect from Arduino"""
        try:
            if self.arduino and self.arduino.is_open:
                self.arduino.close()
            self.arduino_connected = False
            print("Arduino disconnected")
        except Exception as e:
            print(f"Error disconnecting from Arduino: {e}")

    def get_tilt(self):
        """Get current tilt data"""
        response = self.send_command("STATUS")
        if response and not isinstance(response, dict):
            return {
                'x': response['angle'],
                'y': 0  # Only using single axis tilt for now
            }
        return None