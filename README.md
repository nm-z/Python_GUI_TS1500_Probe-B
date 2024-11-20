## Quick Start (Ubuntu)

Run this single command in your terminal:

```bash
sudo pacman -Syu --noconfirm && \
sudo pacman -S xorg-xhost docker docker-compose --noconfirm && \
sudo systemctl start docker && \
rm -rf Python_GUI_TS1500_Probe-B && \
git clone https://github.com/nm-z/Python_GUI_TS1500_Probe-B.git && \
cd Python_GUI_TS1500_Probe-B && \
xhost +local:docker && \
sudo docker-compose up --build
```

This command will:
1. Update your system
2. Install necessary packages (xorg-xhost, docker, docker-compose)
3. Start the Docker service
4. Remove any existing copy of the repository
5. Clone a fresh copy of the repository
6. Build and run the Docker container

This will install all necessary components and run the application in an Ubuntu-based Docker container.

