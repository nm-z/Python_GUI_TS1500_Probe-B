# Measurement System Overview

The measurement system is designed to collect and display data from various devices, including a digital thermometer, a miniVNA Tiny, and an accelerometer. The system allows users to select the measurement frequency in seconds and features automatic logging controls, data visualization, and file management.

## Main Components

### Data Acquisition and Display

- **Temperature** (from digital thermometer)
- **VNA data** (using miniVNA Tiny)
- **Angle Position**:
  - Accelerometer data (for tilt and potentially liquid level)
  - Digital Electronic Level

### Automatic Logging Controls

- Start/Stop logging button
- Logging interval setting

### Data Visualization

- Real-time graphs for temperature, tilt, and liquid level

### File Management

- Log file naming option
- Export data button

## GUI Features

1. Real-time display of data from digital thermometer, VNA, and accelerometer
2. Start/Stop button for automated logging
3. Adjustable logging interval
4. Real-time graph showing temperature trends
5. Option to name and export the log file

## Device Communication and Implementation

### Mini VNA Tiny (VNA Data)

- Library: **pySerial**
- Installation: `pip install pyserial`

### TEMPer1F (USB Temperature Sensor)

- Library: **temper-python**
- Installation: `pip install temperusb`

### GY-521 MPU-6050 (Accelerometer/Gyroscope)

- Library: **mpu6050-raspberrypi**
- Installation: `pip install mpu6050-raspberrypi`

### To read from all these devices simultaneously and record the time:

1. Use the `threading` module to read from each device concurrently.
2. Use the `time` module to record timestamps for each reading.

### USB connection

- Connect to the miniVNA Tiny using the identified serial port.
- Read data from the miniVNA Tiny using the `pyserial` connection.

## Future Enhancements

- Host the GUI on a port for remote viewing of live data without being the host of the connected devices

## Development Steps

1. Set up device communications
2. Design and implement GUI layout
3. Develop data acquisition and display functions
4. Implement logging and data export functionality
5. Create real-time graphing capabilities
6. Add start/stop and interval control for logging
7. Implement file management features
8. Test and refine the system

## Notes

- Ensure proper error handling for device communications
- Consider multi-threading for smooth operation with multiple devices
- Implement data validation to ensure accuracy
- Design a user-friendly interface for easy operation
