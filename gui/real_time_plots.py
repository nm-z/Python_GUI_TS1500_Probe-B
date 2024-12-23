from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
import pyqtgraph as pg
from .styles import Styles

class RealTimePlots(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout(self)
        
        # Create plots
        self.tilt_plot = pg.PlotWidget()
        self.temp_plot = pg.PlotWidget()
        
        # Set dark theme
        pg.setConfigOption('background', Styles.COLORS['background'])
        pg.setConfigOption('foreground', Styles.COLORS['foreground'])
        
        # Configure tilt plot
        self.tilt_plot.setTitle("Tilt Angle vs Time")
        self.tilt_plot.setLabel('left', 'Tilt Angle', units='degrees')
        self.tilt_plot.setLabel('bottom', 'Time', units='s')
        self.tilt_plot.showGrid(x=True, y=True)
        
        # Configure temperature plot
        self.temp_plot.setTitle("Temperature vs Time")
        self.temp_plot.setLabel('left', 'Temperature', units='°C')
        self.temp_plot.setLabel('bottom', 'Time', units='s')
        self.temp_plot.showGrid(x=True, y=True)
        
        # Add plots to layout
        layout.addWidget(self.tilt_plot)
        
        # Add temperature plot with recenter button
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(self.temp_plot)
        
        temp_recenter_btn = QPushButton("Recenter")
        temp_recenter_btn.clicked.connect(self.recenter_temp_plot)
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
        
    def update_tilt(self, time, angle):
        """Update tilt plot with new data"""
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
