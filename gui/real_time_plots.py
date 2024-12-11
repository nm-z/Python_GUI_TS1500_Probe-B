from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QSplitter
from PyQt6.QtCore import Qt
import pyqtgraph as pg
from .styles import Styles

class RealTimePlots(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Initialize the real-time plots UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Styles.MARGINS, Styles.MARGINS, 
                                Styles.MARGINS, Styles.MARGINS)
        layout.setSpacing(Styles.SPACING)

        # Set up dark theme for plots
        pg.setConfigOption('background', Styles.COLORS['background'])
        pg.setConfigOption('foreground', Styles.COLORS['foreground'])

        # Create plot widgets
        self.tilt_plot = pg.PlotWidget(title="Tilt vs. Time")
        self.tilt_plot.setLabel('left', 'Angle', units='degrees')
        self.tilt_plot.setLabel('bottom', 'Time', units='s')
        self.tilt_plot.showGrid(x=True, y=True, alpha=0.3)
        
        self.temp_plot = pg.PlotWidget(title="Temperature vs. Time")
        self.temp_plot.setLabel('left', 'Temperature', units='°C')
        self.temp_plot.setLabel('bottom', 'Time', units='s')
        self.temp_plot.showGrid(x=True, y=True, alpha=0.3)

        # Style plots
        for plot in [self.tilt_plot, self.temp_plot]:
            plot.getAxis('bottom').setPen(Styles.COLORS['foreground'])
            plot.getAxis('left').setPen(Styles.COLORS['foreground'])
            plot.getAxis('bottom').setTextPen(Styles.COLORS['foreground'])
            plot.getAxis('left').setTextPen(Styles.COLORS['foreground'])
            plot.setTitle(title=plot.windowTitle(), color=Styles.COLORS['foreground'])

        # Create plot curves with specified colors
        self.tilt_curve = self.tilt_plot.plot(pen=pg.mkPen(color='#ff073a', width=2))
        self.temp_curve = self.temp_plot.plot(pen=pg.mkPen(color='#0FFF50', width=2))

        # Initialize data
        self.time_data = []
        self.tilt_data = []
        self.temp_data = []

        # Create a splitter and add plots to it
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.tilt_plot)
        splitter.addWidget(self.temp_plot)
        
        # Set initial sizes (50% each)
        splitter.setSizes([500, 500])

        # Add splitter to layout
        layout.addWidget(splitter)

    def update_data(self, data):
        """Update plot data
        
        Args:
            data (dict): Dictionary containing time_point, tilt_angle, and temperature
        """
        try:
            print(f"[DEBUG] Updating plot data: {data}")
            
            if 'time_point' in data and 'tilt_angle' in data and 'temperature' in data:
                # Append new data
                self.time_data.append(data['time_point'])
                self.tilt_data.append(data['tilt_angle'])
                self.temp_data.append(data['temperature'])

                # Update plots
                self.tilt_curve.setData(self.time_data, self.tilt_data)
                self.temp_curve.setData(self.time_data, self.temp_data)
                
                print(f"[DEBUG] Plot data updated - Points: {len(self.time_data)}")
            else:
                print(f"[WARNING] Invalid plot data format: {data}")
                
        except Exception as e:
            import traceback
            print(f"[ERROR] Plot update error: {str(e)}")
            print("[ERROR] Traceback:")
            print(traceback.format_exc())

    def clear_data(self):
        """Clear all plot data"""
        try:
            print("[DEBUG] Clearing plot data")
            self.time_data = []
            self.tilt_data = []
            self.temp_data = []
            self.tilt_curve.setData([], [])
            self.temp_curve.setData([], [])
            print("[DEBUG] Plot data cleared")
            
        except Exception as e:
            import traceback
            print(f"[ERROR] Plot clear error: {str(e)}")
            print("[ERROR] Traceback:")
            print(traceback.format_exc())
            
    def resizeEvent(self, event):
        """Handle plot resize events"""
        try:
            super().resizeEvent(event)
            print(f"[DEBUG] Plots resized to {self.width()}x{self.height()}")
            
            # Update plot layouts
            for plot in [self.tilt_plot, self.temp_plot]:
                plot.getViewBox().updateAutoRange()
                
        except Exception as e:
            import traceback
            print(f"[ERROR] Plot resize error: {str(e)}")
            print("[ERROR] Traceback:")
            print(traceback.format_exc())
