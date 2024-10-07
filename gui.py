import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv
from datetime import datetime
import threading
import serial
from serial.tools.list_ports import comports
from flask import Flask, jsonify, render_template
import os
import subprocess
import pyperclip
import time
from temperusb import TemperHandler

# Add the following try-except blocks after the existing import statements

try:
    import adafruit_max31865
except ImportError:
    adafruit_max31865 = None
    print("Warning: adafruit_max31865 not found. VNA functionality will be disabled.")

try:
    import adafruit_bno055
except ImportError:
    adafruit_bno055 = None
    print("Warning: adafruit_bno055 not found. Accelerometer functionality will be disabled.")

try:
    from RpiMotorLib import RpiMotorLib
except ImportError:
    RpiMotorLib = None
    print("Warning: RpiMotorLib not found. Motor controls will be disabled.")

try:
    import board
except ImportError:
    board = None
    print("Warning: board module not found. Board-specific functionalities will be disabled.")

try:
    import busio
except ImportError:
    busio = None
    print("Warning: busio module not found. I/O functionalities will be disabled.")

try:
    import digitalio
except ImportError:
    digitalio = None
    print("Warning: digitalio module not found. Digital I/O functionalities will be disabled.")

# Configuration
ENABLE_WEB_SERVER = True

app = Flask(__name__)

# Mock mpu6050 for testing
class MockMPU6050:
    def get_accel_data(self):
        return {'x': 0.0, 'y': 0.0, 'z': 0.0}
    def get_gyro_data(self):
        return {'x': 0.0, 'y': 0.0, 'z': 0.0}

mpu6050 = MockMPU6050()

class EnhancedAutoDataLoggerGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Enhanced Automated Data Logger")
        self.master.geometry("1000x700")  # Adjusted initial size
        
        self.create_widgets()
        self.data = []
        self.is_logging = False
        self.web_port_enabled = False
        self.vna_connected = False
        self.temp_sensor_connected = False
        self.motor = None
        
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)  # Handle window close event
        
        # Connect devices on startup
        self.connect_devices()
    
    def create_widgets(self):
        # Create tabs
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Logging Controls tab
        logging_tab = ttk.Frame(self.notebook)
        self.notebook.add(logging_tab, text="Logging Controls")
        
        # Current Readings tab
        readings_tab = ttk.Frame(self.notebook)
        self.notebook.add(readings_tab, text="Current Readings")
        
        # Real-time Graphs tab
        graphs_tab = ttk.Frame(self.notebook)
        self.notebook.add(graphs_tab, text="Real-time Graphs")
        
        # Device Connections tab
        device_tab = ttk.Frame(self.notebook)
        self.notebook.add(device_tab, text="Device Connections")
        
        # Motor Controls tab
        motor_tab = ttk.Frame(self.notebook)
        self.notebook.add(motor_tab, text="Motor Controls")
        
        # Logging Controls frame
        logging_frame = ttk.LabelFrame(logging_tab, text="Logging Controls")
        logging_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Frequency input
        ttk.Label(logging_frame, text="Measurement Frequency (seconds):").grid(row=0, column=0, sticky="w")
        self.freq_entry = ttk.Entry(logging_frame, width=10)
        self.freq_entry.insert(0, "1")
        self.freq_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Start/Stop button
        self.log_button = ttk.Button(logging_frame, text="Start Logging", command=self.toggle_logging)
        self.log_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        # Current Readings frame
        readings_frame = ttk.LabelFrame(readings_tab, text="Current Readings")
        readings_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Temperature display
        ttk.Label(readings_frame, text="Temperature:").grid(row=0, column=0, sticky="w")
        self.temp_display = ttk.Label(readings_frame, text="0.00C", width=10)
        self.temp_display.grid(row=0, column=1, padx=5, pady=5)
        
        # VNA data display
        ttk.Label(readings_frame, text="VNA Data:").grid(row=1, column=0, sticky="w")
        self.vna_display = ttk.Label(readings_frame, text="0.00", width=10)
        self.vna_display.grid(row=1, column=1, padx=5, pady=5)
        
        # Accelerometer angle display
        ttk.Label(readings_frame, text="Accelerometer Angle:").grid(row=2, column=0, sticky="w")
        self.accel_display = ttk.Label(readings_frame, text="0.00°", width=10)
        self.accel_display.grid(row=2, column=1, padx=5, pady=5)
        
        # Digital level angle display
        ttk.Label(readings_frame, text="Digital Level Angle:").grid(row=3, column=0, sticky="w")
        self.level_display = ttk.Label(readings_frame, text="0.00°", width=10)
        self.level_display.grid(row=3, column=1, padx=5, pady=5)
        
        # Real-time Graphs frame
        graphs_frame = ttk.LabelFrame(graphs_tab, text="Real-time Graphs")
        graphs_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Create figure and subplots
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(6, 6))
        
        # Create canvas for displaying the graphs
        self.canvas = FigureCanvasTkAgg(self.fig, master=graphs_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Device Connections frame
        device_frame = ttk.LabelFrame(device_tab, text="Device Connections")
        device_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        self.connect_button = ttk.Button(device_frame, text="Connect Devices", command=self.connect_devices)
        self.connect_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5)
        
        self.vna_status_label = ttk.Label(device_frame, text="VNA: Disconnected", foreground="red")
        self.vna_status_label.grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        
        self.temp_status_label = ttk.Label(device_frame, text="TEMPerX v3.3: Disconnected", foreground="red")
        self.temp_status_label.grid(row=4, column=0, columnspan=2, padx=5, pady=5)
        
        # Export to CSV button
        ttk.Button(device_frame, text="Export to CSV", command=self.save_to_csv).grid(row=5, column=0, columnspan=2, padx=5, pady=5)
        
        # File name entry
        ttk.Label(device_frame, text="File Name:").grid(row=6, column=0, sticky="w")
        self.file_name = ttk.Entry(device_frame, width=20)
        self.file_name.insert(0, "data.csv")
        self.file_name.grid(row=6, column=1, padx=5, pady=5)
        
        # Web Port toggle button
        self.web_button = ttk.Button(device_frame, text="Enable Web Port", command=self.toggle_web_port)
        self.web_button.grid(row=7, column=0, columnspan=2, padx=5, pady=5)
        
        # Motor Controls frame
        motor_frame = ttk.LabelFrame(motor_tab, text="Motor Controls")
        motor_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Motor angle input
        ttk.Label(motor_frame, text="Set Motor Angle:").grid(row=0, column=0, sticky="w")
        self.motor_angle_entry = ttk.Entry(motor_frame, width=10)
        self.motor_angle_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Set Motor Angle button
        self.set_motor_button = ttk.Button(motor_frame, text="Set Angle", command=self.set_motor_angle)
        self.set_motor_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
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
            self.log_button.config(text="Start Logging")
        else:
            if not self.check_connections():
                return
            try:
                interval = int(self.freq_entry.get())
                if interval <= 0:
                    raise ValueError("Measurement frequency must be a positive integer.")
                self.is_logging = True
                self.log_button.config(text="Stop Logging")
                threading.Thread(target=self.log_data, daemon=True).start()
            except ValueError as e:
                messagebox.showerror("Input Error", str(e))

    def check_connections(self):
        if not self.vna_connected:
            messagebox.showerror("Connection Error", "VNA is not connected. Please connect VNA before starting logging.")
            return False
        if not self.temp_sensor_connected:
            messagebox.showerror("Connection Error", "Temperature Sensor is not connected. Please connect Temperature Sensor before starting logging.")
            return False
        return True

    def log_data(self):
        while self.is_logging:
            try:
                temp = self.read_temperature()
                if temp is None:
                    raise ValueError("Failed to read temperature")
                vna_data = self.read_vna()
                accel_data = self.read_accelerometer()
                level_data = self.read_digital_level()

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                entry = [timestamp, temp, vna_data, accel_data, level_data]
                self.data.append(entry)

                self.update_display(temp, vna_data, accel_data, level_data)
                self.update_graphs()

                interval = int(self.freq_entry.get())
                threading.Event().wait(interval)

            except Exception as e:
                messagebox.showerror("Data Logging Error", f"Error reading data: {e}")
                self.is_logging = False
                self.master.after(0, lambda: self.log_button.config(text="Start Logging"))
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

    def setup_temp_sensor(self):
        try:
            print("Attempting to set up TEMPerX v3.3 device...")
            
            self.th = TemperHandler()
            devices = self.th.get_devices()
            
            print(f"TemperHandler found {len(devices)} device(s)")
            
            if not devices:
                print("No TEMPer devices found by TemperHandler")
                raise ValueError("TEMPerX v3.3 device not found")
            
            self.temper_device = devices[0]  # Use the first detected device
            
            # Try to read data to confirm the device is working
            temperatures = self.temper_device.get_temperatures()
            print(f"Temperatures read: {temperatures}")
            
            if len(temperatures) > 1:
                print(f"Outer temperature: {temperatures[1]:.2f}°C")
            
            print("TEMPerX v3.3 device found and configured successfully")
            self.temp_sensor_connected = True
            self.temp_status_label.config(text="TEMPerX v3.3: Connected", foreground="green")
        except Exception as e:
            print(f"Error connecting to TEMPerX v3.3 device: {e}")
            messagebox.showerror("Connection Error", f"Error connecting to TEMPerX v3.3 device: {e}")
            self.temp_sensor_connected = False
            self.temp_status_label.config(text="TEMPerX v3.3: Disconnected", foreground="red")

    def read_temperature(self):
        if self.temp_sensor_connected and hasattr(self, 'temper_device'):
            try:
                temperatures = self.temper_device.get_temperatures()
                if len(temperatures) > 1:
                    return temperatures[1]  # Return the outer temperature
                return temperatures[0]  # Return the first temperature reading if outer is not available
            except Exception as e:
                print(f"Error reading temperature: {e}")
                return None
        else:
            print("TEMPerX v3.3 device not initialized")
            return None

    def read_accelerometer(self):
        return mpu6050.get_accel_data()['x']

    def read_digital_level(self):
        return mpu6050.get_gyro_data()['x']

    def update_display(self, temp, vna_data, accel_data, level_data):
        self.temp_display.config(text=f"{temp:.2f}C")
        self.vna_display.config(text=f"{vna_data}")
        self.accel_display.config(text=f"{accel_data:.2f}°")
        self.level_display.config(text=f"{level_data:.2f}°")

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
        filename = self.file_name.get()
        try:
            with open(filename, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Timestamp", "Temperature", "VNA Data", "Accelerometer Angle", "Digital Level Angle"])
                writer.writerows(self.data)
            messagebox.showinfo("Export Successful", f"Data exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting data: {e}")

    def on_closing(self):
        self.is_logging = False  # Stop logging if active
        self.master.destroy()
        self.master.quit()
        app.do_teardown_appcontext()
        exit()

    def connect_devices(self):
        self.setup_vna()
        self.setup_temp_sensor()
        self.setup_motor()

    def setup_vna(self):
        try:
            vna_port = next((port.device for port in comports() if 'USB' in port.device), None)
            if vna_port:
                self.vna = serial.Serial(vna_port, 115200)
                print(f"Connected to VNA on port: {vna_port}")
                self.vna_connected = True
                self.vna_status_label.config(text="VNA: Connected", foreground="green")
            else:
                raise ValueError("VNA device not found")
        except Exception as e:
            print(f"Error connecting to VNA: {e}")
            messagebox.showerror("Connection Error", f"Error connecting to VNA: {e}")
            self.vna_connected = False
            self.vna_status_label.config(text="VNA: Disconnected", foreground="red")

    def setup_motor(self):
        try:
            self.motor = RpiMotorLib.BYJMotor("StepperMotor", "28BYJ")
            print("Stepper motor setup complete")
        except Exception as e:
            print(f"Error setting up stepper motor: {e}")
            messagebox.showerror("Connection Error", f"Error setting up stepper motor: {e}")

    def set_motor_angle(self):
        try:
            angle = float(self.motor_angle_entry.get())
            steps = int(angle * (4096 / 360))  # Convert angle to steps for 28BYJ motor
            self.motor.motor_run(digitalio.DigitalInOut(board.D23), 0.001, steps, False, False, "half")
            print(f"Motor set to angle: {angle}")
        except Exception as e:
            messagebox.showerror("Motor Error", f"Error setting motor angle: {e}")

@app.route('/')
def index():
    data = {
        'temperature': app.logger_gui.temp_display.cget("text"),
        'vna_data': app.logger_gui.vna_display.cget("text"),
        'accelerometer_angle': app.logger_gui.accel_display.cget("text"),
        'digital_level_angle': app.logger_gui.level_display.cget("text")
    }
    return render_template('index.html', data=data)

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app.logger_gui = EnhancedAutoDataLoggerGUI(root)

        if ENABLE_WEB_SERVER:
            threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5000}, daemon=True).start()

        root.mainloop()
    except PermissionError as e:
        print(f"Permission error: {e}")
        print("Try running the script with sudo or grant necessary permissions to the serial ports.")
    except Exception as e:
        print(f"An error occurred: {e}")