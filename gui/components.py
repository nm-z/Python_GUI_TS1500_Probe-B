from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QLabel, 
    QScrollArea, QFrame, QGridLayout, QHBoxLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen, QIcon
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np
from datetime import datetime, timedelta
import os

from .styles import Styles as StylesModule

class RealTimePlots(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
        # Data storage
        self.temperature_data = []
        self.angle_data = []
        self.time_window = timedelta(minutes=5)  # Show last 5 minutes
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Create temperature plot
        self.temp_figure = Figure(figsize=(8, 4))
        self.temp_canvas = FigureCanvasQTAgg(self.temp_figure)
        self.temp_ax = self.temp_figure.add_subplot(111)
        self.temp_ax.set_title('Temperature vs Time')
        self.temp_ax.set_xlabel('Time')
        self.temp_ax.set_ylabel('Temperature (°C)')
        self.temp_figure.patch.set_facecolor('#1c1c1c')
        self.temp_ax.set_facecolor('#353535')
        self.temp_ax.tick_params(colors='white')
        self.temp_ax.title.set_color('white')
        self.temp_ax.xaxis.label.set_color('white')
        self.temp_ax.yaxis.label.set_color('white')
        layout.addWidget(self.temp_canvas)
        
        # Create angle plot
        self.angle_figure = Figure(figsize=(8, 4))
        self.angle_canvas = FigureCanvasQTAgg(self.angle_figure)
        self.angle_ax = self.angle_figure.add_subplot(111)
        self.angle_ax.set_title('Platform Angle vs Time')
        self.angle_ax.set_xlabel('Time')
        self.angle_ax.set_ylabel('Angle (degrees)')
        self.angle_figure.patch.set_facecolor('#1c1c1c')
        self.angle_ax.set_facecolor('#353535')
        self.angle_ax.tick_params(colors='white')
        self.angle_ax.title.set_color('white')
        self.angle_ax.xaxis.label.set_color('white')
        self.angle_ax.yaxis.label.set_color('white')
        layout.addWidget(self.angle_canvas)
        
        # Add tilt indicator
        self.tilt_indicator = TiltIndicator()
        self.tilt_indicator.setFixedSize(200, 200)  # Set a fixed size for the indicator
        tilt_container = QWidget()
        tilt_layout = QHBoxLayout(tilt_container)
        tilt_layout.addStretch()
        tilt_layout.addWidget(self.tilt_indicator)
        tilt_layout.addStretch()
        layout.addWidget(tilt_container)
        
        self.setLayout(layout)
        
    def update_data(self, data):
        current_time = datetime.now()
        cutoff_time = current_time - self.time_window
        
        # Update temperature data
        if 'temperature' in data:
            self.temperature_data.append((current_time, data['temperature']))
            self.temperature_data = [(t, v) for t, v in self.temperature_data 
                                   if t > cutoff_time]
            
            # Update temperature plot
            times, temps = zip(*self.temperature_data) if self.temperature_data else ([], [])
            self.temp_ax.clear()
            self.temp_ax.plot(times, temps, 'w-')
            self.temp_ax.set_title('Temperature vs Time')
            self.temp_ax.set_xlabel('Time')
            self.temp_ax.set_ylabel('Temperature (°C)')
            self.temp_ax.tick_params(colors='white')
            self.temp_ax.title.set_color('white')
            self.temp_ax.xaxis.label.set_color('white')
            self.temp_ax.yaxis.label.set_color('white')
            self.temp_canvas.draw()
        
        # Update angle data
        if 'current_angle' in data:
            self.angle_data.append((current_time, data['current_angle']))
            self.angle_data = [(t, v) for t, v in self.angle_data 
                             if t > cutoff_time]
            
            # Update angle plot
            times, angles = zip(*self.angle_data) if self.angle_data else ([], [])
            self.angle_ax.clear()
            self.angle_ax.plot(times, angles, 'w-')
            self.angle_ax.set_title('Platform Angle vs Time')
            self.angle_ax.set_xlabel('Time')
            self.angle_ax.set_ylabel('Angle (degrees)')
            self.angle_ax.tick_params(colors='white')
            self.angle_ax.title.set_color('white')
            self.angle_ax.xaxis.label.set_color('white')
            self.angle_ax.yaxis.label.set_color('white')
            self.angle_canvas.draw()
            
            # Update tilt indicator
            self.tilt_indicator.set_angle(data['current_angle'])
            
    def clear_data(self):
        """Clear all plot data"""
        self.temperature_data = []
        self.angle_data = []
        self.temp_ax.clear()
        self.angle_ax.clear()
        self.temp_canvas.draw()
        self.angle_canvas.draw()
        self.tilt_indicator.set_angle(0.0)

class LogViewer(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #353535;
                color: white;
                border: 1px solid #2a82da;
                border-radius: 3px;
            }
        """)
        
    def append_log(self, message, level="INFO"):
        color = {
            "INFO": "white",
            "WARNING": "#ffff44",
            "ERROR": "#ff4444",
            "CRITICAL": "#ff0000",
            "DEBUG": "#44ff44"
        }.get(level, "white")
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f'<font color="{color}">[{timestamp}] {level}: {message}</font>'
        self.append(formatted_message)

class StatusIndicators(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QGridLayout()
        
        # Temperature status
        self.temp_label = QLabel("Temperature: N/A")
        layout.addWidget(self.temp_label, 0, 0)
        
        # Angle status
        self.angle_label = QLabel("Current Angle: 0.0°")
        layout.addWidget(self.angle_label, 1, 0)
        
        # Test status
        self.test_status = QLabel("Test Status: Ready")
        layout.addWidget(self.test_status, 2, 0)
        
        # Data storage status
        self.storage_status = QLabel("Data Storage: Ready")
        layout.addWidget(self.storage_status, 3, 0)
        
        self.setLayout(layout)
        
    def update_status(self, data):
        if 'temperature' in data:
            self.temp_label.setText(f"Temperature: {data['temperature']:.1f}°C")
        
        if 'current_angle' in data:
            self.angle_label.setText(f"Current Angle: {data['current_angle']:.1f}°")
        
        if 'test_status' in data:
            self.test_status.setText(f"Test Status: {data['test_status']}")
        
        if 'storage_status' in data:
            self.storage_status.setText(f"Data Storage: {data['storage_status']}")

class TiltIndicator(QWidget):
    def __init__(self):
        super().__init__()
        self.angle = 0.0
        self.setMinimumSize(200, 200)
        
    def set_angle(self, angle):
        self.angle = angle
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate center and radius
        width = self.width()
        height = self.height()
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 3
        
        # Draw background circle
        painter.setPen(QPen(QColor(StylesModule.COLORS['accent']), 2))
        painter.drawEllipse(int(center_x - radius), int(center_y - radius),
                          int(radius * 2), int(radius * 2))
        
        # Draw angle indicator
        painter.setPen(QPen(QColor(StylesModule.COLORS['foreground']), 3))
        angle_rad = np.radians(self.angle)
        end_x = center_x + radius * np.sin(angle_rad)
        end_y = center_y - radius * np.cos(angle_rad)
        painter.drawLine(int(center_x), int(center_y),
                        int(end_x), int(end_y))
        
        # Draw angle text
        painter.drawText(10, height - 10, f"Angle: {self.angle:.1f}°")
        
    def update_data(self, data):
        if 'current_angle' in data:
            self.set_angle(data['current_angle']) 

def setup_icons():
    """Set up icons for components"""
    icons = {}
    icon_files = {
        'issue': 'icons/issue.png',
        'components': 'icons/components.png',
        'help': 'icons/help.png',
        'reset': 'icons/reset.png',
        'sync': 'icons/sync.png',
        'upload': 'icons/upload.png',
        'backup': 'icons/backup.png',
        'params': 'icons/params.png',
        'hardware': 'icons/hardware.png',
        'plots': 'icons/plots.png',
        'tilt': 'icons/tilt.png',
        'logs': 'icons/logs.png',
        'stop': 'icons/stop.png',
        'pause': 'icons/pause.png',
        'export': 'icons/export.png',
        'start': 'icons/start.png',
        'save': 'icons/save.png',
        'open': 'icons/open.png'
    }
    
    print("Setting up icons from:", os.getcwd())
    for name, path in icon_files.items():
        try:
            if not os.path.exists(path):
                print(f"Warning: Icon file not found: {path}")
                continue
            icons[name] = QIcon(path)
            print(f"Successfully loaded icon: {name}")
        except Exception as e:
            print(f"Error loading icon {name} from {path}: {str(e)}")
            # Create an empty icon as fallback
            icons[name] = QIcon()
    
    return icons