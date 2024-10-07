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
import os
import subprocess
import pyperclip

# Configuration
ENABLE_WEB_SERVER = True

app = Flask(__name__)

# Mock mpu6050 for testing
class MockMPU6050:
    def get_accel_data(self):
        return {'x': 0.0, 'y': 0.0, 'z': 0.0}
    def get_gyro_data(self):
        return {'x': 0.0, 'y': 0.0, 'z': 0.0}

mpu6050 = MockMPU6050

# Mock Temper for testing
class MockTemper:
    def __init__(self, port):
        self.port = port

    def get_temperature(self):
        return 25.0  # Return a mock temperature

temper = MockTemper

class EnhancedAutoDataLoggerGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Enhanced Automated Data Logger")
        self.master.geometry("1000x700")  # Adjusted initial size
        
        # Set dark mode color scheme
        self.master.configure(background='#1c1c1c')
        ttk.Style().configure('TFrame', background='#1c1c1c')
        ttk.Style().configure('TLabelframe', background='#1c1c1c', foreground='white')
        ttk.Style().configure('TLabelframe.Label', background='#1c1c1c', foreground='white')
        ttk.Style().configure('TLabel', background='#1c1c1c', foreground='white')
        ttk.Style().configure('TButton', background='#4c4c4c', foreground='white')
        ttk.Style().configure('TEntry', fieldbackground='#4c4c4c', foreground='white')
        ttk.Style().configure('TCombobox', fieldbackground='#4c4c4c', foreground='white')
        ttk.Style().configure('TNotebook', background='#1c1c1c')
        ttk.Style().configure('TNotebook.Tab', background='#4c4c4c', foreground='white')
        ttk.Style().configure('TRadiobutton', background='#1c1c1c', foreground='white')
        
        self.create_logger()
        self.create_widgets()
        self.data = []
        self.is_logging = False
        self.web_port_enabled = False
        self.vna_connected = False
        self.temp_sensor_connected = False
        
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)  # Handle window close event
    
    def create_widgets(self):
        # Create tabs
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Logging Controls tab
        logging_tab = ttk.Frame(self.notebook)
        self.notebook.add(logging_tab, text="Logging Controls")
        
        # Data tab
        data_tab = ttk.Frame(self.notebook)
        self.notebook.add(data_tab, text="Data")
        
        # Device Connections tab
        device_tab = ttk.Frame(self.notebook)
        self.notebook.add(device_tab, text="Device Connections")
        
        # Logging Controls frame
        logging_frame = ttk.LabelFrame(logging_tab, text="Logging Controls")
        logging_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Frequency input
        ttk.Label(logging_frame, text="Measurement Frequency (seconds):").grid(row=0, column=0, sticky="w")
        self.freq_entry = ttk.Entry(logging_frame, width=10)
        self.freq_entry.insert(0, "1")
        self.freq_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Start/Stop button
        self.log_button = ttk.Button(logging_frame, text="Start Logging", command=self.toggle_logging)
        self.log_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        # Add Tilt Sensor toggle button
        self.tilt_sensor_button = ttk.Button(logging_frame, text="Disable Tilt Sensor", command=self.toggle_tilt_sensor)
        self.tilt_sensor_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5)
        
        # Data frame
        data_frame = ttk.Frame(data_tab)
        data_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Accelerometer data display
        accel_frame = ttk.LabelFrame(data_frame, text="Accelerometer Data")
        accel_frame.pack(padx=10, pady=10)

        self.accel_display = ttk.Label(accel_frame, text="N/A")
        self.accel_display.pack()

        # Create figure and subplots
        self.fig = plt.figure(figsize=(12, 6))
        self.ax1 = self.fig.add_subplot(121)  # Temperature graph on the left
        self.ax_orientation = self.fig.add_subplot(122, projection='3d')  # 3D angle visualization on the right

        # Set dark mode colors for the plots
        self.fig.patch.set_facecolor('#1c1c1c')
        self.ax1.set_facecolor('#4c4c4c')
        self.ax_orientation.set_facecolor('#4c4c4c')
        self.ax1.xaxis.label.set_color('white')
        self.ax1.yaxis.label.set_color('white')
        self.ax1.tick_params(axis='x', colors='white')
        self.ax1.tick_params(axis='y', colors='white')
        
        # Set up 3D plot
        self.ax_orientation.set_xlim(-1, 1)
        self.ax_orientation.set_ylim(-1, 1)
        self.ax_orientation.set_zlim(-1, 1)
        self.ax_orientation.set_xticklabels([])
        self.ax_orientation.set_yticklabels([])
        self.ax_orientation.set_zticklabels([])
        self.ax_orientation.grid(False)
        self.ax_orientation.xaxis.line.set_color('red')
        self.ax_orientation.yaxis.line.set_color('green')
        self.ax_orientation.zaxis.line.set_color('blue')
        self.ax_orientation.set_xlabel('X', color='red')
        self.ax_orientation.set_ylabel('Y', color='green')
        self.ax_orientation.set_zlabel('Z', color='blue')
        self.ax_orientation.xaxis.pane.fill = False
        self.ax_orientation.yaxis.pane.fill = False
        self.ax_orientation.zaxis.pane.fill = False
        self.ax_orientation.xaxis.pane.set_edgecolor('none')
        self.ax_orientation.yaxis.pane.set_edgecolor('none')
        self.ax_orientation.zaxis.pane.set_edgecolor('none')

        # Disable mouse interaction
        self.ax_orientation.mouse_init(rotate_btn=None, zoom_btn=None)

        # Set initial view
        self.ax_orientation.view_init(elev=30, azim=45)

        # Create canvas for displaying the graphs
        self.canvas_orientation = FigureCanvasTkAgg(self.fig, master=data_frame)
        self.canvas_orientation.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Device Connections frame
        device_frame = ttk.LabelFrame(device_tab, text="Device Connections")
        device_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        ttk.Label(device_frame, text="VNA Port:").grid(row=0, column=0, sticky="w", pady=5)
        self.vna_port = ttk.Combobox(device_frame, values=self.get_usb_ports(), state="readonly", width=15)
        self.vna_port.grid(row=0, column=1, pady=5)
        self.vna_port.bind("<<ComboboxSelected>>", self.on_vna_port_selected)
        self.vna_status_label = ttk.Label(device_frame, text="Disconnected", foreground="red")
        self.vna_status_label.grid(row=0, column=2, padx=5)
        
        ttk.Label(device_frame, text="Temperature Sensor Port:").grid(row=1, column=0, sticky="w", pady=5)
        self.temp_port = ttk.Combobox(device_frame, values=self.get_usb_ports(), state="readonly", width=15)
        self.temp_port.grid(row=1, column=1, pady=5)
        self.temp_port.bind("<<ComboboxSelected>>", self.on_temp_port_selected)
        self.temp_status_label = ttk.Label(device_frame, text="Disconnected", foreground="red")
        self.temp_status_label.grid(row=1, column=2, padx=5)
        
        # Export to CSV button
        ttk.Button(device_frame, text="Export to CSV", command=self.save_to_csv).grid(row=2, column=0, columnspan=2, padx=5, pady=5)
        
        # File name entry
        ttk.Label(device_frame, text="File Name:").grid(row=3, column=0, sticky="w")
        self.file_name = ttk.Entry(device_frame, width=20)
        self.file_name.insert(0, "data.csv")
        self.file_name.grid(row=3, column=1, padx=5, pady=5)
        
        # Web Port toggle button
        self.web_button = ttk.Button(device_frame, text="Enable Web Port", command=self.toggle_web_port)
        self.web_button.grid(row=4, column=0, columnspan=2, padx=5, pady=5)
    
    def get_usb_ports(self):
        ports = [port.device for port in comports()]
        temper_device = usb.core.find(idVendor=0x413d, idProduct=0x2107)
        if temper_device:
            ports.append("TEMPer1F")
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
                temp = self.read_temperature()
                vna_data = self.read_vna()
                accel_data = self.read_accelerometer()
                level_data = self.read_digital_level()

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                entry = [timestamp, self.vna_data, accel_data, level_data]
                self.data.append(entry)

                self.update_display(temp, vna_data, accel_data, level_data)
                self.update_graph(temp)

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

    def read_temperature(self):
        try:
            # Send a command to request temperature
            self.temp_device.ctrl_transfer(bmRequestType=0x21, bRequest=0x09, 
                                           wValue=0x0200, wIndex=0x01, data_or_wLength=[0x01,0x80,0x33,0x01,0x00,0x00,0x00,0x00])
            
            # Read the temperature data
            data = self.temp_endpoint.read(8)
            
            # Convert the raw data to temperature in Celsius
            temp = (data[3] & 0xFF) + (data[2] & 0xFF) * 256
            temp = temp * 125.0 / 32000.0
            return temp
        except Exception as e:
            print(f"Error reading temperature: {e}")
            return None

    def read_accelerometer(self):
        return self.mpu.get_accel_data()['x']

    def read_digital_level(self):
        return self.mpu.get_gyro_data()['x']

    def update_display(self, vna_data, accel_data, level_data):
        if accel_data is not None:
            ax, ay, az, gx, gy, gz = accel_data
            self.accel_display.config(text=f"Accel: X={ax}, Y={ay}, Z={az} | Gyro: X={gx}, Y={gy}, Z={gz}")
        else:
            self.accel_display.config(text="Accel: N/A | Gyro: N/A")

    def update_graphs(self):
        self.ax1.clear()

        timestamps = [entry[0] for entry in self.data[-50:]]  # Last 50 entries
        temps = [entry[1] for entry in self.data[-50:]]

        self.ax1.plot(timestamps, temps)
        self.ax1.set_ylabel('Temperature (°C)')
        self.ax1.set_title('Temperature Over Time')
        self.ax1.tick_params(axis='x', rotation=45)

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
        self.is_logging = False  # Stop logging if active
        if self.arduino:
            self.arduino.close()
        self.master.destroy()
        self.master.quit()
        app.do_teardown_appcontext()
        exit()

    def on_vna_port_selected(self, event):
        selected_port = self.vna_port.get()
        print(f"Selected VNA Port: {selected_port}")
        self.setup_vna(selected_port)

    def on_temp_port_selected(self, event):
        selected_port = self.temp_port.get()
        print(f"Selected Temperature Sensor: {selected_port}")
        if selected_port == "TEMPer1F":
            self.setup_temp_sensor(None)  # We don't need a port for USB device
        else:
            messagebox.showerror("Connection Error", "Please select the TEMPer1F device")

    def check_and_request_permissions(self, port):
        if not os.access(port, os.R_OK | os.W_OK):
            try:
                group = "dialout"  # This is typically the group for serial ports
                subprocess.run(["sudo", "usermod", "-a", "-G", group, os.getlogin()], check=True)
                subprocess.run(["sudo", "chmod", "a+rw", port], check=True)
                print(f"Permissions granted for {port}")
                # The user needs to log out and log back in for group changes to take effect
                messagebox.showinfo("Permissions Updated", 
                                    "Permissions have been updated. Please log out and log back in for changes to take effect.")
                return True
            except subprocess.CalledProcessError as e:
                print(f"Failed to set permissions: {e}")
                messagebox.showerror("Permission Error", 
                                     f"Failed to set permissions for {port}. Try running the script with sudo.")
                return False
        return True

    def setup_vna(self, port):
        if self.check_and_request_permissions(port):
            try:
                self.vna = serial.Serial(port, 115200)
                print(f"Connected to VNA on port: {port}")
                self.vna_connected = True
                self.vna_status_label.config(text="Connected", foreground="green")
            except Exception as e:
                print(f"Error connecting to VNA: {e}")
                messagebox.showerror("Connection Error", f"Error connecting to VNA: {e}")
                self.vna_connected = False
                self.vna_status_label.config(text="Disconnected", foreground="red")

    def setup_temp_sensor(self, port):
        try:
            # Find the TEMPer1F device
            self.temp_device = usb.core.find(idVendor=0x413d, idProduct=0x2107)
            
            if self.temp_device is None:
                raise ValueError("TEMPer1F device not found")
            
            # Try to set the configuration without detaching the kernel driver
            try:
                self.temp_device.set_configuration()
            except usb.core.USBError as e:
                if e.errno == 13:  # Permission denied error
                    self.show_permission_dialog()
                    return
            
            # Get the endpoint
            cfg = self.temp_device.get_active_configuration()
            intf = cfg[(0,0)]
            self.temp_endpoint = usb.util.find_descriptor(
                intf,
                custom_match = lambda e: 
                    usb.util.endpoint_direction(e.bEndpointAddress) == 
                    usb.util.ENDPOINT_IN
            )
            
            print("Connected to TEMPer1F")
            self.temp_sensor_connected = True
            self.temp_status_label.config(text="Connected", foreground="green")
        except usb.core.USBError as e:
            print(f"USB Error connecting to TEMPer1F: {e}")
            self.show_permission_dialog()
            self.temp_sensor_connected = False
            self.temp_status_label.config(text="Disconnected", foreground="red")
        except Exception as e:
            print(f"Error connecting to TEMPer1F: {e}")
            messagebox.showerror("Connection Error", f"Error connecting to TEMPer1F: {e}")
            self.temp_sensor_connected = False
            self.temp_status_label.config(text="Disconnected", foreground="red")

    def show_permission_dialog(self):
        current_user = os.getlogin()
        permission_commands = f"""
sudo tee /etc/udev/rules.d/99-temper.rules << EOF
SUBSYSTEM=="usb", ATTRS{{idVendor}}=="413d", ATTRS{{idProduct}}=="2107", MODE="0666"
EOF
sudo udevadm control --reload-rules
sudo udevadm trigger
sudo usermod -a -G dialout {current_user}
"""
        
        dialog = tk.Toplevel(self.master)
        dialog.title("Grant Permissions for TEMPer1F")
        dialog.geometry("600x300")
        
        tk.Label(dialog, text="To grant permissions for the TEMPer1F device, run these commands in your terminal:").pack(pady=10)
        
        text_area = tk.Text(dialog, height=10, width=80)
        text_area.pack(pady=10)
        text_area.insert(tk.END, permission_commands.strip())
        
        def copy_to_clipboard():
            pyperclip.copy(permission_commands.strip())
            messagebox.showinfo("Copied", "Commands copied to clipboard!")
        
        copy_button = ttk.Button(dialog, text="Copy Commands", command=copy_to_clipboard)
        copy_button.pack(pady=10)
        
        tk.Label(dialog, text="After running these commands, unplug and replug the TEMPer1F device, then restart this application.").pack(pady=10)

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
        print(f"An error occurred: {e}")
        