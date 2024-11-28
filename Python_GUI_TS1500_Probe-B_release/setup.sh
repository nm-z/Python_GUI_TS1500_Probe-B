#!/bin/bash

# Detect package manager
if command -v apt &> /dev/null; then
    # Ubuntu/Debian
    sudo apt update && sudo apt upgrade -y
    sudo apt install -y x11-xserver-utils docker.io docker-compose
elif command -v pacman &> /dev/null; then
    # Arch Linux
    sudo pacman -Syu --noconfirm
    sudo pacman -S --noconfirm x11-xserver-utils docker docker-compose
else
    echo "Unsupported distribution. Please install Docker and x11-xserver-utils manually."
    exit 1
fi

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Allow Docker to access X server
xhost +local:docker

# Create docker-compose.yml
cat > docker-compose.yml << 'EOYAML'
version: '3'

services:
  gui:
    build:
      context: https://github.com/nm-z/Python_GUI_TS1500_Probe-B.git#Beta
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix
      - ${HOME}/.Xauthority:/home/appuser/.Xauthority
      - vna_exports:/home/nate/Desktop/Python_GUI_TS1500_Probe-B/VNA_Exports
      - /dev:/dev
    environment:
      - DISPLAY=${DISPLAY}
      - QT_X11_NO_MITSHM=1
    devices:
      - /dev/ttyACM0:/dev/ttyACM0
    privileged: true
    network_mode: host

volumes:
  vna_exports:
EOYAML

# Build and run the container
sudo docker-compose up --build
