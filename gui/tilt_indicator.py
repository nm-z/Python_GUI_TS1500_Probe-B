from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer
import pyqtgraph as pg
import numpy as np
from .styles import Styles as StylesModule

class TiltIndicator(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tilt Indicator")
        self.setModal(False)  # Allow interaction with main window
        self.resize(400, 400)
        self.init_ui()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(StylesModule.MARGINS, StylesModule.MARGINS, 
                                StylesModule.MARGINS, StylesModule.MARGINS)
        layout.setSpacing(StylesModule.SPACING)

        # Set up dark theme for plot
        pg.setConfigOption('background', StylesModule.COLORS['background'])
        pg.setConfigOption('foreground', StylesModule.COLORS['foreground'])

        # Create 3D plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setAspectLocked(True)
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setLabel('left', 'Y Tilt', units='degrees')
        self.plot_widget.setLabel('bottom', 'X Tilt', units='degrees')

        # Create scatter plot item for the tilt indicator
        self.scatter = pg.ScatterPlotItem(
            size=20, 
            brush=pg.mkBrush(StylesModule.COLORS['accent']),
            pen=pg.mkPen(None)
        )
        self.plot_widget.addItem(self.scatter)

        # Add reference circle
        circle = self.create_reference_circle()
        self.plot_widget.addItem(circle)

        # Set plot ranges
        self.plot_widget.setXRange(-10, 10)
        self.plot_widget.setYRange(-10, 10)
        
        layout.addWidget(self.plot_widget)

        # Add labels for tilt angles
        angles_layout = QHBoxLayout()
        
        # X angle
        x_layout = QVBoxLayout()
        x_layout.addWidget(QLabel("X Angle:"))
        self.x_angle_label = QLabel("0.0°")
        self.x_angle_label.setFont(StylesModule.HEADER_FONT)
        x_layout.addWidget(self.x_angle_label)
        angles_layout.addLayout(x_layout)
        
        # Y angle
        y_layout = QVBoxLayout()
        y_layout.addWidget(QLabel("Y Angle:"))
        self.y_angle_label = QLabel("0.0°")
        self.y_angle_label.setFont(StylesModule.HEADER_FONT)
        y_layout.addWidget(self.y_angle_label)
        angles_layout.addLayout(y_layout)
        
        layout.addLayout(angles_layout)

        # Current angles
        self.current_x = 0.0
        self.current_y = 0.0

        # Set up update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_plot)
        self.update_timer.start(100)  # Update every 100ms

    def create_reference_circle(self):
        """Create a reference circle for the tilt indicator"""
        theta = np.linspace(0, 2*np.pi, 100)
        radius = 5  # 5 degrees radius
        x = radius * np.cos(theta)
        y = radius * np.sin(theta)
        return pg.PlotCurveItem(
            x, y, 
            pen=pg.mkPen(StylesModule.COLORS['foreground'], width=1, style=Qt.DashLine)
        )

    def update_plot(self):
        """Update the plot with current tilt values"""
        self.scatter.setData([self.current_x], [self.current_y])
        self.x_angle_label.setText(f"{self.current_x:.1f}°")
        self.y_angle_label.setText(f"{self.current_y:.1f}°")

    def set_tilt(self, x_angle, y_angle):
        """Set the current tilt angles"""
        self.current_x = x_angle
        self.current_y = y_angle

    def closeEvent(self, event):
        """Handle window close event"""
        self.update_timer.stop()
        super().closeEvent(event) 