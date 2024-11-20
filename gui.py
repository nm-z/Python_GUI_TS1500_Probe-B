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
from PIL import Image, ImageTk
from datetime import timedelta
import pygame
from matplotlib.widgets import RadioButtons, TextBox
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk

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
        self.master.geometry("800x1200")
        
        # Enforce Minimum Window Size
        self.master.minsize(800, 1000)
        self.master.maxsize(1600, 1600)
        
        # Initialize variables before creating widgets
        self.data = []
        self.is_logging = False
        self.web_port_enabled = False
        self.vna_connected = False
        self.vna_data = None
        self.arduino = None
        self.arduino_port = None
        self.arduino_connected = False
        self.tilt_sensor_enabled = True
        self.temperature_history = []
        self.last_temp = None
        self.angle_x = 0.0
        self.angle_y = 0.0
        self.gyro_bias = np.zeros(3)
        self.orientation = np.array([1, 0, 0, 0])
        self.test_sequence = []
        
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
        
        # Create widgets
        self.create_logger()
        self.create_widgets()
        
        # Log "Logger active" on startup
        self.logger.info("Logger active", extra={'color': 'green'})
        
        # Initialize devices and connections
        self.find_and_connect_arduino()
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.connect_devices()
        
        # Initialize Tilt Indicator **After create_widgets**
        # Ensure self.tilt_canvas is defined in create_widgets before this line
        self.tilt_indicator = TiltIndicator(self.tilt_canvas)
        
        # Start updating the tilt indicator
        self.update_tilt_indicator()
        
        # Start temperature simulation
        self.simulate_temperature_data()
    
    def create_logger(self):
        self.log_widget = ScrolledText(self.master, state='disabled', height=10, bg='#4c4c4c', fg='white', padx=10, pady=10)
        self.log_widget.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
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
        # 1. Top Frame: Navigation and Tabs (1/4)
        top_frame = ttk.Frame(self.master, height=160)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=20, pady=10)
        top_frame.pack_propagate(False)
        
        # Create Menu Bar
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)
        
        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Data", command=self.save_to_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Troubleshooting Menu
        trouble_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Troubleshooting", menu=trouble_menu)
        trouble_menu.add_command(label="Test Connection", command=self.find_and_connect_arduino)
        trouble_menu.add_command(label="Calibrate Sensors", command=self.calibrate_sensor)
        
        # Create Notebook (Tabs)
        self.notebook = ttk.Notebook(top_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create only necessary tab frames
        self.create_testing_tab()
        self.create_settings_tab()
        
        # 2. Test Parameters/Settings Frame (formerly Real-Time Parameters)
        test_params_frame = ttk.LabelFrame(self.master, text="Test Parameters/Settings", height=200)
        test_params_frame.pack(fill=tk.X, padx=10, pady=10)
        test_params_frame.pack_propagate(False)
        
        # Create two columns in test_params_frame
        for i in range(2):
            test_params_frame.columnconfigure(i, weight=1)
        
        # Tilt Angles Section
        tilt_frame = ttk.LabelFrame(test_params_frame, text="Tilt Angles")
        tilt_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        # Use a monospace font and fixed width for consistent display
        self.tilt_angles_label = ttk.Label(
            tilt_frame,
            text="X: +0.0° Y: +0.0° Z: +0.0°",
            font=('Courier', 10),  # Use monospace font
            width=30  # Fixed width
        )
        self.tilt_angles_label.pack(pady=2, padx=2)
        
        # Configure the frame to maintain size
        tilt_frame.grid_propagate(False)
        
        # Status Display
        status_frame = ttk.LabelFrame(test_params_frame, text="Test Status")
        status_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        self.test_status_label = ttk.Label(status_frame, text="Current Phase: Idle", foreground='yellow')
        self.test_status_label.pack(pady=2, padx=2)
        
        # Hardware Feedback Section
        hardware_feedback_frame = ttk.LabelFrame(test_params_frame, text="Hardware Feedback")
        hardware_feedback_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        
        # Stepper Motor Status
        ttk.Label(hardware_feedback_frame, text="Stepper Motor Status:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.stepper_status_label = ttk.Label(hardware_feedback_frame, text="Position: 0 | Speed: 60 RPM")
        self.stepper_status_label.grid(row=0, column=1, sticky='w', padx=5, pady=2)
        
        # Motion-Tracking Device Output
        ttk.Label(hardware_feedback_frame, text="Motion-Tracker Output:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.motion_tracker_label = ttk.Label(hardware_feedback_frame, text="Pitch: 0° | Roll: 0°")
        self.motion_tracker_label.grid(row=1, column=1, sticky='w', padx=5, pady=2)
        
        # 3. Visualization Frame (3/4)
        visual_frame = ttk.LabelFrame(self.master, text="Visualization")
        visual_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Create container frame
        container_frame = ttk.Frame(visual_frame, height=1000)  # Increased height
        container_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        container_frame.pack_propagate(False)  # Prevent shrinking
        
        # Configure grid weights
        container_frame.grid_columnconfigure(0, weight=1)
        container_frame.grid_columnconfigure(1, weight=1)
        container_frame.grid_rowconfigure(0, weight=1)
        
        # Left frame for Pygame visualization - enforce square aspect ratio
        left_visual_frame = ttk.Frame(container_frame)
        left_visual_frame.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        
        # Bind configure event to maintain square aspect ratio
        def maintain_square(event):
            width = event.width
            height = event.height
            size = min(width, height)
            left_visual_frame.configure(width=size, height=size)
            # Update canvas size
            self.tilt_canvas.configure(width=size, height=size)
            if hasattr(self, 'tilt_indicator'):
                self.tilt_indicator.resize(size, size)
        
        left_visual_frame.bind('<Configure>', maintain_square)
        
        # Create the Pygame canvas
        self.tilt_canvas = tk.Canvas(
            left_visual_frame, 
            bg='#1c1c1c', 
            width=400, 
            height=400,
            highlightthickness=0,
            borderwidth=0
        )
        self.tilt_canvas.grid(row=0, column=0, sticky='nsew')
        
        # Right frame for temperature graph
        right_visual_frame = ttk.Frame(container_frame)
        right_visual_frame.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)
        
        # Temperature Graph
        self.fig_temperature, self.ax_temperature = plt.subplots(figsize=(5, 3), facecolor='#4c4c4c')
        self.ax_temperature.set_title('Temperature Over Time', color='white')
        self.ax_temperature.set_xlabel('Time', color='white')
        self.ax_temperature.set_ylabel('Temperature (°C)', color='white')
        self.ax_temperature.tick_params(colors='white')
        self.ax_temperature.grid(True, color='gray')
        
        # Adjust the layout to prevent label cutoff
        self.fig_temperature.subplots_adjust(bottom=0.2)  # Add more space at the bottom
        self.fig_temperature.tight_layout()  # Apply tight layout after adjusting
        
        self.temperature_canvas = FigureCanvasTkAgg(self.fig_temperature, master=right_visual_frame)
        self.temperature_canvas.draw()
        self.temperature_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initialize Tilt Indicator
        self.tilt_indicator = TiltIndicator(self.tilt_canvas)
        
        # Start updating the tilt indicator and temperature graph
        self.update_tilt_indicator()
        self.simulate_temperature_data()
        
        # 4. Logger Frame (4/4)
        log_frame = ttk.LabelFrame(self.master, text="Data Logging & Events")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Logger controls in a horizontal frame
        log_controls = ttk.Frame(log_frame)
        log_controls.pack(fill=tk.X, padx=5, pady=2)
        
        # Left side controls
        left_controls = ttk.Frame(log_controls)
        left_controls.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        ttk.Label(left_controls, text="Log Frequency:").pack(side=tk.TOP, anchor='w', padx=5, pady=2)
        self.freq_entry = ttk.Entry(left_controls, width=10)
        self.freq_entry.insert(0, "1")
        self.freq_entry.pack(side=tk.TOP, anchor='w', padx=5, pady=2)
        
        self.log_button = ttk.Button(left_controls, text="Start Logging", command=self.toggle_logging)
        self.log_button.pack(side=tk.TOP, anchor='w', padx=5, pady=5)
        
        # **Repositioned "Logger active" Label**
        self.logger_status_label = ttk.Label(left_controls, text="Logger active", foreground='green')
        self.logger_status_label.pack(side=tk.TOP, anchor='w', padx=5, pady=5)
        
        # Right side controls
        right_controls = ttk.Frame(log_controls)
        right_controls.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        ttk.Label(right_controls, text="File:").pack(side=tk.TOP, anchor='w', padx=5, pady=2)
        self.file_name = tk.StringVar(value="data.csv")
        file_entry = ttk.Entry(right_controls, textvariable=self.file_name, width=20)
        file_entry.pack(side=tk.TOP, anchor='w', padx=5, pady=2)
        
        ttk.Button(right_controls, text="Export Logs", command=self.save_to_csv).pack(side=tk.TOP, anchor='w', padx=5, pady=5)
        
        # Create new log widget (the old one will be removed)
        self.log_widget = ScrolledText(log_frame, height=5, bg='#4c4c4c', fg='white', state='disabled')
        self.log_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_realtime_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Real-Time Parameters")
        # Add real-time parameter controls here

    def create_testing_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Testing Controls")
        
        # Add Test Controls here
        test_controls_frame = ttk.LabelFrame(tab, text="Test Controls")
        test_controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Configure grid for balanced alignment
        for i in range(5):  # Adjusted to accommodate an additional column for the Tilt Angle Label
            test_controls_frame.columnconfigure(i, weight=1, pad=10)
        
        # Start Test Button
        start_test_button = ttk.Button(test_controls_frame, text="Start Test", command=self.start_test)
        start_test_button.grid(row=0, column=0, padx=5, pady=5, sticky='ew')
        
        # Pause Test Button
        pause_test_button = ttk.Button(test_controls_frame, text="Pause Test", command=self.pause_test)
        pause_test_button.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        # Stop Test Button
        stop_test_button = ttk.Button(test_controls_frame, text="Stop Test", command=self.stop_test)
        stop_test_button.grid(row=0, column=2, padx=5, pady=5, sticky='ew')
        
        # Angle Increment
        ttk.Label(test_controls_frame, text="Angle Increment:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.angle_increment_var = tk.IntVar(value=1)
        angle_increment_spinbox = ttk.Spinbox(
            test_controls_frame, from_=1, to=10, textvariable=self.angle_increment_var, width=5
        )
        angle_increment_spinbox.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        
        # Angle Step Size
        ttk.Label(test_controls_frame, text="Angle Step Size:").grid(row=1, column=2, sticky='e', padx=5, pady=5)
        self.angle_step_size_var = tk.IntVar(value=10)
        angle_step_size_spinbox = ttk.Spinbox(
            test_controls_frame, from_=10, to=90, increment=5, textvariable=self.angle_step_size_var, width=5
        )
        angle_step_size_spinbox.grid(row=1, column=3, sticky='w', padx=5, pady=5)
        
        # Oil Leveling Time
        ttk.Label(test_controls_frame, text="Oil Leveling Time (s):").grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.oil_leveling_time_var = tk.IntVar(value=5)
        oil_leveling_time_entry = ttk.Entry(
            test_controls_frame, textvariable=self.oil_leveling_time_var, width=5
        )
        oil_leveling_time_entry.grid(row=2, column=1, sticky='w', padx=5, pady=5)
        
        # Tilt Angle Range Slider
        ttk.Label(test_controls_frame, text="Tilt Angle Range (±°):").grid(row=2, column=2, sticky='e', padx=5, pady=5)
        self.tilt_angle_var = tk.IntVar(value=30)
        tilt_angle_slider = ttk.Scale(test_controls_frame, from_=1, to=90, orient=tk.HORIZONTAL,
                                     variable=self.tilt_angle_var, command=self.update_tilt_angle_range)
        tilt_angle_slider.grid(row=2, column=3, sticky='ew', padx=5, pady=5)
        self.tilt_angle_label = ttk.Label(test_controls_frame, text="±30°")
        self.tilt_angle_label.grid(row=2, column=4, sticky='w', padx=5, pady=5)

    def create_data_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Data Logs & Visualization")
        # Keep existing data visualization code
        self.fig = plt.figure(figsize=(8, 4))
        self.ax1 = self.fig.add_subplot(121)
        self.ax_orientation = self.fig.add_subplot(122, projection='3d')
        self.configure_plots()
        self.canvas_orientation = FigureCanvasTkAgg(self.fig, master=tab)
        self.canvas_orientation.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def create_settings_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Settings")
        
        # Create sections with horizontal layout
        settings_frame = ttk.Frame(tab)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Arduino Settings
        arduino_frame = ttk.LabelFrame(settings_frame, text="Arduino Settings")
        arduino_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Arduino Port Label
        ttk.Label(arduino_frame, text="Arduino Port:").grid(row=0, column=0, sticky='w', padx=5, pady=(5, 2))
        
        # Arduino Port Combobox: Shortened width and moved below label
        self.arduino_port_combobox = ttk.Combobox(
            arduino_frame, values=self.get_usb_ports(),
            state="readonly", width=15  # Shortened from 25 to 15
        )
        self.arduino_port_combobox.grid(row=1, column=0, sticky='w', padx=5, pady=(0, 5))  # Moved to row=1
        
        # Temperature Settings
        temp_frame = ttk.LabelFrame(settings_frame, text="Temperature Monitor Settings")
        temp_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # Units frame
        units_frame = ttk.LabelFrame(temp_frame, text="Temperature Units")
        units_frame.pack(fill=tk.X, pady=5)
        
        self.temp_unit = tk.StringVar(value='C')
        for unit, symbol in [('C', '°C'), ('F', '°F'), ('K', 'K')]:
            ttk.Radiobutton(units_frame, text=symbol, variable=self.temp_unit,
                           value=unit, command=self.update_temp_display).pack(side=tk.LEFT, padx=10)
        
        # Time range frame
        time_frame = ttk.LabelFrame(temp_frame, text="Graph Time Range")
        time_frame.pack(fill=tk.X, pady=5)
        
        self.timeframe = tk.StringVar(value='1m')
        for time_val, time_text in [('1m', '1 Min'), ('5m', '5 Min'), ('1h', '1 Hour')]:
            ttk.Radiobutton(time_frame, text=time_text, variable=self.timeframe,
                           value=time_val, command=self.update_temp_graph).pack(side=tk.LEFT, padx=10)
        
        # Hardware Configurations
        hardware_frame = ttk.LabelFrame(settings_frame, text="Hardware Configurations")
        hardware_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        
        ttk.Label(hardware_frame, text="NNTP Server:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.nntp_server_entry = ttk.Entry(hardware_frame, width=30)
        self.nntp_server_entry.grid(row=0, column=1, sticky='w', padx=5, pady=5)
        self.nntp_server_entry.insert(0, "nntp.example.com")  # Default value
        
        ttk.Label(hardware_frame, text="Log Frequency (seconds):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.log_freq_entry = ttk.Entry(hardware_frame, width=10)
        self.log_freq_entry.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        self.log_freq_entry.insert(0, "1")  # Default value
        
        ttk.Label(hardware_frame, text="Stepper Motor Speed (RPM):").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.stepper_speed_entry = ttk.Entry(hardware_frame, width=10)
        self.stepper_speed_entry.grid(row=2, column=1, sticky='w', padx=5, pady=5)
        self.stepper_speed_entry.insert(0, "60")  # Default value
        
        # Save Settings Button
        save_settings_button = ttk.Button(hardware_frame, text="Save Settings", command=self.save_hardware_settings)
        save_settings_button.grid(row=3, column=1, sticky='e', padx=5, pady=10)

    # Add these new methods for test control
    def start_test(self):
        if not self.is_logging:
            self.is_logging = True
            self.update_test_status("Running")
            self.log_button.config(text="Stop Logging")
            self.logger.info("Test started", extra={'color': 'green'})
            threading.Thread(target=self.log_data, daemon=True).start()

    def pause_test(self):
        if self.is_logging:
            self.is_logging = False
            self.update_test_status("Paused")
            self.log_button.config(text="Start Logging")
            self.logger.info("Test paused", extra={'color': 'green'})

    def stop_test(self):
        if self.is_logging:
            self.is_logging = False
            self.update_test_status("Idle")
            self.log_button.config(text="Start Logging")
            self.logger.info("Test stopped", extra={'color': 'green'})

    def configure_plots(self):
        # Configure plot styles for dark mode
        self.fig.patch.set_facecolor('#1c1c1c')
        for ax in [self.ax1, self.ax_orientation]:
            ax.set_facecolor('#4c4c4c')
            if hasattr(ax, 'xaxis'):
                ax.xaxis.label.set_color('white')
                ax.tick_params(axis='x', colors='white')
            if hasattr(ax, 'yaxis'):
                ax.yaxis.label.set_color('white')
                ax.tick_params(axis='y', colors='white')

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
                            # Update the display with new values
                            self.update_tilt_angles(ax, ay, az)
                            return (ax, ay, az, gx, gy, gz)
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
        # Update Fill Level
        if level_data is not None:
            fill_level = level_data
            self.fill_level_label.config(text=f"Fill Level: {fill_level}")
            self.logger.info(f"Fill Level: {fill_level}", extra={'color': 'green'})
        else:
            self.fill_level_label.config(text="Fill Level: N/A")
        
        # Update Tilt Angles
        if accel_data is not None:
            ax, ay, az, gx, gy, gz = accel_data
            self.tilt_angles_label.config(text=f"X: {ax}° | Y: {ay}° | Z: {az}°")
            self.logger.info(f"Tilt Angles: X={ax}°, Y={ay}°, Z={az}°", extra={'color': 'green'})
        else:
            self.tilt_angles_label.config(text="X: N/A° | Y: N/A° | Z: N/A°")

    def update_graphs(self):
        self.ax1.clear()

        timestamps = [entry[0] for entry in self.data[-50:]]  # Last 50 entries
        temps = [entry[1] for entry in self.data[-50:]]

        self.ax1.plot(timestamps, temps, color='white')
        self.ax1.set_ylabel('Temperature (°C)')
        self.ax1.set_title('Temperature Over Time', color='white')
        self.ax1.tick_params(axis='x', rotation=45, colors='white')
        self.ax1.tick_params(axis='y', colors='white')
        self.ax1.grid(True, color='gray')

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
        if hasattr(self, 'tilt_indicator'):
            self.tilt_indicator.cleanup()
        self.is_logging = False
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
                    self.arduino.close()
                self.arduino = serial.Serial(port, 115200)
                self.logger.info(f"Connected to Arduino on port: {port}", extra={'color': 'green'})
                self.arduino_connected = True
                self.update_device_status('arduino', True)
                self.update_xyz_data()
            except Exception as e:
                self.logger.error(f"Error connecting to Arduino: {e}", extra={'color': 'red'})
                self.arduino_connected = False
                self.update_device_status('arduino', False)

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
                self.update_device_status('arduino', False)

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

    def update_device_status(self, device, connected):
        status_map = {
            'arduino': self.arduino_status_label,
            'tilt': self.tilt_status_label,
            'vna': self.vna_status_label
        }
        
        if device in status_map:
            label = status_map[device]
            status = "Connected" if connected else "Disconnected"
            color = "green" if connected else "red"
            label.config(text=f"{device.title()}: {status}", foreground=color)

    def update_readings(self):
        # Update tilt reading
        if hasattr(self, 'angle_x') and hasattr(self, 'angle_y'):
            self.tilt_reading_label.config(
                text=f"Tilt: X={self.angle_x:.1f}°, Y={self.angle_y:.1f}°"
            )
        
        # Update temperature reading (if you have temperature data)
        if self.data and len(self.data[-1]) > 1:
            temp = self.data[-1][1]
            self.temp_reading_label.config(text=f"Temperature: {temp}°C")

    def update_temp_display(self):
        if not hasattr(self, 'last_temp') or self.last_temp is None:
            return
        
        temp_c = self.last_temp
        unit = self.temp_unit.get()
        
        if unit == 'F':
            temp = (temp_c * 9/5) + 32
            suffix = '°F'
        elif unit == 'K':
            temp = temp_c + 273.15
            suffix = 'K'
        else:  # Celsius
            temp = temp_c
            suffix = '°C'
        
        # Update temperature display in the Test Parameters/Settings frame
        if hasattr(self, 'tilt_angles_label'):
            # Assuming you want to display temperature alongside tilt angles
            # If you have a separate label for temperature, adjust accordingly
            self.tilt_angles_label.config(text=f"X: {self.tilt_angles_label.cget('text').split('|')[0][3:]} | Y: {self.tilt_angles_label.cget('text').split('|')[1][3:]} | Z: {self.tilt_angles_label.cget('text').split('|')[2][3:]} | Temperature: {temp:.1f}{suffix}")
        
        # Update the temperature graph
        self.update_graphs()

    def update_temp_graph(self):
        self.ax1.clear()
        
        # Get timeframe
        timeframe = self.timeframe.get()
        
        # Calculate delta based on timeframe
        if timeframe == '1m':
            delta = timedelta(minutes=1)
        elif timeframe == '5m':
            delta = timedelta(minutes=5)
        elif timeframe == '1h':
            delta = timedelta(hours=1)
        elif timeframe == 'custom':
            try:
                value = float(self.custom_time.get())
                if self.custom_time_unit.get() == 'Hours':
                    delta = timedelta(hours=value)
                else:  # Minutes
                    delta = timedelta(minutes=value)
            except (ValueError, AttributeError):
                self.logger.error("Invalid custom time value", extra={'color': 'red'})
                return
        else:
            delta = timedelta(hours=1)  # Default fallback
        
        # Rest of your existing update_temp_graph code...
        now = datetime.now()
        start_time = now - delta
        
        filtered_data = [(t, temp) for t, temp in self.temperature_history 
                        if t >= start_time]
        
        if filtered_data:
            times, temps = zip(*filtered_data)
            
            # Convert temperatures if needed
            unit = self.temp_unit.get()
            if unit == 'F':
                temps = [(t * 9/5) + 32 for t in temps]
            elif unit == 'K':
                temps = [t + 273.15 for t in temps]
            
            self.ax1.plot(times, temps, 'w-')
            self.ax1.set_facecolor('#4c4c4c')
            self.ax1.grid(True, color='gray')
            
            # Update title to show custom time if applicable
            if timeframe == 'custom':
                title = f'Temperature History (Custom: {self.custom_time.get()} {self.custom_time_unit.get()})'
            else:
                title = f'Temperature History ({timeframe})'
            
            self.ax1.set_title(title, color='white')
        
        self.ax1.tick_params(axis='x', rotation=45)
        self.ax1.set_ylabel('Temperature (°C)')
        self.ax1.set_title('Temperature Over Time')
        self.ax1.grid(True)
        self.ax1.tight_layout()
        self.ax1.draw()

    def update_temperature(self, temp_c):
        try:
            self.last_temp = temp_c
            self.temperature_history.append((datetime.now(), temp_c))
            self.update_temp_display()
        except Exception as e:
            print(f"Error updating temperature: {e}")

    def apply_custom_timeframe(self):
        try:
            value = float(self.custom_time.get())
            if value <= 0:
                raise ValueError("Time must be positive")
            
            self.timeframe.set('custom')
            self.update_temp_graph()
            
        except ValueError as e:
            self.logger.error(f"Invalid custom time value: {str(e)}", extra={'color': 'red'})

    def update_tilt_indicator(self):
        try:
            if hasattr(self, 'angle_x') and hasattr(self, 'angle_y'):
                self.tilt_indicator.update(self.angle_y, self.angle_x)
        except Exception as e:
            self.logger.error(f"Error in update_tilt_indicator: {e}", extra={'color': 'red'})
        finally:
            # Continue updating
            self.master.after(33, self.update_tilt_indicator)

    def on_temp_unit_change(self, label):
        unit_map = {'°C': 'C', '°F': 'F', 'K': 'K'}
        self.temp_unit.set(unit_map[label])
        self.update_temp_display()
        
    def on_timeframe_change(self, label):
        time_map = {'1 Min': '1m', '5 Min': '5m', '1 Hour': '1h'}
        self.timeframe.set(time_map[label])
        self.update_temp_graph()
        
    def on_custom_time_submit(self, text):
        try:
            value = float(text)
            if value <= 0:
                raise ValueError("Time must be positive")
            self.timeframe.set('custom')
            self.custom_time.set(str(value))
            self.update_temp_graph()
        except ValueError as e:
            self.logger.error(f"Invalid custom time value: {str(e)}", extra={'color': 'red'})

    def simulate_temperature_data(self):
        try:
            # Simulate temperature data for testing (always positive, smaller range)
            current_time = datetime.now()
            # Base temperature of 21°C with ±0.5°C variation converted to always positive
            temp = 21.0 + 0.5 * math.sin(current_time.timestamp() / 60)  # Increased frequency for smoother wave
            self.update_temperature(temp)
        except Exception as e:
            print(f"Error in temperature simulation: {e}")
        finally:
            self.master.after(1000, self.simulate_temperature_data)

    def save_hardware_settings(self):
        nntp_server = self.nntp_server_entry.get()
        try:
            log_freq = float(self.log_freq_entry.get())
            stepper_speed = float(self.stepper_speed_entry.get())
        except ValueError:
            self.logger.error("Invalid input for log frequency or stepper motor speed.", extra={'color': 'red'})
            return
        
        # Here you would typically save these settings to a config file or apply them directly
        self.logger.info(f"NNTP Server set to: {nntp_server}", extra={'color': 'green'})
        self.logger.info(f"Log Frequency set to: {log_freq} seconds", extra={'color': 'green'})
        self.logger.info(f"Stepper Motor Speed set to: {stepper_speed} RPM", extra={'color': 'green'})
        
        # Optionally, update internal variables or reconfigure components as needed

    def update_test_status(self, status):
        self.test_status_label.config(text=f"Current Phase: {status}")
        self.logger.info(f"Test Status: {status}", extra={'color': 'green'})

    def create_test_controls(self):
        test_controls_frame = ttk.LabelFrame(self.master, text="Test Controls")
        test_controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Start Test Button
        start_button = ttk.Button(test_controls_frame, text="Start Test", command=self.start_test)
        start_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Pause Test Button
        pause_button = ttk.Button(test_controls_frame, text="Pause Test", command=self.pause_test)
        pause_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Stop Test Button
        stop_button = ttk.Button(test_controls_frame, text="Stop Test", command=self.stop_test)
        stop_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Tilt Angle Range Slider
        ttk.Label(test_controls_frame, text="Tilt Angle Range (± degrees):").pack(side=tk.LEFT, padx=5)
        self.tilt_angle_range = tk.IntVar(value=30)
        tilt_slider = ttk.Scale(test_controls_frame, from_=1, to=90, orient=tk.HORIZONTAL,
                                    variable=self.tilt_angle_range)
        tilt_slider.pack(side=tk.LEFT, padx=5)
        self.tilt_angle_label = ttk.Label(test_controls_frame, text="±30°")
        self.tilt_angle_label.pack(side=tk.LEFT, padx=5)
        self.tilt_angle_range.trace('w', self.update_tilt_angle_label)
        
        # Fill Increment Steps Slider
        ttk.Label(test_controls_frame, text="Fill Increment Steps:").pack(side=tk.LEFT, padx=5)
        self.fill_increment_steps = tk.IntVar(value=10)
        fill_slider = ttk.Scale(test_controls_frame, from_=1, to=100, orient=tk.HORIZONTAL,
                                    variable=self.fill_increment_steps)
        fill_slider.pack(side=tk.LEFT, padx=5)
        self.fill_increment_label = ttk.Label(test_controls_frame, text="10")
        self.fill_increment_label.pack(side=tk.LEFT, padx=5)
        self.fill_increment_steps.trace('w', self.update_fill_increment_label)
    
    def update_tilt_angle_label(self, *args):
        self.tilt_angle_label.config(text=f"±{self.tilt_angle_range.get()}°")
    
    def update_fill_increment_label(self, *args):
        self.fill_increment_label.config(text=str(self.fill_increment_steps.get()))
    
    def update_tilt_angle_range(self, event):
        angle = self.tilt_angle_var.get()
        self.tilt_angle_label.config(text=f"±{angle}°")
        self.logger.info(f"Tilt Angle Range set to ±{angle}°", extra={'color': 'green'})
    
    def update_fill_increment_steps(self, event):
        steps = self.fill_increment_var.get()
        self.fill_increment_label.config(text=str(int(steps)))
        self.logger.info(f"Fill Increment Steps set to {int(steps)}", extra={'color': 'green'})
    
    def start_test(self):
        if not self.is_logging:
            self.is_logging = True
            self.update_test_status("Running")
            self.log_button.config(text="Stop Logging")
            self.logger.info("Test started", extra={'color': 'green'})
            # Apply tilt angle range and fill increment steps as needed
            tilt_range = self.tilt_angle_var.get()
            fill_steps = self.fill_increment_var.get()
            self.logger.info(f"Tilt Angle Range: ±{tilt_range}°", extra={'color': 'green'})
            self.logger.info(f"Fill Increment Steps: {fill_steps}", extra={'color': 'green'})
            threading.Thread(target=self.log_data, daemon=True).start()
    
    def pause_test(self):
        if self.is_logging:
            self.is_logging = False
            self.update_test_status("Paused")
            self.log_button.config(text="Start Logging")
            self.logger.info("Test paused", extra={'color': 'green'})
    
    def stop_test(self):
        if self.is_logging:
            self.is_logging = False
            self.update_test_status("Idle")
            self.log_button.config(text="Start Logging")
            self.logger.info("Test stopped", extra={'color': 'green'})

    def update_tilt_angles(self, x, y, z):
        """Update tilt angles display with compact format"""
        # Format numbers to always show sign and limit decimal places
        x_text = f"{x:+.1f}°"
        y_text = f"{y:+.1f}°"
        z_text = f"{z:+.1f}°"
        
        # Use shorter labels and fixed-width formatting
        text = f"X:{x_text:>7} Y:{y_text:>7} Z:{z_text:>7}"
        self.tilt_angles_label.config(text=text)


class TiltIndicator:
    def __init__(self, canvas):
        self.canvas = canvas
        self.width = 400
        self.height = 400
        self.setup_pygame()
        
    def setup_pygame(self):
        self.canvas.update()
        os.environ['SDL_WINDOWID'] = str(self.canvas.winfo_id())
        
        if not pygame.get_init():
            pygame.init()
        pygame.display.init()
        
        # Set up the display with exact size match
        self.surface = pygame.display.set_mode(
            (self.width, self.height),
            pygame.NOFRAME | pygame.SCALED | pygame.HWSURFACE | pygame.DOUBLEBUF
        )
        
        pygame.event.set_blocked(None)
        self.canvas.update()
        
    def update(self, pitch, roll):
        try:
            # Just call the original draw_attitude_indicator without modifications
            from tilt_indicator import draw_attitude_indicator
            draw_attitude_indicator(pitch, roll, self.surface)
            pygame.display.flip()
        except Exception as e:
            print(f"Error updating tilt indicator: {e}")
    
    def cleanup(self):
        try:
            pygame.quit()
        except Exception:
            pass

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
        
        
        