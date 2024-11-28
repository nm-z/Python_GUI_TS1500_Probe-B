#!/bin/bash

# Create temporary directory for binary creation
TEMP_DIR=$(mktemp -d)
BINARY_DIR="$TEMP_DIR/bin"
mkdir -p "$BINARY_DIR"

# Create the binary script
cat > "$BINARY_DIR/ts1500-probe" << 'EOL'
#!/bin/bash

# Check if running on Ubuntu
if ! grep -q "Ubuntu" /etc/os-release; then
    echo "This binary is designed for Ubuntu systems only."
    exit 1
fi

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    sudo apt update
    sudo apt install -y docker.io docker-compose
    sudo systemctl start docker
    sudo systemctl enable docker
fi

# Create application directory if it doesn't exist
APP_DIR="/opt/ts1500-probe"
sudo mkdir -p "$APP_DIR"

# Create or update docker-compose.yml
sudo tee "$APP_DIR/docker-compose.yml" > /dev/null << 'EOYAML'
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

# Allow Docker to access X server
xhost +local:docker

# Run the application
cd "$APP_DIR" && sudo docker-compose up --build
EOL

# Make the binary executable
chmod +x "$BINARY_DIR/ts1500-probe"

# Create release notes
cat > release_notes.md << 'EOL'
# Release v1.0.2

## Ubuntu Binary Release
This release contains a single executable binary for Ubuntu systems.

### Usage:
1. Download the `ts1500-probe` binary
2. Make it executable: `chmod +x ts1500-probe`
3. Run it: `./ts1500-probe`

The binary will automatically:
- Install Docker if needed
- Set up the required environment
- Pull and run the application

Requirements:
- Ubuntu 20.04 or newer
- Internet connection for first run
- USB access for probe connection
EOL

# Optional: Install GitHub CLI if needed
if ! command -v gh &> /dev/null; then
    echo "GitHub CLI not found. Installing..."
    sudo pacman -S --noconfirm github-cli
fi

# Delete existing local tag if it exists
git tag -d v1.0.2 2>/dev/null || true

# Delete existing remote tag if it exists
gh release delete v1.0.2 --yes 2>/dev/null || true
git push --delete origin v1.0.2 2>/dev/null || true

# Create GitHub release with the binary
gh release create v1.0.2 \
    "$BINARY_DIR/ts1500-probe" \
    --title "v1.0.2" \
    --notes-file release_notes.md \
    --prerelease

# Cleanup
rm -rf "$TEMP_DIR"