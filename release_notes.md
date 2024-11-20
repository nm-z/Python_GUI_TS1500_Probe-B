# Release v1.0.0

Implemented startup script for Ubuntu, Code now pulls code from the repo through Docker. 
Dependencies are now handled by by apt-get in the Dockerfile. 
Python Dependencies are now handled by requirements.txt and virtualenv in Dockerfile.
Application-Specific Dependencies are now handled by application code and additional scripts.
As for vna.js, it still needs to be ran alongside the application. Keyboard events are still sent to the application through docker. 
vna.js components could be ran directly through docker, but I have not tested this yet.
Arduino Pinouts will need to be consistent to be able to be ran on different systems. This will allow pinouts to be hard coded to prevent errors.

