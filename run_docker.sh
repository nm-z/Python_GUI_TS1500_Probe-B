#!/bin/bash

# Allow X server connections
xhost +local:docker

# Build and run the container
docker-compose up --build

# Disable X server connections when done
xhost -local:docker 