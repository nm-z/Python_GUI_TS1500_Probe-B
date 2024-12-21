import serial
import time
import logging
from utils.logger import hardware_logger

class HardwareController:
    def __init__(self, port='/dev/ttyACM0', baudrate=250000):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.logger = hardware_logger
        
    def connect(self):
        """Connect to Arduino"""
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=0.5)  # Shorter timeout
            time.sleep(1)  # Wait for Arduino to reset
            
            # Wait for ready signal and clear initialization messages
            start_time = time.time()
            ready_received = False
            while (time.time() - start_time) < 2:  # 2 second timeout
                if self.serial.in_waiting:
                    response = self.serial.readline().decode().strip()
                    if response:
                        self.logger.info(f"Arduino: {response}")
                        if response == "READY":
                            ready_received = True
                            break
                time.sleep(0.01)  # Shorter sleep interval
                
            if ready_received:
                self.logger.info("Connected to Arduino successfully")
                return True
                
            raise Exception("Timeout waiting for READY signal from Arduino")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Arduino: {str(e)}")
            return False
            
    def disconnect(self):
        """Disconnect from Arduino"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            self.logger.info("Disconnected from Arduino")
            
    def is_connected(self):
        """Check if Arduino is connected and responding"""
        return self.serial is not None and self.serial.is_open
            
    def send_command(self, command):
        """Send command to Arduino and get response
        
        Args:
            command (str): Command to send
            
        Returns:
            list: List of response lines from Arduino
        """
        if not self.serial or not self.serial.is_open:
            raise Exception("Not connected to Arduino")
            
        try:
            # Send command
            self.serial.write(f"{command}\n".encode())
            self.serial.flush()
            
            # Read all available responses with shorter timeout
            responses = []
            start_time = time.time()
            while (time.time() - start_time) < 0.5:  # 500ms timeout
                if self.serial.in_waiting:
                    line = self.serial.readline().decode().strip()
                    if line:
                        self.logger.info(f"Arduino: {line}")
                        responses.append(line)
                        if command == "TEST" and line == "TEST_SUCCESS":
                            break
                        if len(responses) > 0:
                            break
                time.sleep(0.01)  # Shorter sleep interval
            
            if responses:
                return responses[0]  # Return first response
            return "NO_RESPONSE"
            
        except Exception as e:
            self.logger.error(f"Error sending command '{command}': {str(e)}")
            raise
            
    def get_temperature(self):
        """Get temperature reading
        
        Returns:
            float: Temperature in Celsius
        """
        try:
            response = self.send_command("STATUS")
            if "ERROR" in response:
                raise Exception(f"Error getting temperature: {response}")
                
            # Parse temperature from status response
            parts = response.split()
            if len(parts) >= 4 and parts[0] == "POS":
                angle = float(parts[3])  # ANGLE value
                return 20.0 + (angle / 30.0)  # Convert angle to temperature for testing
                
            raise Exception("Invalid status response format")
            
        except Exception as e:
            self.logger.error(f"Error reading temperature: {str(e)}")
            return None
            
    def get_angle(self):
        """Get current tilt angle
        
        Returns:
            float: Current angle in degrees
        """
        try:
            response = self.send_command("STATUS")
            if "ERROR" in response:
                raise Exception(f"Error getting angle: {response}")
                
            # Parse angle from status response
            parts = response.split()
            if len(parts) >= 4 and parts[0] == "POS":
                return float(parts[3])  # ANGLE value
                
            raise Exception("Invalid status response format")
            
        except Exception as e:
            self.logger.error(f"Error reading angle: {str(e)}")
            return None
            
    def move_to_angle(self, angle):
        """Move to specified angle
        
        Args:
            angle (float): Target angle in degrees
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert angle to steps
            steps = int(angle * 5000)  # 5000 steps per degree
            response = self.send_command(f"MOVE {steps}")
            
            if "ERROR" in response:
                raise Exception(f"Error moving to angle: {response}")
                
            return True
            
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