import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
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
import math
from mpl_toolkits.mplot3d import Axes3D
import logging
import time
import numpy as np
from scipy.spatial.transform import Rotation as R

# Configuration
ENABLE_WEB_SERVER = False

app = Flask(__name__)

VNA_EXPORTS_FOLDER = "/home/nate/Desktop/Python_GUI_TS1500_Probe-B/VNA_Exports"

class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.configure(state='normal')
        if hasattr(record, 'color'):
            self.text_widget.insert(tk.END, msg + '\n', record.color)
        else:
            self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.configure(state='disabled')
        self.text_widget.see(tk.END)

class EnhancedAutoDataLoggerGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Enhanced Automated Data Logger")
        self.master.geometry("800x600")  # Adjusted initial size
        
        # Set dark mode color scheme
        self.master.configure(background='#1c1c1c')
        ttk.Style().configure('TFrame', background='#1c1c1c')
        ttk.Style().configure('TLabelframe', background='#1c1c1c', foreground='white')
        ttk.Style().configure('TLabelframe.Label', background='#1c1c1c', foreground='white')
        ttk.Style().configure('TLabel', background='#1c1c1c', foreground='white')
        ttk.Style().configure('TButton', background='#4c4c4c', foreground='white')
        ttk.Style().configure('TEntry', fieldbackground='#4c4c4c', foreground='white')
        ttk.Style().configure('TCombobox', fieldbackground='#4c4c4c', foreground='white')
        ttk.Style().configure('TNotebook', background='#1c1c1c')
        ttk.Style().configure('TNotebook.Tab', background='#4c4c4c', foreground='white')
        
        self.create_logger()
        self.create_widgets()
        self.data = []
        self.is_logging = False
        self.web_port_enabled = False
        self.vna_connected = False
        self.vna_data = None
        self.temp_sensor_connected = False
        self.arduino = None
        self.arduino_port = None
        self.find_and_connect_arduino()
        
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)  # Handle window close event
        self.connect_devices()
        
        self.create_logger()
        self.gyro_bias = np.zeros(3)
        self.orientation = np.array([1, 0, 0, 0])  # Initial orientation as a quaternion
    
    def create_logger(self):
        self.log_widget = ScrolledText(self.master, state='disabled', height=10, bg='#4c4c4c', fg='white')
        self.log_widget.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        
        text_handler = TextHandler(self.log_widget)
        self.logger.addHandler(text_handler)
    
    def find_and_connect_arduino(self):
        ports = self.get_usb_ports()
        for port in ports:
            if 'Arduino Due' in port:
                self.arduino_port = port.split(' ')[0]  # Extract the port name
                self.setup_arduino(self.arduino_port)
                # Update the dropdown menu
                self.arduino_port_combobox.set(port)
                break
    
    def create_widgets(self):
        # Create tabs
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Logging Controls tab
        logging_tab = ttk.Frame(self.notebook)
        self.notebook.add(logging_tab, text="Logging Controls")
        
        # Data tab
        data_tab = ttk.Frame(self.notebook)
        self.notebook.add(data_tab, text="Data")
        
        # Device Connections tab
        device_tab = ttk.Frame(self.notebook)
        self.notebook.add(device_tab, text="Device Connections")
        
        # Test tab
        test_tab = ttk.Frame(self.notebook)
        self.notebook.add(test_tab, text="Test")
        
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
        
        # Data frame
        data_frame = ttk.Frame(data_tab)
        data_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Accelerometer data display
        accel_frame = ttk.LabelFrame(data_frame, text="Accelerometer Data")
        accel_frame.pack(padx=10, pady=10)

        self.accel_display = ttk.Label(accel_frame, text="N/A")
        self.accel_display.pack()

        # Create figure and subplots
        self.fig = plt.figure(figsize=(12, 6))
        self.ax1 = self.fig.add_subplot(121)  # Temperature graph on the left
        self.ax3 = self.fig.add_subplot(122, projection='3d')  # 3D angle visualization on the right

        # Set dark mode colors for the plots
        self.fig.patch.set_facecolor('#1c1c1c')
        self.ax1.set_facecolor('#4c4c4c')
        self.ax3.set_facecolor('#4c4c4c')
        self.ax1.xaxis.label.set_color('white')
        self.ax1.yaxis.label.set_color('white')
        self.ax1.tick_params(axis='x', colors='white')
        self.ax1.tick_params(axis='y', colors='white')
        
        # Set up 3D plot
        self.ax3.set_xlim(-1, 1)
        self.ax3.set_ylim(-1, 1)
        self.ax3.set_zlim(-1, 1)
        self.ax3.set_xticklabels([])
        self.ax3.set_yticklabels([])
        self.ax3.set_zticklabels([])
        self.ax3.grid(False)
        self.ax3.xaxis.line.set_color('red')
        self.ax3.yaxis.line.set_color('green')
        self.ax3.zaxis.line.set_color('blue')
        self.ax3.set_xlabel('X', color='red')
        self.ax3.set_ylabel('Y', color='green')
        self.ax3.set_zlabel('Z', color='blue')
        self.ax3.xaxis.pane.fill = False
        self.ax3.yaxis.pane.fill = False
        self.ax3.zaxis.pane.fill = False
        self.ax3.xaxis.pane.set_edgecolor('none')
        self.ax3.yaxis.pane.set_edgecolor('none')
        self.ax3.zaxis.pane.set_edgecolor('none')

        # Disable mouse interaction
        self.ax3.mouse_init(rotate_btn=None, zoom_btn=None)

        # Set initial view
        self.ax3.view_init(elev=30, azim=45)

        # Create canvas for displaying the graphs
        self.canvas = FigureCanvasTkAgg(self.fig, master=data_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Device Connections frame
        device_frame = ttk.LabelFrame(device_tab, text="Device Connections")
        device_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Remove VNA Port selection
        
        ttk.Label(device_frame, text="Temperature Sensor Port:").grid(row=1, column=0, sticky="w", pady=5)
        self.temp_port = ttk.Combobox(device_frame, values=self.get_usb_ports(), state="readonly", width=15)
        self.temp_port.grid(row=1, column=1, pady=5)
        self.temp_port.bind("<<ComboboxSelected>>", self.on_temp_port_selected)
        self.temp_status_label = ttk.Label(device_frame, text="Disconnected", foreground="red")
        self.temp_status_label.grid(row=1, column=2, padx=5)
        
        ttk.Label(device_frame, text="Arduino Port:").grid(row=0, column=0, sticky="w", pady=5)
        self.arduino_port_combobox = ttk.Combobox(device_frame, values=self.get_usb_ports(), state="readonly", width=30)
        self.arduino_port_combobox.grid(row=0, column=1, pady=5)
        self.arduino_port_combobox.bind("<<ComboboxSelected>>", self.on_arduino_port_selected)
        self.arduino_status_label = ttk.Label(device_frame, text="Disconnected", foreground="red")
        self.arduino_status_label.grid(row=0, column=2, padx=5)
        
        # Export to CSV button
        ttk.Button(device_frame, text="Export to CSV", command=self.save_to_csv).grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        
        # File name entry
        ttk.Label(device_frame, text="File Name:").grid(row=4, column=0, sticky="w")
        self.file_name = ttk.Entry(device_frame, width=20)
        self.file_name.insert(0, "data.csv")
        self.file_name.grid(row=4, column=1, padx=5, pady=5)
        
        # Web Port toggle button
        self.web_button = ttk.Button(device_frame, text="Enable Web Port", command=self.toggle_web_port)
        self.web_button.grid(row=5, column=0, columnspan=2, padx=5, pady=5)
        
        # Test frame
        test_frame = ttk.LabelFrame(test_tab, text="Test Controls")
        test_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Test VNA Sweep button
        ttk.Button(test_frame, text="Test VNA Sweep", command=self.test_vna_sweep).pack(pady=5)
        
        # Get Angle button
        ttk.Button(test_frame, text="Get Angle", command=self.get_angle).pack(pady=5)
        
        # Calibrate button
        ttk.Button(test_frame, text="Calibrate", command=self.calibrate_sensor).pack(pady=5)
        
        # Bind F12 key to activate VNA sweep
        self.master.bind('<F12>', self.activate_vna_sweep)
    
    def get_usb_ports(self):
        ports = []
        for port in comports():
            if 'Arduino Due' in port.description:
                ports.append(f"{port.device} (Arduino Due)")
            elif 'FT230X Basic UART' in port.description:
                ports.append(f"{port.device} (mini VNA tiny)")
            else:
                ports.append(port.device)
        
        temper_device = usb.core.find(idVendor=0x413d, idProduct=0x2107)
        if temper_device:
            ports.append("TEMPer1F")
        
        return ports

    def toggle_web_port(self):
        if self.web_port_enabled:
            self.web_port_enabled = False
            self.logger.info("Web port disabled")
        else:
            self.web_port_enabled = True
            self.logger.info(f"Web port enabled at http://localhost:5000")
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
                self.logger.error(f"Input Error: {str(e)}", extra={'color': 'red'})

    def check_connections(self):
        if not self.temp_sensor_connected:
            self.logger.error("Temperature Sensor is not connected. Please connect Temperature Sensor before starting logging.", extra={'color': 'red'})
            return False
        return True

    def log_data(self):
        while self.is_logging:
            try:
                temp = self.read_temperature()
                self.read_vna_data()  # Read the latest VNA data
                accel_data = self.read_accelerometer()
                level_data = self.read_digital_level()

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                entry = [timestamp, temp, self.vna_data, accel_data, level_data]
                self.data.append(entry)

                self.update_display(temp, self.vna_data, accel_data, level_data)
                self.update_graphs()

                interval = int(self.freq_entry.get())
                threading.Event().wait(interval)

            except Exception as e:
                self.logger.error(f"Data Logging Error: Error reading data: {e}", extra={'color': 'red'})
                self.is_logging = False
                self.master.after(0, lambda: self.log_button.config(text="Start Logging"))
                break

    def read_vna_data(self):
        try:
            latest_file = self.get_latest_vna_file()
            if latest_file:
                with open(latest_file, 'r') as file:
                    lines = file.readlines()
                    if len(lines) >= 4:
                        self.vna_data = ''.join(lines[:4])
                        self.logger.info(f"VNA data:\n{self.vna_data}")
                    else:
                        self.logger.warning("Insufficient data in the VNA file.")
            else:
                self.logger.warning("No VNA file found.")
        except Exception as e:
            self.logger.error(f"Error reading VNA data: {e}")
            self.logger.exception("Traceback:")  # Log the traceback for debugging

    def get_latest_vna_file(self):
        try:
            files = os.listdir(VNA_EXPORTS_FOLDER)
            vna_files = [f for f in files if f.startswith("VNA_") and f.endswith(".csv")]
            if vna_files:
                latest_file = max(vna_files, key=lambda f: os.path.getctime(os.path.join(VNA_EXPORTS_FOLDER, f)))
                return os.path.join(VNA_EXPORTS_FOLDER, latest_file)
            else:
                self.logger.warning("No VNA files found in the exports folder.")
        except Exception as e:
            self.logger.error(f"Error getting the latest VNA file: {e}")
            self.logger.exception("Traceback:")  # Log the traceback for debugging
        return None

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
            self.logger.error(f"Error reading temperature: {e}")
            return None

    def read_accelerometer(self):
        if self.arduino:
            self.arduino.write(b"GET_ACCEL\n")
            self.arduino.timeout = 1  # Set a timeout of 1 second
            
            try:
                response = self.arduino.readline().decode().strip()
                if response.startswith("XYZ:"):
                    try:
                        values = response.split(":")[1].split(",")
                        if len(values) == 6:
                            ax, ay, az = map(int, values[:3])
                            gx, gy, gz = map(float, values[3:])
                            return ax, ay, az, gx, gy, gz
                        else:
                            self.logger.error("Invalid accelerometer data format")
                    except ValueError:
                        self.logger.error("Invalid accelerometer data format")
            except serial.SerialTimeoutException:
                self.logger.warning("Timeout waiting for accelerometer data")
        
        return None, None, None, None, None, None

    def read_digital_level(self):
        return None  # Placeholder, implement if needed

    def update_display(self, temp, vna_data, accel_data, level_data):
        self.temp_display.config(text=f"{temp:.2f}C")
        self.vna_display.config(text=f"{vna_data}")
        if accel_data is not None:
            x, y, z, _, _, _ = accel_data
            self.accel_display.config(text=f"X: {x}, Y: {y}, Z: {z}")
        else:
            self.accel_display.config(text="N/A")
        self.level_display.config(text=f"{level_data:.2f}°")

    def update_graphs(self):
        self.ax1.clear()

        timestamps = [entry[0] for entry in self.data[-50:]]  # Last 50 entries
        temps = [entry[1] for entry in self.data[-50:]]

        self.ax1.plot(timestamps, temps)
        self.ax1.set_ylabel('Temperature (°C)')
        self.ax1.set_title('Temperature Over Time')
        self.ax1.tick_params(axis='x', rotation=45)

        # Update 3D angle visualization
        self.update_3d_plot()

        self.fig.tight_layout()
        self.canvas.draw()

    def update_3d_plot(self):
        if not self.data or len(self.data[-1]) < 4 or self.data[-1][3] is None:
            return

        self.ax3.clear()
        
        # Convert accelerometer data to g-force
        accel_range = 4  # Accelerometer range is set to ±4g
        ax_g = self.data[-1][3][0] / 32768.0 * accel_range
        ay_g = self.data[-1][3][1] / 32768.0 * accel_range
        az_g = self.data[-1][3][2] / 32768.0 * accel_range
        
        # Convert gyroscope data to degrees per second
        gyro_range = 500  # Gyroscope range is set to ±500 degrees/second
        gx_dps = self.data[-1][3][3] / 32768.0 * gyro_range
        gy_dps = self.data[-1][3][4] / 32768.0 * gyro_range
        gz_dps = self.data[-1][3][5] / 32768.0 * gyro_range
        
        # Calculate accelerometer angles
        accel_angle_x = np.arctan2(ay_g, np.sqrt(ax_g**2 + az_g**2)) * 180 / np.pi
        accel_angle_y = np.arctan2(-ax_g, np.sqrt(ay_g**2 + az_g**2)) * 180 / np.pi
        
        # Complementary filter
        alpha = 0.98
        dt = 0.01  # Assuming 10ms interval
        
        if not hasattr(self, 'angle_x'):
            self.angle_x = accel_angle_x
            self.angle_y = accel_angle_y
        
        self.angle_x = alpha * (self.angle_x + gx_dps * dt) + (1 - alpha) * accel_angle_x
        self.angle_y = alpha * (self.angle_y + gy_dps * dt) + (1 - alpha) * accel_angle_y
        
        # Set plot limits based on accelerometer and gyroscope ranges
        self.ax3.set_xlim(-accel_range, accel_range)
        self.ax3.set_ylim(-accel_range, accel_range)
        self.ax3.set_zlim(-accel_range, accel_range)
        
        # Remove tick labels
        self.ax3.set_xticklabels([])
        self.ax3.set_yticklabels([])
        self.ax3.set_zticklabels([])
        
        # Remove grid lines
        self.ax3.grid(False)
        
        # Set axis colors and labels
        self.ax3.xaxis.line.set_color('red')
        self.ax3.yaxis.line.set_color('green')
        self.ax3.zaxis.line.set_color('blue')
        self.ax3.set_xlabel('X', color='red')
        self.ax3.set_ylabel('Y', color='green')
        self.ax3.set_zlabel('Z', color='blue')
        
        self.ax3.set_title('Orientation')

        # Convert angles to radians
        angle_x_rad = np.radians(self.angle_x)
        angle_y_rad = np.radians(self.angle_y)
        
        # Calculate rotation matrix
        rot_x = np.array([[1, 0, 0],
                          [0, np.cos(angle_x_rad), -np.sin(angle_x_rad)],
                          [0, np.sin(angle_x_rad), np.cos(angle_x_rad)]])
        
        rot_y = np.array([[np.cos(angle_y_rad), 0, np.sin(angle_y_rad)],
                          [0, 1, 0],
                          [-np.sin(angle_y_rad), 0, np.cos(angle_y_rad)]])
        
        rotation_matrix = np.dot(rot_y, rot_x)

        # Create a cube to represent the orientation
        cube_size = 1
        cube_vertices = np.array([
            [-cube_size, -cube_size, -cube_size],
            [cube_size, -cube_size, -cube_size],
            [cube_size, cube_size, -cube_size],
            [-cube_size, cube_size, -cube_size],
            [-cube_size, -cube_size, cube_size],
            [cube_size, -cube_size, cube_size],
            [cube_size, cube_size, cube_size],
            [-cube_size, cube_size, cube_size]
        ])

        # Apply rotation to the cube vertices
        rotated_vertices = np.dot(rotation_matrix, cube_vertices.T).T

        # Plot the cube
        self.ax3.plot(rotated_vertices[:, 0], rotated_vertices[:, 1], rotated_vertices[:, 2], 'k-')

        # Connect the vertices to form the cube edges
        edges = [
            [0, 1], [1, 2], [2, 3], [3, 0],  # Bottom face
            [4, 5], [5, 6], [6, 7], [7, 4],  # Top face
            [0, 4], [1, 5], [2, 6], [3, 7]   # Vertical edges
        ]

        for edge in edges:
            self.ax3.plot(rotated_vertices[edge, 0], rotated_vertices[edge, 1], rotated_vertices[edge, 2], 'k-')

        # Only show the main axes
        self.ax3.xaxis.pane.fill = False
        self.ax3.yaxis.pane.fill = False
        self.ax3.zaxis.pane.fill = False

        self.ax3.xaxis.pane.set_edgecolor('none')
        self.ax3.yaxis.pane.set_edgecolor('none')
        self.ax3.zaxis.pane.set_edgecolor('none')

        # Disable mouse interaction
        self.ax3.mouse_init(rotate_btn=None, zoom_btn=None)

        # Set static view
        self.ax3.view_init(elev=30, azim=45)

        self.canvas.draw()

    def save_to_csv(self):
        filename = self.file_name.get()
        try:
            with open(filename, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Timestamp", "Temperature", "VNA Data", "Accelerometer Angle", "Digital Level Angle"])
                writer.writerows(self.data)
            self.logger.info(f"Data exported to {filename}")
        except Exception as e:
            self.logger.error(f"Export Error: Error exporting data: {e}", extra={'color': 'red'})

    def on_closing(self):
        self.is_logging = False  # Stop logging if active
        self.master.destroy()
        self.master.quit()
        app.do_teardown_appcontext()
        exit()

    def on_temp_port_selected(self, event):
        selected_port = self.temp_port.get()
        self.logger.info(f"Selected Temperature Sensor: {selected_port}")
        if selected_port == "TEMPer1F":
            self.setup_temp_sensor(None)  # We don't need a port for USB device
        else:
            self.logger.error("Please select the TEMPer1F device", extra={'color': 'red'})

    def check_and_request_permissions(self, port):
        if not os.access(port, os.R_OK | os.W_OK):
            try:
                group = "dialout"  # This is typically the group for serial ports
                subprocess.run(["sudo", "usermod", "-a", "-G", group, os.getlogin()], check=True)
                subprocess.run(["sudo", "chmod", "a+rw", port], check=True)
                self.logger.info(f"Permissions granted for {port}")
                # The user needs to log out and log back in for group changes to take effect
                self.logger.info("Permissions updated. Please log out and log back in for changes to take effect.", extra={'color': 'red'})
                return True
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to set permissions: {e}", extra={'color': 'red'})
                self.logger.error(f"Failed to set permissions for {port}. Try running the script with sudo.", extra={'color': 'red'})
                return False
        return True

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
            
            self.logger.info("Connected to TEMPer1F")
            self.temp_sensor_connected = True
            self.temp_status_label.config(text="Connected", foreground="green")
        except usb.core.USBError as e:
            self.logger.error(f"USB Error connecting to TEMPer1F: {e}", extra={'color': 'red'})
            self.show_permission_dialog()
            self.temp_sensor_connected = False
            self.temp_status_label.config(text="Disconnected", foreground="red")
        except Exception as e:
            self.logger.error(f"Error connecting to TEMPer1F: {e}", extra={'color': 'red'})
            self.temp_sensor_connected = False
            self.temp_status_label.config(text="Disconnected", foreground="red")

class EnhancedAutoDataLoggerGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Enhanced Automated Data Logger")
        self.master.geometry("800x600")  # Adjusted initial size
        
        # Set dark mode color scheme
        self.master.configure(background='#1c1c1c')
        ttk.Style().configure('TFrame', background='#1c1c1c')
        ttk.Style().configure('TLabelframe', background='#1c1c1c', foreground='white')
        ttk.Style().configure('TLabelframe.Label', background='#1c1c1c', foreground='white')
        ttk.Style().configure('TLabel', background='#1c1c1c', foreground='white')
        ttk.Style().configure('TButton', background='#4c4c4c', foreground='white')
        ttk.Style().configure('TEntry', fieldbackground='#4c4c4c', foreground='white')
        ttk.Style().configure('TCombobox', fieldbackground='#4c4c4c', foreground='white')
        ttk.Style().configure('TNotebook', background='#1c1c1c')
        ttk.Style().configure('TNotebook.Tab', background='#4c4c4c', foreground='white')
        
        self.create_logger()
        self.create_widgets()
        self.data = []
        self.is_logging = False
        self.web_port_enabled = False
        self.vna_connected = False
        self.vna_data = None
        self.temp_sensor_connected = False
        self.arduino = None
        self.arduino_port = None
        self.find_and_connect_arduino()
        
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)  # Handle window close event
        self.connect_devices()
        
        self.create_logger()
        self.gyro_bias = np.zeros(3)
        self.orientation = np.array([1, 0, 0, 0])  # Initial orientation as a quaternion
    
    def create_logger(self):
        self.log_widget = ScrolledText(self.master, state='disabled', height=10, bg='#4c4c4c', fg='white')
        self.log_widget.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        
        text_handler = TextHandler(self.log_widget)
        self.logger.addHandler(text_handler)
    
    def find_and_connect_arduino(self):
        ports = self.get_usb_ports()
        for port in ports:
            if 'Arduino Due' in port:
                self.arduino_port = port.split(' ')[0]  # Extract the port name
                self.setup_arduino(self.arduino_port)
                # Update the dropdown menu
                self.arduino_port_combobox.set(port)
                break
    
    def create_widgets(self):
        # Create tabs
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Logging Controls tab
        logging_tab = ttk.Frame(self.notebook)
        self.notebook.add(logging_tab, text="Logging Controls")
        
        # Data tab
        data_tab = ttk.Frame(self.notebook)
        self.notebook.add(data_tab, text="Data")
        
        # Device Connections tab
        device_tab = ttk.Frame(self.notebook)
        self.notebook.add(device_tab, text="Device Connections")
        
        # Test tab
        test_tab = ttk.Frame(self.notebook)
        self.notebook.add(test_tab, text="Test")
        
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
        
        # Data frame
        data_frame = ttk.Frame(data_tab)
        data_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Create figure and subplots
        self.fig = plt.figure(figsize=(12, 6))
        self.ax1 = self.fig.add_subplot(121)  # Temperature graph on the left
        self.ax3 = self.fig.add_subplot(122, projection='3d')  # 3D angle visualization on the right

        # Set dark mode colors for the plots
        self.fig.patch.set_facecolor('#1c1c1c')
        self.ax1.set_facecolor('#4c4c4c')
        self.ax3.set_facecolor('#4c4c4c')
        self.ax1.xaxis.label.set_color('white')
        self.ax1.yaxis.label.set_color('white')
        self.ax1.tick_params(axis='x', colors='white')
        self.ax1.tick_params(axis='y', colors='white')
        self.ax3.xaxis.label.set_color('red')
        self.ax3.yaxis.label.set_color('green')
        self.ax3.zaxis.label.set_color('blue')
        self.ax3.tick_params(axis='x', colors='white')
        self.ax3.tick_params(axis='y', colors='white')
        self.ax3.tick_params(axis='z', colors='white')

        # Set up 3D plot
        self.ax3.set_xlim(-1, 1)
        self.ax3.set_ylim(-1, 1)
        self.ax3.set_zlim(-1, 1)
        self.ax3.set_xticklabels([])
        self.ax3.set_yticklabels([])
        self.ax3.set_zticklabels([])
        self.ax3.grid(False)
        self.ax3.xaxis.line.set_color('red')
        self.ax3.yaxis.line.set_color('green')
        self.ax3.zaxis.line.set_color('blue')
        self.ax3.set_xlabel('X', color='red')
        self.ax3.set_ylabel('Y', color='green')
        self.ax3.set_zlabel('Z', color='blue')
        self.ax3.xaxis.pane.fill = False
        self.ax3.yaxis.pane.fill = False
        self.ax3.zaxis.pane.fill = False
        self.ax3.xaxis.pane.set_edgecolor('none')
        self.ax3.yaxis.pane.set_edgecolor('none')
        self.ax3.zaxis.pane.set_edgecolor('none')

        # Disable mouse interaction
        self.ax3.mouse_init(rotate_btn=None, zoom_btn=None)

        # Set initial view
        self.ax3.view_init(elev=30, azim=45)

        # Create canvas for displaying the graphs
        self.canvas = FigureCanvasTkAgg(self.fig, master=data_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Device Connections frame
        device_frame = ttk.LabelFrame(device_tab, text="Device Connections")
        device_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Remove VNA Port selection
        
        ttk.Label(device_frame, text="Temperature Sensor Port:").grid(row=1, column=0, sticky="w", pady=5)
        self.temp_port = ttk.Combobox(device_frame, values=self.get_usb_ports(), state="readonly", width=15)
        self.temp_port.grid(row=1, column=1, pady=5)
        self.temp_port.bind("<<ComboboxSelected>>", self.on_temp_port_selected)
        self.temp_status_label = ttk.Label(device_frame, text="Disconnected", foreground="red")
        self.temp_status_label.grid(row=1, column=2, padx=5)
        
        ttk.Label(device_frame, text="Arduino Port:").grid(row=0, column=0, sticky="w", pady=5)
        self.arduino_port_combobox = ttk.Combobox(device_frame, values=self.get_usb_ports(), state="readonly", width=30)
        self.arduino_port_combobox.grid(row=0, column=1, pady=5)
        self.arduino_port_combobox.bind("<<ComboboxSelected>>", self.on_arduino_port_selected)
        self.arduino_status_label = ttk.Label(device_frame, text="Disconnected", foreground="red")
        self.arduino_status_label.grid(row=0, column=2, padx=5)
        
        # Export to CSV button
        ttk.Button(device_frame, text="Export to CSV", command=self.save_to_csv).grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        
        # File name entry
        ttk.Label(device_frame, text="File Name:").grid(row=4, column=0, sticky="w")
        self.file_name = ttk.Entry(device_frame, width=20)
        self.file_name.insert(0, "data.csv")
        self.file_name.grid(row=4, column=1, padx=5, pady=5)
        
        # Web Port toggle button
        self.web_button = ttk.Button(device_frame, text="Enable Web Port", command=self.toggle_web_port)
        self.web_button.grid(row=5, column=0, columnspan=2, padx=5, pady=5)
        
        # Test frame
        test_frame = ttk.LabelFrame(test_tab, text="Test Controls")
        test_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Test VNA Sweep button
        ttk.Button(test_frame, text="Test VNA Sweep", command=self.test_vna_sweep).pack(pady=5)
        
        # Get Angle button
        ttk.Button(test_frame, text="Get Angle", command=self.get_angle).pack(pady=5)
        
        # Calibrate button
        ttk.Button(test_frame, text="Calibrate", command=self.calibrate_sensor).pack(pady=5)
        
        # Bind F12 key to activate VNA sweep
        self.master.bind('<F12>', self.activate_vna_sweep)
    
    def get_usb_ports(self):
        ports = []
        for port in comports():
            if 'Arduino Due' in port.description:
                ports.append(f"{port.device} (Arduino Due)")
            elif 'FT230X Basic UART' in port.description:
                ports.append(f"{port.device} (mini VNA tiny)")
            else:
                ports.append(port.device)
        
        temper_device = usb.core.find(idVendor=0x413d, idProduct=0x2107)
        if temper_device:
            ports.append("TEMPer1F")
        
        return ports

    def toggle_web_port(self):
        if self.web_port_enabled:
            self.web_port_enabled = False
            self.logger.info("Web port disabled")
        else:
            self.web_port_enabled = True
            self.logger.info(f"Web port enabled at http://localhost:5000")
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
                self.logger.error(f"Input Error: {str(e)}", extra={'color': 'red'})

    def check_connections(self):
        if not self.temp_sensor_connected:
            self.logger.error("Temperature Sensor is not connected. Please connect Temperature Sensor before starting logging.", extra={'color': 'red'})
            return False
        return True

    def log_data(self):
        while self.is_logging:
            try:
                temp = self.read_temperature()
                self.read_vna_data()  # Read the latest VNA data
                accel_data = self.read_accelerometer()
                level_data = self.read_digital_level()

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                entry = [timestamp, temp, self.vna_data, accel_data, level_data]
                self.data.append(entry)

                self.update_display(temp, self.vna_data, accel_data, level_data)
                self.update_graphs()

                interval = int(self.freq_entry.get())
                threading.Event().wait(interval)

            except Exception as e:
                self.logger.error(f"Data Logging Error: Error reading data: {e}", extra={'color': 'red'})
                self.is_logging = False
                self.master.after(0, lambda: self.log_button.config(text="Start Logging"))
                break

    def read_vna_data(self):
        try:
            latest_file = self.get_latest_vna_file()
            if latest_file:
                with open(latest_file, 'r') as file:
                    lines = file.readlines()
                    if len(lines) >= 4:
                        self.vna_data = ''.join(lines[:4])
                        self.logger.info(f"VNA data:\n{self.vna_data}")
                    else:
                        self.logger.warning("Insufficient data in the VNA file.")
            else:
                self.logger.warning("No VNA file found.")
        except Exception as e:
            self.logger.error(f"Error reading VNA data: {e}")
            self.logger.exception("Traceback:")  # Log the traceback for debugging

    def get_latest_vna_file(self):
        try:
            files = os.listdir(VNA_EXPORTS_FOLDER)
            vna_files = [f for f in files if f.startswith("VNA_") and f.endswith(".csv")]
            if vna_files:
                latest_file = max(vna_files, key=lambda f: os.path.getctime(os.path.join(VNA_EXPORTS_FOLDER, f)))
                return os.path.join(VNA_EXPORTS_FOLDER, latest_file)
            else:
                self.logger.warning("No VNA files found in the exports folder.")
        except Exception as e:
            self.logger.error(f"Error getting the latest VNA file: {e}")
            self.logger.exception("Traceback:")  # Log the traceback for debugging
        return None

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
            self.logger.error(f"Error reading temperature: {e}")
            return None

    def read_accelerometer(self):
        if self.arduino:
            self.arduino.write(b"GET_ACCEL\n")
            self.arduino.timeout = 1  # Set a timeout of 1 second
            
            try:
                response = self.arduino.readline().decode().strip()
                if response.startswith("XYZ:"):
                    try:
                        values = response.split(":")[1].split(",")
                        if len(values) == 6:
                            ax, ay, az = map(int, values[:3])
                            gx, gy, gz = map(float, values[3:])
                            return ax, ay, az, gx, gy, gz
                        else:
                            self.logger.error("Invalid accelerometer data format")
                    except ValueError:
                        self.logger.error("Invalid accelerometer data format")
            except serial.SerialTimeoutException:
                self.logger.warning("Timeout waiting for accelerometer data")
        
        return None, None, None, None, None, None

    def read_digital_level(self):
        return None  # Placeholder, implement if needed

    def update_display(self, temp, vna_data, accel_data, level_data):
        self.temp_display.config(text=f"{temp:.2f}C")
        self.vna_display.config(text=f"{vna_data}")
        if accel_data is not None:
            x, y, z, _, _, _ = accel_data
            self.accel_display.config(text=f"X: {x}, Y: {y}, Z: {z}")
        else:
            self.accel_display.config(text="N/A")
        self.level_display.config(text=f"{level_data:.2f}°")

    def update_graphs(self):
        self.ax1.clear()

        timestamps = [entry[0] for entry in self.data[-50:]]  # Last 50 entries
        temps = [entry[1] for entry in self.data[-50:]]

        self.ax1.plot(timestamps, temps)
        self.ax1.set_ylabel('Temperature (°C)')
        self.ax1.set_title('Temperature Over Time')
        self.ax1.tick_params(axis='x', rotation=45)

        # Update 3D angle visualization
        self.update_3d_plot()

        self.fig.tight_layout()
        self.canvas.draw()

    def update_3d_plot(self):
        if not self.data or len(self.data[-1]) < 4 or self.data[-1][3] is None:
            return

        self.ax3.clear()
        
        # Convert accelerometer data to g-force
        accel_range = 4  # Accelerometer range is set to ±4g
        ax_g = self.data[-1][3][0] / 32768.0 * accel_range
        ay_g = self.data[-1][3][1] / 32768.0 * accel_range
        az_g = self.data[-1][3][2] / 32768.0 * accel_range
        
        # Convert gyroscope data to degrees per second
        gyro_range = 500  # Gyroscope range is set to ±500 degrees/second
        gx_dps = self.data[-1][3][3] / 32768.0 * gyro_range
        gy_dps = self.data[-1][3][4] / 32768.0 * gyro_range
        gz_dps = self.data[-1][3][5] / 32768.0 * gyro_range
        
        # Calculate accelerometer angles
        accel_angle_x = np.arctan2(ay_g, np.sqrt(ax_g**2 + az_g**2)) * 180 / np.pi
        accel_angle_y = np.arctan2(-ax_g, np.sqrt(ay_g**2 + az_g**2)) * 180 / np.pi
        
        # Complementary filter
        alpha = 0.98
        dt = 0.01  # Assuming 10ms interval
        
        if not hasattr(self, 'angle_x'):
            self.angle_x = accel_angle_x
            self.angle_y = accel_angle_y
        
        self.angle_x = alpha * (self.angle_x + gx_dps * dt) + (1 - alpha) * accel_angle_x
        self.angle_y = alpha * (self.angle_y + gy_dps * dt) + (1 - alpha) * accel_angle_y
        
        # Set plot limits based on accelerometer and gyroscope ranges
        self.ax3.set_xlim(-accel_range, accel_range)
        self.ax3.set_ylim(-accel_range, accel_range)
        self.ax3.set_zlim(-accel_range, accel_range)
        
        # Remove tick labels
        self.ax3.set_xticklabels([])
        self.ax3.set_yticklabels([])
        self.ax3.set_zticklabels([])
        
        # Remove grid lines
        self.ax3.grid(False)
        
        # Set axis colors and labels
        self.ax3.xaxis.line.set_color('red')
        self.ax3.yaxis.line.set_color('green')
        self.ax3.zaxis.line.set_color('blue')
        self.ax3.set_xlabel('X', color='red')
        self.ax3.set_ylabel('Y', color='green')
        self.ax3.set_zlabel('Z', color='blue')
        
        self.ax3.set_title('Orientation')

        # Convert angles to radians
        angle_x_rad = np.radians(self.angle_x)
        angle_y_rad = np.radians(self.angle_y)
        
        # Calculate rotation matrix
        rot_x = np.array([[1, 0, 0],
                          [0, np.cos(angle_x_rad), -np.sin(angle_x_rad)],
                          [0, np.sin(angle_x_rad), np.cos(angle_x_rad)]])
        
        rot_y = np.array([[np.cos(angle_y_rad), 0, np.sin(angle_y_rad)],
                          [0, 1, 0],
                          [-np.sin(angle_y_rad), 0, np.cos(angle_y_rad)]])
        
        rotation_matrix = np.dot(rot_y, rot_x)

        # Create a cube to represent the orientation
        cube_size = 1
        cube_vertices = np.array([
            [-cube_size, -cube_size, -cube_size],
            [cube_size, -cube_size, -cube_size],
            [cube_size, cube_size, -cube_size],
            [-cube_size, cube_size, -cube_size],
            [-cube_size, -cube_size, cube_size],
            [cube_size, -cube_size, cube_size],
            [cube_size, cube_size, cube_size],
            [-cube_size, cube_size, cube_size]
        ])

        # Apply rotation to the cube vertices
        rotated_vertices = np.dot(rotation_matrix, cube_vertices.T).T

        # Plot the cube
        self.ax3.plot(rotated_vertices[:, 0], rotated_vertices[:, 1], rotated_vertices[:, 2], 'k-')

        # Connect the vertices to form the cube edges
        edges = [
            [0, 1], [1, 2], [2, 3], [3, 0],  # Bottom face
            [4, 5], [5, 6], [6, 7], [7, 4],  # Top face
            [0, 4], [1, 5], [2, 6], [3, 7]   # Vertical edges
        ]

        for edge in edges:
            self.ax3.plot(rotated_vertices[edge, 0], rotated_vertices[edge, 1], rotated_vertices[edge, 2], 'k-')

        # Only show the main axes
        self.ax3.xaxis.pane.fill = False
        self.ax3.yaxis.pane.fill = False
        self.ax3.zaxis.pane.fill = False

        self.ax3.xaxis.pane.set_edgecolor('none')
        self.ax3.yaxis.pane.set_edgecolor('none')
        self.ax3.zaxis.pane.set_edgecolor('none')

        # Disable mouse interaction
        self.ax3.mouse_init(rotate_btn=None, zoom_btn=None)

        # Set static view
        self.ax3.view_init(elev=30, azim=45)

        self.canvas.draw()

    def save_to_csv(self):
        filename = self.file_name.get()
        try:
            with open(filename, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Timestamp", "Temperature", "VNA Data", "Accelerometer Angle", "Digital Level Angle"])
                writer.writerows(self.data)
            self.logger.info(f"Data exported to {filename}")
        except Exception as e:
            self.logger.error(f"Export Error: Error exporting data: {e}", extra={'color': 'red'})

    def on_closing(self):
        if self.arduino:
            self.arduino.close()
        self.master.destroy()
class EnhancedAutoDataLoggerGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Enhanced Automated Data Logger")
        self.master.geometry("800x600")  # Adjusted initial size
        
        # Set dark mode color scheme
        self.master.configure(background='#1c1c1c')
        ttk.Style().configure('TFrame', background='#1c1c1c')
        ttk.Style().configure('TLabelframe', background='#1c1c1c', foreground='white')
        ttk.Style().configure('TLabelframe.Label', background='#1c1c1c', foreground='white')
        ttk.Style().configure('TLabel', background='#1c1c1c', foreground='white')
        ttk.Style().configure('TButton', background='#4c4c4c', foreground='white')
        ttk.Style().configure('TEntry', fieldbackground='#4c4c4c', foreground='white')
        ttk.Style().configure('TCombobox', fieldbackground='#4c4c4c', foreground='white')
        ttk.Style().configure('TNotebook', background='#1c1c1c')
        ttk.Style().configure('TNotebook.Tab', background='#4c4c4c', foreground='white')
        
        self.create_logger()
        self.create_widgets()
        self.data = []
        self.is_logging = False
        self.web_port_enabled = False
        self.vna_connected = False
        self.vna_data = None
        self.temp_sensor_connected = False
        self.arduino = None
        self.arduino_port = None
        self.find_and_connect_arduino()
        
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)  # Handle window close event
        self.connect_devices()
        
        self.create_logger()
        self.gyro_bias = np.zeros(3)
        self.orientation = np.array([1, 0, 0, 0])  # Initial orientation as a quaternion
    
    def create_logger(self):
        self.log_widget = ScrolledText(self.master, state='disabled', height=10, bg='#4c4c4c', fg='white')
        self.log_widget.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        
        text_handler = TextHandler(self.log_widget)
        self.logger.addHandler(text_handler)
    
    def find_and_connect_arduino(self):
        ports = self.get_usb_ports()
        for port in ports:
            if 'Arduino Due' in port:
                self.arduino_port = port.split(' ')[0]  # Extract the port name
                self.setup_arduino(self.arduino_port)
                # Update the dropdown menu
                self.arduino_port_combobox.set(port)
                break
    
    def create_widgets(self):
        # Create tabs
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Logging Controls tab
        logging_tab = ttk.Frame(self.notebook)
        self.notebook.add(logging_tab, text="Logging Controls")
        
        # Data tab
        data_tab = ttk.Frame(self.notebook)
        self.notebook.add(data_tab, text="Data")
        
        # Device Connections tab
        device_tab = ttk.Frame(self.notebook)
        self.notebook.add(device_tab, text="Device Connections")
        
        # Test tab
        test_tab = ttk.Frame(self.notebook)
        self.notebook.add(test_tab, text="Test")
        
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
        
        # Data frame
        data_frame = ttk.Frame(data_tab)
        data_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Accelerometer data display
        accel_frame = ttk.LabelFrame(data_frame, text="Accelerometer Data")
        accel_frame.pack(padx=10, pady=10)

        self.accel_display = ttk.Label(accel_frame, text="N/A")
        self.accel_display.pack()

        # Create figure and subplots
        self.fig = plt.figure(figsize=(12, 6))
        self.ax1 = self.fig.add_subplot(121)  # Temperature graph on the left
        self.ax3 = self.fig.add_subplot(122, projection='3d')  # 3D angle visualization on the right

        # Set dark mode colors for the plots
        self.fig.patch.set_facecolor('#1c1c1c')
        self.ax1.set_facecolor('#4c4c4c')
        self.ax3.set_facecolor('#4c4c4c')
        self.ax1.xaxis.label.set_color('white')
        self.ax1.yaxis.label.set_color('white')
        self.ax1.tick_params(axis='x', colors='white')
        self.ax1.tick_params(axis='y', colors='white')
        self.ax3.xaxis.label.set_color('white')
        self.ax3.yaxis.label.set_color('white')
        self.ax3.zaxis.label.set_color('white')
        self.ax3.tick_params(axis='x', colors='white')
        self.ax3.tick_params(axis='y', colors='white')
        self.ax3.tick_params(axis='z', colors='white')

        # Set up 3D plot
        self.ax3.set_xlim(-1, 1)
        self.ax3.set_ylim(-1, 1)
        self.ax3.set_zlim(-1, 1)
        self.ax3.set_xticklabels([])
        self.ax3.set_yticklabels([])
        self.ax3.set_zticklabels([])
        self.ax3.grid(False)
        self.ax3.xaxis.line.set_color('red')
        self.ax3.yaxis.line.set_color('green')
        self.ax3.zaxis.line.set_color('blue')
        self.ax3.set_xlabel('X', color='red')
        self.ax3.set_ylabel('Y', color='green')
        self.ax3.set_zlabel('Z', color='blue')
        self.ax3.xaxis.pane.fill = False
        self.ax3.yaxis.pane.fill = False
        self.ax3.zaxis.pane.fill = False
        self.ax3.xaxis.pane.set_edgecolor('none')
        self.ax3.yaxis.pane.set_edgecolor('none')
        self.ax3.zaxis.pane.set_edgecolor('none')

        # Disable mouse interaction
        self.ax3.mouse_init(rotate_btn=None, zoom_btn=None)

        # Set initial view
        self.ax3.view_init(elev=30, azim=45)

        # Create canvas for displaying the graphs
        self.canvas = FigureCanvasTkAgg(self.fig, master=data_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Device Connections frame
        device_frame = ttk.LabelFrame(device_tab, text="Device Connections")
        device_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Remove VNA Port selection
        
        ttk.Label(device_frame, text="Temperature Sensor Port:").grid(row=1, column=0, sticky="w", pady=5)
        self.temp_port = ttk.Combobox(device_frame, values=self.get_usb_ports(), state="readonly", width=15)
        self.temp_port.grid(row=1, column=1, pady=5)
        self.temp_port.bind("<<ComboboxSelected>>", self.on_temp_port_selected)
        self.temp_status_label = ttk.Label(device_frame, text="Disconnected", foreground="red")
        self.temp_status_label.grid(row=1, column=2, padx=5)
        
        ttk.Label(device_frame, text="Arduino Port:").grid(row=0, column=0, sticky="w", pady=5)
        self.arduino_port_combobox = ttk.Combobox(device_frame, values=self.get_usb_ports(), state="readonly", width=30)
        self.arduino_port_combobox.grid(row=0, column=1, pady=5)
        self.arduino_port_combobox.bind("<<ComboboxSelected>>", self.on_arduino_port_selected)
        self.arduino_status_label = ttk.Label(device_frame, text="Disconnected", foreground="red")
        self.arduino_status_label.grid(row=0, column=2, padx=5)
        
        # Export to CSV button
        ttk.Button(device_frame, text="Export to CSV", command=self.save_to_csv).grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        
        # File name entry
        ttk.Label(device_frame, text="File Name:").grid(row=4, column=0, sticky="w")
        self.file_name = ttk.Entry(device_frame, width=20)
        self.file_name.insert(0, "data.csv")
        self.file_name.grid(row=4, column=1, padx=5, pady=5)
        
        # Web Port toggle button
        self.web_button = ttk.Button(device_frame, text="Enable Web Port", command=self.toggle_web_port)
        self.web_button.grid(row=5, column=0, columnspan=2, padx=5, pady=5)
        
        # Test frame
        test_frame = ttk.LabelFrame(test_tab, text="Test Controls")
        test_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Test VNA Sweep button
        ttk.Button(test_frame, text="Test VNA Sweep", command=self.test_vna_sweep).pack(pady=5)
        
        # Get Angle button
        ttk.Button(test_frame, text="Get Angle", command=self.get_angle).pack(pady=5)
        
        # Calibrate button
        ttk.Button(test_frame, text="Calibrate", command=self.calibrate_sensor).pack(pady=5)
        
        # Bind F12 key to activate VNA sweep
        self.master.bind('<F12>', self.activate_vna_sweep)
    
    def get_usb_ports(self):
        ports = []
        for port in comports():
            if 'Arduino Due' in port.description:
                ports.append(f"{port.device} (Arduino Due)")
            elif 'FT230X Basic UART' in port.description:
                ports.append(f"{port.device} (mini VNA tiny)")
            else:
                ports.append(port.device)
        
        temper_device = usb.core.find(idVendor=0x413d, idProduct=0x2107)
        if temper_device:
            ports.append("TEMPer1F")
        
        return ports

    def toggle_web_port(self):
        if self.web_port_enabled:
            self.web_port_enabled = False
            self.logger.info("Web port disabled")
        else:
            self.web_port_enabled = True
            self.logger.info(f"Web port enabled at http://localhost:5000")
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
                self.logger.error(f"Input Error: {str(e)}", extra={'color': 'red'})

    def check_connections(self):
        if not self.temp_sensor_connected:
            self.logger.error("Temperature Sensor is not connected. Please connect Temperature Sensor before starting logging.", extra={'color': 'red'})
            return False
        return True

    def log_data(self):
        while self.is_logging:
            try:
                temp = self.read_temperature()
                self.read_vna_data()  # Read the latest VNA data
                accel_data = self.read_accelerometer()
                level_data = self.read_digital_level()

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                entry = [timestamp, temp, self.vna_data, accel_data, level_data]
                self.data.append(entry)

                self.update_display(temp, self.vna_data, accel_data, level_data)
                self.update_graphs()

                interval = int(self.freq_entry.get())
                threading.Event().wait(interval)

            except Exception as e:
                self.logger.error(f"Data Logging Error: Error reading data: {e}", extra={'color': 'red'})
                self.is_logging = False
                self.master.after(0, lambda: self.log_button.config(text="Start Logging"))
                break

    def read_vna_data(self):
        try:
            latest_file = self.get_latest_vna_file()
            if latest_file:
                with open(latest_file, 'r') as file:
                    lines = file.readlines()
                    if len(lines) >= 4:
                        self.vna_data = ''.join(lines[:4])
                        self.logger.info(f"VNA data:\n{self.vna_data}")
                    else:
                        self.logger.warning("Insufficient data in the VNA file.")
            else:
                self.logger.warning("No VNA file found.")
        except Exception as e:
            self.logger.error(f"Error reading VNA data: {e}")
            self.logger.exception("Traceback:")  # Log the traceback for debugging

    def get_latest_vna_file(self):
        try:
            files = os.listdir(VNA_EXPORTS_FOLDER)
            vna_files = [f for f in files if f.startswith("VNA_") and f.endswith(".csv")]
            if vna_files:
                latest_file = max(vna_files, key=lambda f: os.path.getctime(os.path.join(VNA_EXPORTS_FOLDER, f)))
                return os.path.join(VNA_EXPORTS_FOLDER, latest_file)
            else:
                self.logger.warning("No VNA files found in the exports folder.")
        except Exception as e:
            self.logger.error(f"Error getting the latest VNA file: {e}")
            self.logger.exception("Traceback:")  # Log the traceback for debugging
        return None

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
            self.logger.error(f"Error reading temperature: {e}")
            return None

    def read_accelerometer(self):
        if self.arduino:
            self.arduino.write(b"GET_ACCEL\n")
            self.arduino.timeout = 1  # Set a timeout of 1 second
            
            try:
                response = self.arduino.readline().decode().strip()
                if response.startswith("XYZ:"):
                    try:
                        values = response.split(":")[1].split(",")
                        if len(values) == 6:
                            ax, ay, az = map(int, values[:3])
                            gx, gy, gz = map(float, values[3:])
                            return ax, ay, az, gx, gy, gz
                        else:
                            self.logger.error("Invalid accelerometer data format")
                    except ValueError:
                        self.logger.error("Invalid accelerometer data format")
            except serial.SerialTimeoutException:
                self.logger.warning("Timeout waiting for accelerometer data")
        
        return None, None, None, None, None, None

    def read_digital_level(self):
        return None  # Placeholder, implement if needed

    def update_display(self, temp, vna_data, accel_data, level_data):
        self.temp_display.config(text=f"{temp:.2f}C")
        self.vna_display.config(text=f"{vna_data}")
        if accel_data is not None:
            x, y, z, _, _, _ = accel_data
            self.accel_display.config(text=f"X: {x}, Y: {y}, Z: {z}")
        else:
            self.accel_display.config(text="N/A")
        self.level_display.config(text=f"{level_data:.2f}°")

    def update_graphs(self):
        self.ax1.clear()

        timestamps = [entry[0] for entry in self.data[-50:]]  # Last 50 entries
        temps = [entry[1] for entry in self.data[-50:]]

        self.ax1.plot(timestamps, temps)
        self.ax1.set_ylabel('Temperature (°C)')
        self.ax1.set_title('Temperature Over Time')
        self.ax1.tick_params(axis='x', rotation=45)

        # Update 3D angle visualization
        self.update_3d_plot()

        self.fig.tight_layout()
        self.canvas.draw()

    def update_3d_plot(self):
        if not self.data or len(self.data[-1]) < 4 or self.data[-1][3] is None:
            return

        self.ax3.clear()
        
        # Convert accelerometer data to g-force
        accel_range = 4  # Accelerometer range is set to ±4g
        ax_g = self.data[-1][3][0] / 32768.0 * accel_range
        ay_g = self.data[-1][3][1] / 32768.0 * accel_range
        az_g = self.data[-1][3][2] / 32768.0 * accel_range
        
        # Convert gyroscope data to degrees per second
        gyro_range = 500  # Gyroscope range is set to ±500 degrees/second
        gx_dps = self.data[-1][3][3] / 32768.0 * gyro_range
        gy_dps = self.data[-1][3][4] / 32768.0 * gyro_range
        gz_dps = self.data[-1][3][5] / 32768.0 * gyro_range
        
        # Calculate accelerometer angles
        accel_angle_x = np.arctan2(ay_g, np.sqrt(ax_g**2 + az_g**2)) * 180 / np.pi
        accel_angle_y = np.arctan2(-ax_g, np.sqrt(ay_g**2 + az_g**2)) * 180 / np.pi
        
        # Complementary filter
        alpha = 0.98
        dt = 0.01  # Assuming 10ms interval
        
        if not hasattr(self, 'angle_x'):
            self.angle_x = accel_angle_x
            self.angle_y = accel_angle_y
        
        self.angle_x = alpha * (self.angle_x + gx_dps * dt) + (1 - alpha) * accel_angle_x
        self.angle_y = alpha * (self.angle_y + gy_dps * dt) + (1 - alpha) * accel_angle_y
        
        # Set plot limits based on accelerometer and gyroscope ranges
        self.ax3.set_xlim(-accel_range, accel_range)
        self.ax3.set_ylim(-accel_range, accel_range)
        self.ax3.set_zlim(-accel_range, accel_range)
        
        # Remove tick labels
        self.ax3.set_xticklabels([])
        self.ax3.set_yticklabels([])
        self.ax3.set_zticklabels([])
        
        # Remove grid lines
        self.ax3.grid(False)
        
        # Set axis colors and labels
        self.ax3.xaxis.line.set_color('red')
        self.ax3.yaxis.line.set_color('green')
        self.ax3.zaxis.line.set_color('blue')
        self.ax3.set_xlabel('X', color='red')
        self.ax3.set_ylabel('Y', color='green')
        self.ax3.set_zlabel('Z', color='blue')
        
        self.ax3.set_title('Orientation')

        # Convert angles to radians
        angle_x_rad = np.radians(self.angle_x)
        angle_y_rad = np.radians(self.angle_y)
        
        # Calculate rotation matrix
        rot_x = np.array([[1, 0, 0],
                          [0, np.cos(angle_x_rad), -np.sin(angle_x_rad)],
                          [0, np.sin(angle_x_rad), np.cos(angle_x_rad)]])
        
        rot_y = np.array([[np.cos(angle_y_rad), 0, np.sin(angle_y_rad)],
                          [0, 1, 0],
                          [-np.sin(angle_y_rad), 0, np.cos(angle_y_rad)]])
        
        rotation_matrix = np.dot(rot_y, rot_x)

        # Create a cube to represent the orientation
        cube_size = 1
        cube_vertices = np.array([
            [-cube_size, -cube_size, -cube_size],
            [cube_size, -cube_size, -cube_size],
            [cube_size, cube_size, -cube_size],
            [-cube_size, cube_size, -cube_size],
            [-cube_size, -cube_size, cube_size],
            [cube_size, -cube_size, cube_size],
            [cube_size, cube_size, cube_size],
            [-cube_size, cube_size, cube_size]
        ])

        # Apply rotation to the cube vertices
        rotated_vertices = np.dot(rotation_matrix, cube_vertices.T).T

        # Plot the cube
        self.ax3.plot(rotated_vertices[:, 0], rotated_vertices[:, 1], rotated_vertices[:, 2], 'k-')

        # Connect the vertices to form the cube edges
        edges = [
            [0, 1], [1, 2], [2, 3], [3, 0],  # Bottom face
            [4, 5], [5, 6], [6, 7], [7, 4],  # Top face
            [0, 4], [1, 5], [2, 6], [3, 7]   # Vertical edges
        ]

        for edge in edges:
            self.ax3.plot(rotated_vertices[edge, 0], rotated_vertices[edge, 1], rotated_vertices[edge, 2], 'k-')

        # Only show the main axes
        self.ax3.xaxis.pane.fill = False
        self.ax3.yaxis.pane.fill = False
        self.ax3.zaxis.pane.fill = False

        self.ax3.xaxis.pane.set_edgecolor('none')
        self.ax3.yaxis.pane.set_edgecolor('none')
        self.ax3.zaxis.pane.set_edgecolor('none')

        # Disable mouse interaction
        self.ax3.mouse_init(rotate_btn=None, zoom_btn=None)

        # Set static view
        self.ax3.view_init(elev=30, azim=45)

        self.canvas.draw()
    
    def save_to_csv(self):
        filename = self.file_name.get()
        try:
            with open(filename, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Timestamp", "Temperature", "VNA Data", "Accelerometer Angle", "Digital Level Angle"])
                writer.writerows(self.data)
            self.logger.info(f"Data exported to {filename}")
        except Exception as e:
            self.logger.error(f"Export Error: Error exporting data: {e}", extra={'color': 'red'})

    def on_closing(self):
        if self.arduino:
            self.arduino.close()
        self.master.destroy()

    def on_temp_port_selected(self, event):
        selected_port = self.temp_port.get()
        self.logger.info(f"Selected Temperature Sensor: {selected_port}")
        if selected_port == "TEMPer1F":
            self.setup_temp_sensor(None)  # We don't need a port for USB device
        else:
            self.logger.error("Please select the TEMPer1F device", extra={'color': 'red'})

    def check_and_request_permissions(self, port):
        if not os.access(port, os.R_OK | os.W_OK):
            try:
                group = "dialout"  # This is typically the group for serial ports
                subprocess.run(["sudo", "usermod", "-a", "-G", group, os.getlogin()], check=True)
                subprocess.run(["sudo", "chmod", "a+rw", port], check=True)
                self.logger.info(f"Permissions granted for {port}")
                # The user needs to log out and log back in for group changes to take effect
                self.logger.info("Permissions updated. Please log out and log back in for changes to take effect.", extra={'color': 'red'})
                return True
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to set permissions: {e}", extra={'color': 'red'})
                self.logger.error(f"Failed to set permissions for {port}. Try running the script with sudo.", extra={'color': 'red'})
                return False
        return True

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
            
            self.logger.info("Connected to TEMPer1F")
            self.temp_sensor_connected = True
            self.temp_status_label.config(text="Connected", foreground="green")
        except usb.core.USBError as e:
            self.logger.error(f"USB Error connecting to TEMPer1F: {e}", extra={'color': 'red'})
            self.show_permission_dialog()
            self.temp_sensor_connected = False
            self.temp_status_label.config(text="Disconnected", foreground="red")
        except Exception as e:
            self.logger.error(f"Error connecting to TEMPer1F: {e}", extra={'color': 'red'})
            self.temp_sensor_connected = False
            self.temp_status_label.config(text="Disconnected", foreground="red")

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
        
        dialog = tk.Toplevel(self.master)
        dialog.title("Grant Permissions for TEMPer1F")
        dialog.geometry("600x300")
        
        tk.Label(dialog, text="To grant permissions for the TEMPer1F device, run these commands in your terminal:").pack(pady=10)
        
        text_area = tk.Text(dialog, height=10, width=80)
        text_area.pack(pady=10)
        text_area.insert(tk.END, permission_commands.strip())
        
        def copy_to_clipboard():
            pyperclip.copy(permission_commands.strip())
            self.logger.info("Commands copied to clipboard!")
        
        copy_button = ttk.Button(dialog, text="Copy Commands", command=copy_to_clipboard)
        copy_button.pack(pady=10)
        
        tk.Label(dialog, text="After running these commands, unplug and replug the TEMPer1F device, then restart this application.").pack(pady=10)

    def setup_arduino(self, port):
        if self.check_and_request_permissions(port):
            try:
                self.arduino = serial.Serial(port, 115200)
                self.logger.info(f"Connected to Arduino on port: {port}")
                self.arduino_connected = True
                self.arduino_status_label.config(text="Connected", foreground="green")
                self.update_xyz_data()  # Start updating XYZ data
            except Exception as e:
                self.logger.error(f"Error connecting to Arduino: {e}", extra={'color': 'red'})
                self.arduino_connected = False
                self.arduino_status_label.config(text="Disconnected", foreground="red")
    
    def update_xyz_data(self):
        if self.arduino and self.arduino.in_waiting:
            data = self.arduino.readline().decode('utf-8').strip()
            if data.startswith("XYZ:"):
                try:
                    values = data.split(':')[1].split(',')
                    if len(values) == 6:
                        ax, ay, az = map(int, values[:3])
                        gx, gy, gz = map(float, values[3:])
                        self.update_3d_plot()
                    else:
                        self.logger.warning(f"Invalid accelerometer data format: {data}")
                except (IndexError, ValueError):
                    self.logger.warning(f"Invalid accelerometer data format: {data}")

        self.master.after(10, self.update_xyz_data)  # Schedule the next update
    
    def on_arduino_port_selected(self, event):
        selected_port = self.arduino_port_combobox.get()
        self.logger.info(f"Selected Arduino Port: {selected_port}")
        self.setup_arduino(selected_port.split(' ')[0])

    def connect_devices(self):
        self.status_label = ttk.Label(self.master, text="")
        self.status_label.pack(side=tk.BOTTOM, pady=10)
        
        self.update_status("Connecting to Temperature Sensor...")
        self.master.after(1000, self.connect_temp_sensor)
    
    def connect_temp_sensor(self):
        try:
            self.setup_temp_sensor(None)
            self.update_status("Temperature Sensor connected.")
        except Exception as e:
            self.update_status(f"Temperature Sensor connection failed: {str(e)}")
        
        self.master.after(5000, self.connect_arduino)
    
    def connect_arduino(self):
        self.update_status("Connecting to Arduino...")
        self.find_and_connect_arduino()
        if self.arduino_connected:
            self.update_status("Arduino connected.")
        else:
            self.update_status("Arduino connection failed.")
        
        self.master.after(5000, self.clear_status)
    
    def clear_status(self):
        self.status_label.config(text="")
    
    def update_status(self, message):
        self.status_label.config(text=message)

    def activate_vna_sweep(self, event):
        self.logger.info("Activating VNA sweep...")
        try:
            # Simulate pressing the F12 key to activate the VNA sweep
            self.master.event_generate('<F12>')
            self.logger.info("VNA sweep activated.")
        except Exception as e:
            self.logger.error(f"Error activating VNA sweep: {e}")
            self.logger.exception("Traceback:")  # Log the traceback for debugging

    def test_vna_sweep(self):
        self.logger.info("Testing VNA sweep...")
        try:
            self.activate_vna_sweep(None)
            time.sleep(2)  # Wait for the sweep to complete
            self.read_vna_data()
        except Exception as e:
            self.logger.error(f"Error during VNA sweep test: {e}", extra={'color': 'red'})
            self.logger.exception("Traceback:")  # Log the traceback for debugging

    def get_angle(self):
        accel_data = self.read_accelerometer()
        if accel_data is not None:
            ax, ay, az, gx, gy, gz = accel_data
            self.logger.info(f"Accelerometer data - X: {ax}, Y: {ay}, Z: {az}, GX: {gx}, GY: {gy}, GZ: {gz}")
            self.accel_display.config(text=f"X: {ax}, Y: {ay}, Z: {az}")
        else:
            self.logger.warning("Failed to read accelerometer data.")
            self.accel_display.config(text="N/A")

    def calibrate_sensor(self):
        self.arduino.write(b"CALIBRATE\n")
        response = self.arduino.readline().decode().strip()
        if response == "CALIBRATED":
            self.logger.info("Sensor calibrated.")
        else:
            self.logger.error("Calibration failed.")

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
        # Set the Qt platform plugin to "xcb"
        os.environ["QT_QPA_PLATFORM"] = "xcb"

        root = tk.Tk()
        app.logger_gui = EnhancedAutoDataLoggerGUI(root)

        if ENABLE_WEB_SERVER:
            threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5000}, daemon=True).start()

        root.mainloop()
    except PermissionError as e:
        app.logger_gui.logger.error(f"Permission error: {e}", extra={'color': 'red'})
        app.logger_gui.logger.error("Try running the script with sudo or grant necessary permissions to the serial ports.", extra={'color': 'red'})
    except Exception as e:
        app.logger_gui.logger.error(f"An error occurred: {e}", extra={'color': 'red'})
        