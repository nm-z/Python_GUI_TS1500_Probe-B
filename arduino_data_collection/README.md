# TS1500 Probe-B Arduino Control System

## Overview
This Arduino project provides a comprehensive control system for a stepper motor with integrated temperature sensing, designed for precise positioning and environmental monitoring.

## Hardware Requirements
- Arduino Board (Tested on Arduino Due)
- Stepper Motor Driver
- DS18B20 Temperature Sensor
- Limit Switch for Homing
- Emergency Stop Button

## Pin Configuration
- Stepper Motor:
  - STEP Pin: 9
  - DIR Pin: 8
- Limit Switch: Pin 3
- Emergency Stop: Pin 4
- Temperature Sensor: Pin 2

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




## Serial Command Interface

### Movement Commands
- `MOVE <steps>`
  - Move relative steps (positive or negative)
  - Example: `MOVE 200` moves 200 steps forward
  - Example: `MOVE -100` moves 100 steps backward

- `GOTO <angle>`
  - Move to absolute angle between -360° and 360°
  - Example: `GOTO 45` moves to 45-degree position
  - Example: `GOTO -90` moves to -90-degree position

- `SPEED <value>`
  - Set motor speed (1-1000 steps/second)
  - Example: `SPEED 500` sets motor speed to 500 steps/second

- `STOP`
  - Immediately stop motor movement

### System Commands
- `HOME`
  - Perform homing sequence using limit switch
  - Resets current position to zero

- `STATUS`
  - Get detailed system status
  - Displays:
    - Current position (steps)
    - Current angle
    - Motor speed
    - Acceleration
    - Homing status
    - Emergency stop status
    - Elapsed time

- `TEMP`
  - Read temperature from DS18B20 sensor
  - Returns temperature in Celsius

- `CALIBRATE`
  - Perform homing and set zero position
  - Prepares system for precise movements

- `RESET`
  - Clear emergency stop condition
  - Re-enable motor outputs

## Safety Features
- Emergency stop button
- Movement range validation
- Idle timeout (motor power down after 5 minutes)
- Homing status checks

## Troubleshooting Guide

### Arduino Communication Issues

#### Serial Port Access
1. **Permission Denied**
   ```bash
   # Add user to dialout group
   sudo usermod -a -G dialout $USER
   # Add user to uucp group (on some systems)
   sudo usermod -a -G uucp $USER
   ```
   Log out and log back in for changes to take effect.

2. **Port Not Found**
   - Check if Arduino is detected:
     ```bash
     arduino-cli board list
     ls -l /dev/ttyACM*
     ```
   - Try unplugging and replugging the Arduino
   - Check USB cable

#### Communication Errors
1. **No Response**
   - Verify correct baud rate (115200)
   - Check if Arduino is properly powered
   - Reset Arduino and retry

2. **Garbled Data**
   - Confirm matching baud rates
   - Check for noise on serial lines
   - Verify ground connections

### Hardware Setup

#### Stepper Motor
1. **Motor Not Moving**
   - Check power supply
   - Verify pin connections (STEP: 9, DIR: 8)
   - Test with `STATUS` command
   - Ensure motor driver is powered

2. **Erratic Movement**
   - Check acceleration settings
   - Verify motor current setting
   - Test with lower speeds

#### Temperature Sensor
1. **No Temperature Reading**
   - Check sensor connection to pin 2
   - Verify pull-up resistor (4.7kΩ)
   - Test with `TEMP` command

2. **Invalid Readings**
   - Check for shorts
   - Verify sensor orientation
   - Test sensor with separate code

#### Limit Switch
1. **Homing Issues**
   - Verify switch connection to pin 3
   - Check switch orientation
   - Test switch with multimeter
   - Use `HOME` command to debug

### Common Error Messages

1. **"ERROR UNKNOWN_COMMAND"**
   - Check command syntax
   - Verify no extra spaces/characters
   - Commands are case-sensitive

2. **"ERROR NOT_HOMED"**
   - Run `HOME` command first
   - Check limit switch
   - Verify homing sequence

3. **"ERROR MOVEMENT_OUT_OF_RANGE"**
   - Value exceeds ±360 degrees
   - Check step calculations
   - Verify movement parameters

4. **"ERROR NO_TEMP_SENSOR"**
   - Check sensor connections
   - Verify OneWire library
   - Test sensor separately

### Debugging Steps

1. **Basic Connectivity**
   ```bash
   # Test serial connection
   arduino-cli monitor -p /dev/ttyACM0 -c baudrate=115200
   ```

2. **Hardware Verification**
   - Use `STATUS` command for system state
   - Check individual components
   - Monitor serial output

3. **Movement Testing**
   ```
   HOME        # Initialize position
   STATUS      # Check current state
   MOVE 100    # Test movement
   STATUS      # Verify new position
   ```

4. **Temperature Testing**
   ```
   TEMP        # Read temperature
   STATUS      # Check system state
   ```

### Advanced Troubleshooting

1. **Serial Monitor Logging**
   - Enable verbose output
   - Log all commands/responses
   - Check timing issues

2. **Hardware Diagnostics**
   - Test components individually
   - Use oscilloscope if available
   - Check power supply stability

3. **System Recovery**
   - Emergency stop: Press E-Stop button
   - Reset Arduino: Press reset button
   - Recalibrate: Use `CALIBRATE` command

## Dependencies
- AccelStepper Library
- OneWire Library
- DallasTemperature Library

## Installation
1. Install required Arduino libraries
2. Connect hardware according to pin configuration
3. Upload `arduino_data_collection.ino` to your Arduino board
4. Open serial monitor at 115200 baud

## Potential Improvements
- Add more advanced calibration routines
- Implement more complex movement patterns
- Enhance error handling and reporting

## Python GUI Interface

### Requirements
- Python 3.7+
- PySerial
- PyQt5/PySide2
- Matplotlib

### GUI Features
- Real-time temperature plotting
- Visual position feedback
- Command history
- Error logging
- System status display

### GUI Installation
```bash
# Install Python dependencies
pip install pyserial pyqt5 matplotlib

# Run the GUI
python main.py
```

### GUI Usage
1. Select COM port from dropdown
2. Connect to Arduino
3. Use control panel for commands
4. Monitor temperature graph
5. Check status display

### GUI Troubleshooting
1. **Port Selection Issues**
   - Refresh port list
   - Check Arduino connection
   - Verify permissions

2. **Connection Errors**
   - Check baud rate matches Arduino (115200)
   - Verify Arduino is programmed
   - Check USB connection

3. **Display Issues**
   - Verify Python version
   - Check Qt dependencies
   - Update graphics drivers

### Common Error Messages

1. **"Arduino not connected" (HardwareError)**
   ```python
   controllers.main_controller.HardwareError: Arduino not connected
   ```
   Solutions:
   - Check if Arduino is properly connected to USB
   - Verify correct port in GUI dropdown (/dev/ttyACM0)
   - Try reconnecting the Arduino
   - Check if Arduino is properly programmed
   - Verify user has permission to access port

2. **"'MainWindow' object has no attribute 'status_label'"**
   ```python
   AttributeError: 'MainWindow' object has no attribute 'status_label'
   ```
   Solutions:
   - Reinstall the GUI application
   - Check GUI initialization code
   - Verify Qt UI file is present and correct
   - Clear cached Python files (*.pyc)

3. **Matplotlib Configuration Issues**
   ```
   DEBUG - CONFIGDIR=/home/nate/.config/matplotlib
   DEBUG - CACHEDIR=/home/nate/.cache/matplotlib
   ```
   Solutions:
   - Ensure matplotlib configuration directories exist:
     ```bash
     mkdir -p ~/.config/matplotlib
     mkdir -p ~/.cache/matplotlib
     ```
   - Reset matplotlib cache:
     ```bash
     rm ~/.cache/matplotlib/fontlist-v390.json
     ```

### GUI Debug Mode

1. **Enable Debug Logging**
   ```bash
   # Run GUI with debug output
   python main.py --debug
   ```

2. **Check Log Files**
   - Application logs: `~/.config/TS1500_Probe/logs/`
   - System logs: `journalctl -f`

3. **Test Individual Components**
   ```python
   # Test serial connection
   python -c "import serial; ser=serial.Serial('/dev/ttyACM0', 115200)"
   
   # Test GUI libraries
   python -c "from PyQt5.QtWidgets import QApplication"
   
   # Test plotting
   python -c "import matplotlib.pyplot as plt"
   ```

### System Requirements

1. **Python Environment**
   ```bash
   # Check Python version (should be 3.7+)
   python --version
   
   # Verify required packages
   pip list | grep -E "pyserial|PyQt5|matplotlib"
   ```

2. **System Libraries**
   ```bash
   # Install required system packages
   sudo apt-get install python3-pyqt5 python3-serial python3-matplotlib
   ```

3. **User Permissions**
   ```bash
   # Add user to required groups
   sudo usermod -a -G dialout,uucp $USER
   
   # Verify groups
   groups
   ```

### GUI Recovery Steps

1. **Complete Reset**
   ```bash
   # Remove configuration
   rm -rf ~/.config/TS1500_Probe
   
   # Clear cache
   rm -rf ~/.cache/TS1500_Probe
   
   # Reinstall dependencies
   pip install -r requirements.txt
   ```

2. **Safe Mode Start**
   ```bash
   # Start GUI without hardware connection
   python main.py --no-hardware
   ```

3. **Configuration Reset**
   ```bash
   # Reset to default settings
   python main.py --reset-config
   ```

### Development Debugging

1. **Run Tests**
   ```bash
   # Run unit tests
   python -m pytest tests/
   
   # Test GUI components
   python -m pytest tests/test_gui.py
   ```

2. **Check Dependencies**
   ```bash
   # Generate dependency graph
   pip install pipdeptree
   pipdeptree
   ```

3. **Profile Performance**
   ```bash
   # Profile GUI startup
   python -m cProfile main.py
   ```

## License
MIT License

Copyright (c) 2023 TS1500 Probe-B Project Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contributors
- Main Arduino Code: [Your Name]
- Python GUI: [Your Name]
- Documentation: [Your Name]
- Testing: [Your Name]

For contributions or issues, please visit the project repository. 