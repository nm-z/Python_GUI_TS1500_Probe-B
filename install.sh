#!/bin/bash

set -e

# Ensure script is running from the project directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Clone the repository into a temporary directory and copy its contents to the current directory
echo "Cloning repository to get all the files..."
TEMP_DIR="$(mktemp -d)"
git clone https://github.com/nm-z/Python_GUI_TS1500_Probe-B.git "$TEMP_DIR"
echo "Copying repository contents to current directory..."
cp -a "$TEMP_DIR"/. .
rm -rf "$TEMP_DIR"

# Get current directory path for use in desktop entries
REPO_DIR="$(pwd)"

echo "Setting up the Python virtual environment..."
# Create virtual environment if it does not exist
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install python dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
  pip install -r requirements.txt
else
  echo "requirements.txt not found, skipping python dependency installation."
fi

# System dependencies for different distributions
DEBIAN_DEPS=(
    libxcb-cursor0
    libxcb-xinerama0
    libxcb-xfixes0
    libxcb-shape0
    libxcb-render-util0
    libxcb-render0
    libxcb-shm0
    libxcb-keysyms1
    libxcb-icccm4
    libxcb-image0
    libxcb-util1
    libxcb-xkb1
    libxkbcommon-x11-0
)

ARCH_DEPS=(
    libxcb
    xcb-util
    xcb-util-cursor
    xcb-util-wm
    xcb-util-image
    xcb-util-keysyms
    xcb-util-renderutil
    libxkbcommon-x11
)

# Install system dependencies based on OS
if command -v apt-get &> /dev/null; then
    echo "Detected Debian/Ubuntu based system. Installing system dependencies..."
    sudo apt-get update
    sudo apt-get install -y "${DEBIAN_DEPS[@]}"
elif command -v pacman &> /dev/null; then
    echo "Detected Arch Linux based system. Installing system dependencies..."
    sudo pacman -Syu --needed --noconfirm "${ARCH_DEPS[@]}"
else
    echo "Could not detect Debian/Ubuntu or Arch Linux based system."
    echo "Please install system dependencies manually:"
    echo "For Debian/Ubuntu: ${DEBIAN_DEPS[*]}"
    echo "For Arch Linux: ${ARCH_DEPS[*]}"
    exit 1
fi

# Define names for the generated desktop entries
CLI_DESKTOP="ts1500-probe-cli.desktop"
GUI_DESKTOP="ts1500-probe-gui.desktop"

# Create desktop entry for CLI mode
cat > "$CLI_DESKTOP" <<EOF
[Desktop Entry]
Version=1.0
Name=TS1500 Probe (CLI)
Comment=CLI Application for TS1500 Probe Control
Exec=bash -c "cd '$REPO_DIR' && source .venv/bin/activate && python main.py --mode cli"
Terminal=true
Type=Application
Categories=Development;Engineering;Science;
Icon=ts1500-probe
StartupNotify=true
EOF

# Create desktop entry for GUI mode
cat > "$GUI_DESKTOP" <<EOF
[Desktop Entry]
Version=1.0
Name=TS1500 Probe (GUI)
Comment=GUI Application for TS1500 Probe Control
Exec=bash -c "cd '$REPO_DIR' && source .venv/bin/activate && python main.py --mode gui"
Terminal=false
Type=Application
Categories=Development;Engineering;Science;
Icon=ts1500-probe
StartupNotify=true
EOF

# Copy desktop entry files to the local applications directory
APPLICATIONS_DIR="$HOME/.local/share/applications"
echo "Copying desktop entries to $APPLICATIONS_DIR..."
mkdir -p "$APPLICATIONS_DIR"
cp "$CLI_DESKTOP" "$APPLICATIONS_DIR"
cp "$GUI_DESKTOP" "$APPLICATIONS_DIR"

# Also copy desktop entry files to the Desktop if it exists
DESKTOP_DIR="$HOME/Desktop"
if [ -d "$DESKTOP_DIR" ]; then
    echo "Copying desktop entries to Desktop..."
    cp "$CLI_DESKTOP" "$DESKTOP_DIR"
    cp "$GUI_DESKTOP" "$DESKTOP_DIR"
fi

echo "Installation complete. You can now launch your application from the system menu or desktop shortcuts." 