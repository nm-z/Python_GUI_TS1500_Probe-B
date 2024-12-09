from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QSplitter
from PyQt6.QtCore import Qt
import pyqtgraph as pg
from .styles import Styles as StylesModule

class RealTimePlots(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Initialize the real-time plots UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(StylesModule.MARGINS, StylesModule.MARGINS, 
                                StylesModule.MARGINS, StylesModule.MARGINS)
        layout.setSpacing(StylesModule.SPACING)

        # Set up dark theme for plots
        pg.setConfigOption('background', StylesModule.COLORS['background'])
        pg.setConfigOption('foreground', StylesModule.COLORS['foreground'])

        # Create plot widgets
        self.tilt_plot = pg.PlotWidget(title="Tilt Angle")
        self.tilt_plot.setLabel('left', 'Angle', units='degrees')
        self.tilt_plot.setLabel('bottom', 'Time', units='s')
        self.tilt_plot.showGrid(x=True, y=True, alpha=0.3)
        
        self.fill_plot = pg.PlotWidget(title="Fill Level")
        self.fill_plot.setLabel('left', 'Level', units='%')
        self.fill_plot.setLabel('bottom', 'Time', units='s')
        self.fill_plot.showGrid(x=True, y=True, alpha=0.3)

        # Style plots
        for plot in [self.tilt_plot, self.fill_plot]:
            plot.getAxis('bottom').setPen(StylesModule.COLORS['foreground'])
            plot.getAxis('left').setPen(StylesModule.COLORS['foreground'])
            plot.getAxis('bottom').setTextPen(StylesModule.COLORS['foreground'])
            plot.getAxis('left').setTextPen(StylesModule.COLORS['foreground'])
            plot.setTitle(title=plot.windowTitle(), color=StylesModule.COLORS['foreground'])

        # Create plot curves
        self.tilt_curve = self.tilt_plot.plot(pen=pg.mkPen(color=StylesModule.COLORS['accent'], width=2))
        self.fill_curve = self.fill_plot.plot(pen=pg.mkPen(color=StylesModule.COLORS['accent'], width=2))

        # Initialize data
        self.time_data = []
        self.tilt_data = []
        self.fill_data = []

        # Create a splitter and add plots to it
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.tilt_plot)
        splitter.addWidget(self.fill_plot)
        
        # Set initial sizes (50% each)
        splitter.setSizes([500, 500])

        # Add splitter to layout
        layout.addWidget(splitter)

    def update_data(self, time_point, tilt_angle, fill_level):
        """Update plot data"""
        # Append new data
        self.time_data.append(time_point)
        self.tilt_data.append(tilt_angle)
        self.fill_data.append(fill_level)

        # Update plots
        self.tilt_curve.setData(self.time_data, self.tilt_data)
        self.fill_curve.setData(self.time_data, self.fill_data)

    def clear_data(self):
        """Clear all plot data"""
        self.time_data = []
        self.tilt_data = []
        self.fill_data = []
        self.tilt_curve.setData([], [])
        self.fill_curve.setData([], [])
