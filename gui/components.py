from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QLabel, 
    QScrollArea, QFrame, QGridLayout, QHBoxLayout,
    QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen, QIcon, QFont
import pyqtgraph as pg
from datetime import datetime
import os

from .styles import Styles

class StatusIndicators(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Create status labels
        self.vna_status = QLabel("VNA: Not Connected")
        self.tilt_status = QLabel("Tilt: Not Connected")
        self.temp_status = QLabel("Temp: Not Connected")
        
        # Add labels to layout with separators
        self.status_widgets = [
            self.vna_status,
            QLabel("|"),
            self.tilt_status,
            QLabel("|"),
            self.temp_status
        ]
        
        for widget in self.status_widgets:
            layout.addWidget(widget)
            
    def update_status(self, status_dict):
        """Update the status indicators
        
        Args:
            status_dict (dict): Dictionary containing status information
                              {'vna': bool, 'tilt': bool, 'temp': bool}
        """
        status_map = {True: ("Connected", Styles.COLORS['success']),
                     False: ("Not Connected", Styles.COLORS['error'])}
        
        if 'vna' in status_dict:
            status, color = status_map[status_dict['vna']]
            self.vna_status.setText(f"VNA: {status}")
            self.vna_status.setStyleSheet(f"color: {color};")
            
        if 'tilt' in status_dict:
            status, color = status_map[status_dict['tilt']]
            self.tilt_status.setText(f"Tilt: {status}")
            self.tilt_status.setStyleSheet(f"color: {color};")
            
        if 'temp' in status_dict:
            status, color = status_map[status_dict['temp']]
            self.temp_status.setText(f"Temp: {status}")
            self.temp_status.setStyleSheet(f"color: {color};")

class LogViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        # Set Ubuntu Bold font
        font = QFont("Ubuntu")
        font.setWeight(QFont.Weight.Bold)
        self.log_text.setFont(font)
        
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Styles.COLORS['background_alt']};
                border: 1px solid {Styles.COLORS['border']};
                border-radius: {Styles.BORDER_RADIUS}px;
                padding: 5px;
                color: {Styles.COLORS['foreground']};
                font-family: 'Ubuntu';
                font-weight: bold;
            }}
        """)
        
        layout.addWidget(self.log_text)
        
    def log_message(self, message, level="info"):
        """Add a message to the log
        
        Args:
            message (str): The message to log
            level (str): The message level (info, success, warning, error)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        color_map = {
            "info": Styles.COLORS['foreground'],
            "success": Styles.COLORS['success'],
            "warning": Styles.COLORS['warning'],
            "error": Styles.COLORS['error']
        }
        
        color = color_map.get(level, Styles.COLORS['foreground'])
        formatted_message = f'<span style="color: {color}">[{timestamp}] {message}</span><br>'
        
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
        self.log_text.insertHtml(formatted_message)
        self.log_text.ensureCursorVisible()

class RealTimePlots(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Set up dark theme for plots
        pg.setConfigOption('background', Styles.COLORS['background'])
        pg.setConfigOption('foreground', Styles.COLORS['foreground'])
        
        # Create plot widgets
        self.tilt_plot = pg.PlotWidget(title="Tilt vs Time")
        self.tilt_plot.setLabel('left', 'Tilt Angle', units='degrees')
        self.tilt_plot.setLabel('bottom', 'Time', units='s')
        self.tilt_plot.showGrid(x=True, y=True)
        
        self.temp_plot = pg.PlotWidget(title="Temperature vs Time")
        self.temp_plot.setLabel('left', 'Temperature', units='°C')
        self.temp_plot.setLabel('bottom', 'Time', units='s')
        self.temp_plot.showGrid(x=True, y=True)
        
        # Create plot curves with specified colors
        self.tilt_curve = self.tilt_plot.plot(pen=pg.mkPen(color='#ff073a', width=2))  # Red for tilt
        self.temp_curve = self.temp_plot.plot(pen=pg.mkPen(color='#0FFF50', width=2))  # Green for temperature
        
        # Create vertical splitter for plots with snapping behavior
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setStyleSheet(Styles.DIVIDER_STYLE)
        splitter.addWidget(self.tilt_plot)
        splitter.addWidget(self.temp_plot)
        
        # Set initial sizes (50% each)
        splitter.setSizes([500, 500])
        
        # Enable snap-to-edge behavior
        splitter.splitterMoved.connect(self.handle_splitter_moved)
        
        layout.addWidget(splitter)
        
        # Initialize data
        self.time_data = []
        self.tilt_data = []
        self.temp_data = []
        
        # Set Ubuntu Bold font for all text
        font = QFont("Ubuntu")
        font.setWeight(QFont.Weight.Bold)
        self.tilt_plot.getAxis('bottom').setStyle(tickFont=font)
        self.tilt_plot.getAxis('left').setStyle(tickFont=font)
        self.temp_plot.getAxis('bottom').setStyle(tickFont=font)
        self.temp_plot.getAxis('left').setStyle(tickFont=font)
        
        # Set title fonts
        title_font = QFont("Ubuntu")
        title_font.setWeight(QFont.Weight.Bold)
        title_font.setPointSize(12)
        self.tilt_plot.setTitle("Tilt vs Time", size="12pt")
        self.temp_plot.setTitle("Temperature vs Time", size="12pt")
        
    def handle_splitter_moved(self, pos, index):
        """Handle splitter movement for snap-to-edge behavior"""
        splitter = self.sender()
        total_height = splitter.height()
        
        # Get current sizes
        sizes = splitter.sizes()
        
        # Check if any handle is close to edges
        snap_threshold = 50  # pixels
        
        # Top panel
        if sizes[0] < snap_threshold:
            sizes[0] = 0
            sizes[1] = total_height
        # Bottom panel
        elif sizes[1] < snap_threshold:
            sizes[0] = total_height
            sizes[1] = 0
        
        splitter.setSizes(sizes)
        
    def update_plots(self, time_point, tilt_angle, temperature):
        """Update the plots with new data
        
        Args:
            time_point (float): Time point in seconds
            tilt_angle (float): Current tilt angle in degrees
            temperature (float): Current temperature in degrees Celsius
        """
        self.time_data.append(time_point)
        self.tilt_data.append(tilt_angle)
        self.temp_data.append(temperature)
        
        self.tilt_curve.setData(self.time_data, self.tilt_data)
        self.temp_curve.setData(self.time_data, self.temp_data)
        
    def clear_plots(self):
        """Clear all plot data"""
        self.time_data = []
        self.tilt_data = []
        self.temp_data = []
        self.tilt_curve.setData([], [])
        self.temp_curve.setData([], [])