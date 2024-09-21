**Run:**
```
gui.py
```
### Arduino Serial Commands

- **GET_TILT:** Retrieves current tilt values for the X, Y, and Z axes.
  - **Response:**
    ```
    Tilt X: <value>
    Tilt Y: <value>
    Tilt Z: <value>
    ```
- **CALIBRATE:** Calibrates the sensors.
  - **Response:** `CALIBRATED`

**Note:** Ensure proper serial communication settings as described in the [Software](#software) section.


# Measurement System Overview

## Installation

### Windows

1. **Install Python 3.x**
   - Download the installer from [Python.org](https://www.python.org/downloads/windows/).
   - Run the installer and ensure that the "Add Python to PATH" option is selected.

2. **Install Required Packages**
   ```bash
   pip install -r requirements.txt
   ```

3. **Connect Hardware Components**
   - Connect the Arduino Due and other peripherals as described in the Hardware Components section.

4. **Run the GUI Application**
   ```bash
   python gui.py
   ```

### macOS

1. **Install Python 3.x**
   - Download the installer from [Python.org](https://www.python.org/downloads/mac-osx/).
   - Run the installer and follow the on-screen instructions.

2. **Install Homebrew (if not already installed)**
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

3. **Install Required Packages**
   ```bash
   pip3 install -r requirements.txt
   ```

4. **Connect Hardware Components**
   - Connect the Arduino Due and other peripherals as described in the Hardware Components section.

5. **Run the GUI Application**
   ```bash
   python3 gui.py
   ```

### Linux

1. **Install Python 3.x and pip**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip
   ```

2. **Install Required Packages**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Connect Hardware Components**
   - Connect the Arduino Due and other peripherals as described in the Hardware Components section.

4. **Run the GUI Application**
   ```bash
   python3 gui.py
   ```

## Hardware Components

### VNA: miniVNA tiny Vector Network Analyzer

- **Frequency range:** 1 MHz to 3 GHz
- **USB connectivity** for data transfer and control
- **Compact and portable** design

#### Advantages of miniVNA tiny:
- Wide frequency range up to 3 GHz
- Simple USB connectivity
- Compact and portable form factor
- High accuracy and reliability

### Microcontroller: Arduino Due

- **84 MHz Atmel SAM3X8E** ARM Cortex-M3 CPU
- **512 KB Flash memory, 96 KB SRAM**
- **54 digital input/output pins** (12 can be used as PWM outputs)
- **12 analog inputs**
- **4 UARTs** (hardware serial ports)
- **Native USB port**

#### Advantages of Arduino Due:
- Powerful 32-bit ARM core microcontroller
- Large number of digital and analog I/O pins
- Hardware support for various communication protocols (SPI, I2C, CAN)
- Real-time processing capabilities
- Extensive Arduino library support

### Sensors

1. **MPU6050 Accelerometer and Gyroscope**
   - Measures acceleration and angular velocity
   - I2C interface for Arduino Due connection

## Setup

1. **Connect miniVNA tiny** to a USB port on the computer.
2. **Connect MPU6050 sensor** to the Arduino Due's I2C pins.
3. **Connect A4988 stepper driver** to digital pins for controlling the NEMA 17 motor.
4. **Upload the `arduino_data_collection.ino`** sketch to the Arduino Due.

## Directions

1. Ensure all hardware components are properly connected as described in the **Setup** section.
2. Open the Arduino IDE Serial Monitor.
3. Set the baud rate to **115200**.
4. To retrieve the current tilt values for the X, Y, and Z axes in degrees, enter the command `GET_TILT` into the Serial Monitor input field and press **Send**.
5. The Arduino will respond with the current tilt values in the format:
   ```
   Tilt X: <value>
   Tilt Y: <value>
   Tilt Z: <value>
   ```
6. Use the GUI application to control the system, visualize data, and perform automated tasks.

## Software

### Arduino Sketch Functionality

1. Initialize all sensors.
2. Continuous loop for:
   - Reading acceleration and gyroscope data from the MPU6050.
   - Logging all data with accurate timestamps.
   - Adjusting the stepper motor to change sensor angle at predetermined intervals.
3. Communicate with the computer for VNA data collection and overall system control.

### Recommended Libraries

- `MPU6050`: for the accelerometer and gyroscope sensor.
- `AccelStepper`: for controlling the stepper motor.

## Key Features

- Fully automated data collection.
- Synchronized timestamps for all data points.
- Automated angle adjustments.
- Continuous operation without human intervention.
- Real-time data visualization.
- Customizable measurement frequency.
- Automatic logging controls.
- File management and data export capabilities.

## Development Steps

1. Set up hardware connections and test individual components.
2. Implement device communication for each sensor and the miniVNA tiny.
3. Develop data acquisition and synchronization routines.
4. Create GUI for real-time data display and system control.
5. Implement logging and data export functionality.
6. Develop automated angle adjustment system.
7. Integrate all components into a cohesive system.
8. Extensive testing and refinement.

## Future Enhancements

- Remote viewing of live data via hosted GUI.
- Advanced data analysis and pattern recognition.
- Integration with cloud services for data backup and sharing.

## Important Considerations

- Implement proper error handling and failsafes.
- Ensure accurate time synchronization across all measurements.
- Optimize power management for long-term operation.
- Develop a user-friendly interface for easy operation and monitoring.
- Consider using a separate computer for GUI and data processing, communicating with the Arduino Due via USB.

