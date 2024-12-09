# TS1500 Probe Control Interface

A Python-based GUI application for controlling and monitoring the TS1500 Probe system with automated tilt testing capabilities.

## Features

- Automated tilt angle control and testing
- Configurable test parameters (start angle, end angle, step size)
- Dwell time control
- Multiple run support
- Optional web server interface
- System time synchronization (when run as root)
- Modern PyQt6-based GUI

## Prerequisites

- Python 3.x
- Linux system with X11 (uses XCB platform)
- Root access for certain features (system time sync)

## Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Required Dependencies

- PyQt6
- Pillow (PIL)
- matplotlib
- Additional dependencies listed in requirements.txt

## Usage

1. Basic execution:
   ```bash
   python main.py
   ```

2. For full functionality (including system time sync):
   ```bash
   sudo python main.py
   ```

## Configuration

The application supports various configuration options:

- Logging level configuration
- Web server settings (optional)
  - Host configuration
  - Port configuration
- Test parameters customization
  - Start angle (default: 0°)
  - End angle (default: 45°)
  - Step size (default: 1°)
  - Dwell time (default: 5s)
  - Number of runs (default: 1)
  - Tilt direction options

## Project Structure

```
project/
├── controllers/     # Application logic and control flow
├── gui/            # PyQt6 GUI components and styles
├── utils/          # Utility functions and configurations
└── main.py         # Application entry point
```

## Error Handling

- Provides detailed logging for troubleshooting
- Handles permission errors for serial ports
- Includes comprehensive error reporting

## License

[Your License Here]

## Support

[Your Support Information Here]
















