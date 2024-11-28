# Quick Start

## Quick Start (Ubuntu)

The application runs in an Ubuntu-based Docker container. Before running, ensure X11 forwarding is properly set up:

```bash
# Add Python 3.8 repository
sudo add-apt-repository ppa:deadsnakes/ppa -y

# Update package lists
sudo apt-get update

# Install Python development tools and dependencies
sudo apt-get install -y python3-dev python3-distutils python3-apt

# Clean up potential lock issues
sudo apt-get clean
sudo rm -f /var/lib/apt/lists/lock
sudo rm -f /var/cache/apt/archives/lock
sudo rm -f /var/lib/dpkg/lock*

# Reinstall python3-apt
sudo apt-get update
sudo apt-get install --reinstall python3-apt

# Install Python 3.8 and other required packages
sudo apt-get install -y python3.8 python3.8-distutils

# Upgrade and install additional packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y x11-xserver-utils docker.io docker-compose git

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Clone the repository
rm -rf Python_GUI_TS1500_Probe-B
git clone https://github.com/nm-z/Python_GUI_TS1500_Probe-B.git
cd Python_GUI_TS1500_Probe-B

# Allow X11 access for Docker
xhost +local:docker

# Build and run the Docker composition
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

## Interacting with the Project

After successfully running the Docker composition and returning to your home directory, here are the steps to interact with the code and potentially run the GUI:

### Viewing and Managing Code

```bash
# View project contents
cd ~/Python_GUI_TS1500_Probe-B
ls  # List the contents of the directory
cat README.md  # Read the project readme

# Open in text editor (choose one)
code .  # If using VS Code
nano .  # If using nano
gedit .  # If using gedit
```

### Managing Docker Containers

```bash
# Run the GUI again
cd ~/Python_GUI_TS1500_Probe-B
xhost +local:docker  # Ensure X11 forwarding is enabled
sudo docker-compose up

# Start existing containers without rebuilding
sudo docker-compose start

# Stop containers
sudo docker-compose down

# Check running containers
sudo docker ps
```

These commands allow you to:
1. Navigate to the project directory
2. View and edit the source code
3. Start and stop the Docker containers
4. Monitor running containers

> Note: Always ensure you're in the project directory (`~/Python_GUI_TS1500_Probe-B`) when running Docker commands.

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

### APT and Package Management Issues

If you encounter errors with APT updates or package installations:

1. **APT Module Errors**:
If you see `ModuleNotFoundError: No module named 'apt_pkg'`, try these steps:
```bash
# Reinstall python3-apt package
sudo apt-get update
sudo apt-get install --reinstall python3-apt

# If that doesn't work, try forcing package configuration
sudo apt-get clean
sudo apt-get update
sudo apt-get install -f
```

2. **Package Installation Verification**:
```bash
# Check if required packages are installed
dpkg -l | grep -E "docker|git|python3.8|x11-xserver-utils"

# Verify Docker installation
sudo systemctl status docker

# Check Python version
python3 --version
```

3. **Clean APT Cache and Fix Broken Packages**:
```bash
# Clean APT cache
sudo apt-get clean
sudo apt-get autoclean

# Fix broken packages
sudo apt-get -f install

# Update package lists
sudo apt-get update
```

4. **Repository Issues**:
If you're having problems with package repositories:
```bash
# Backup current sources
sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup

# Update package lists
sudo apt-get update

# If you see errors, try
sudo apt-get update --fix-missing
```
















