FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Python 3.8 and build tools
RUN apt update && apt install -y \
    python3.8 \
    python3.8-venv \
    python3.8-dev \
    tzdata \
    g++ \
    python3-tk \
    patchelf \
    zip

# Make Python 3.8 the default
RUN ln -sf /usr/bin/python3.8 /usr/bin/python

# Create working directory
WORKDIR /SpectraMatcher/

# Copy only requirements for faster cache during development
COPY requirements/unix.txt requirements/

# Install Python dependencies
RUN python -m venv venv38 && \
    . venv38/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements/unix.txt

# Copy full project
COPY . .

# Build using Nuitka
RUN ./venv38/bin/python -m nuitka --standalone --follow-imports --enable-plugin=tk-inter --include-data-dir=./fonts=fonts --include-data-dir=./resources=resources --assume-yes-for-downloads --output-filename=SpectraMatcher main.py && \
    cd linux_installer/ && \
    rm -rf bin && \
    mv ../main.dist/ bin/ && \
    cp spectramatcher.sh bin/ && \
    zip -9 -r SpectraMatcher_Linux_Installer.zip bin/ install_spectramatcher.sh README.txt LICENSE

