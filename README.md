# Measurement System Overview

This project implements a comprehensive measurement system with various sensors and data visualization capabilities, utilizing an Arduino Due as the central controller and a miniVNA tiny Vector Network Analyzer for VNA measurements.

## Hardware Components

### VNA: miniVNA tiny Vector Network Analyzer

- Frequency range: 1 MHz to 3 GHz
- Capable of performing sweeps from 1 MHz to 3 GHz
- USB connectivity for data transfer and control
- Compact and portable design
- Professional-grade solution

#### Advantages of miniVNA tiny:
- Wide frequency range up to 3 GHz
- Simple USB connectivity
- Compact and portable form factor
- High accuracy and reliability

### Microcontroller: Arduino Due

- 84 MHz Atmel SAM3X8E ARM Cortex-M3 CPU
- 512 KB Flash memory, 96 KB SRAM
- 54 digital input/output pins (12 can be used as PWM outputs)
- 12 analog inputs
- 4 UARTs (hardware serial ports)
- Native USB port

#### Advantages of Arduino Due:
- Powerful 32-bit ARM core microcontroller
- Large number of digital and analog I/O pins
- Hardware support for various communication protocols (SPI, I2C, CAN)
- Real-time processing capabilities
- Extensive Arduino library support

### Sensors

1. **Orientation and Temperature Sensor**: BNO055 Absolute Orientation Sensor
   - Accurate tilt and orientation data
   - Built-in temperature sensor
   - I2C interface for Arduino Due connection

2. **Stepper Motor + Driver**: NEMA 17 Stepper Motor + A4988 Driver
   - For automated angle adjustments of the sensor in the liquid container
   - Controlled by the Arduino Due via digital pins

## Setup

1. Connect miniVNA tiny to a USB port on the computer
2. Connect BNO055 sensor to the Arduino Due's I2C pins
3. Connect A4988 stepper driver to digital pins for controlling the NEMA 17 motor

## Software

### Arduino Sketch Functionality

1. Initialize all sensors
2. Continuous loop for:
   - Reading temperature and orientation data from the BNO055
   - Logging all data with accurate timestamps
   - Adjusting the stepper motor to change sensor angle at predetermined intervals
3. Communicate with the computer for VNA data collection and overall system control

### Recommended Libraries

- `Adafruit_BNO055`: for the orientation and temperature sensor
- `AccelStepper`: for controlling the stepper motor

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
2. Implement device communication for each sensor and the miniVNA tiny
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
- Consider using a separate computer for GUI and data processing, communicating with the Arduino Due via USB

