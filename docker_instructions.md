# Docker Setup Instructions

## Prerequisites
- Docker installed on your system
- Docker Compose installed on your system
- X11 server running (for Linux GUI support)

## Building and Running the Container

1. Make sure all files are in the same directory:
   - Dockerfile
   - docker-compose.yml
   - requirements.txt
   - gui.py
   - run_docker.sh

2. Make the run script executable:
   ```bash
   chmod +x run_docker.sh
   ```

3. Run the container:
   ```bash
   ./run_docker.sh
   ```

## Troubleshooting

### Permission Issues
If you encounter permission issues with the serial port, you may need to add your user to the dialout group:
```bash
sudo usermod -a -G dialout $USER
```
Then log out and log back in for the changes to take effect.

### Display Issues
If the GUI doesn't appear, ensure your X server is configured correctly:
```bash
xhost +local:docker
```

### Serial Port Issues
Make sure the Arduino is connected and the correct port is mapped in docker-compose.yml. You may need to adjust the device mapping if your Arduino uses a different port.

## Notes
- The container runs with privileged access to allow hardware access
- X11 forwarding is enabled for GUI display
- Serial ports are mapped for Arduino communication
- A volume is mounted for VNA exports 