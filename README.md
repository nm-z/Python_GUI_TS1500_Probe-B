# Measurement System Overview

This project implements a comprehensive measurement system with various sensors and data visualization capabilities, utilizing a Raspberry Pi 4 as the central controller and an AURSINC NanoVNA-H Vector Network Analyzer for VNA measurements.

## Hardware Components

### VNA: Mini-VNA Tiny Vector Network Analyzer

- Frequency range: 1 MHz to 3 GHz
- Capable of performing sweeps from 1 MHz to 20 MHz
- USB connectivity for data transfer and control
- Compact and portable design
- Cost-effective solution

#### Advantages of Mini-VNA Tiny:
- Wide frequency range up to 3 GHz
- Simple USB connectivity
- Compact and portable form factor
- Compatible with various software options

### Microcontroller: Raspberry Pi 4

- Quad-core Cortex-A72 (ARM v8) 64-bit SoC @ 1.5GHz
- 2GB, 4GB, or 8GB RAM options
- Runs full Linux OS
- Extensive connectivity (Ethernet, Wi-Fi, Bluetooth, USB 3.0)
- 40 GPIO pins, supports various interfaces (I2C, SPI, UART)

#### Advantages over Arduino:
- Significantly more processing power
- Much larger memory capacity
- Full operating system support
- Better connectivity options
- Larger software ecosystem
- Greater scalability for future expansions

### Sensors

1. **Temperature Sensor**: MAX31865 RTD Amplifier + PT100 Probe
   - High-precision temperature readings
   - SPI interface for Raspberry Pi connection

2. **Angle Position Sensor**: BNO055 Absolute Orientation Sensor
   - Accurate tilt and orientation data
   - I2C interface for Raspberry Pi connection

3. **Stepper Motor + Driver**: NEMA 17 Stepper Motor + A4988 Driver
   - For automated angle adjustments of the sensor in the liquid container
   - Controlled by the Raspberry Pi via GPIO

## Setup

1. Connect Mini-VNA Tiny to a USB port on the Raspberry Pi
2. Connect MAX31865 RTD Amplifier to the Raspberry Pi's SPI pins
3. Connect BNO055 sensor to the Raspberry Pi's I2C pins
4. Connect A4988 stepper driver to GPIO pins for controlling the NEMA 17 motor

## Software

### Python Script Functionality

1. Initialize all sensors and the Mini-VNA Tiny
2. Continuous loop for:
   - Reading temperature from the MAX31865
   - Collecting data from the Mini-VNA Tiny
   - Getting orientation data from the BNO055
   - Logging all data with accurate timestamps
   - Adjusting the stepper motor to change sensor angle at predetermined intervals

### Recommended Libraries

- `minivna-python`: for interfacing with the Mini-VNA Tiny
- `adafruit-circuitpython-max31865`: for the temperature sensor
- `adafruit-circuitpython-bno055`: for the orientation sensor
- `RpiMotorLib`: for controlling the stepper motor

## Key Features

- Fully automated data collection
- Synchronized timestamps for all data points
- Automated angle adjustments
- Continuous operation without human intervention
- Real-time data visualization
- Customizable measurement frequency
- Automatic logging controls
- File management and data export capabilities

## Development Steps

1. Set up hardware connections and test individual components
2. Implement device communication for each sensor and the Mini-VNA Tiny
3. Develop data acquisition and synchronization routines
4. Create GUI for real-time data display and system control
5. Implement logging and data export functionality
6. Develop automated angle adjustment system
7. Integrate all components into a cohesive system
8. Extensive testing and refinement

## Future Enhancements

- Remote viewing of live data via hosted GUI
- Advanced data analysis and pattern recognition
- Integration with cloud services for data backup and sharing

## Important Considerations

- Implement proper error handling and failsafes
- Ensure accurate time synchronization across all measurements
- Optimize power management for long-term operation
- Develop a user-friendly interface for easy operation and monitoring



test github sync 