FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:0

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-tk \
    python3-dev \
    build-essential \
    git \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    xvfb \
    x11-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /home/nate/Desktop/Python_GUI_TS1500_Probe-B/VNA_Exports && \
    useradd -m appuser && \
    chown -R appuser:appuser /app /home/nate

USER appuser

CMD ["bash", "-c", "Xvfb :0 -screen 0 1024x768x24 -ac +extension GLX +render -noreset & sleep 1 && python3 gui.py"] 