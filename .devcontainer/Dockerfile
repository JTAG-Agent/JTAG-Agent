FROM mcr.microsoft.com/devcontainers/python:3.11

# Install Hardware Emulation and Debugging Tools
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
       qemu-system-arm \
       qemu-system-x86 \
       gdb-multiarch \
       openocd \
       libftdi1-dev \
       telnet

# Set up a mock BSDL and SVD directory
RUN mkdir -p /workspaces/JTAG-Hardware/assets/hardware_maps