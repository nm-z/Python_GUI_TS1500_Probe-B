# Enhanced Automated Data Logger

A Python-based GUI application for automated data logging with Arduino integration.

## Features

- Real-time tilt sensor monitoring
- Temperature logging
- Arduino communication
- Modern GUI interface

## Prerequisites

- Python 3.9 or higher
- Docker (optional)
- Arduino board connected via USB

## Installation

### Using Docker

1. Build and run using Docker Compose:
   ```bash
   docker-compose up --build
   ```

### Manual Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   .\venv\Scripts\activate  # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Connect your Arduino board

2. Run the application:
   ```bash
   python main.py
   ```

## Project Structure

```
your_project/
├── models/          # Data models and business logic
├── views/           # GUI components
├── controllers/     # Application controllers
├── hardware/        # Hardware communication
├── main.py         # Application entry point
└── requirements.txt # Project dependencies
```

## Development

- Models: Handle data and business logic
- Views: Manage GUI components
- Controllers: Coordinate between Models and Views
- Hardware: Manage device communication

## License

MIT License
















