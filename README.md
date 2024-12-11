# TS1500 Probe Control Software

A PyQt6-based GUI application for controlling and monitoring the TS1500 Probe system.

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

## Requirements

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

## Installation

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

## Usage

1. Start the application:
```bash
python main.py
```

2. Configure test parameters in the left panel:
   - Set tilt increment (default: 1°)
   - Set minimum tilt (default: -30°)
   - Set maximum tilt (default: +30°)
   - Set oil level time (default: 15s)

3. Control tests using:
   - Start Test: Begin test sequence
   - Pause/Resume: Pause or resume current test
   - Stop: Stop current test
   - Emergency Stop: Immediate halt of all operations

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
  ├── logs/
  └── results/
  ```

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
















