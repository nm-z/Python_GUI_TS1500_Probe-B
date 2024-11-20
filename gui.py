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
import tkinter.messagebox
from tilt_indicator import TiltIndicator

# Configuration
ENABLE_WEB_SERVER = False
DEBUG_FRAMES = False

app = Flask(__name__)

VNA_EXPORTS_FOLDER = "/home/nate/Desktop/Python_GUI_TS1500_Probe-B/VNA_Exports"

class DebugHighlightConfig:
    def __init__(self, parent):
        self.parent = parent
        self.dialog = tk.Toplevel(parent.master)
        self.dialog.title("Debug Highlight Configuration")
        self.dialog.geometry("400x600")
        self.dialog.configure(bg='#1c1c1c')
        
        # Initialize the result dictionary
        self.dialog.result = {}
        
        # Create main frame
        main_frame = ttk.Frame(self.dialog)
        main_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        
        # Configure grid weights
        self.dialog.grid_columnconfigure(0, weight=1)
        self.dialog.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Add toggle buttons
        toggle_frame = ttk.Frame(main_frame)
        toggle_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        
        # Configure toggle frame grid
        toggle_frame.grid_columnconfigure((0, 1), weight=1)
        
        ttk.Button(toggle_frame, text="Enable All", command=self.select_all).grid(row=0, column=0, padx=5)
        ttk.Button(toggle_frame, text="Disable All", command=self.deselect_all).grid(row=0, column=1, padx=5)
        
        # Create checkboxes with hierarchical structure
        self.checkboxes = {}
        
        # Main sections
        main_sections = [
            "Navigation Bar",
            "Test Parameters/Settings",
            "Visualization",
            "Data Logging & Events"
        ]
        
        # Navigation Bar subsections
        nav_subsections = [
            "Test Controls Section",
            "Arduino Settings Section",
            "Temperature Settings Section",
            "Hardware Config Section"
        ]
        
        # Create main sections using grid
        current_row = 1
        for name in main_sections:
            var = tk.BooleanVar(value=False)
            self.checkboxes[name] = var
            self.dialog.result[name] = False
            
            frame = ttk.Frame(main_frame)
            frame.grid(row=current_row, column=0, sticky='w', pady=2)
            
            cb = ttk.Checkbutton(
                frame,
                text=name,
                variable=var,
                command=lambda n=name, v=var: self.on_checkbox_change(n, v)
            )
            cb.grid(row=0, column=0, sticky='w')
            
            # Add subsections for Navigation Bar
            if name == "Navigation Bar":
                subframe = ttk.Frame(main_frame)
                subframe.grid(row=current_row + 1, column=0, sticky='w', padx=20)
                
                for sub_name in nav_subsections:
                    sub_var = tk.BooleanVar(value=False)
                    self.checkboxes[sub_name] = sub_var
                    self.dialog.result[sub_name] = False
                    
                    ttk.Checkbutton(
                        subframe,
                        text=sub_name,
                        variable=sub_var,
                        command=lambda n=sub_name, v=sub_var: self.on_checkbox_change(n, v)
                    ).grid(row=nav_subsections.index(sub_name), column=0, sticky='w', pady=2)
                
                current_row += len(nav_subsections)
            
            current_row += 1
        
        # Add Apply and Cancel buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=current_row + 1, column=0, sticky='ew', pady=(10, 0))
        
        button_frame.grid_columnconfigure((0, 1), weight=1)
        
        ttk.Button(button_frame, text="Apply", command=self.apply).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).grid(row=0, column=1, padx=5)
    
    def on_checkbox_change(self, name, var):
        """Handle individual checkbox changes with immediate update"""
        try:
            # Update result dictionary
            self.dialog.result[name] = var.get()
            
            # Debug print
            print(f"Checkbox changed: {name} = {var.get()}")
            
            # Immediately apply the change
            if hasattr(self.parent, 'apply_debug_highlights'):
                self.parent.apply_debug_highlights(self.dialog.result)
                
        except Exception as e:
            print(f"Error handling checkbox change for {name}: {e}")
    
    def select_all(self):
        """Enable all checkboxes with immediate update"""
        for var in self.checkboxes.values():
            var.set(True)
        # Apply changes immediately
        if hasattr(self.parent, 'apply_debug_highlights'):
            self.dialog.result = {widget: True for widget in self.checkboxes.keys()}
            self.parent.apply_debug_highlights(self.dialog.result)
    
    def deselect_all(self):
        """Disable all checkboxes with immediate update"""
        for var in self.checkboxes.values():
            var.set(False)
        # Apply changes immediately
        if hasattr(self.parent, 'apply_debug_highlights'):
            self.dialog.result = {widget: False for widget in self.checkboxes.keys()}
            self.parent.apply_debug_highlights(self.dialog.result)
    
    def apply(self):
        """Apply current checkbox states"""
        try:
            result = {
                widget: var.get() 
                for widget, var in self.checkboxes.items()
            }
            self.dialog.result = result
            
            if hasattr(self.parent, 'apply_debug_highlights'):
                self.parent.apply_debug_highlights(result)
        except Exception as e:
            print(f"Error applying debug configuration: {e}")
    
    def cancel(self):
        """Cancel the debug configuration dialog"""
        try:
            # Clear any existing highlights
            if hasattr(self.parent, 'clear_debug_highlights'):
                self.parent.clear_debug_highlights()
            
            # Close the dialog
            self.dialog.destroy()
            
        except Exception as e:
            print(f"Error canceling debug config: {e}")

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
        print("DEBUG: Starting GUI initialization")
        try:
            self.master = master
            self.tk = master.tk
            self.master.title("Enhanced Automated Data Logger")
            
            # Set a reasonable minimum size instead of fixed dimensions
            self.master.minsize(800, 600)
            
            # Configure main window grid weights
            self.master.grid_columnconfigure(0, weight=1)
            self.master.grid_rowconfigure(0, weight=1)  # For main_container
            self.master.grid_rowconfigure(1, weight=0)  # For log_widget
            self.master.grid_rowconfigure(2, weight=0)  # For status_label
            
            # Create main container frame with proper grid configuration
            self.main_container = ttk.Frame(self.master)
            self.main_container.grid(row=0, column=0, sticky='nsew')
            self.main_container.grid_columnconfigure(0, weight=1)
            self.main_container.grid_rowconfigure(1, weight=1)  # Row 1 will expand
            
            # Initialize variables
            self.initialize_variables()
            
            # Create widgets
            self.create_logger()
            self.create_widgets()
            
            # Initialize devices and connections
            self.initialize_devices()
            
        except Exception as e:
            print(f"DEBUG ERROR in __init__: {str(e)}")
            raise
    
    def initialize_variables(self):
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
        self.timeframe = tk.StringVar(value='1m')
        self.temp_unit = tk.StringVar(value='C')
        
        # Set dark mode color scheme
        self.master.configure(background='#1c1c1c')
        style = ttk.Style()
        style.configure('TFrame', background='#1c1c1c')
        style.configure('TLabelframe', background='#1c1c1c', foreground='white')
        style.configure('TLabelframe.Label', background='#1c1c1c', foreground='white')
        style.configure('TLabel', background='#1c1c1c', foreground='white')
        style.configure('TButton', background='#4c4c4c', foreground='white')
        style.configure('TEntry', fieldbackground='#4c4c4c', foreground='white')
        style.configure('TCombobox', fieldbackground='#4c4c4c', foreground='white')
        style.configure('TNotebook', background='#1c1c1c')
        style.configure('TNotebook.Tab', background='#4c4c4c', foreground='white')
        style.configure('TRadiobutton', background='#1c1c1c', foreground='white')
    
    def create_logger(self):
        self.log_widget = ScrolledText(
            self.main_container,
            state='disabled',
            height=10,
            bg='#4c4c4c',
            fg='white',
            padx=10,
            pady=10
        )
        self.log_widget.grid(
            row=2,
            column=0,
            sticky='ew',
            padx=10,
            pady=10
        )
        
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        
        text_handler = TextHandler(self.log_widget)
        self.logger.addHandler(text_handler)
        
        # Configure high-contrast green text tag
        self.log_widget.tag_configure('green', foreground='#00FF00')
    
    def initialize_devices(self):
        print("DEBUG: Starting initialize_devices")
        try:
            # Initialize devices and connections
            self.find_and_connect_arduino()
            self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.connect_devices()
            
            # Initialize Tilt Indicator
            if hasattr(self, 'tilt_canvas'):
                print("DEBUG: Initializing tilt indicator")
                self.tilt_indicator = TiltIndicator(self.tilt_canvas)
                
                # Start updating the tilt indicator
                self.update_tilt_indicator()
                
                # Start temperature simulation
                self.simulate_temperature_data()
            else:
                print("DEBUG: Warning - tilt_canvas not found")
                
        except Exception as e:
            print(f"DEBUG ERROR in initialize_devices: {str(e)}")
            raise
    
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
        print("DEBUG: Starting create_widgets")
        try:
            # Top Frame: Navigation and Tabs
            print("DEBUG: Creating top frame")
            top_frame = ttk.Frame(self.main_container)
            top_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
            top_frame.grid_columnconfigure(0, weight=1)
            
            # Create Menu Bar
            print("DEBUG: Creating menu bar")
            self.create_menu_bar()
            
            # Create Notebook (Tabs)
            print("DEBUG: Creating notebook")
            self.notebook = ttk.Notebook(top_frame)
            self.notebook.grid(row=0, column=0, sticky='ew')
            
            # Create tabs
            print("DEBUG: Creating tabs")
            self.create_testing_tab()
            self.create_settings_tab()
            self.create_data_tab()
            
            # Middle Frame
            print("DEBUG: Creating middle frame")
            middle_frame = ttk.Frame(self.main_container)
            middle_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
            middle_frame.grid_columnconfigure(0, weight=1)
            middle_frame.grid_rowconfigure(1, weight=1)
            
            # Test Parameters Frame
            print("DEBUG: Creating parameters frame")
            params_frame = self.create_test_parameters_frame(middle_frame)
            params_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
            
            # Visualization Frame
            print("DEBUG: Creating visualization frame")
            visual_frame = self.create_visualization_frame(middle_frame)
            visual_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
            
            # Bottom Frame: Logging
            print("DEBUG: Creating log widget")
            self.log_widget.grid(row=2, column=0, sticky='ew', padx=5, pady=5)
            
            # Create test controls
            self.create_test_controls()
            
        except Exception as e:
            print(f"DEBUG ERROR in create_widgets: {str(e)}")
            raise
    
    def create_realtime_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Real-Time Parameters")
        # Add real-time parameter controls here

    def create_testing_tab(self):
        print("DEBUG: Starting create_testing_tab")
        try:
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text="Testing Controls")
            
            # Configure grid weights
            tab.grid_columnconfigure(0, weight=1)
            
            # Test Controls Frame
            test_controls_frame = ttk.LabelFrame(tab, text="Test Controls")
            test_controls_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
            
            # Configure test controls frame grid
            test_controls_frame.grid_columnconfigure(1, weight=1)  # Make column 1 expandable
            
            # Start Test Button
            ttk.Button(test_controls_frame, text="Start Test", command=self.start_test).grid(
                row=0, column=0, padx=5, pady=5)
            
            # Pause Test Button
            ttk.Button(test_controls_frame, text="Pause Test", command=self.pause_test).grid(
                row=0, column=1, padx=5, pady=5)
            
            # Stop Test Button
            ttk.Button(test_controls_frame, text="Stop Test", command=self.stop_test).grid(
                row=0, column=2, padx=5, pady=5)
            
            # Add the log button
            self.log_button = ttk.Button(test_controls_frame, text="Start Logging", command=self.toggle_logging)
            self.log_button.grid(row=0, column=3, padx=5, pady=5)
            
            # Tilt Angle Range
            ttk.Label(test_controls_frame, text="Tilt Angle Range (±°):").grid(
                row=1, column=0, sticky='e', padx=5, pady=5)
            
            self.tilt_angle_var = tk.IntVar(value=30)
            tilt_slider = ttk.Scale(test_controls_frame, from_=1, to=90, orient=tk.HORIZONTAL,
                                   variable=self.tilt_angle_var, command=self.update_tilt_angle_range)
            tilt_slider.grid(row=1, column=1, sticky='ew', padx=5, pady=5)
            
            self.tilt_angle_label = ttk.Label(test_controls_frame, text="±30°")
            self.tilt_angle_label.grid(row=1, column=2, sticky='w', padx=5, pady=5)

        except Exception as e:
            print(f"DEBUG ERROR in create_testing_tab: {str(e)}")
            raise

    def create_data_tab(self):
        print("DEBUG: Starting create_data_tab")
        try:
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text="Data Logs & Visualization")
            
            # Configure grid weights for the tab
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            
            # Create the figure and canvas using grid instead of pack
            self.fig = plt.figure(figsize=(8, 4))
            self.ax1 = self.fig.add_subplot(121)
            self.ax_orientation = self.fig.add_subplot(122, projection='3d')
            self.configure_plots()
            
            self.canvas_orientation = FigureCanvasTkAgg(self.fig, master=tab)
            self.canvas_orientation.get_tk_widget().grid(row=0, column=0, sticky='nsew', padx=5, pady=5)  # Changed from pack to grid

        except Exception as e:
            print(f"DEBUG ERROR in create_data_tab: {str(e)}")
            raise

    def create_settings_tab(self):
        print("DEBUG: Starting create_settings_tab")
        try:
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text="Settings")
            
            # Create main settings frame first
            settings_frame = ttk.Frame(tab)
            settings_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
            
            # Configure grid weights
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            settings_frame.grid_columnconfigure((0, 1, 2), weight=1)
            
            # Store frame references as class attributes
            self.arduino_settings_frame = ttk.LabelFrame(settings_frame, text="Arduino Settings")
            self.arduino_settings_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
            
            self.temp_settings_frame = ttk.LabelFrame(settings_frame, text="Temperature Monitor Settings")
            self.temp_settings_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
            
            self.hardware_config_frame = ttk.LabelFrame(settings_frame, text="Hardware Configurations")
            self.hardware_config_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
            
            # Arduino Settings
            # Arduino Port Label
            ttk.Label(self.arduino_settings_frame, text="Arduino Port:").grid(row=0, column=0, sticky='w', padx=5, pady=(5, 2))
            
            # Arduino Port Combobox
            self.arduino_port_combobox = ttk.Combobox(
                self.arduino_settings_frame, values=self.get_usb_ports(),
                state="readonly", width=15
            )
            self.arduino_port_combobox.grid(row=1, column=0, sticky='w', padx=5, pady=(0, 5))
            
            # Temperature Settings
            # Units frame
            units_frame = ttk.LabelFrame(self.temp_settings_frame, text="Temperature Units")
            units_frame.grid(row=0, column=0, sticky='ew', pady=5)
            
            # Configure units frame columns
            units_frame.grid_columnconfigure((0, 1, 2), weight=1)
            
            # Radio buttons
            self.temp_unit = tk.StringVar(value='C')
            for i, (unit, symbol) in enumerate([('C', '°C'), ('F', '°F'), ('K', 'K')]):
                ttk.Radiobutton(units_frame, text=symbol, variable=self.temp_unit,
                               value=unit, command=self.update_temp_display).grid(
                                   row=0, column=i, padx=10)
            
            # Time range frame
            time_frame = ttk.LabelFrame(self.temp_settings_frame, text="Graph Time Range")
            time_frame.grid(row=1, column=0, sticky='ew', pady=5)
            
            # Configure time frame columns
            time_frame.grid_columnconfigure((0, 1, 2), weight=1)
            
            # Time range radio buttons
            self.timeframe = tk.StringVar(value='1m')
            for i, (time_val, time_text) in enumerate([('1m', '1 Min'), ('5m', '5 Min'), ('1h', '1 Hour')]):
                ttk.Radiobutton(time_frame, text=time_text, variable=self.timeframe,
                               value=time_val, command=self.update_temp_graph).grid(
                                   row=0, column=i, padx=10)
            
            # Hardware Configurations
            ttk.Label(self.hardware_config_frame, text="NNTP Server:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
            self.nntp_server_entry = ttk.Entry(self.hardware_config_frame, width=30)
            self.nntp_server_entry.grid(row=0, column=1, sticky='w', padx=5, pady=5)
            self.nntp_server_entry.insert(0, "nntp.example.com")
            
            ttk.Label(self.hardware_config_frame, text="Log Frequency (seconds):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
            self.log_freq_entry = ttk.Entry(self.hardware_config_frame, width=10)
            self.log_freq_entry.grid(row=1, column=1, sticky='w', padx=5, pady=5)
            self.log_freq_entry.insert(0, "1")
            
            ttk.Label(self.hardware_config_frame, text="Stepper Motor Speed (RPM):").grid(row=2, column=0, sticky='w', padx=5, pady=5)
            self.stepper_speed_entry = ttk.Entry(self.hardware_config_frame, width=10)
            self.stepper_speed_entry.grid(row=2, column=1, sticky='w', padx=5, pady=5)
            self.stepper_speed_entry.insert(0, "60")
            
            # Save Settings Button
            save_settings_button = ttk.Button(self.hardware_config_frame, text="Save Settings", command=self.save_hardware_settings)
            save_settings_button.grid(row=3, column=1, sticky='e', padx=5, pady=10)

        except Exception as e:
            print(f"DEBUG ERROR in create_settings_tab: {str(e)}")
            raise

    # Add these new methods for test control
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
        """Handle window closing"""
        try:
            # Clean up Pygame resources
            self.cleanup_pygame_resources()
            
            # Stop logging
            self.is_logging = False
            
            # Close Arduino connection
            if hasattr(self, 'arduino') and self.arduino:
                self.arduino.close()
            
            # Clean up Flask
            app.do_teardown_appcontext()
            
            # Destroy the window
            self.master.destroy()
            self.master.quit()
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            exit()

    def on_arduino_port_selected(self, event):
        selected_port = self.arduino_port_combobox.get()
        self.logger.info(f"Selected Arduino Port: {selected_port}")
        self.setup_arduino(selected_port.split(' ')[0])

    def connect_devices(self):
        # Create status label using grid instead of pack
        self.status_label = ttk.Label(self.master, text="")
        self.status_label.grid(row=3, column=0, sticky='ew', pady=10)  # Row 3 since main_container and log_widget use rows 0-2
        
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
        """Update temperature with proper error handling"""
        try:
            if not hasattr(self, 'temperature_history'):
                self.temperature_history = []
            
            self.last_temp = temp_c
            current_time = datetime.now()
            
            # Add new temperature reading
            self.temperature_history.append((current_time, temp_c))
            
            # Keep only last 100 readings
            if len(self.temperature_history) > 100:
                self.temperature_history = self.temperature_history[-100:]
            
            # Update display only if we have data and the window exists
            if self.temperature_history and hasattr(self, 'master') and self.master.winfo_exists():
                self.update_temp_display()
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error updating temperature: {e}", extra={'color': 'red'})
            else:
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
        """Simulate temperature data with proper error handling"""
        try:
            if not hasattr(self, 'master') or not self.master.winfo_exists():
                return
            
            current_time = datetime.now()
            temp = 21.0 + 0.5 * math.sin(current_time.timestamp() / 60)
            
            if not hasattr(self, 'temperature_history'):
                self.temperature_history = []
            
            # Add new temperature reading
            self.temperature_history.append((current_time, temp))
            
            # Keep only last 100 readings
            if len(self.temperature_history) > 100:
                self.temperature_history = self.temperature_history[-100:]
            
            self.update_temperature(temp)
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error in temperature simulation: {e}", extra={'color': 'red'})
            else:
                print(f"Error in temperature simulation: {e}")
        finally:
            # Schedule next update only if window exists
            if hasattr(self, 'master') and self.master.winfo_exists():
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
        # Store frame reference as class attribute
        self.test_controls_frame = ttk.LabelFrame(self.master, text="Test Controls")
        self.test_controls_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        
        # Start Test Button
        start_button = ttk.Button(self.test_controls_frame, text="Start Test", command=self.start_test)
        start_button.grid(row=0, column=0, padx=5, pady=5)
        
        # Pause Test Button
        pause_button = ttk.Button(self.test_controls_frame, text="Pause Test", command=self.pause_test)
        pause_button.grid(row=0, column=1, padx=5, pady=5)
        
        # Stop Test Button
        stop_button = ttk.Button(self.test_controls_frame, text="Stop Test", command=self.stop_test)
        stop_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Add the log button
        self.log_button = ttk.Button(self.test_controls_frame, text="Start Logging", command=self.toggle_logging)
        self.log_button.grid(row=0, column=3, padx=5, pady=5)
        
        # Tilt Angle Range Slider
        ttk.Label(self.test_controls_frame, text="Tilt Angle Range (± degrees):").grid(row=1, column=0, padx=5)
        self.tilt_angle_range = tk.IntVar(value=30)
        tilt_slider = ttk.Scale(self.test_controls_frame, from_=1, to=90, orient=tk.HORIZONTAL,
                                    variable=self.tilt_angle_range)
        tilt_slider.grid(row=1, column=1, padx=5)
        self.tilt_angle_label = ttk.Label(self.test_controls_frame, text="±30°")
        self.tilt_angle_label.grid(row=1, column=2, padx=5)
        self.tilt_angle_range.trace('w', self.update_tilt_angle_label)
        
        # Fill Increment Steps Slider
        ttk.Label(self.test_controls_frame, text="Fill Increment Steps:").grid(row=2, column=0, padx=5)
        self.fill_increment_steps = tk.IntVar(value=10)
        fill_slider = ttk.Scale(self.test_controls_frame, from_=1, to=100, orient=tk.HORIZONTAL,
                                    variable=self.fill_increment_steps)
        fill_slider.grid(row=2, column=1, padx=5)
        self.fill_increment_label = ttk.Label(self.test_controls_frame, text="10")
        self.fill_increment_label.grid(row=2, column=2, padx=5)
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

    def apply_debug_highlights(self, highlight_config):
        """Apply debug highlights based on configuration"""
        try:
            self.clear_debug_highlights()
            
            # Map configuration names to actual frames
            frames = {
                # Main sections
                "Navigation Bar": self.notebook,
                "Test Parameters/Settings": self.params_frame,
                "Visualization": self.visual_frame,
                "Data Logging & Events": self.log_widget,
                
                # Navigation Bar subsections
                "Test Controls Section": self.test_controls_frame,
                "Arduino Settings Section": self.arduino_settings_frame,
                "Temperature Settings Section": self.temp_settings_frame,
                "Hardware Config Section": self.hardware_config_frame
            }
            
            # Add debug info
            print("DEBUG: Available frames for highlighting:")
            for name, widget in frames.items():
                print(f"{name}: {'Available' if widget else 'Not available'}")
            
            # Get the root window's position
            root_x = self.master.winfo_x()
            root_y = self.master.winfo_y()
            
            for name, widget in frames.items():
                if (name in highlight_config and 
                    highlight_config[name] and 
                    widget and 
                    hasattr(widget, 'winfo_exists') and 
                    widget.winfo_exists()):
                    try:
                        # Get widget coordinates relative to root window
                        x = widget.winfo_rootx() - root_x
                        y = widget.winfo_rooty() - root_y
                        width = widget.winfo_width()
                        height = widget.winfo_height()
                        
                        if width <= 1 or height <= 1:
                            print(f"Skipping {name} - invalid dimensions: {width}x{height}")
                            continue
                        
                        # Create outline for each edge
                        for outline in [
                            (x, y, width, 2),  # Top
                            (x, y + height - 2, width, 2),  # Bottom
                            (x, y, 2, height),  # Left
                            (x + width - 2, y, 2, height)  # Right
                        ]:
                            outline_canvas = tk.Canvas(
                                self.master,
                                width=outline[2],
                                height=outline[3],
                                bg='#90EE90',  # Light green
                                highlightthickness=0,
                                borderwidth=0
                            )
                            outline_canvas.place(x=outline[0], y=outline[1])
                            outline_canvas._is_debug_outline = True
                            
                            # Add hover effect
                            outline_canvas.bind('<Enter>', lambda e: e.widget.configure(bg='#00FF00'))
                            outline_canvas.bind('<Leave>', lambda e: e.widget.configure(bg='#90EE90'))
                            
                    except Exception as e:
                        print(f"Error highlighting {name}: {e}")
                        
        except Exception as e:
            print(f"Error applying highlights: {e}")

    def clear_debug_highlights(self):
        """Remove all existing debug highlight frames"""
        for widget in self.master.winfo_children():
            if isinstance(widget, tk.Canvas) and hasattr(widget, '_is_debug_outline'):
                widget.destroy()

    def show_debug_config(self):
        """Show debug configuration dialog"""
        try:
            # Clear any existing highlights
            self.clear_debug_highlights()
            
            # Print debug info about available frames
            print("\nDEBUG: Frame Availability Check")
            frames_to_check = [
                'notebook', 'params_frame', 'visual_frame', 'log_widget',
                'test_controls_frame', 'arduino_settings_frame', 
                'temp_settings_frame', 'hardware_config_frame'
            ]
            
            for frame_name in frames_to_check:
                has_frame = hasattr(self, frame_name)
                frame = getattr(self, frame_name, None)
                exists = frame and hasattr(frame, 'winfo_exists') and frame.winfo_exists()
                print(f"{frame_name}: {'Available and exists' if exists else 'Not available or not existing'}")
            
            # Create or show existing config dialog
            if not hasattr(self, '_debug_config') or not self._debug_config.dialog.winfo_exists():
                self._debug_config = DebugHighlightConfig(self)
            else:
                self._debug_config.dialog.lift()
                self._debug_config.dialog.focus_set()
        except Exception as e:
            print(f"Error showing debug config: {e}")

    def create_visualization_frame(self, parent):
        print("DEBUG: Starting create_visualization_frame")
        try:
            # Store frame reference as class attribute
            self.visual_frame = ttk.LabelFrame(parent, text="Visualization")
            self.visual_frame.grid_columnconfigure(0, weight=1)
            self.visual_frame.grid_columnconfigure(1, weight=1)
            self.visual_frame.grid_rowconfigure(0, weight=1)
            
            # Create left frame for tilt indicator
            left_frame = ttk.Frame(self.visual_frame)
            left_frame.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
            left_frame.grid_columnconfigure(0, weight=1)
            left_frame.grid_rowconfigure(0, weight=1)
            
            # Create canvas for tilt indicator
            self.tilt_canvas = tk.Canvas(
                left_frame,
                width=200,
                height=200,
                bg='black'
            )
            self.tilt_canvas.grid(row=0, column=0, sticky='nsew')
            
            # Create right frame for temperature graph
            right_frame = ttk.Frame(self.visual_frame)
            right_frame.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)
            right_frame.grid_columnconfigure(0, weight=1)
            right_frame.grid_rowconfigure(0, weight=1)
            
            # Create temperature graph
            self.fig, self.ax = plt.subplots(figsize=(6, 4))
            self.canvas = FigureCanvasTkAgg(self.fig, right_frame)
            self.canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew')
            
            return self.visual_frame
            
        except Exception as e:
            print(f"DEBUG ERROR in create_visualization_frame: {str(e)}")
            raise

    def on_canvas_resize(self, event):
        """Handle canvas resize events"""
        # Update canvas size
        size = min(event.width, event.height)
        if hasattr(self, 'tilt_indicator'):
            self.tilt_indicator.resize(size, size)

    def create_menu_bar(self):
        """Create the application menu bar"""
        try:
            # Create Menu Bar
            menubar = tk.Menu(self.master)
            self.master.config(menu=menubar)
            
            # File Menu
            file_menu = tk.Menu(menubar, tearoff=0, bg='#1c1c1c', fg='white')
            menubar.add_cascade(label="File", menu=file_menu)
            file_menu.add_command(label="Export Data", command=self.save_to_csv)
            file_menu.add_separator()
            file_menu.add_command(label="Exit", command=self.on_closing)
            
            # Troubleshooting Menu
            trouble_menu = tk.Menu(menubar, tearoff=0, bg='#1c1c1c', fg='white')
            menubar.add_cascade(label="Troubleshooting", menu=trouble_menu)
            trouble_menu.add_command(label="Test Connection", command=self.find_and_connect_arduino)
            trouble_menu.add_command(label="Calibrate Sensors", command=self.calibrate_sensor)
            trouble_menu.add_separator()
            trouble_menu.add_command(label="Configure Debug Highlights", command=self.show_debug_config)
            
            # Help Menu
            help_menu = tk.Menu(menubar, tearoff=0, bg='#1c1c1c', fg='white')
            menubar.add_cascade(label="Help", menu=help_menu)
            help_menu.add_command(label="About", command=self.show_about)
            
        except Exception as e:
            self.logger.error(f"Error creating menu bar: {e}", extra={'color': 'red'})

    def create_test_parameters_frame(self, parent):
        print("DEBUG: Starting create_test_parameters_frame")
        try:
            # Create and store the params_frame as class attribute
            self.params_frame = ttk.LabelFrame(parent, text="Test Parameters/Settings")
            self.params_frame.grid_columnconfigure(0, weight=1)
            
            # Tilt Angles Frame
            self.tilt_frame = ttk.LabelFrame(self.params_frame, text="Tilt Angles")
            self.tilt_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
            
            # Add tilt angles display
            self.tilt_angles_label = ttk.Label(
                self.tilt_frame,
                text="X: +0.0° Y: +0.0° Z: +0.0°",
                font=('Courier', 10)
            )
            self.tilt_angles_label.grid(row=0, column=0, pady=2, padx=2)
            
            # Status Display Frame
            self.status_frame = ttk.LabelFrame(self.params_frame, text="Test Status")
            self.status_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
            self.test_status_label = ttk.Label(self.status_frame, text="Current Phase: Idle")
            self.test_status_label.grid(row=0, column=0, pady=2, padx=2)
            
            # Hardware Feedback Frame
            self.hardware_feedback_frame = ttk.LabelFrame(self.params_frame, text="Hardware Feedback")
            self.hardware_feedback_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
            
            # Add hardware feedback content
            feedback_grid = ttk.Frame(self.hardware_feedback_frame)
            feedback_grid.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
            
            # Configure feedback_grid columns
            feedback_grid.grid_columnconfigure(1, weight=1)
            
            # Stepper Motor Status
            ttk.Label(feedback_grid, text="Stepper Motor Status:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
            self.stepper_status_label = ttk.Label(feedback_grid, text="Position: 0 | Speed: 60 RPM")
            self.stepper_status_label.grid(row=0, column=1, sticky='w', padx=5, pady=2)
            
            # Motion-Tracking Device Output
            ttk.Label(feedback_grid, text="Motion-Tracker Output:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
            self.motion_tracker_label = ttk.Label(feedback_grid, text="Pitch: 0° | Roll: 0°")
            self.motion_tracker_label.grid(row=1, column=1, sticky='w', padx=5, pady=2)
            
            return self.params_frame
            
        except Exception as e:
            print(f"DEBUG ERROR in create_test_parameters_frame: {str(e)}")
            raise

    def show_about(self):
        """Show the about dialog"""
        try:
            about_window = tk.Toplevel(self.master)
            about_window.title("About")
            about_window.geometry("400x300")
            about_window.configure(bg='#1c1c1c')
            
            # Make the window modal
            about_window.transient(self.master)
            about_window.grab_set()
            
            # Create main frame for about window
            about_frame = ttk.Frame(about_window)
            about_frame.grid(row=0, column=0, sticky='nsew', padx=20, pady=20)
            
            # Configure grid weights
            about_frame.grid_columnconfigure(0, weight=1)
            about_window.grid_columnconfigure(0, weight=1)
            about_window.grid_rowconfigure(0, weight=1)
            
            # Add content using grid
            ttk.Label(
                about_frame,
                text="Enhanced Automated Data Logger",
                font=('Helvetica', 14, 'bold')
            ).grid(row=0, column=0, pady=20)
            
            ttk.Label(
                about_frame,
                text="Version 1.0\n\n" +
                     "A comprehensive data logging and visualization tool\n" +
                     "for automated testing and monitoring.",
                justify=tk.CENTER
            ).grid(row=1, column=0, pady=10)
            
            # Close button
            ttk.Button(
                about_frame,
                text="Close",
                command=about_window.destroy
            ).grid(row=2, column=0, pady=20)
            
        except Exception as e:
            self.logger.error(f"Error showing about dialog: {e}", extra={'color': 'red'})

    def handle_error(self, error_msg, title="Error"):
        """Generic error handler for displaying error messages"""
        try:
            # Log the error
            self.logger.error(error_msg, extra={'color': 'red'})
            
            # Show error dialog
            tk.messagebox.showerror(title, error_msg)
            
        except Exception as e:
            # If even the error handler fails, print to console as last resort
            print(f"Critical error: {e}")
            print(f"Original error: {error_msg}")

    def check_geometry_managers(self, widget):
        """Debug helper to check geometry managers of a widget and its children"""
        try:
            print(f"DEBUG: Checking widget {widget}")
            
            # Check the widget's geometry manager
            try:
                pack_info = widget.pack_info()
                print(f"DEBUG: Widget uses pack: {pack_info}")
            except:
                try:
                    grid_info = widget.grid_info()
                    print(f"DEBUG: Widget uses grid: {grid_info}")
                except:
                    print("DEBUG: Widget uses neither pack nor grid")
            
            # Check all children
            for child in widget.winfo_children():
                self.check_geometry_managers(child)
                
        except Exception as e:
            print(f"DEBUG: Error checking geometry managers: {e}")

    def cleanup_pygame_resources(self):
        """Clean up Pygame resources properly"""
        try:
            if hasattr(self, 'tilt_indicator'):
                self.tilt_indicator.cleanup()
            
            # Force garbage collection to clean up Pygame surfaces
            import gc
            gc.collect()
            
        except Exception as e:
            print(f"Error cleaning up Pygame resources: {e}")

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
        
        
        