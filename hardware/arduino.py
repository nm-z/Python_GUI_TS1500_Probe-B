from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import serial
import time

class ArduinoController(QObject):
    # Define signals
    angle_updated_signal = pyqtSignal(float)
    connection_status_changed = pyqtSignal(bool)
    initialization_message = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.arduino = None
        self.arduino_connected = False
        self.test_running = False
        
        # Create timer for monitoring serial port
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.check_serial)
        self.monitor_timer.start(10)  # Check every 10ms for faster updates
        
    def check_serial(self):
        """Check for new messages from Arduino"""
        if self.arduino and self.arduino.is_open and self.arduino.in_waiting:
            try:
                line = self.arduino.readline().decode('utf-8').strip()
                if line:
                    self.initialization_message.emit(line)  # Send raw Arduino output to GUI
            except Exception as e:
                self.initialization_message.emit(f"Error reading Arduino: {str(e)}")

    def connect(self, port='/dev/ttyACM0', baudrate=250000):
        """Connect to Arduino"""
        try:
            if self.arduino and self.arduino.is_open:
                self.arduino.close()
                
            self.arduino = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=1
            )
            
            self.arduino_connected = True
            self.connection_status_changed.emit(True)
            return True
            
        except Exception as e:
            self.initialization_message.emit(f"Error connecting to Arduino: {str(e)}")
            self.arduino_connected = False
            self.connection_status_changed.emit(False)
            return False
            
    def is_connected(self):
        """Check if Arduino is connected"""
        return self.arduino and self.arduino.is_open
            
    def disconnect(self):
        """Safely disconnect from Arduino"""
        try:
            if self.arduino and self.arduino.is_open:
                self.arduino.close()
            self.arduino_connected = False
            self.connection_status_changed.emit(False)
            self.test_running = False
        except Exception as e:
            self.initialization_message.emit(f"Error disconnecting: {str(e)}")

    def start_test(self):
        """Start a test sequence"""
        self.test_running = True
        return self.send_command("START")

    def stop_test(self):
        """Stop the test sequence"""
        if self.test_running:
            self.test_running = False
            return self.send_command("STOP")
        return None

    def send_command(self, command):
        """Send command to Arduino and read response"""
        # Only allow commands if test is running or it's a START/STOP command
        if not self.test_running and command not in ["START", "STOP", "EMERGENCY_STOP"]:
            self.initialization_message.emit(f"Command blocked - test not running: {command}")
            return None

        if not self.arduino or not self.arduino.is_open:
            self.initialization_message.emit("Cannot send command - Arduino not connected")
            return None
            
        try:
            # Send command
            self.initialization_message.emit(f"Sending to Arduino: {command}")
            self.arduino.write(f"{command}\n".encode('utf-8'))
            self.arduino.flush()
            
            # Read response
            responses = []
            start_time = time.time()
            in_test = False
            
            while (time.time() - start_time) < 2:  # 2 second timeout
                if self.arduino.in_waiting:
                    line = self.arduino.readline().decode('utf-8').strip()
                    if line:
                        self.initialization_message.emit(line)  # Send raw Arduino output to GUI
                        responses.append(line)
                        
                        # If not in a TEST command, break after first response
                        if not in_test and command != "TEST":
                            break
                            
                time.sleep(0.01)  # Shorter sleep for faster response
            
            return responses[0] if responses else None
                
        except Exception as e:
            self.initialization_message.emit(f"Command error: {str(e)}")
            return None

    def get_tilt(self):
        """Get current tilt data"""
        if not self.test_running:
            return None
        response = self.send_command("STATUS")
        if response and not isinstance(response, dict):
            return {
                'x': response['angle'],
                'y': 0  # Only using single axis tilt for now
            }
        return None