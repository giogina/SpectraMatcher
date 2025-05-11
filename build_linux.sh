#!/bin/bash

VERSION="1.1.0"

set -e  # Exit on error

echo "=> Building Docker image from Dockerfile..."
sudo docker build -f linux_installer/Dockerfile -t spectramatcher-builder .

echo "=> Creating temporary container..."
container_id=$(sudo docker create spectramatcher-builder)

echo "=> Extracting build artifact..."
sudo docker cp "$container_id:/SpectraMatcher/linux_installer/SpectraMatcher_Linux_Installer.zip" linux_installer/
mv linux_installer/SpectraMatcher_Linux_Installer.zip "linux_installer/SpectraMatcher_Linux_Installer_$VERSION.zip"

echo "=> Cleaning up..."
sudo docker rm "$container_id"

echo "Done. Output available at: linux_installer/SpectraMatcher_Linux_Installer_$VERSION.zip"


