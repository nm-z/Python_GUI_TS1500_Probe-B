# Use Ubuntu as base image
FROM ubuntu:22.04

# Prevent timezone prompt during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:0

# Install system dependencies and Python
RUN apt-get update && apt-get install -y \
    python3.9 \
    python3-pip \
    python3-tk \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxcb-xinerama0 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    x11-xserver-utils \
    python3-dev \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create a directory for VNA exports
RUN mkdir -p /home/nate/Desktop/Python_GUI_TS1500_Probe-B/VNA_Exports

# Add a non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Command to run the application
CMD ["python3", "gui.py"] 