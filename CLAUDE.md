# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

PyQt6 GUI + CLI application for controlling the TS1500 Probe system — an automated test rig with an Arduino Due, stepper motor, MPU6050 tilt sensor, MAX6675 thermocouple, and miniVNA. Runs tilt tests and fill tests by stepping through positions, triggering VNA sweeps, and logging data.

## Commands

```bash
# Run CLI mode (default)
python main.py

# Run GUI mode
python main.py --mode gui

# Setup
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Full install (system deps + desktop entries)
./install.sh
```

No test suite exists. `test_arduino.py` and `test_serial.py` are manual hardware diagnostic scripts, not automated tests.

## Architecture

**Entry point:** `main.py` (~3700 lines) — contains CLI interface, test routines, and all test execution logic (setup, movement loops, VNA triggering, CSV logging).

**Hardware layer** (`hardware/`):
- `controller.py` — `HardwareController(QObject)`: serial connection to Arduino Due (250000 baud), command send/receive with QMutex locking, auto-detection of Arduino Due Native/Programming ports. Emits Qt signals for connection status, temperature, tilt, errors.
- `arduino.py` — `ArduinoController`: lower-level serial interface with context manager support, connection retry with exponential backoff, PING/PONG handshake.

**GUI layer** (`gui/`):
- `main_window.py` — top-level window
- `control_panel.py` — motor/test controls
- `real_time_plots.py` / `plots_window.py` — live data plotting via pyqtgraph
- `status_indicators.py`, `tilt_indicator.py` — hardware state display
- `settings_dialog.py`, `test_parameters_dialog.py` — configuration UIs

**Controllers** (`controllers/`):
- `main_controller.py` — orchestrates tests in GUI mode, manages threads, emits signals for UI updates.

**Utils** (`utils/`):
- `config.py` — singleton `Config` class, loads `config.yaml`
- `logger.py` — dual logging: `QTextEditLogger` for GUI, colored console for CLI
- `backup.py`, `time_sync.py`, `test_routines.py`, `keyboard_control.py`

**Legacy:** `views/main_view.py` is an obsolete Tkinter view, unused.

## Key Details

- **Serial protocol:** Arduino Due at 250000 baud. Commands: `HOME`, `MOVE <steps>`, `TEMP`, `STATUS`, `TEST`, `STOP`, `CALIBRATE`, `EMERGENCY_STOP`. Responses are newline-terminated strings that sometimes arrive duplicated/corrupted and get cleaned.
- **VNA triggering:** Sends F12 (or configurable key from `config.yaml`) to the miniVNA window using pyautogui + python-xlib window focus.
- **Two test types:** Tilt Test (starts at min, steps up) and Fill Test (starts at 0, multiple loops with drain delays).
- **Config:** `config.yaml` for runtime settings (data paths, test params, VNA key). `config.json` for hardware defaults (baudrate, port, web server).
- **Data output:** CSV files in `data/` subdirectories. Run numbers tracked persistently. Temperature logs go to a configurable external path.
- **Arduino sketch:** `arduino_data_collection/arduino_data_collection.ino` — firmware for the Due.

## Conventions

- Qt signals/slots for all async GUI updates. QMutex for thread-safe hardware commands.
- ANSI color codes in CLI output, HTML color in GUI log viewer.
- Hardware errors (e.g., MPU6050 read failures) are logged but don't halt tests. Movement errors abort.
