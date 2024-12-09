# Use Ubuntu as base image
FROM ubuntu:22.04

# Avoid timezone prompt during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    xvfb \
    libgl1-mesa-dev \
    libx11-dev \
    libxcb1-dev \
    libxkbcommon-x11-dev \
    libdbus-1-3 \
    qt6-base-dev \
    cmake \
    ninja-build \
    pkg-config \
    # Pillow dependencies
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    zlib1g-dev \
    libffi-dev \
    libjpeg8-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only the requirements file first
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir wheel setuptools && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Set display environment variable for GUI
ENV DISPLAY=:99
ENV QT_QPA_PLATFORM=xcb
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Create entrypoint script with debugging
RUN echo '#!/bin/bash\n\
echo "Current directory: $PWD"\n\
echo "Directory contents:"\n\
ls -la\n\
echo "Python path:"\n\
echo $PYTHONPATH\n\
echo "Python version:"\n\
python3 --version\n\
echo "Starting Xvfb..."\n\
Xvfb :99 -screen 0 1024x768x16 &\n\
sleep 1\n\
echo "Starting main.py..."\n\
cd /app && python3 main.py\n' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"] 