from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from utils.logger import gui_logger

class PlotsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Results")
        self.resize(800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Set dark theme by default
        self.dark_mode = True
        
        # Create figure with dark theme
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # Create tilt angle subplot
        self.tilt_ax = self.figure.add_subplot(211)
        self.tilt_ax.set_title("Tilt Angle vs Time")
        self.tilt_ax.set_xlabel("Time (s)")
        self.tilt_ax.set_ylabel("Angle (degrees)")
        self.tilt_ax.grid(True)
        
        # Create temperature subplot
        self.temp_ax = self.figure.add_subplot(212)
        self.temp_ax.set_title("Temperature vs Time")
        self.temp_ax.set_xlabel("Time (s)")
        self.temp_ax.set_ylabel("Temperature (°C)")
        self.temp_ax.grid(True)
        
        # Add recenter button
        self.recenter_button = QPushButton("Recenter Plots")
        self.recenter_button.clicked.connect(self.recenter_plots)
        layout.addWidget(self.recenter_button)
        
        # Initialize data arrays
        self.time_points = []
        self.tilt_angles = []
        self.temperatures = []
        
        # Create plot lines with theme-appropriate colors
        self.tilt_line, = self.tilt_ax.plot([], [], '#FF073A', label='Tilt Angle', linewidth=2)
        self.temp_line, = self.temp_ax.plot([], [], '#0FFF50', label='Temperature', linewidth=2)
        
        # Add legends
        self.tilt_ax.legend()
        self.temp_ax.legend()
        
        # Apply dark theme
        self.update_theme(True)
        
        # Adjust layout
        self.figure.tight_layout()
        
    def update_tilt(self, time_point, angle):
        """Update tilt angle plot
        
        Args:
            time_point (float): Time point in seconds
            angle (float): Tilt angle in degrees
        """
        try:
            # Append new data point
            self.time_points.append(time_point)
            self.tilt_angles.append(angle)
            
            # Update plot data
            self.tilt_line.set_data(self.time_points, self.tilt_angles)
            
            # Adjust plot limits if needed
            self._adjust_plot_limits(self.tilt_ax, self.time_points, self.tilt_angles)
            
            # Update title with current value
            self.tilt_ax.set_title(f"Tilt Angle vs Time (Current: {angle:.1f}°)")
            
            # Redraw canvas
            self.canvas.draw()
            
        except Exception as e:
            gui_logger.error(f"Error updating tilt plot: {str(e)}")
            
    def update_temperature(self, time_point, temperature):
        """Update temperature plot
        
        Args:
            time_point (float): Time point in seconds
            temperature (float): Temperature in Celsius
        """
        try:
            # Append new data point
            if time_point not in self.time_points:
                self.time_points.append(time_point)
            self.temperatures.append(temperature)
            
            # Update plot data
            self.temp_line.set_data(self.time_points, self.temperatures)
            
            # Adjust plot limits if needed
            self._adjust_plot_limits(self.temp_ax, self.time_points, self.temperatures)
            
            # Update title with current value
            self.temp_ax.set_title(f"Temperature vs Time (Current: {temperature:.1f}°C)")
            
            # Redraw canvas
            self.canvas.draw()
            
        except Exception as e:
            gui_logger.error(f"Error updating temperature plot: {str(e)}")
            
    def _adjust_plot_limits(self, ax, x_data, y_data):
        """Adjust plot limits to show all data with padding
        
        Args:
            ax (Axes): Matplotlib axes to adjust
            x_data (list): X-axis data points
            y_data (list): Y-axis data points
        """
        if not x_data or not y_data:
            return
            
        # Calculate limits with 10% padding
        x_min, x_max = min(x_data), max(x_data)
        y_min, y_max = min(y_data), max(y_data)
        
        x_range = max(x_max - x_min, 1)  # Avoid zero range
        y_range = max(y_max - y_min, 1)  # Avoid zero range
        
        x_padding = x_range * 0.1
        y_padding = y_range * 0.1
        
        # Set new limits
        ax.set_xlim(x_min - x_padding, x_max + x_padding)
        ax.set_ylim(y_min - y_padding, y_max + y_padding)
        
        # Update grid
        ax.grid(True, linestyle='--', alpha=0.5)
        
    def clear_plots(self):
        """Clear all plot data"""
        self.time_points = []
        self.tilt_angles = []
        self.temperatures = []
        
        # Clear plot lines
        self.tilt_line.set_data([], [])
        self.temp_line.set_data([], [])
        
        # Reset titles
        self.tilt_ax.set_title("Tilt Angle vs Time")
        self.temp_ax.set_title("Temperature vs Time")
        
        # Reset plot limits
        self.tilt_ax.relim()
        self.tilt_ax.autoscale()
        self.temp_ax.relim()
        self.temp_ax.autoscale()
        
        # Redraw canvas
        self.canvas.draw()
        
    def recenter_plots(self):
        """Recenter both plots"""
        try:
            # Recenter tilt plot
            if self.tilt_angles:
                self._adjust_plot_limits(self.tilt_ax, self.time_points, self.tilt_angles)
                
            # Recenter temperature plot
            if self.temperatures:
                self._adjust_plot_limits(self.temp_ax, self.time_points, self.temperatures)
                
            # Redraw canvas
            self.canvas.draw()
            
        except Exception as e:
            gui_logger.error(f"Error recentering plots: {str(e)}")
            
    def update_theme(self, is_dark_mode=True):
        """Update plot theme
        
        Args:
            is_dark_mode (bool): Whether to use dark mode
        """
        try:
            self.dark_mode = is_dark_mode
            
            if is_dark_mode:
                bg_color = '#121212'
                text_color = 'white'
                grid_color = '#404040'
            else:
                bg_color = 'white'
                text_color = 'black'
                grid_color = '#E0E0E0'
            
            # Update figure and axes colors
            self.figure.patch.set_facecolor(bg_color)
            
            for ax in [self.tilt_ax, self.temp_ax]:
                ax.set_facecolor(bg_color)
                ax.tick_params(colors=text_color)
                ax.xaxis.label.set_color(text_color)
                ax.yaxis.label.set_color(text_color)
                ax.title.set_color(text_color)
                ax.grid(True, color=grid_color, linestyle='--', alpha=0.5)
                
                # Update spine colors
                for spine in ax.spines.values():
                    spine.set_color(text_color)
                    
                # Update legend colors
                if ax.get_legend():
                    for text in ax.get_legend().get_texts():
                        text.set_color(text_color)
            
            # Update button style
            button_style = """
                QPushButton {
                    background-color: #2F3438;
                    color: white;
                    border: 1px solid #47A8E5;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #3F444A;
                }
                QPushButton:pressed {
                    background-color: #1F2428;
                }
            """ if is_dark_mode else """
                QPushButton {
                    background-color: white;
                    color: black;
                    border: 1px solid #47A8E5;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #F0F0F0;
                }
                QPushButton:pressed {
                    background-color: #E0E0E0;
                }
            """
            self.recenter_button.setStyleSheet(button_style)
            
            # Set window background
            self.setStyleSheet(f"background-color: {bg_color};")
            
            # Redraw canvas
            self.canvas.draw()
            
        except Exception as e:
            gui_logger.error(f"Error updating plot theme: {str(e)}")
            
    def closeEvent(self, event):
        """Handle window close event"""
        try:
            # Clear plot data
            self.clear_plots()
            
            # Accept the close event
            event.accept()
            
        except Exception as e:
            gui_logger.error(f"Error closing plots window: {str(e)}")
            event.accept()
        
    def showEvent(self, event):
        """Handle window show event"""
        super().showEvent(event)
        # Ensure theme is applied when window is shown
        self.update_theme(self.dark_mode)