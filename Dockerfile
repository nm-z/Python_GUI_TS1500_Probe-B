FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:0

# Install system dependencies including SDL libraries for Pygame
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-tk \
    python3-dev \
    build-essential \
    git \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libxrender1 \
    libxext6 \
    libfontconfig1 \
    fonts-liberation \
    mesa-utils \
    xvfb \
    x11-utils \
    python3-pygame \
    libsdl2-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-ttf-2.0-0 \
    fonts-ubuntu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install virtual environment and dependencies
RUN pip3 install virtualenv
RUN python3 -m virtualenv venv
COPY requirements.txt .
RUN ./venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories and set up user permissions
RUN mkdir -p /home/nate/Desktop/Python_GUI_TS1500_Probe-B/VNA_Exports && \
    useradd -m appuser && \
    chown -R appuser:appuser /app /home/nate && \
    # Ensure Ubuntu fonts are accessible
    mkdir -p /home/appuser/.fonts && \
    cp /usr/share/fonts/truetype/ubuntu/Ubuntu-Light.ttf /home/appuser/.fonts/ && \
    chown -R appuser:appuser /home/appuser/.fonts

# Switch to non-root user
USER appuser

# Start the application
CMD ["bash", "-c", "Xvfb :0 -screen 0 1024x768x24 -ac +extension GLX +render -noreset & sleep 1 && ./venv/bin/python gui.py"] 