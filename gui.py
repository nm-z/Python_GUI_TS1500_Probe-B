"""
Arduino Serial Commands:

- GET_TILT:
  - Description: Retrieves current tilt values for the X, Y, and Z axes.
  - Expected Response:
    Tilt X: <value>
    Tilt Y: <value>
    Tilt Z: <value>

- CALIBRATE:
  - Description: Calibrates the sensors.
  - Expected Response: CALIBRATED

**Note:** Ensure correct serial port configuration for proper communication with the Arduino.
"""

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
        ttk.Style().configure('TRadiobutton', background='#1c1c1c', foreground='white')
        
        self.create_logger()
        self.create_widgets()
        self.data = []
        self.is_logging = False
        self.web_port_enabled = False
        self.vna_connected = False
        self.vna_data = None
        self.arduino = None
        self.arduino_port = None
        self.arduino_connected = False  # Initialize arduino_connected
        self.tilt_sensor_enabled = True  # Initialize tilt sensor status
        self.find_and_connect_arduino()
        
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)  # Handle window close event
        self.connect_devices()
        
        self.gyro_bias = np.zeros(3)
        self.orientation = np.array([1, 0, 0, 0])  # Initial orientation as a quaternion
        self.test_sequence = []
        self.create_test_loop_widgets()
        
        # Initialize the 3D plot with the red arrow
        self.update_3d_plot()
        
        # Initialize angle variables
        self.angle_x = 0.0
        self.angle_y = 0.0
    
    def create_logger(self):
        self.log_widget = ScrolledText(self.master, state='disabled', height=10, bg='#4c4c4c', fg='white')
        self.log_widget.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        
        text_handler = TextHandler(self.log_widget)
        self.logger.addHandler(text_handler)
        
        # Configure high-contrast green text tag
        self.log_widget.tag_configure('green', foreground='#00FF00')
    
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
        
        # Add Tilt Sensor toggle button
        self.tilt_sensor_button = ttk.Button(logging_frame, text="Disable Tilt Sensor", command=self.toggle_tilt_sensor)
        self.tilt_sensor_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5)
        
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
        self.ax_orientation = self.fig.add_subplot(122, projection='3d')  # 3D angle visualization on the right

        # Set dark mode colors for the plots
        self.fig.patch.set_facecolor('#1c1c1c')
        self.ax1.set_facecolor('#4c4c4c')
        self.ax_orientation.set_facecolor('#4c4c4c')
        self.ax1.xaxis.label.set_color('white')
        self.ax1.yaxis.label.set_color('white')
        self.ax1.tick_params(axis='x', colors='white')
        self.ax1.tick_params(axis='y', colors='white')
        
        # Set up 3D plot
        self.ax_orientation.set_xlim(-1, 1)
        self.ax_orientation.set_ylim(-1, 1)
        self.ax_orientation.set_zlim(-1, 1)
        self.ax_orientation.set_xticklabels([])
        self.ax_orientation.set_yticklabels([])
        self.ax_orientation.set_zticklabels([])
        self.ax_orientation.grid(False)
        self.ax_orientation.xaxis.line.set_color('red')
        self.ax_orientation.yaxis.line.set_color('green')
        self.ax_orientation.zaxis.line.set_color('blue')
        self.ax_orientation.set_xlabel('X', color='red')
        self.ax_orientation.set_ylabel('Y', color='green')
        self.ax_orientation.set_zlabel('Z', color='blue')
        self.ax_orientation.xaxis.pane.fill = False
        self.ax_orientation.yaxis.pane.fill = False
        self.ax_orientation.zaxis.pane.fill = False
        self.ax_orientation.xaxis.pane.set_edgecolor('none')
        self.ax_orientation.yaxis.pane.set_edgecolor('none')
        self.ax_orientation.zaxis.pane.set_edgecolor('none')

        # Disable mouse interaction
        self.ax_orientation.mouse_init(rotate_btn=None, zoom_btn=None)

        # Set initial view
        self.ax_orientation.view_init(elev=30, azim=45)

        # Create canvas for displaying the graphs
        self.canvas_orientation = FigureCanvasTkAgg(self.fig, master=data_frame)
        self.canvas_orientation.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Device Connections frame
        device_frame = ttk.LabelFrame(device_tab, text="Device Connections")
        device_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Remove VNA Port selection
        
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
        if not self.arduino_connected:
            self.logger.error("Arduino is not connected. Please connect Arduino before starting logging.", extra={'color': 'red'})
            return False
        return True

    def log_data(self):
        while self.is_logging:
            try:
                self.read_vna_data()  # Read the latest VNA data
                accel_data = self.read_accelerometer()
                level_data = self.read_digital_level()

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                entry = [timestamp, self.vna_data, accel_data, level_data]
                self.data.append(entry)

                self.update_display(self.vna_data, accel_data, level_data)
                self.update_graphs()  # Refresh graphs, including the 3D plot

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

    def read_accelerometer(self):
        if self.arduino:
            self.arduino.timeout = 1  # Set a timeout of 1 second
            
            try:
                # Read lines until XYZ is found or timeout
                start_time = time.time()
                while time.time() - start_time < self.arduino.timeout:
                    response = self.arduino.readline().decode().strip()
                    if response.startswith("XYZ:"):  # Handle only XYZ data
                        try:
                            ax, ay, az, gx, gy, gz = map(float, response.split(":")[1].split(","))
                            self.logger.info(f"Accel: X={ax}, Y={ay}, Z={az} | Gyro: X={gx}, Y={gy}, Z={gz}")
                            return (ax, ay, az, gx, gy, gz)  # Return the latest reading
                        except (IndexError, ValueError):
                            self.logger.error("Invalid XYZ data format")
                self.logger.error("Failed to read XYZ data.")
            except serial.SerialTimeoutException:
                self.logger.warning("Timeout waiting for XYZ data")
    
        return None

    def get_angle(self):
        accel_data = self.read_accelerometer()
        if accel_data is not None:
            ax, ay, az, gx, gy, gz = accel_data
            self.accel_display.config(text=f"Accel: X={ax}, Y={ay}, Z={az} | Gyro: X={gx}, Y={gy}, Z={gz}")
            self.update_graphs()  # Refresh 3D plot
        else:
            self.accel_display.config(text="Accel: N/A | Gyro: N/A")

    def read_digital_level(self):
        return None  # Placeholder, implement if needed

    def update_display(self, vna_data, accel_data, level_data):
        if accel_data is not None:
            ax, ay, az, gx, gy, gz = accel_data
            self.accel_display.config(text=f"Accel: X={ax}, Y={ay}, Z={az} | Gyro: X={gx}, Y={gy}, Z={gz}")
        else:
            self.accel_display.config(text="Accel: N/A | Gyro: N/A")

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
        self.canvas_orientation.draw()

    def update_3d_plot(self):
        if not self.data or len(self.data[-1]) < 4 or self.data[-1][3] is None:
            self.logger.warning("Insufficient data for 3D plot.")
            return

        accel_data = self.data[-1][3]
        ax, ay, az, gx, gy, gz = accel_data

        # Calculate accelerometer angles
        accel_angle_x = np.degrees(np.arctan2(ay, np.sqrt(ax**2 + az**2)))
        accel_angle_y = np.degrees(np.arctan2(-ax, np.sqrt(ay**2 + az**2)))

        # Complementary filter
        alpha = 0.98
        dt = 0.01  # 10ms interval
        self.angle_x = alpha * (self.angle_x + gx * dt) + (1 - alpha) * accel_angle_x
        self.angle_y = alpha * (self.angle_y + gy * dt) + (1 - alpha) * accel_angle_y

        # Store and average tilt readings
        self.tilt_readings.append((self.angle_x, self.angle_y))
        if len(self.tilt_readings) > 10:
            self.tilt_readings.pop(0)

        avg_tilt_x = np.mean([tilt[0] for tilt in self.tilt_readings])
        avg_tilt_y = np.mean([tilt[1] for tilt in self.tilt_readings])

        # Use scipy Rotation for rotation matrices
        rot_x = R.from_euler('x', avg_tilt_x, degrees=True).as_matrix()
        rot_y = R.from_euler('y', avg_tilt_y, degrees=True).as_matrix()
        rotation_matrix = rot_y @ rot_x

        # Draw red arrow representing orientation
        if self.red_arrow:
            self.red_arrow.remove()

        self.red_arrow = self.ax_orientation.quiver(
            0, 0, 0,
            rotation_matrix[0, 2],
            rotation_matrix[1, 2],
            rotation_matrix[2, 2],
            color='red',
            linewidth=2
        )

        # Plot the cube
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

        rotated_vertices = np.dot(rotation_matrix, cube_vertices.T).T

        self.ax_orientation.plot(rotated_vertices[:, 0], rotated_vertices[:, 1], rotated_vertices[:, 2], 'k-')

        edges = [
            [0, 1], [1, 2], [2, 3], [3, 0],  # Bottom face
            [4, 5], [5, 6], [6, 7], [7, 4],  # Top face
            [0, 4], [1, 5], [2, 6], [3, 7]   # Vertical edges
        ]

        for edge in edges:
            self.ax_orientation.plot(rotated_vertices[edge, 0],
                                     rotated_vertices[edge, 1],
                                     rotated_vertices[edge, 2], 'k-')

        # Configure the 3D plot aesthetics
        self.ax_orientation.set_title("Orientation")
        self.ax_orientation.set_xlim([-2, 2])
        self.ax_orientation.set_ylim([-2, 2])
        self.ax_orientation.set_zlim([-2, 2])
        self.ax_orientation.view_init(elev=30, azim=45)
        self.ax_orientation.axis('off')  # Hide axes for clarity

        self.logger.info(f"Drawing red arrow with rotation matrix: {rotation_matrix}")
        self.canvas_orientation.draw()

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
        if self.arduino:
            self.arduino.close()
        self.master.destroy()
        self.master.quit()
        app.do_teardown_appcontext()
        exit()

    def on_arduino_port_selected(self, event):
        selected_port = self.arduino_port_combobox.get()
        self.logger.info(f"Selected Arduino Port: {selected_port}")
        self.setup_arduino(selected_port.split(' ')[0])

    def connect_devices(self):
        self.status_label = ttk.Label(self.master, text="")
        self.status_label.pack(side=tk.BOTTOM, pady=10)
        
        self.update_status("Connecting to Arduino...")
        self.master.after(1000, self.connect_arduino)
    
    def connect_arduino(self):
        if not self.arduino_connected:
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

    def calibrate_sensor(self):
        def calibration_process():
            self.arduino.reset_input_buffer()  # Clear serial buffer before sending command
            self.arduino.write(b"CALIBRATE\n")
            
            for remaining in range(15, 0, -1):  # Countdown from 15 to 1
                self.logger.info(f"CALIBRATING ({remaining} seconds remaining)")
                
                # Check for "CALIBRATED" during the countdown
                if self.arduino.in_waiting:
                    line = self.arduino.readline().decode().strip()
                    if line == "CALIBRATED":
                        self.logger.info("Sensor calibrated.", extra={'color': 'green'})
                        return  # Exit the calibration process early
                
                time.sleep(1)
            
            # After countdown, perform a final check for "CALIBRATED"
            start_time = time.time()
            timeout = 5  # Additional 5 seconds to wait for response
            response = None
            while time.time() - start_time < timeout:
                if self.arduino.in_waiting:
                    line = self.arduino.readline().decode().strip()
                    if line == "CALIBRATED":
                        response = "CALIBRATED"
                        break
                time.sleep(0.5)  # Small delay to prevent busy waiting
            
            if response == "CALIBRATED":
                self.logger.info("Sensor calibrated.", extra={'color': 'green'})
            else:
                self.logger.error("Calibration failed.")

        threading.Thread(target=calibration_process, daemon=True).start()

    def setup_arduino(self, port):
        if self.check_and_request_permissions(port):
            try:
                if self.arduino:
                    self.arduino.close()  # Close the previous connection if it exists
                self.arduino = serial.Serial(port, 115200)
                self.logger.info(f"Connected to Arduino on port: {port}", extra={'color': 'green'})
                self.arduino_connected = True
                self.arduino_status_label.config(text="Connected", foreground="green")
                self.update_xyz_data()  # Start updating XYZ data
            except Exception as e:
                self.logger.error(f"Error connecting to Arduino: {e}", extra={'color': 'red'})
                self.arduino_connected = False
                self.arduino_status_label.config(text="Disconnected", foreground="red")

    def update_xyz_data(self):
        if self.arduino and self.arduino.is_open:
            try:
                data = self.arduino.readline().decode('utf-8', errors='ignore').strip()
                if data.startswith("XYZ:"):
                    try:
                        values = data.split(':')[1].split(',')
                        if len(values) == 6:
                            ax, ay, az = map(int, values[:3])
                            gx, gy, gz = map(float, values[3:])
                            self.update_3d_plot()  # Ensure this method exists and updates correctly
                    except (IndexError, ValueError):
                        self.logger.warning(f"Invalid accelerometer data format: {data}")
            except serial.SerialException:
                self.logger.error("Arduino disconnected.", extra={'color': 'red'})
                self.arduino_connected = False
                self.arduino_status_label.config(text="Disconnected", foreground="red")

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

    def create_test_loop_widgets(self):
        # Implementation of create_test_loop_widgets
        # Ensure this method is properly defined to avoid AttributeError
        # Example placeholder implementation:
        pass  # Replace with actual widget creation code

    def toggle_tilt_sensor(self):
        if self.tilt_sensor_enabled:
            self.tilt_sensor_enabled = False
            self.tilt_sensor_button.config(text="Enable Tilt Sensor")
            self.logger.info("Tilt Sensor disabled.")
        else:
            self.tilt_sensor_enabled = True
            self.tilt_sensor_button.config(text="Disable Tilt Sensor")
            self.logger.info("Tilt Sensor enabled.")

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
        if hasattr(app, 'logger_gui') and app.logger_gui.logger:
            app.logger_gui.logger.error(f"Permission error: {e}", extra={'color': 'red'})
            app.logger_gui.logger.error("Try running the script with sudo or grant necessary permissions to the serial ports.", extra={'color': 'red'})
        else:
            print(f"Permission error: {e}")
            print("Try running the script with sudo or grant necessary permissions to the serial ports.")
    except Exception as e:
        if hasattr(app, 'logger_gui') and app.logger_gui.logger:
            app.logger_gui.logger.error(f"An error occurred: {e}", extra={'color': 'red'})
        else:
            print(f"An error occurred: {e}")
        
        