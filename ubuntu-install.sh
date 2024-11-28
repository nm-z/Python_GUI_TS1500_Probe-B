#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to show GUI messages
show_message() {
    if command -v zenity &> /dev/null; then
        zenity --info --text="$1" --title="TS1500 Probe Installer"
    else
        echo -e "${BLUE}$1${NC}"
    fi
}

# Function to show error messages
show_error() {
    if command -v zenity &> /dev/null; then
        zenity --error --text="$1" --title="TS1500 Probe Installer Error"
    else
        echo -e "\033[0;31m$1${NC}"
    fi
}

# Ensure script runs with sudo privileges through GUI if needed
if [ $EUID != 0 ]; then
    if command -v zenity &> /dev/null; then
        exec pkexec "$0" "$@"
    else
        show_error "Please run this script with sudo privileges"
        exit 1
    fi
fi

# Install zenity if not present
if ! command -v zenity &> /dev/null; then
    apt update
    apt install -y zenity
fi

show_message "Installing Python GUI TS1500 Probe-B..."

# Install required packages if not present
if ! command -v docker &> /dev/null; then
    show_message "Installing Docker..."
    apt update
    apt install -y docker.io docker-compose x11-xserver-utils
    systemctl start docker
    systemctl enable docker
fi

# Allow Docker to access X server
xhost +local:docker

# Create app directory
APP_DIR="/opt/ts1500-probe"
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# Create docker-compose.yml
cat > docker-compose.yml << 'EOL'
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
EOL

# Create launcher script
cat > /usr/local/bin/ts1500-probe << 'EOL'
#!/bin/bash
# Check for updates
echo "Checking for updates..."
cd /opt/ts1500-probe
docker-compose pull

# Run the application
echo "Starting TS1500 Probe..."
docker-compose up --build
EOL

chmod +x /usr/local/bin/ts1500-probe

# Create desktop shortcut
cat > /usr/share/applications/ts1500-probe.desktop << EOL
[Desktop Entry]
Name=TS1500 Probe
Comment=Launch TS1500 Probe Application
Exec=pkexec /usr/local/bin/ts1500-probe
Icon=utilities-terminal
Type=Application
Categories=Science;
Terminal=true
EOL

# Create installer desktop file to make the script executable on double-click
cat > /usr/share/applications/ts1500-probe-installer.desktop << EOL
[Desktop Entry]
Name=Install TS1500 Probe
Comment=Install TS1500 Probe Application
Exec=pkexec $(readlink -f "$0")
Icon=system-software-install
Type=Application
Categories=System;
Terminal=true
EOL

show_message "Installation complete! You can now run TS1500 Probe from your applications menu or by typing 'ts1500-probe' in terminal." 