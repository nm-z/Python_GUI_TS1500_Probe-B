#!/bin/bash

# Create release directory
RELEASE_DIR="Python_GUI_TS1500_Probe-B_release"
mkdir -p "$RELEASE_DIR"
cd "$RELEASE_DIR" || { echo "Failed to enter directory $RELEASE_DIR"; exit 1; }

# Create setup script
cat > setup.sh << 'EOL'
#!/bin/bash

# Update and install required packages
sudo pacman -Syu --noconfirm
sudo pacman -S --noconfirm x11-xserver-utils docker docker-compose

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
EOL

# Make setup script executable
chmod +x setup.sh

# Create README
cat > README.md << 'EOL'
# Python GUI TS1500 Probe-B Quick Setup

This release contains a setup script that will automatically install and run the Python GUI TS1500 Probe-B application using Docker.

## Requirements
- Arch Linux or compatible Linux distribution
- Internet connection
- USB port for Arduino connection

## Installation

1. Extract the release package:
EOL

cd ..

# Create release package
tar -czf Python_GUI_TS1500_Probe-B_release.tar.gz "$RELEASE_DIR"

# Create release notes file
cat > release_notes.md << 'EOL'
# Release v1.0.0

Implemented startup script for Ubuntu, Code now pulls code from the repo through Docker. 
Dependencies are now handled by by apt-get in the Dockerfile. 
Python Dependencies are now handled by requirements.txt and virtualenv in Dockerfile.
Application-Specific Dependencies are now handled by application code and additional scripts.
As for vna.js, it still needs to be ran alongside the application. Keyboard events are still sent to the application through docker. 
vna.js components could be ran directly through docker, but I have not tested this yet.
Arduino Pinouts will need to be consistent to be able to be ran on different systems. This will allow pinouts to be hard coded to prevent errors.

EOL

# Optional: Install GitHub CLI if needed
if ! command -v gh &> /dev/null; then
    echo "GitHub CLI not found. Installing..."
    sudo pacman -S --noconfirm github-cli
fi

# Create GitHub release with notes
gh release create v1.0.0 Python_GUI_TS1500_Probe-B_release.tar.gz --title "v1.0.0" --notes-file release_notes.md --prerelease




