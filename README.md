# Quick Start

## Quick Start (Ubuntu)

The application runs in an Ubuntu-based Docker container. Before running, ensure X11 forwarding is properly set up:

```bash
# Update system and install dependencies
cd ~ && \
sudo apt update && sudo apt upgrade -y && \
sudo apt install -y x11-xserver-utils docker.io docker-compose git python3.8 python3.8-distutils && \
sudo systemctl start docker && \
sudo systemctl enable docker && \

# Clone and run the application
rm -rf Python_GUI_TS1500_Probe-B && \
git clone https://github.com/nm-z/Python_GUI_TS1500_Probe-B.git && \
cd Python_GUI_TS1500_Probe-B && \
xhost +local:docker && \
sudo docker-compose up --build
```

These commands will:
1. Update your system
2. Install necessary packages (including docker-compose from Ubuntu repositories)
3. Start and enable Docker service
4. Clone a fresh copy of the repository
5. Build and run the Docker container

The application will run in an Ubuntu-based Docker container. This will ensure that the application has consistent behavior across systems.

> Note: We use `docker-compose` (with hyphen) as we're using the version from Ubuntu's repositories. Also, we need to run it with `sudo` to ensure proper permissions.

## Troubleshooting

If you encounter any issues during installation or setup, try these solutions:

### Package Installation Issues

If you experience problems with python3-apt or other packages, try these commands:

```bash
# Reinstall python3-apt package
sudo apt-get update
sudo apt-get install --reinstall python3-apt

# If package installation is still failing, try:
sudo apt-get clean
sudo apt-get update
sudo apt-get install -y x11-xserver-utils docker.io docker-compose git python3.8 python3.8-distutils
```

### Python Version and Dependency Issues

If you're experiencing Python version conflicts or dependency issues:

1. **Using Virtual Environments (Recommended Approach)**:
```bash
sudo apt update
sudo apt install python3.8 python3.8-venv
python3.8 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools
```

2. **System-wide Python 3.8 Installation**:
```bash
# Backup APT sources
sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup_$(date +%F)
sudo cp -r /etc/apt/sources.list.d /etc/apt/sources.list.d.backup_$(date +%F)

# Add Deadsnakes PPA and install Python 3.8
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.8 python3.8-distutils

# Configure Python alternatives
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 2
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1
sudo update-alternatives --set python3 /usr/bin/python3.8
```

### Docker and Docker Compose Issues

If you're experiencing Docker-related issues:

1. **Permission Denied Errors**:
```bash
# Add your user to the docker group
sudo usermod -aG docker $USER

# Log out and log back in, or reboot
sudo reboot
```

2. **Missing `importlib_resources` Module**:
```bash
# Try APT installation first
sudo apt update
sudo apt install python3-importlib-resources

# If APT fails, use pip
sudo python3 -m pip install importlib_resources
```

3. **Docker Compose Installation Issues**:
```bash
# Remove existing docker-compose if needed
sudo apt remove --purge docker-compose

# Install using official Docker method
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

# Verify installation
docker-compose --version
```

### X11 Display Issues

If you're having problems with the GUI display:

1. **Check X11 Forwarding**:
```bash
# Allow Docker containers to connect to X server
xhost +local:docker

# After finishing, you can revoke permissions
xhost -local:docker
```

2. **Verify DISPLAY Environment**:
```bash
echo $DISPLAY
```

### System Maintenance Tips

Regular system maintenance can prevent issues:

```bash
# Regular system updates
sudo apt update && sudo apt upgrade -y

# Monitor system logs for issues
sudo journalctl -xe

# Backup important configurations
sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup
sudo cp -r /etc/apt/sources.list.d /etc/apt/sources.list.d.backup
```

### Verifying Setup

After troubleshooting, verify your setup:

```bash
# Check Docker status
docker ps

# Verify user groups
groups $USER

# Test Docker permissions
docker run hello-world
```

If you continue to experience issues, please check the system logs or reach out for additional support.
















