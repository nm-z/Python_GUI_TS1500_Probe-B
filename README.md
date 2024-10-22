#### Arch Linux Instructions:
Paste single string command into the VS Code terminal:

```bash
mkdir Python_GUI_TS1500_Probe-B && cd Python_GUI_TS1500_Probe-B && git clone https://github.com/nm-z/Python_GUI_TS1500_Probe-B.git && cd Python_GUI_TS1500_Probe-B && code --add . && sudo pacman -Syu --noconfirm && sudo pacman -S python python-pip --noconfirm && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python gui.py
```















---
Dev (depreciated): 
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




#### Debian/Ubuntu

1. **Update Package List and Install Python 3.x and pip**

    ```bash
    sudo apt update
    sudo apt install python3 python3-pip
    ```

2. **Set Up a Virtual Environment (Recommended)**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **Install Required Python Packages**

    ```bash
    pip install -r requirements.txt
    ```

4. **Connect Hardware Components**

    - Connect the Arduino Due and any other peripherals as described in the [Hardware Components](#hardware-components) section.

5. **Run the GUI Application**

    ```bash
    python gui.py
    ```

#### Fedora

1. **Update System and Install Python 3.x and pip**

    ```bash
    sudo dnf update
    sudo dnf install python3 python3-pip
    ```

2. **Set Up a Virtual Environment (Recommended)**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **Install Required Python Packages**

    ```bash
    pip install -r requirements.txt
    ```

4. **Connect Hardware Components**

    - Connect the Arduino Due and any other peripherals as described in the [Hardware Components](#hardware-components) section.

5. **Run the GUI Application**

    ```bash
    python gui.py
    ```

#### openSUSE

1. **Update System and Install Python 3.x and pip**

    ```bash
    sudo zypper refresh
    sudo zypper install python3 python3-pip
    ```

2. **Set Up a Virtual Environment (Recommended)**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **Install Required Python Packages**

    ```bash
    pip install -r requirements.txt
    ```

4. **Connect Hardware Components**

    - Connect the Arduino Due and any other peripherals as described in the [Hardware Components](#hardware-components) section.

5. **Run the GUI Application**

    ```bash
    python gui.py
    ```

#### Other Linux Distributions

1. **Install Python 3.x and pip**

    Use your distribution’s package manager to install Python 3 and pip. For example:

    - **Arch Linux:** `sudo pacman -S python python-pip`
    - **Debian/Ubuntu:** `sudo apt install python3 python3-pip`
    - **Fedora:** `sudo dnf install python3 python3-pip`
    - **openSUSE:** `sudo zypper install python3 python3-pip`
    - **Others:** Refer to your distribution’s documentation for installing Python 3 and pip.

2. **Set Up a Virtual Environment (Recommended)**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **Install Required Python Packages**

    ```bash
    pip install -r requirements.txt
    ```

4. **Connect Hardware Components**

    - Connect the Arduino Due and any other peripherals as described in the [Hardware Components](#hardware-components) section.

5. **Run the GUI Application**

    ```bash
    python gui.py
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

### MPU6050 Accelerometer and Gyroscope

#### Pinout Information
1. **MPU-6050 Connection**
   - **VCC:** Connect to Arduino's 3.3V or 5V pin, depending on the module's voltage regulator.
   - **GND:** Connect to Arduino's GND pin.
   - **SCL:** Connect to Arduino's SCL pin (A5 on Arduino Uno).
   - **SDA:** Connect to Arduino's SDA pin (A4 on Arduino Uno).
   - **AD0:** Connect to GND to set the I2C address to 0x68. For multiple MPU-6050s, use different addresses by connecting AD0 to VCC for 0x69.

### MAX6675 Connection
2. **MAX6675 Connection**
   - **VCC:** Connect to Arduino's 3.3V pin.
   - **GND:** Connect to Arduino's GND pin.
   - **SCK:** Connect to any digital pin on Arduino (e.g., Pin 6).
   - **CS:** Connect to any digital pin on Arduino (e.g., Pin 5).
   - **SO:** Connect to any digital pin on Arduino (e.g., Pin 4).

### A4988 Driver and NEMA 17 Stepper Motor Connection
3. **A4988 Driver and NEMA 17 Stepper Motor Connection**
   - **A4988 Power:**
     - **VDD:** Connect to Arduino's 5V pin.
     - **VMOT:** Connect to an external power supply (8V to 35V).
     - **GND:** Connect to Arduino's GND and the power supply's GND.
   - **Motor Connection:**
     - **1A and 1B:** Connect to one coil of the NEMA 17 Stepper Motor.
     - **2A and 2B:** Connect to the other coil of the NEMA 17 Stepper Motor.
   - **Control Pins:**
     - **STEP:** Connect to any digital pin on Arduino (e.g., Pin 2).
     - **DIR:** Connect to any digital pin on Arduino (e.g., Pin 3).
   - **Additional:**
     - **SLEEP:** Connect to a digital pin on Arduino to control sleep mode, or tie to VDD to keep the driver enabled.
     - **MS1, MS2, MS3:** Leave disconnected for full-step mode or connect to digital pins on Arduino for microstepping.

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

