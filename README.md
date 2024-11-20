# Quick Start

## Quick Start (Ubuntu)

The application runs in an Ubuntu-based Docker container. Copy codeblock below and paste directly in terminal:

```bash
# Update system and install dependencies
sudo apt update && sudo apt upgrade -y && \
sudo apt install -y x11-xserver-utils docker.io docker-compose git python3-setuptools && \
sudo systemctl start docker && \
sudo systemctl enable docker && \

# Clone and run the application (Beta branch)
cd ~ && \
rm -rf Python_GUI_TS1500_Probe-B && \
git clone -b Beta https://github.com/nm-z/Python_GUI_TS1500_Probe-B.git && \
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

