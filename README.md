# TS1500 Probe Control Software

A PyQt6-based GUI application for controlling and monitoring the TS1500 Probe system.

## Quick Start Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Python_GUI_TS1500_Probe-B.git
cd Python_GUI_TS1500_Probe-B
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Start the application:
```bash
python main.py
```

## Dependencies

```bash
# Core Dependencies
PyQt6==6.5.2
pyserial==3.5
pyqtgraph==0.13.3

# Data Processing
numpy==1.22.4
matplotlib==3.5.2
pandas==1.4.3

# Additional Tools
PyYAML==6.0.1
keyboard==0.13.5
```

## System Dependencies

Before installing Python dependencies, ensure the following system libraries are installed:

```bash
sudo apt update
sudo apt install libxcb-cursor0 libxcb-xinerama0 libxcb-xfixes0 libxcb-shape0 \
    libxcb-render-util0 libxcb-render0 libxcb-shm0 libxcb-keysyms1 libxcb-icccm4 \
    libxcb-image0 libxcb-util1 libxcb-xkb1 libxkbcommon-x11-0
```

These libraries are required for the PyQt6 GUI components to function properly.

<<<<<<< HEAD
=======


>>>>>>> 9a821f2 (WIP)
## Features

### Hardware Control
- VNA integration with key event triggering
- Stepper motor control (±0.0002° precision)
- Temperature sensor monitoring
- Real-time connection status updates
- Emergency stop functionality

### GUI Interface
- Dark theme with Ubuntu Bold font
- Draggable dividers with light blue borders (#47A8E5)
- Real-time plotting of tilt angle and temperature
- Color-coded logger messages
- Test progress monitoring

### Configuration
- Test parameter configuration:
  - Tilt Increment (0.1° accuracy)
  - Minimum Tilt (-30° to +30°)
  - Maximum Tilt (-30° to +30°)
  - Oil Level Time (stabilization delay)
- YAML-based configuration management
- Auto-loading of last used settings

### Data Management
- Automatic data logging
- Backup and restore functionality
- Results tracking with run numbers
- VNA and temperature data file management

## Data Files

- `results.txt`: Contains test results including:
  - Run number
  - VNA data file paths
  - Temperature data file paths
  - Total execution time
  - Angles tested
  - Configuration used

- Data directory structure:
  ```
  data/
  ├── vna/
  │   └── vna_measurements.csv
  ├── temperature/
  │   └── temperature_log.csv
  ├���─ logs/
  └── results/
  ```


# Arduino Library: 

1. **LiquidCrystal** (v1.0.7)  
   - For controlling alphanumeric LCD displays (Hitachi HD44780).

2. **AccelStepper** (v1.64)  
   - Object-oriented library for controlling stepper motors.

3. **Adafruit BusIO** (v1.12.6)  
   - Abstraction library for I2C and SPI interfaces.

4. **Adafruit GFX Library** (v1.11.11)  
   - Core graphics library for Adafruit displays.

5. **Adafruit MPU6050** (v2.2.6)  
   - Arduino library for MPU6050 accelerometer/gyroscope.

6. **Adafruit SSD1306** (v2.5.13)  
   - Driver for SSD1306 monochrome OLED displays (128x64, 128x32).

7. **Adafruit Unified Sensor** (v1.1.14)  
   - Sensor abstraction layer for Adafruit sensor libraries.

8. **DallasTemperature** (v3.9.0)  
   - Library for Dallas Temperature ICs (e.g., DS18B20).

9. **MAX6675** (v0.3.2)  
   - Library for MAX6675 K-type thermocouple.

10. **MAX6675 Thermocouple** (v2.0.2)  
    - Thermocouple temperature handling library for MAX6675.

11. **MPU6050** (v1.4.1)  
    - Another MPU6050 library for 6-axis accelerometer/gyroscope.

12. **OneWire** (v2.3.8)  
    - Access library for 1-Wire devices, including temperature sensors.

13. **Time** (v1.6.1)  
    - Library for timekeeping functionality in Arduino, supporting GPS and NTP.



# MPU-6050 Wiring (Tilt)

| **MPU-6050 Pin** | **Arduino Pin**  | **Notes**                                                  |
| ---------------- | ---------------- | ---------------------------------------------------------- |
| **VCC**          | **Power - 3.3V** | Supply voltage to the MPU-6050. Ensure 3.3V compatibility. |
| **GND**          | **Power - GND**  | Ground connection.                                         |
| **SCL**          | **SCL Pin 21**   | I2C Clock line (SCL).                                      |
| **SDA**          | **SDA Pin 20**   | I2C Data line (SDA).                                       |

# MAX6675 Wiring (Temp)

| **MAX6675 Pin** | **Arduino ICSP Header** | **Notes**                                                      |
| --------------- | ----------------------- | -------------------------------------------------------------- |
| **GND**         | **Pin 6 - GND**         | Connect to Ground.                                             |
| **VCC**         | **Pin 2 - VCC**         | Connect to 3.3V or 5V (based on MAX6675 module compatibility). |
| **SO**          | **Pin 12 - MISO**       | SPI Data Out (Slave Out).                                      |
| **SCK**         | **Pin 13 - SCK**        | SPI Clock.                                                     |
| **CS**          | **PWM Pin 10**          | Chip Select (can be any digital pin).                          |
|                 |                         |                                                                |
|                 |                         |                                                                |




## Hardware Commands

- `TEST`: System-wide self-test
- `STATUS`: Current system status
- `TEMP`: Read temperature sensor
- `MOVE <steps>`: Move stepper motor
- `HOME`: Home stepper motor
- `STOP`: Stop motor movement
- `CALIBRATE`: System calibration
- `EMERGENCY_STOP`: Emergency stop

## Development

The project follows a modular architecture:
- `controllers/`: Business logic and hardware control
- `gui/`: PyQt6 interface components
- `utils/`: Helper functions and utilities
- `models/`: Data models and structures
- `hardware/`: Hardware communication layer

## License

[Your License Here]
















