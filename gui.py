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
        self.find_and_connect_arduino()
        
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)  # Handle window close event
        self.connect_devices()
        
        self.gyro_bias = np.zeros(3)
        self.orientation = np.array([1, 0, 0, 0])  # Initial orientation as a quaternion
        self.test_sequence = []
        self.create_test_loop_widgets()
    
    def create_logger(self):
        self.log_widget = ScrolledText(self.master, state='disabled', height=10, bg='#4c4c4c', fg='white')
        self.log_widget.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        
        text_handler = TextHandler(self.log_widget)
        self.logger.addHandler(text_handler)
        
        self.log_widget.tag_configure('green', foreground='#00FF00')  # Configure high-contrast green text tag
    
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
        self.data_tab = ttk.Frame(self.notebook)  # Changed from data_tab to self.data_tab
        self.notebook.add(self.data_tab, text="Data")
        
        # Device Connections tab
        device_tab = ttk.Frame(self.notebook)
        self.notebook.add(device_tab, text="Device Connections")
        
        # Test tab
        self.test_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.test_tab, text="Test")
        
        # Logging Controls frame
        logging_frame = ttk.LabelFrame(logging_tab, text="Logging Controls")
        logging_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Frequency input
        ttk.Label(logging_frame, text="Measurement Frequency (seconds):").grid(row=0, column=0, sticky="w")
        self.freq_entry = ttk.Entry(logging_frame, width=10)
        self.freq_entry.insert(0, "60")  # Default to 1 minute
        self.freq_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Start/Stop button
        self.log_button = ttk.Button(logging_frame, text="Start Logging", command=self.toggle_logging)
        self.log_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        # Move File name entry to Logging Controls
        ttk.Label(logging_frame, text="File Name:").grid(row=2, column=0, sticky="w")
        self.file_name = ttk.Entry(logging_frame, width=20)
        self.file_name.insert(0, "data.csv")
        self.file_name.grid(row=2, column=1, padx=5, pady=5)
        
        # Device Connections frame
        device_frame = ttk.LabelFrame(device_tab, text="Device Connections")
        device_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Arduino Port selection
        ttk.Label(device_frame, text="Arduino Port:").grid(row=0, column=0, sticky="w", pady=5)
        self.arduino_port_combobox = ttk.Combobox(device_frame, values=self.get_usb_ports(), state="readonly", width=30)
        self.arduino_port_combobox.grid(row=0, column=1, pady=5)
        self.arduino_port_combobox.bind("<<ComboboxSelected>>", self.on_arduino_port_selected)
        self.arduino_status_label = ttk.Label(device_frame, text="Disconnected", foreground="red")
        self.arduino_status_label.grid(row=0, column=2, padx=5)
        
        # Web Port toggle button
        self.web_button = ttk.Button(device_frame, text="Enable Web Port", command=self.toggle_web_port)
        self.web_button.grid(row=5, column=0, columnspan=2, padx=5, pady=5)
        
        # Test frame
        test_frame = ttk.LabelFrame(self.test_tab, text="Test Controls")
        test_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Test VNA Sweep button
        ttk.Button(test_frame, text="Test VNA Sweep", command=self.test_vna_sweep).pack(pady=5)
        
        # Get Angle button
        ttk.Button(test_frame, text="Get Angle", command=self.get_angle).pack(pady=5)
        
        # Calibrate button
        ttk.Button(test_frame, text="Calibrate", command=self.calibrate_sensor).pack(pady=5)
        
        # Bind F12 key to activate VNA sweep
        self.master.bind('<F12>', self.activate_vna_sweep)
    
    def create_test_loop_widgets(self):
        # Test Loop frame
        test_loop_frame = ttk.LabelFrame(self.test_tab, text="Test Loop")
        test_loop_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Angle Range inputs
        ttk.Label(test_loop_frame, text="Angle Range (start, end, step):").grid(row=0, column=0, sticky="w")
        self.angle_start_entry = ttk.Entry(test_loop_frame, width=5)
        self.angle_start_entry.grid(row=0, column=1, padx=5, pady=5)
        self.angle_end_entry = ttk.Entry(test_loop_frame, width=5)
        self.angle_end_entry.grid(row=0, column=2, padx=5, pady=5)
        self.angle_step_entry = ttk.Entry(test_loop_frame, width=5)
        self.angle_step_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # Repetitions input
        ttk.Label(test_loop_frame, text="Repetitions:").grid(row=1, column=0, sticky="w")
        self.repetitions_entry = ttk.Entry(test_loop_frame, width=5)
        self.repetitions_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Generate Sequence button
        ttk.Button(test_loop_frame, text="Generate Sequence", command=self.generate_test_sequence).grid(row=2, column=0, columnspan=4, padx=5, pady=5)
        
        # Test Sequence table
        self.test_sequence_table = ttk.Treeview(test_loop_frame, columns=("Angle",), show="headings")
        self.test_sequence_table.heading("Angle", text="Angle")
        self.test_sequence_table.grid(row=3, column=0, columnspan=4, padx=5, pady=5)
        
        # Add/Remove/Clear buttons
        ttk.Button(test_loop_frame, text="Add Entry", command=self.add_test_entry).grid(row=4, column=0, padx=5, pady=5)
        ttk.Button(test_loop_frame, text="Remove Entry", command=self.remove_test_entry).grid(row=4, column=1, padx=5, pady=5)
        ttk.Button(test_loop_frame, text="Clear Sequence", command=self.clear_test_sequence).grid(row=4, column=2, padx=5, pady=5)
        
        # Save/Load Sequence buttons
        ttk.Button(test_loop_frame, text="Save Sequence", command=self.save_test_sequence).grid(row=5, column=0, padx=5, pady=5)
        ttk.Button(test_loop_frame, text="Load Sequence", command=self.load_test_sequence).grid(row=5, column=1, padx=5, pady=5)
        
        # Start Test button
        ttk.Button(test_loop_frame, text="Start Test", command=self.start_test_loop).grid(row=6, column=0, columnspan=4, padx=5, pady=5)
        
        # Add Mock X Angle Visual
        # Create a frame for the angle visual
        ttk.Label(test_loop_frame, text="X Angle Visualization:").grid(row=7, column=0, columnspan=4, pady=5)
        self.angle_canvas = tk.Canvas(test_loop_frame, width=200, height=200, bg='#1c1c1c')
        self.angle_canvas.grid(row=8, column=0, columnspan=4, pady=10)
        
        # Draw the 360-degree circle
        self.angle_canvas.create_oval(50, 50, 150, 150, outline='white', width=2)
        # Draw the initial angle indicator
        self.angle_indicator = self.angle_canvas.create_line(100, 100, 100, 50, fill='red', width=2)
        
        # Split the Data tab into two frames side by side
        self.data_frame = ttk.Frame(self.data_tab)
        self.data_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Create left_frame and right_frame with unequal sizing (left smaller, right larger)
        self.left_frame = ttk.Frame(self.data_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5), width=300)

        self.right_frame = ttk.Frame(self.data_frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # Add Interval Frame at the top of left_frame
        self.interval_frame = ttk.Frame(self.left_frame)
        self.interval_frame.pack(pady=(0, 10), fill=tk.X)

        self.interval_var = tk.IntVar(value=60)  # Initialize interval_var

        # Create a style for the radio buttons
        style = ttk.Style()
        style.configure("TRadiobutton", background='#1c1c1c', foreground='white')

        # Pack radio buttons horizontally
        ttk.Radiobutton(self.interval_frame, text="1 Min", variable=self.interval_var, value=60, 
                        command=self.set_interval, style="TRadiobutton").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(self.interval_frame, text="5 Min", variable=self.interval_var, value=300, 
                        command=self.set_interval, style="TRadiobutton").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(self.interval_frame, text="30 Min", variable=self.interval_var, value=1800, 
                        command=self.set_interval, style="TRadiobutton").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(self.interval_frame, text="4 Hours", variable=self.interval_var, value=14400, 
                        command=self.set_interval, style="TRadiobutton").pack(side=tk.LEFT, padx=5)

        # Move Temperature Graph to left_frame
        self.fig_temp = plt.Figure(figsize=(4, 6), dpi=100)  # Increased height
        self.ax_temp = self.fig_temp.add_subplot(111)
        self.ax_temp.set_title("Temperature Over Time")
        self.ax_temp.set_ylabel("Temperature (°C)")
        self.ax_temp.yaxis.set_label_position("right")
        self.ax_temp.yaxis.tick_right()
        self.canvas_temp = FigureCanvasTkAgg(self.fig_temp, master=self.left_frame)
        self.canvas_temp.draw()
        self.canvas_temp.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Move Orientation Graph to right_frame
        self.fig_orientation = plt.Figure(figsize=(6, 6), dpi=100)  # Increased size
        self.ax_orientation = self.fig_orientation.add_subplot(111, projection='3d')
        self.ax_orientation.set_title("Orientation")
        self.canvas_orientation = FigureCanvasTkAgg(self.fig_orientation, master=self.right_frame)
        self.canvas_orientation.draw()
        self.canvas_orientation.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Add a Visible 3D Red Arrow in the Orientation Graph
        self.red_arrow = None  # Reference to the red arrow
        self.tilt_readings = []  # Store last 10 tilt readings

        # Update the angle canvas
        self.angle_canvas.itemconfig(self.angle_indicator, fill='white')  # Change indicator color to white
        self.angle_canvas.itemconfig(self.angle_canvas.find_withtag("oval"), outline='white')  # Change circle color to white

    def set_interval(self):
        seconds = self.interval_var.get()
        self.freq_entry.delete(0, tk.END)
        self.freq_entry.insert(0, str(seconds))
        self.logger.info(f"Measurement frequency set to {seconds} seconds")

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
        
        # Update Temperature graph
        self.update_temperature_graph()

    def update_temperature_graph(self):
        self.ax_temp.clear()
        timestamps = [entry[0] for entry in self.data[-50:]]  # Last 50 entries
        temps = [entry[1] for entry in self.data[-50:]]
        self.ax_temp.plot(timestamps, temps, color='orange')
        self.ax_temp.set_ylabel('Temperature (°C)')
        self.ax_temp.set_xlabel('Timestamp')
        self.ax_temp.tick_params(axis='x', rotation=45)
        self.fig_temp.tight_layout()
        self.canvas_temp.draw()

    def update_graphs(self):
        self.ax_orientation.clear()

        timestamps = [entry[0] for entry in self.data[-50:]]  # Last 50 entries
        temps = [entry[1] for entry in self.data[-50:]]

        self.ax_orientation.plot(timestamps, temps)
        self.ax_orientation.set_ylabel('Temperature (°C)')
        self.ax_orientation.set_title('Temperature Over Time')
        self.ax_orientation.tick_params(axis='x', rotation=45)

        # Update 3D angle visualization
        self.update_3d_plot()

        self.fig_orientation.tight_layout()
        self.canvas_orientation.draw()

    def update_3d_plot(self):
        if not self.data or len(self.data[-1]) < 4 or self.data[-1][3] is None:
            return

        self.ax_orientation.clear()
        
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
        
        # Store tilt readings
        self.tilt_readings.append((self.angle_x, self.angle_y))
        if len(self.tilt_readings) > 10:
            self.tilt_readings.pop(0)
        
        # Calculate average tilt
        avg_tilt_x = np.mean([tilt[0] for tilt in self.tilt_readings])
        avg_tilt_y = np.mean([tilt[1] for tilt in self.tilt_readings])
        
        # Create rotation matrix based on average tilt
        rot_x = np.array([[1, 0, 0],
                          [0, np.cos(np.radians(avg_tilt_x)), -np.sin(np.radians(avg_tilt_x))],
                          [0, np.sin(np.radians(avg_tilt_x)), np.cos(np.radians(avg_tilt_x))]])
        
        rot_y = np.array([[np.cos(np.radians(avg_tilt_y)), 0, np.sin(np.radians(avg_tilt_y))],
                          [0, 1, 0],
                          [-np.sin(np.radians(avg_tilt_y)), 0, np.cos(np.radians(avg_tilt_y))]])
        
        rotation_matrix = np.dot(rot_y, rot_x)
        
        # Draw red arrow representing orientation
        if self.red_arrow:
            self.red_arrow.remove()  # Remove previous arrow
        
        self.red_arrow = self.ax_orientation.quiver(0, 0, 0, 
                                               rotation_matrix[0, 2], 
                                               rotation_matrix[1, 2], 
                                               rotation_matrix[2, 2], 
                                               color='red', linewidth=2)
        
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

        # Apply rotation to the cube vertices
        rotated_vertices = np.dot(rotation_matrix, cube_vertices.T).T

        # Plot the cube
        self.ax_orientation.plot(rotated_vertices[:, 0], rotated_vertices[:, 1], rotated_vertices[:, 2], 'k-')

        # Connect the vertices to form the cube edges
        edges = [
            [0, 1], [1, 2], [2, 3], [3, 0],  # Bottom face
            [4, 5], [5, 6], [6, 7], [7, 4],  # Top face
            [0, 4], [1, 5], [2, 6], [3, 7]   # Vertical edges
        ]

        for edge in edges:
            self.ax_orientation.plot(rotated_vertices[edge, 0], rotated_vertices[edge, 1], rotated_vertices[edge, 2], 'k-')

        # Only show the main axes
        self.ax_orientation.xaxis.pane.fill = False
        self.ax_orientation.yaxis.pane.fill = False
        self.ax_orientation.zaxis.pane.fill = False

        self.ax_orientation.xaxis.pane.set_edgecolor('none')
        self.ax_orientation.yaxis.pane.set_edgecolor('none')
        self.ax_orientation.zaxis.pane.set_edgecolor('none')

        # Disable mouse interaction
        self.ax_orientation.mouse_init(rotate_btn=None, zoom_btn=None)

        # Set static view
        self.ax_orientation.view_init(elev=30, azim=45)

        self.canvas_orientation.draw()

    def on_closing(self):
        self.is_logging = False  # Stop logging if active
        self.master.destroy()
        self.master.quit()
        app.do_teardown_appcontext()
        exit()

    def on_arduino_port_selected(self, event):
        selected_port = self.arduino_port_combobox.get()
        self.logger.info(f"Selected Arduino Port: {selected_port}")
        self.setup_arduino(selected_port)

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
        self.find_and_connect_arduino()
        
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)  # Handle window close event
        self.connect_devices()
        
        self.gyro_bias = np.zeros(3)
        self.orientation = np.array([1, 0, 0, 0])  # Initial orientation as a quaternion
        self.test_sequence = []
        self.create_test_loop_widgets()
    
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
        
        # Store tilt readings
        self.tilt_readings.append((self.angle_x, self.angle_y))
        if len(self.tilt_readings) > 10:
            self.tilt_readings.pop(0)
        
        # Calculate average tilt
        avg_tilt_x = np.mean([tilt[0] for tilt in self.tilt_readings])
        avg_tilt_y = np.mean([tilt[1] for tilt in self.tilt_readings])
        
        # Create rotation matrix based on average tilt
        rot_x = np.array([[1, 0, 0],
                          [0, np.cos(np.radians(avg_tilt_x)), -np.sin(np.radians(avg_tilt_x))],
                          [0, np.sin(np.radians(avg_tilt_x)), np.cos(np.radians(avg_tilt_x))]])
        
        rot_y = np.array([[np.cos(np.radians(avg_tilt_y)), 0, np.sin(np.radians(avg_tilt_y))],
                          [0, 1, 0],
                          [-np.sin(np.radians(avg_tilt_y)), 0, np.cos(np.radians(avg_tilt_y))]])
        
        rotation_matrix = np.dot(rot_y, rot_x)
        
        # Draw red arrow representing orientation
        if self.red_arrow:
            self.red_arrow.remove()  # Remove previous arrow
        
        self.red_arrow = self.ax3.quiver(0, 0, 0, 
                                               rotation_matrix[0, 2], 
                                               rotation_matrix[1, 2], 
                                               rotation_matrix[2, 2], 
                                               color='red', linewidth=2)
        
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
        self.arduino.write(b"CALIBRATE\n")
        response = self.arduino.readline().decode().strip()
        if response == "CALIBRATED":
            self.logger.info("Sensor calibrated.")
        else:
            self.logger.error("Calibration failed.")

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
        
        