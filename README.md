<<<<<<< HEAD
# Quick Start
=======
## Quick Start (Ubuntu)
>>>>>>> 35b94c30397c48755e97199d7ea43fefe0e1ae28

The application runs in an Ubuntu-based Docker container. Choose the command for your system:

## For Ubuntu/Debian:
```bash
sudo apt update && sudo apt upgrade -y && \
sudo apt install -y x11-xserver-utils docker.io docker-compose git && \
sudo systemctl start docker && \
sudo systemctl enable docker && \
rm -rf Python_GUI_TS1500_Probe-B && \
git clone https://github.com/nm-z/Python_GUI_TS1500_Probe-B.git && \
cd Python_GUI_TS1500_Probe-B && \
xhost +local:docker && \
sudo docker-compose up --build
```

## For Arch Linux:
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

These commands will:
1. Update your system
2. Install necessary packages
3. Start and enable Docker service
4. Remove any existing copy of the repository
5. Clone a fresh copy of the repository
6. Build and run the Docker container

The application will run in an Ubuntu-based Docker container, ensuring consistent behavior across systems.

