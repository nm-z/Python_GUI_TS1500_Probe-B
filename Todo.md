[[Phase I Opt Test Stand Parts List with Hyperlinks]]

---
# Docker:
```python
project/
│
├── Dockerfile
├── docker-compose.yml (optional, for orchestration)
├── requirements.txt
├── app/
│   ├── main.py
│   ├── gui.py
│   ├── routine.py
│   ├── logger.py
│   └── settings.json
```
- **`main.py`**: Entry point of the application.
- **`gui.py`**: Handles GUI components.
- **`routine.py`**: Contains routine execution functions.
- **`logger.py`**: Manages logging configuration.
- **`settings.json`**: User configuration file.
- **`requirements.txt`**: Lists Python dependencies.
### Dockerfile:
```dockerfile
# Use an official Python base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the application code into the container
COPY app/ /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Expose any required ports (if GUI is accessed remotely via VNC or similar)
EXPOSE 8080

# Set the command to run the application
CMD ["python", "main.py"]
```
###### **To run**:
```bash
docker run -it --rm \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    my-python-gui-app
```
###### To Edit code:
- Make changes directly to the source files on your local system



---
# Structure:
### **Pre-Routine**:
##### **Set routine**:
	Routine will do actions on HW with user set timings
	Function will use .json set through GUI by user
		Inputs:
			Function will start once .json loaded 
				and
			Function will start once run button clicked
		Output:
			Function will return arduino commands
			then
			Function will pass commands to arduino
	Routine Execution:
```python
import json
import serial

def load_json(file_path):
    """Load and validate JSON configuration."""
    with open(file_path, 'r') as f:
        config = json.load(f)
    gui_logger.info("Configuration loaded: %s", file_path)
    return config

def execute_routine(config):
    """Perform actions based on the JSON configuration."""
    try:
        with serial.Serial('/dev/ttyUSB0', 9600) as arduino:
            for command in config.get("commands", []):
                arduino.write(command.encode())
                gui_logger.debug("Sent command: %s", command)
    except Exception as e:
        gui_logger.error("Routine execution failed: %s", e)

# User actions
if __name__ == "__main__":
    config = load_json("settings.json")
    execute_routine(config)
```
### **Logging**:
##### **Standard Out**/stdout (Visual logger) 
	Set priority in GUI
		Debug
		Info
		Warning
		Error
	Do this by having Root logger +
		multiple custom non-root loggers
			propegate to the root logger  
	Standardize format string in GUI logger
##### **File** (Output after routine complete)
		Set All logs (Root logs) to log in "archive.json"
		User sets paramaters of the "output_log.csv"
	CSV Log Output:
```python
import csv

def export_csv(file_path, logs):
    """Export logs to a CSV file."""
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Logger", "Level", "Message"])
        writer.writerows(logs)
    gui_logger.info("Logs exported to: %s", file_path)
```






















---
[[Ubuntu-Test-User-Packages]]

![[IMG_8058.jpeg]]
![[IMG_8058 1.jpeg]]



![[IMG_8059.jpeg]]

---

![[InterimProgress_OptionPhase_Report_102124_final.pdf]]




