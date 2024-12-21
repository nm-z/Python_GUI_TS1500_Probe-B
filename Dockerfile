# Build stage
FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    libgl1-mesa-dev \
    libx11-dev \
    libxcb1-dev \
    libxkbcommon-x11-dev \
    qt6-base-dev \
    cmake \
    ninja-build \
    pkg-config \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    zlib1g-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .

# Build wheels
RUN pip3 wheel --no-cache-dir -r requirements.txt -w /wheels

# Final stage
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV QT_QPA_PLATFORM=xcb
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    xvfb \
    libgl1-mesa-glx \
    libx11-6 \
    libxcb1 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libqt6core6 \
    libqt6gui6 \
    libqt6widgets6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy wheels and install
COPY --from=builder /wheels /wheels
RUN pip3 install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application code
COPY . .

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Create entrypoint script
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

ENTRYPOINT ["/app/entrypoint.sh"] 