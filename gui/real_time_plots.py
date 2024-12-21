from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
import pyqtgraph as pg
from .styles import Styles

class RealTimePlots(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the plots UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Set up dark theme for plots
        pg.setConfigOption('background', Styles.DARK_BG)
        pg.setConfigOption('foreground', 'w')
        
        # Create tilt plot
        self.tilt_plot = pg.PlotWidget()
        self.setup_plot(self.tilt_plot, "Tilt vs Time", "Tilt (degrees)", "Time (s)")
        
        # Add recenter button for tilt plot
        tilt_layout = QHBoxLayout()
        tilt_layout.addWidget(self.tilt_plot)
        tilt_recenter_btn = QPushButton("Recenter")
        tilt_recenter_btn.setStyleSheet(Styles.BUTTON_STYLE)
        tilt_recenter_btn.clicked.connect(lambda: self.recenter_plot(self.tilt_plot))
        tilt_recenter_btn.setMaximumWidth(100)
        tilt_layout.addWidget(tilt_recenter_btn, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        layout.addLayout(tilt_layout)
        
        # Create temperature plot
        self.temp_plot = pg.PlotWidget()
        self.setup_plot(self.temp_plot, "Temperature vs Time", "Temperature (°C)", "Time (s)")
        
        # Add recenter button for temperature plot
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(self.temp_plot)
        temp_recenter_btn = QPushButton("Recenter")
        temp_recenter_btn.setStyleSheet(Styles.BUTTON_STYLE)
        temp_recenter_btn.clicked.connect(lambda: self.recenter_plot(self.temp_plot))
        temp_recenter_btn.setMaximumWidth(100)
        temp_layout.addWidget(temp_recenter_btn, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        layout.addLayout(temp_layout)
        
        # Initialize plot data
        self.tilt_data = {'x': [], 'y': []}
        self.temp_data = {'x': [], 'y': []}
        
        # Create plot curves with specified colors
        self.tilt_curve = self.tilt_plot.plot(pen=pg.mkPen(color=Styles.TILT_LINE_COLOR, width=2))
        self.temp_curve = self.temp_plot.plot(pen=pg.mkPen(color=Styles.TEMP_LINE_COLOR, width=2))
        
    def setup_plot(self, plot, title, y_label, x_label):
        """Set up common plot properties"""
        plot.setTitle(title, color='w', size='12pt')
        plot.setLabel('left', y_label, color='w')
        plot.setLabel('bottom', x_label, color='w')
        plot.showGrid(x=True, y=True, alpha=0.3)
        
        # Style axis
        plot.getAxis('bottom').setPen('w')
        plot.getAxis('left').setPen('w')
        plot.getAxis('bottom').setTextPen('w')
        plot.getAxis('left').setTextPen('w')
        
    def update_tilt(self, angle):
        """Update tilt plot with new data
        
        Args:
            angle (float): Current tilt angle in degrees
        """
        # Calculate time since start if no time data exists
        if not self.tilt_data['x']:
            time = 0
        else:
            time = self.tilt_data['x'][-1] + 0.1  # Assume 100ms between updates
            
        self.tilt_data['x'].append(time)
        self.tilt_data['y'].append(angle)
        self.tilt_curve.setData(self.tilt_data['x'], self.tilt_data['y'])
        
    def update_temperature(self, time, temp):
        """Update temperature plot with new data"""
        self.temp_data['x'].append(time)
        self.temp_data['y'].append(temp)
        self.temp_curve.setData(self.temp_data['x'], self.temp_data['y'])
        
    def clear_data(self):
        """Clear all plot data"""
        self.tilt_data = {'x': [], 'y': []}
        self.temp_data = {'x': [], 'y': []}
        self.tilt_curve.setData([], [])
        self.temp_curve.setData([], [])
        
    def recenter_plot(self, plot_widget):
        """Recenter the plot to (0,0)"""
        plot_widget.setRange(xRange=[0, 0], yRange=[0, 0], padding=0.1)
        
    def update_theme(self, is_dark_mode):
        """Update plot colors based on theme"""
        background_color = Styles.DARK_BG if is_dark_mode else 'w'
        text_color = 'w' if is_dark_mode else 'k'
        grid_alpha = 0.3 if is_dark_mode else 0.2
        
        # Update plot configurations
        pg.setConfigOption('background', background_color)
        pg.setConfigOption('foreground', text_color)
        
        # Update both plots
        for plot in [self.tilt_plot, self.temp_plot]:
            plot.getAxis('bottom').setPen(text_color)
            plot.getAxis('left').setPen(text_color)
            plot.getAxis('bottom').setTextPen(text_color)
            plot.getAxis('left').setTextPen(text_color)
            plot.getPlotItem().titleLabel.setAttr('color', text_color)
            plot.showGrid(x=True, y=True, alpha=grid_alpha)
