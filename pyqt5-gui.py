import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QMessageBox, QFileDialog
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import csv
from datetime import datetime
import threading
import serial
from serial.tools.list_ports import comports
from flask import Flask, jsonify, render_template
import usb.core
import usb.util
import os
import subprocess
import pyperclip

# Configuration
ENABLE_WEB_SERVER = False

app = Flask(__name__)

# Mock mpu6050 for testing
class MockMPU6050:
    def get_accel_data(self):
        return {'x': 0.0, 'y': 0.0, 'z': 0.0}
    def get_gyro_data(self):
        return {'x': 0.0, 'y': 0.0, 'z': 0.0}

mpu6050 = MockMPU6050

# Mock Temper for testing
class MockTemper:
    def __init__(self, port):
        self.port = port

    def get_temperature(self):
        return 25.0  # Return a mock temperature

temper = MockTemper

class EnhancedAutoDataLoggerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enhanced Automated Data Logger")
        self.setGeometry(100, 100, 800, 600)
        
        self.create_widgets()
        self.data = []
        self.is_logging = False
        self.web_port_enabled = False
        self.vna_connected = False
        self.temp_sensor_connected = False
        self.arduino = None
    
    def create_widgets(self):
        # Create tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Logging Controls tab
        logging_tab = QWidget()
        self.tabs.addTab(logging_tab, "Logging Controls")
        
        logging_layout = QVBoxLayout()
        logging_tab.setLayout(logging_layout)
        
        freq_layout = QHBoxLayout()
        freq_label = QLabel("Measurement Frequency (seconds):")
        self.freq_entry = QLineEdit("1")
        self.freq_entry.setFixedWidth(100)
        freq_layout.addWidget(freq_label)
        freq_layout.addWidget(self.freq_entry)
        freq_layout.addStretch()
        
        self.log_button = QPushButton("Start Logging")
        self.log_button.clicked.connect(self.toggle_logging)
        
        logging_layout.addLayout(freq_layout)
        logging_layout.addWidget(self.log_button)
        
        # Current Readings tab
        readings_tab = QWidget()
        self.tabs.addTab(readings_tab, "Current Readings")
        
        readings_layout = QVBoxLayout()
        readings_tab.setLayout(readings_layout)
        
        temp_layout = QHBoxLayout()
        temp_label = QLabel("Temperature:")
        self.temp_display = QLabel("0.00C")
        temp_layout.addWidget(temp_label)
        temp_layout.addWidget(self.temp_display)
        temp_layout.addStretch()
        
        vna_layout = QHBoxLayout()
        vna_label = QLabel("VNA Data:")
        self.vna_display = QLabel("0.00")
        vna_layout.addWidget(vna_label)
        vna_layout.addWidget(self.vna_display)
        vna_layout.addStretch()
        
        accel_layout = QHBoxLayout()
        accel_label = QLabel("Accelerometer Angle:")
        self.accel_display = QLabel("0.00°")
        accel_layout.addWidget(accel_label)
        accel_layout.addWidget(self.accel_display)
        accel_layout.addStretch()
        
        level_layout = QHBoxLayout()
        level_label = QLabel("Digital Level Angle:")
        self.level_display = QLabel("0.00°")
        level_layout.addWidget(level_label)
        level_layout.addWidget(self.level_display)
        level_layout.addStretch()
        
        readings_layout.addLayout(temp_layout)
        readings_layout.addLayout(vna_layout)
        readings_layout.addLayout(accel_layout)
        readings_layout.addLayout(level_layout)
        
        # Real-time Graphs tab
        graphs_tab = QWidget()
        self.tabs.addTab(graphs_tab, "Real-time Graphs")
        
        graphs_layout = QVBoxLayout()
        graphs_tab.setLayout(graphs_layout)
        
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(6, 6))
        self.canvas = FigureCanvas(self.fig)
        graphs_layout.addWidget(self.canvas)
        
        # Device Connections tab
        device_tab = QWidget()
        self.tabs.addTab(device_tab, "Device Connections")
        
        device_layout = QVBoxLayout()
        device_tab.setLayout(device_layout)
        
        vna_layout = QHBoxLayout()
        vna_label = QLabel("VNA Port:")
        self.vna_port = QComboBox()
        self.vna_port.addItems(self.get_usb_ports())
        self.vna_port.currentIndexChanged.connect(self.on_vna_port_selected)
        self.vna_status_label = QLabel("Disconnected")
        self.vna_status_label.setStyleSheet("color: red")
        vna_layout.addWidget(vna_label)
        vna_layout.addWidget(self.vna_port)
        vna_layout.addWidget(self.vna_status_label)
        
        temp_layout = QHBoxLayout()
        temp_label = QLabel("Temperature Sensor Port:")
        self.temp_port = QComboBox()
        self.temp_port.addItems(self.get_usb_ports())
        self.temp_port.currentIndexChanged.connect(self.on_temp_port_selected)
        self.temp_status_label = QLabel("Disconnected")
        self.temp_status_label.setStyleSheet("color: red")
        temp_layout.addWidget(temp_label)
        temp_layout.addWidget(self.temp_port)
        temp_layout.addWidget(self.temp_status_label)
        
        arduino_layout = QHBoxLayout()
        arduino_label = QLabel("Arduino Port:")
        self.arduino_port = QComboBox()
        self.arduino_port.addItems(self.get_usb_ports())
        self.arduino_port.currentIndexChanged.connect(self.on_arduino_port_selected)
        self.arduino_status_label = QLabel("Disconnected")
        self.arduino_status_label.setStyleSheet("color: red")
        arduino_layout.addWidget(arduino_label)
        arduino_layout.addWidget(self.arduino_port)
        arduino_layout.addWidget(self.arduino_status_label)
        
        export_button = QPushButton("Export to CSV")
        export_button.clicked.connect(self.save_to_csv)
        
        file_layout = QHBoxLayout()
        file_label = QLabel("File Name:")
        self.file_name = QLineEdit("data.csv")
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_name)
        
        self.web_button = QPushButton("Enable Web Port")
        self.web_button.clicked.connect(self.toggle_web_port)
        
        device_layout.addLayout(vna_layout)
        device_layout.addLayout(temp_layout)
        device_layout.addLayout(arduino_layout)
        device_layout.addWidget(export_button)
        device_layout.addLayout(file_layout)
        device_layout.addWidget(self.web_button)
    
    def get_usb_ports(self):
        ports = [port.device for port in comports()]
        temper_device = usb.core.find(idVendor=0x413d, idProduct=0x2107)
        if temper_device:
            ports.append("TEMPer1F")
        return ports

    def toggle_web_port(self):
        if self.web_port_enabled:
            self.web_port_enabled = False
            print("Web port disabled")
        else:
            self.web_port_enabled = True
            print(f"Web port enabled at http://localhost:5000")
            threading.Thread(target=self.run_web_server, daemon=True).start()

    def run_web_server(self):
        app.run(host='0.0.0.0', port=5000)

    def toggle_logging(self):
        if self.is_logging:
            self.is_logging = False
            self.log_button.setText("Start Logging")
        else:
            if not self.check_connections():
                return
            try:
                interval = int(self.freq_entry.text())
                if interval <= 0:
                    raise ValueError("Measurement frequency must be a positive integer.")
                self.is_logging = True
                self.log_button.setText("Stop Logging")
                threading.Thread(target=self.log_data, daemon=True).start()
            except ValueError as e:
                QMessageBox.critical(self, "Input Error", str(e))

    def check_connections(self):
        if not self.vna_connected:
            QMessageBox.critical(self, "Connection Error", "VNA is not connected. Please connect VNA before starting logging.")
            return False
        if not self.temp_sensor_connected:
            QMessageBox.critical(self, "Connection Error", "Temperature Sensor is not connected. Please connect Temperature Sensor before starting logging.")
            return False
        return True

    def log_data(self):
        while self.is_logging:
            try:
                temp = self.read_temperature()
                vna_data = self.read_vna()
                accel_data = self.read_accelerometer()
                level_data = self.read_digital_level()

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                entry = [timestamp, temp, vna_data, accel_data, level_data]
                self.data.append(entry)

                self.update_display(temp, vna_data, accel_data, level_data)
                self.update_graph(temp)

                interval = int(self.freq_entry.text())
                threading.Event().wait(interval)

            except Exception as e:
                QMessageBox.critical(self, "Data Logging Error", f"Error reading data: {e}")
                self.is_logging = False
                self.log_button.setText("Start Logging")
                break

    def read_vna(self):
        try:
            # Send a command to set the frequency range
            self.vna.write(b'FREQ 1000000 3000000\n')
            
            # Send a command to read dB measurement data
            self.vna.write(b'READ 2000000\n')
            
            # Read the response from the miniVNA
            response = self.vna.readline().decode().strip()
            
            return response
        except Exception as e:
            print(f"Error reading from VNA: {e}")
            return "Error"

    def read_temperature(self):
        try:
            # Send a command to request temperature
            self.temp_device.ctrl_transfer(bmRequestType=0x21, bRequest=0x09, 
                                           wValue=0x0200, wIndex=0x01, data_or_wLength=[0x01,0x80,0x33,0x01,0x00,0x00,0x00,0x00])
            
            # Read the temperature data
            data = self.temp_endpoint.read(8)
            
            # Convert the raw data to temperature in Celsius
            temp = (data[3] & 0xFF) + (data[2] & 0xFF) * 256
            temp = temp * 125.0 / 32000.0
            return temp
        except Exception as e:
            print(f"Error reading temperature: {e}")
            return None

    def read_accelerometer(self):
        return self.mpu.get_accel_data()['x']

    def read_digital_level(self):
        return self.mpu.get_gyro_data()['x']

    def update_display(self, temp, vna_data, accel_data, level_data):
        self.temp_display.setText(f"{temp:.2f}C")
        self.vna_display.setText(f"{vna_data}")
        self.accel_display.setText(f"{accel_data:.2f}°")
        self.level_display.setText(f"{level_data:.2f}°")

    def update_graphs(self):
        self.ax1.clear()
        self.ax2.clear()

        timestamps = [entry[0] for entry in self.data[-50:]]  # Last 50 entries
        temps = [entry[1] for entry in self.data[-50:]]
        angles = [entry[3] for entry in self.data[-50:]]  # Using accelerometer data for angle

        self.ax1.plot(timestamps, temps)
        self.ax1.set_ylabel('Temperature (°C)')
        self.ax1.set_title('Temperature Over Time')

        self.ax2.plot(timestamps, angles)
        self.ax2.set_xlabel('Time')
        self.ax2.set_ylabel('Angle (°)')
        self.ax2.set_title('Angle Over Time')

        plt.xticks(rotation=45)
        self.fig.tight_layout()
        self.canvas.draw()

    def save_to_csv(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save CSV File", self.file_name.text(), "CSV Files (*.csv)")
        if filename:
            try:
                with open(filename, 'w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(["Timestamp", "Temperature", "VNA Data", "Accelerometer Angle", "Digital Level Angle"])
                    writer.writerows(self.data)
                QMessageBox.information(self, "Export Successful", f"Data exported to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Error exporting data: {e}")

    def closeEvent(self, event):
        self.is_logging = False  # Stop logging if active
        event.accept()
        app.do_teardown_appcontext()
        exit()

    def on_vna_port_selected(self, index):
        selected_port = self.vna_port.currentText()
        print(f"Selected VNA Port: {selected_port}")
        self.setup_vna(selected_port)

    def on_temp_port_selected(self, index):
        selected_port = self.temp_port.currentText()
        print(f"Selected Temperature Sensor: {selected_port}")
        if selected_port == "TEMPer1F":
            self.setup_temp_sensor(None)  # We don't need a port for USB device
        else:
            QMessageBox.critical(self, "Connection Error", "Please select the TEMPer1F device")

    def check_and_request_permissions(self, port):
        if not os.access(port, os.R_OK | os.W_OK):
            try:
                group = "dialout"  # This is typically the group for serial ports
                subprocess.run(["sudo", "usermod", "-a", "-G", group, os.getlogin()], check=True)
                subprocess.run(["sudo", "chmod", "a+rw", port], check=True)
                print(f"Permissions granted for {port}")
                # The user needs to log out and log back in for group changes to take effect
                QMessageBox.information(self, "Permissions Updated", 
                                        "Permissions have been updated. Please log out and log back in for changes to take effect.")
                return True
            except subprocess.CalledProcessError as e:
                print(f"Failed to set permissions: {e}")
                QMessageBox.critical(self, "Permission Error", 
                                     f"Failed to set permissions for {port}. Try running the script with sudo.")
                return False
        return True

    def setup_vna(self, port):
        if self.check_and_request_permissions(port):
            try:
                self.vna = serial.Serial(port, 115200)
                print(f"Connected to VNA on port: {port}")
                self.vna_connected = True
                self.vna_status_label.setText("Connected")
                self.vna_status_label.setStyleSheet("color: green")
            except Exception as e:
                print(f"Error connecting to VNA: {e}")
                QMessageBox.critical(self, "Connection Error", f"Error connecting to VNA: {e}")
                self.vna_connected = False
                self.vna_status_label.setText("Disconnected")
                self.vna_status_label.setStyleSheet("color: red")

    def setup_temp_sensor(self, port):
        try:
            # Find the TEMPer1F device
            self.temp_device = usb.core.find(idVendor=0x413d, idProduct=0x2107)
            
            if self.temp_device is None:
                raise ValueError("TEMPer1F device not found")
            
            # Try to set the configuration without detaching the kernel driver
            try:
                self.temp_device.set_configuration()
            except usb.core.USBError as e:
                if e.errno == 13:  # Permission denied error
                    self.show_permission_dialog()
                    return
            
            # Get the endpoint
            cfg = self.temp_device.get_active_configuration()
            intf = cfg[(0,0)]
            self.temp_endpoint = usb.util.find_descriptor(
                intf,
                custom_match = lambda e: 
                    usb.util.endpoint_direction(e.bEndpointAddress) == 
                    usb.util.ENDPOINT_IN
            )
            
            print("Connected to TEMPer1F")
            self.temp_sensor_connected = True
            self.temp_status_label.setText("Connected")
            self.temp_status_label.setStyleSheet("color: green")
        except usb.core.USBError as e:
            print(f"USB Error connecting to TEMPer1F: {e}")
            self.show_permission_dialog()
            self.temp_sensor_connected = False
            self.temp_status_label.setText("Disconnected")
            self.temp_status_label.setStyleSheet("color: red")
        except Exception as e:
            print(f"Error connecting to TEMPer1F: {e}")
            QMessageBox.critical(self, "Connection Error", f"Error connecting to TEMPer1F: {e}")
            self.temp_sensor_connected = False
            self.temp_status_label.setText("Disconnected")
            self.temp_status_label.setStyleSheet("color: red")

    def show_permission_dialog(self):
        current_user = os.getlogin()
        permission_commands = f"""
sudo tee /etc/udev/rules.d/99-temper.rules << EOF
SUBSYSTEM=="usb", ATTRS{{idVendor}}=="413d", ATTRS{{idProduct}}=="2107", MODE="0666"
EOF
sudo udevadm control --reload-rules
sudo udevadm trigger
sudo usermod -a -G dialout {current_user}
"""
        
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Grant Permissions for TEMPer1F")
        dialog.setText("To grant permissions for the TEMPer1F device, run these commands in your terminal:")
        dialog.setDetailedText(permission_commands.strip())
        dialog.setStandardButtons(QMessageBox.Ok)
        
        def copy_to_clipboard():
            pyperclip.copy(permission_commands.strip())
            QMessageBox.information(self, "Copied", "Commands copied to clipboard!")
        
        copy_button = dialog.addButton("Copy Commands", QMessageBox.ActionRole)
        copy_button.clicked.connect(copy_to_clipboard)
        
        dialog.setInformativeText("After running these commands, unplug and replug the TEMPer1F device, then restart this application.")
        dialog.exec_()

    def setup_arduino(self, port):
        try:
            self.arduino = serial.Serial(port, 115200)
            print(f"Connected to Arduino on port: {port}")
        except Exception as e:
            print(f"Error connecting to Arduino: {e}")
            QMessageBox.critical(self, "Connection Error", f"Error connecting to Arduino: {e}")
    
    def read_tilt_angle(self):
        if self.arduino:
            self.arduino.write(b"GET_TILT\n")
            response = self.arduino.readline().decode().strip()
            if response.startswith("TILT_ANGLE:"):
                tilt_angle = float(response.split(":")[1])
                return tilt_angle
        return None
    
    def set_stepper_angle(self, angle):
        if self.arduino:
            command = f"SET_ANGLE:{angle}\n".encode()
            self.arduino.write(command)
            response = self.arduino.readline().decode().strip()
            if response == "ANGLE_SET":
                print(f"Stepper angle set to {angle} degrees")
            else:
                print("Failed to set stepper angle")
    
    def on_arduino_port_selected(self, index):
        selected_port = self.arduino_port.currentText()
        print(f"Selected Arduino Port: {selected_port}")
        self.setup_arduino(selected_port)

@app.route('/')
def index():
    data = {
        'temperature': app.logger_gui.temp_display.text(),
        'vna_data': app.logger_gui.vna_display.text(),
        'accelerometer_angle': app.logger_gui.accel_display.text(),
        'digital_level_angle': app.logger_gui.level_display.text()
    }
    return render_template('index.html', data=data)

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = EnhancedAutoDataLoggerGUI()
        window.show()
        
        if ENABLE_WEB_SERVER:
            web_thread = QThread()
            web_thread.run = lambda: app.run(host='0.0.0.0', port=5000)
            web_thread.start()
        
        sys.exit(app.exec_())
    except PermissionError as e:
        print(f"Permission error: {e}")
        print("Try running the script with sudo or grant necessary permissions to the serial ports.")
    except Exception as e:
        print(f"An error occurred: {e}")
        