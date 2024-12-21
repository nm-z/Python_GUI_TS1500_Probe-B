import tkinter as tk
from tkinter import ttk, scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import math
from datetime import datetime, timedelta
import numpy as np
import json
import os
from utils.text_handler import TextHandler
import logging
from utils.logger import gui_logger

class MainView:
    def __init__(self, master, controller):
        self.master = master
        self.controller = controller
        self.master.title("Enhanced Automated Data Logger")
        self.master.geometry("1024x1200")
        
        # Enforce Minimum Window Size
        self.master.minsize(1024, 1000)
        self.master.maxsize(1600, 1600)
        
        # Initialize data storage
        self.temperature_data = []
        self.tilt_angle_data = []
        self.fill_level_data = []
        
        # Connection status label
        self.connection_status = tk.Label(self.master, text="Disconnected", fg="white", bg="#1c1c1c")
        self.connection_status.pack(pady=5)
        
        # Set dark mode color scheme
        self.set_dark_mode()
        
        # Create widgets
        self.create_widgets()
        
        # Initialize logger
        self.create_logger()
        
        # Start data collection thread
        self.start_data_collection()
        
        # Protocol for window closing
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_data_collection(self):
        """Start the data collection thread"""
        self.data_collection_thread = threading.Thread(target=self.collect_data, daemon=True)
        self.data_collection_thread.start()

    def collect_data(self):
        """Collect data from sensors periodically"""
        while True:
            try:
                # Get data from controller
                temperature = self.controller.get_temperature()
                tilt_angle = self.controller.get_tilt_angle()
                fill_level = self.controller.get_fill_level()
                
                # Update data lists
                current_time = datetime.now()
                self.temperature_data.append((current_time, temperature))
                self.tilt_angle_data.append((current_time, tilt_angle))
                self.fill_level_data.append((current_time, fill_level))
                
                # Keep only last hour of data
                cutoff_time = current_time - timedelta(hours=1)
                self.temperature_data = [(t, v) for t, v in self.temperature_data if t > cutoff_time]
                self.tilt_angle_data = [(t, v) for t, v in self.tilt_angle_data if t > cutoff_time]
                self.fill_level_data = [(t, v) for t, v in self.fill_level_data if t > cutoff_time]
                
                # Update plots
                self.master.after(0, self.update_plots)
                
            except Exception as e:
                self.logger.error(f"Error collecting data: {e}")
            
            # Sleep for a short duration
            self.master.after(1000)
        
        # Simulate temperature data for demonstration
        if not hasattr(self, 'temperature_data'):
            self.temperature_data = []
            self.time_data = []

    def update_status(self, message, color="white"):
        """Update the status label with the given message and color."""
        if hasattr(self, 'connection_status'):
            self.connection_status.config(text=message, fg=color)
        
        if hasattr(self, 'status_bar'):
            self.status_bar.config(text=f"Status: {message}")
        
        # Log the status update
        if hasattr(self, 'logger'):
            self.logger.info(f"Status updated: {message}")

    def set_dark_mode(self):
        style = ttk.Style()
        
        # Configure colors
        bg_color = '#1c1c1c'
        fg_color = 'white'
        accent_color = '#4CAF50'
        hover_color = '#45a049'
        button_bg = '#4c4c4c'
        entry_bg = '#2c2c2c'
        
        # Configure base styles
        style.configure('.',
            background=bg_color,
            foreground=fg_color,
            fieldbackground=entry_bg,
            troughcolor=entry_bg,
            selectbackground=accent_color,
            selectforeground=fg_color
        )
        
        # Frame styles
        style.configure('TFrame', background=bg_color)
        style.configure('TLabelframe', background=bg_color, foreground=fg_color)
        style.configure('TLabelframe.Label', background=bg_color, foreground=fg_color)
        
        # Label styles
        style.configure('TLabel', background=bg_color, foreground=fg_color)
        style.configure('Param.TLabel', background=bg_color, foreground=fg_color, font=('Arial', 10))
        
        # Button styles
        style.configure('TButton',
            background=button_bg,
            foreground=fg_color,
            padding=5,
            font=('Arial', 10)
        )
        style.map('TButton',
            background=[('active', hover_color)],
            foreground=[('active', fg_color)]
        )
        
        # Action button style (for main control buttons)
        style.configure('Action.TButton',
            background=accent_color,
            foreground=fg_color,
            padding=8,
            font=('Arial', 11, 'bold')
        )
        style.map('Action.TButton',
            background=[('active', hover_color)],
            foreground=[('active', fg_color)]
        )
        
        # Entry and Combobox styles
        style.configure('TEntry', fieldbackground=entry_bg, foreground=fg_color)
        style.configure('TCombobox',
            fieldbackground=entry_bg,
            background=button_bg,
            foreground=fg_color,
            arrowcolor=fg_color
        )
        style.map('TCombobox',
            fieldbackground=[('readonly', entry_bg)],
            selectbackground=[('readonly', accent_color)]
        )
        
        # Notebook styles
        style.configure('TNotebook',
            background=bg_color,
            tabmargins=[2, 5, 2, 0]
        )
        style.configure('TNotebook.Tab',
            background=button_bg,
            foreground=fg_color,
            padding=[10, 5],
            font=('Arial', 10)
        )
        style.map('TNotebook.Tab',
            background=[('selected', accent_color)],
            foreground=[('selected', fg_color)]
        )
        
        # Scale styles
        style.configure('Custom.Horizontal.TScale',
            background=bg_color,
            troughcolor=entry_bg,
            sliderrelief='flat'
        )
        
        # Progressbar style
        style.configure('Custom.Horizontal.TProgressbar',
            background=accent_color,
            troughcolor=entry_bg,
            bordercolor=entry_bg,
            lightcolor=accent_color,
            darkcolor=accent_color
        )
        
        # Treeview styles
        style.configure('Custom.Treeview',
            background=entry_bg,
            foreground=fg_color,
            fieldbackground=entry_bg,
            font=('Arial', 9)
        )
        style.configure('Custom.Treeview.Heading',
            background=button_bg,
            foreground=fg_color,
            font=('Arial', 10, 'bold')
        )
        style.map('Custom.Treeview',
            background=[('selected', accent_color)],
            foreground=[('selected', fg_color)]
        )
        
        # Configure master window
        self.master.configure(background=bg_color)

    def create_logger(self):
        self.log_widget = scrolledtext.ScrolledText(
            self.master, 
            state='disabled',
            height=10,
            bg='#4c4c4c',
            fg='white',
            padx=10,
            pady=10
        )
        self.log_widget.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        self.logger = logging.getLogger('MainView')
        self.logger.setLevel(logging.INFO)
        
        text_handler = TextHandler(self.log_widget)
        self.logger.addHandler(text_handler)
        
        # Configure text tags for colors
        self.log_widget.tag_configure('green', foreground='#00FF00')
        self.log_widget.tag_configure('red', foreground='red')
        self.log_widget.tag_configure('yellow', foreground='yellow')

    def create_widgets(self):
        # Create main paned window
        self.main_pane = ttk.PanedWindow(self.master, orient=tk.VERTICAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)
        
        # Upper section for controls and visualization
        self.upper_section = ttk.Frame(self.main_pane)
        self.main_pane.add(self.upper_section, weight=3)
        
        # Create control frame
        self.control_frame = ttk.LabelFrame(self.upper_section, text="Controls")
        self.control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.control_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs
        self.create_testing_tab()
        self.create_settings_tab()
        self.create_data_management_tab()
        
        # Create visualization section
        self.visualization_frame = ttk.LabelFrame(self.upper_section, text="Real-Time Data")
        self.visualization_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create visualization grid
        self.create_visualization_grid()
        
        # Lower section for logging
        self.log_frame = ttk.Frame(self.main_pane)
        self.main_pane.add(self.log_frame, weight=1)
        
        # Create enhanced logging view
        self.create_enhanced_log_view()
        
        # Status bar at the bottom
        self.status_bar = ttk.Label(
            self.master,
            text="Status: Disconnected",
            background='#333333',
            foreground='white',
            anchor='center',
            padding=5
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_data_management_tab(self):
        """Create the data management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Data Management")
        
        # Data Export Frame
        export_frame = ttk.LabelFrame(tab, text="Data Export")
        export_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Export buttons
        ttk.Button(
            export_frame,
            text="Export Data to CSV",
            command=self.controller.export_data_to_csv,
            style='Action.TButton'
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Button(
            export_frame,
            text="Export Logs",
            command=self.controller.export_logs,
            style='Action.TButton'
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Backup Frame
        backup_frame = ttk.LabelFrame(tab, text="Backup Management")
        backup_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(
            backup_frame,
            text="Backup Data",
            command=self.controller.backup_data,
            style='Action.TButton'
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Button(
            backup_frame,
            text="Restore Backup",
            command=self.controller.restore_backup,
            style='Action.TButton'
        ).pack(side=tk.LEFT, padx=5, pady=5)

    def create_visualization_grid(self):
        """Create the visualization grid with real-time plots"""
        # Temperature Graph
        self.fig_temperature, self.ax_temperature = plt.subplots(figsize=(6, 3), facecolor='#2c2c2c')
        self.setup_plot(self.ax_temperature, 'Temperature Over Time', 'Time', 'Temperature (°C)')
        self.temperature_canvas = FigureCanvasTkAgg(self.fig_temperature, master=self.visualization_frame)
        self.temperature_canvas.get_tk_widget().grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
        
        # Tilt Angle Graph
        self.fig_tilt, self.ax_tilt = plt.subplots(figsize=(6, 3), facecolor='#2c2c2c')
        self.setup_plot(self.ax_tilt, 'Tilt Angle Over Time', 'Time', 'Angle (degrees)')
        self.tilt_canvas = FigureCanvasTkAgg(self.fig_tilt, master=self.visualization_frame)
        self.tilt_canvas.get_tk_widget().grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        
        # Fill Level Graph
        self.fig_fill, self.ax_fill = plt.subplots(figsize=(6, 3), facecolor='#2c2c2c')
        self.setup_plot(self.ax_fill, 'Fill Level Over Time', 'Time', 'Fill Level (%)')
        self.fill_canvas = FigureCanvasTkAgg(self.fig_fill, master=self.visualization_frame)
        self.fill_canvas.get_tk_widget().grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')
        
        # Configure grid weights
        self.visualization_frame.grid_columnconfigure(0, weight=1)
        self.visualization_frame.grid_columnconfigure(1, weight=1)
        self.visualization_frame.grid_rowconfigure(0, weight=1)
        self.visualization_frame.grid_rowconfigure(1, weight=1)

    def setup_plot(self, ax, title, xlabel, ylabel):
        """Setup common plot parameters"""
        ax.set_facecolor('#1e1e1e')
        ax.set_title(title, color='white', fontsize=12, pad=10)
        ax.set_xlabel(xlabel, color='white', fontsize=10)
        ax.set_ylabel(ylabel, color='white', fontsize=10)
        ax.tick_params(colors='white')
        ax.grid(True, color='gray', linestyle='--', alpha=0.3)

    def create_enhanced_log_view(self):
        """Create an enhanced logging view using Treeview"""
        columns = ('Time', 'Level', 'Message')
        self.log_tree = ttk.Treeview(
            self.log_frame,
            columns=columns,
            show='headings',
            style='Custom.Treeview'
        )
        
        # Configure column headings
        self.log_tree.heading('Time', text='Time')
        self.log_tree.heading('Level', text='Level')
        self.log_tree.heading('Message', text='Message')
        
        # Configure column widths
        self.log_tree.column('Time', width=150)
        self.log_tree.column('Level', width=70)
        self.log_tree.column('Message', width=800)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(self.log_frame, orient="vertical", command=self.log_tree.yview)
        hsb = ttk.Scrollbar(self.log_frame, orient="horizontal", command=self.log_tree.xview)
        self.log_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout
        self.log_tree.grid(column=0, row=0, sticky='nsew')
        vsb.grid(column=1, row=0, sticky='ns')
        hsb.grid(column=0, row=1, sticky='ew')
        
        # Configure grid weights
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(0, weight=1)

    def on_closing(self):
        """Handle window closing"""
        self.controller.cleanup()
        self.master.quit()

    def update_tilt_indicator(self):
        """Update tilt indicator (placeholder for future implementation)"""
        self.master.after(100, self.update_tilt_indicator)

    def simulate_temperature_data(self):
        """Simulate temperature data for demonstration"""
        if not hasattr(self, 'temperature_data'):
            self.temperature_data = []
            self.time_data = []

    def update_temperature_display(self, temp):
        self.temp_label.config(
            text=f"Temperature: {temp:.1f}°C"
        )

    def update_fill_level_display(self, fill_data):
        """Update the fill level graph with new data"""
        if not hasattr(self, 'ax_fill_level'):
            return
            
        self.ax_fill_level.clear()
        
        if fill_data:
            times = [entry[0] for entry in fill_data]
            levels = [entry[1] for entry in fill_data]
            
            self.ax_fill_level.plot(times, levels, 'g-', linewidth=2)
            
        # Maintain dark theme
        self.ax_fill_level.set_facecolor('#1e1e1e')
        self.ax_fill_level.grid(True, color='gray', linestyle='--', alpha=0.3)
        self.ax_fill_level.set_title('Fill Level History', color='white', fontsize=12, pad=10)
        self.ax_fill_level.set_xlabel('Time', color='white', fontsize=10)
        self.ax_fill_level.set_ylabel('Fill Level (%)', color='white', fontsize=10)
        self.ax_fill_level.tick_params(axis='both', colors='white')
        
        # Update the canvas
        self.fill_level_canvas.draw()

    def update_status_label(self, text):
        """Update the status label text"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=f"Status: {text}")

    def simulate_temperature_data(self):
        # Simulate temperature data for testing
        current_time = datetime.now()
        temp = 21.0 + 0.5 * math.sin(current_time.timestamp() / 60)
        self.controller.model.update_temperature(temp)
        self.master.after(1000, self.simulate_temperature_data)

    def create_testing_tab(self):
        """Create the testing controls tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Testing Controls")
        
        # Test Controls Frame
        test_controls_frame = ttk.LabelFrame(tab, text="Test Controls")
        test_controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Configure grid with equal column weights
        for i in range(3):
            test_controls_frame.columnconfigure(i, weight=1, pad=10)
        
        # Control buttons with improved styling
        button_style = {'width': 15, 'padding': 5}
        
        self.start_test_button = ttk.Button(
            test_controls_frame,
            text="Start Test",
            command=lambda: self.controller.start_test(),
            style='Action.TButton',
            **button_style
        )
        self.start_test_button.grid(row=0, column=0, padx=10, pady=10, sticky='ew')
        
        self.pause_test_button = ttk.Button(
            test_controls_frame,
            text="Pause Test",
            command=lambda: self.controller.pause_test(),
            style='Action.TButton',
            **button_style
        )
        self.pause_test_button.grid(row=0, column=1, padx=10, pady=10, sticky='ew')
        
        self.stop_test_button = ttk.Button(
            test_controls_frame,
            text="Stop Test",
            command=lambda: self.controller.stop_test(),
            style='Action.TButton',
            **button_style
        )
        self.stop_test_button.grid(row=0, column=2, padx=10, pady=10, sticky='ew')
        
        # Progress bar
        self.progress = ttk.Progressbar(
            test_controls_frame,
            orient="horizontal",
            mode="determinate",
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 10), sticky='ew')
        
        # Parameters Frame
        params_frame = ttk.LabelFrame(tab, text="Test Parameters")
        params_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Configure grid for parameters
        params_frame.columnconfigure(1, weight=1)
        params_frame.columnconfigure(3, weight=1)
        
        # Angle Increment
        ttk.Label(
            params_frame,
            text="Angle Increment:",
            style='Param.TLabel'
        ).grid(row=0, column=0, padx=5, pady=10, sticky='e')
        
        self.angle_increment_var = tk.IntVar(value=1)
        self.angle_increment_scale = ttk.Scale(
            params_frame,
            from_=1,
            to=10,
            orient="horizontal",
            variable=self.angle_increment_var,
            style='Custom.Horizontal.TScale'
        )
        self.angle_increment_scale.grid(row=0, column=1, padx=10, pady=10, sticky='ew')
        
        # Angle Step Size
        ttk.Label(
            params_frame,
            text="Angle Step Size:",
            style='Param.TLabel'
        ).grid(row=0, column=2, padx=5, pady=10, sticky='e')
        
        self.angle_step_size_var = tk.IntVar(value=10)
        self.angle_step_size_scale = ttk.Scale(
            params_frame,
            from_=10,
            to=90,
            orient="horizontal",
            variable=self.angle_step_size_var,
            style='Custom.Horizontal.TScale'
        )
        self.angle_step_size_scale.grid(row=0, column=3, padx=10, pady=10, sticky='ew')

    def create_settings_tab(self):
        """Create the settings controls tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Settings")
        
        # Hardware Configuration Frame
        hardware_frame = ttk.LabelFrame(tab, text="Hardware Configuration")
        hardware_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Arduino Port Selection
        ttk.Label(
            hardware_frame,
            text="Arduino Port:",
            style='Param.TLabel'
        ).grid(row=0, column=0, padx=5, pady=5, sticky='e')
        
        self.arduino_port_var = tk.StringVar(value='/dev/ttyUSB0')
        self.arduino_port_combo = ttk.Combobox(
            hardware_frame,
            textvariable=self.arduino_port_var,
            values=['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0']
        )
        self.arduino_port_combo.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        # Refresh Ports Button
        ttk.Button(
            hardware_frame,
            text="Refresh Ports",
            command=self.controller.refresh_ports,
            style='Action.TButton'
        ).grid(row=0, column=2, padx=5, pady=5)
        
        # Test Parameters Frame
        params_frame = ttk.LabelFrame(tab, text="Test Parameters")
        params_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Temperature Threshold
        ttk.Label(
            params_frame,
            text="Temperature Threshold:",
            style='Param.TLabel'
        ).grid(row=0, column=0, padx=5, pady=10, sticky='e')
        
        self.temperature_threshold_var = tk.DoubleVar(value=25.0)
        self.temperature_threshold_scale = ttk.Scale(
            params_frame,
            from_=20.0,
            to=30.0,
            orient="horizontal",
            variable=self.temperature_threshold_var,
            style='Custom.Horizontal.TScale'
        )
        self.temperature_threshold_scale.grid(row=0, column=1, padx=10, pady=10, sticky='ew')
        
        # Fill Level Threshold
        ttk.Label(
            params_frame,
            text="Fill Level Threshold:",
            style='Param.TLabel'
        ).grid(row=0, column=2, padx=5, pady=10, sticky='e')
        
        self.fill_level_threshold_var = tk.DoubleVar(value=80.0)
        self.fill_level_threshold_scale = ttk.Scale(
            params_frame,
            from_=70.0,
            to=90.0,
            orient="horizontal",
            variable=self.fill_level_threshold_var,
            style='Custom.Horizontal.TScale'
        )
        self.fill_level_threshold_scale.grid(row=0, column=3, padx=10, pady=10, sticky='ew')
        
        # Sampling Configuration Frame
        sampling_frame = ttk.LabelFrame(tab, text="Sampling Configuration")
        sampling_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Sampling Rate
        ttk.Label(
            sampling_frame,
            text="Sampling Rate (Hz):",
            style='Param.TLabel'
        ).grid(row=0, column=0, padx=5, pady=5, sticky='e')
        
        self.sampling_rate_var = tk.DoubleVar(value=1.0)
        sampling_rate_entry = ttk.Entry(
            sampling_frame,
            textvariable=self.sampling_rate_var,
            width=10
        )
        sampling_rate_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        # Data Storage Path
        ttk.Label(
            sampling_frame,
            text="Data Storage Path:",
            style='Param.TLabel'
        ).grid(row=1, column=0, padx=5, pady=5, sticky='e')
        
        self.storage_path_var = tk.StringVar(value='./data')
        storage_path_entry = ttk.Entry(
            sampling_frame,
            textvariable=self.storage_path_var,
            width=30
        )
        storage_path_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky='ew')
        
        ttk.Button(
            sampling_frame,
            text="Browse",
            command=self.browse_storage_path,
            style='Action.TButton'
        ).grid(row=1, column=3, padx=5, pady=5)
        
        # NTP Configuration Frame
        ntp_frame = ttk.LabelFrame(tab, text="Time Synchronization")
        ntp_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # NTP Server
        ttk.Label(
            ntp_frame,
            text="NTP Server:",
            style='Param.TLabel'
        ).grid(row=0, column=0, padx=5, pady=5, sticky='e')
        
        self.ntp_server_var = tk.StringVar(value='pool.ntp.org')
        ntp_server_entry = ttk.Entry(
            ntp_frame,
            textvariable=self.ntp_server_var,
            width=30
        )
        ntp_server_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Button(
            ntp_frame,
            text="Sync Time",
            command=self.controller.sync_time,
            style='Action.TButton'
        ).grid(row=0, column=2, padx=5, pady=5)
        
        # Configure grid weights
        for frame in [hardware_frame, params_frame, sampling_frame, ntp_frame]:
            frame.grid_columnconfigure(1, weight=1)

    def browse_storage_path(self):
        """Open a directory browser to select data storage path"""
        from tkinter import filedialog
        path = filedialog.askdirectory(
            title="Select Data Storage Directory",
            initialdir=self.storage_path_var.get()
        )
        if path:
            self.storage_path_var.set(path)
            self.logger.info(f"Data storage path updated to: {path}") 