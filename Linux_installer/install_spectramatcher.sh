#!/bin/bash

set -e

# ===== CONFIG =====
APP_NAME="SpectraMatcher"
BINARY_DIR="./bin"
INSTALL_DIR="/opt/$APP_NAME"
BIN_PATH="$INSTALL_DIR/SpectraMatcher"
LAUNCHER_PATH="$INSTALL_DIR/spectramatcher.sh"
MIME_XML="/usr/share/mime/packages/spectramatcher.xml"

# ===== Detect Package Manager =====
detect_package_manager() {
    if command -v apt &> /dev/null; then echo "apt"
    elif command -v pacman &> /dev/null; then echo "pacman"
    elif command -v dnf &> /dev/null; then echo "dnf"
    elif command -v zypper &> /dev/null; then echo "zypper"
    else echo "unknown"; fi
}

# ===== Install Dependencies =====
install_dependencies() {
    echo "Checking Dependencies..."

    REQUIRED_PACKAGES=(xclip wmctrl)
    MISSING_PACKAGES=()
    for pkg in "${REQUIRED_PACKAGES[@]}"; do
        if ! command -v "$pkg" &>/dev/null; then
            MISSING_PACKAGES+=("$pkg")
        fi
    done

    if ! python3 -c "import tkinter" &>/dev/null; then
        MISSING_PACKAGES+=("python3-tk")
    fi

    if [ ${#MISSING_PACKAGES[@]} -eq 0 ]; then
        echo -e "\033[1;32mAll dependencies already installed.\033[0m"
        echo ""
        return
    fi

    PKG_MANAGER=$(detect_package_manager)
    echo "Detected package manager: $PKG_MANAGER"

    if [[ "$PKG_MANAGER" == "unknown" ]]; then
        echo -e "\033[1;33mUnknown package manager. Cannot install dependencies automatically.\033[0m"
        echo -e "Please ensure the following are installed: \033[1m${REQUIRED_PACKAGES[*]}\033[0m"
        return
    fi

    echo -e "\033[1;33mInstalling missing packages: ${MISSING_PACKAGES[*]}\033[0m"


    case $PKG_MANAGER in
        apt)
            sudo apt update
            sudo apt install -y python3-tk xclip wmctrl
            ;;
        pacman)
            sudo pacman -Sy --noconfirm tk xclip wmctrl
            ;;
        dnf)
            sudo dnf install -y python3-tkinter xclip wmctrl
            ;;
        zypper)
            sudo zypper install -y python3-tk xclip wmctrl
            ;;
        *)
            echo "Unknown package manager. Please install dependencies manually:"
            echo "    python3-tk xclip wmctrl"
            ;;
    esac
}

# ===== Copy Executable and Data =====
install_binary() {
    echo "Installing SpectraMatcher to $INSTALL_DIR..."
    sudo mkdir -p "$INSTALL_DIR"
    sudo cp -r "$BINARY_DIR"/* "$INSTALL_DIR/"
    sudo chmod +x "$BIN_PATH"
    sudo chmod +x "$LAUNCHER_PATH"
}

# ===== Create .desktop file =====
install_desktop_file() {
    echo "Installing .desktop file..."
    DESKTOP_FILE="/usr/share/applications/spectramatcher.desktop"

    if [ ! -f "$BIN_PATH" ]; then
        echo -e "\033[1;31mError: Binary not found at $EXEC_PATH\033[0m"
        return
    fi

    # Write the .desktop file
    sudo tee "$DESKTOP_FILE" > /dev/null << EOF
[Desktop Entry]
Name=SpectraMatcher
Exec=$LAUNCHER_PATH %f
Type=Application
MimeType=application/x-spectramatcher;
Icon=spectramatcher
Categories=Education;Science;Utility;
Comment=Analyze and match vibronic spectra
Keywords=spectrum;spectroscopy;vibronic;match;gaussian;plot;
Terminal=false
EOF

    sudo chmod +x "$DESKTOP_FILE"
    # Refresh desktop database
    sudo update-desktop-database /usr/share/applications
}

ask_desktop_shortcut() {
    echo ""
    read -p "Do you want to create a desktop shortcut? [Y/n] " response
    response=${response,,}  # to lowercase

    if [[ "$response" == "y" || "$response" == "" ]]; then

        DESKTOP_PATH=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")
        if [ -d "$DESKTOP_PATH" ]; then
            cp /usr/share/applications/spectramatcher.desktop "$DESKTOP_PATH/SpectraMatcher.desktop"
            chmod +x "$DESKTOP_PATH/SpectraMatcher.desktop"
        else
            echo -e "\033[1;33mDesktop folder not found, skipping desktop shortcut.\033[0m"
        fi
    fi
}

# ===== Create MIME type =====
install_mime_type() {
    echo "Registering MIME type..."
    mkdir -p "$(dirname "$MIME_XML")"
sudo tee "$MIME_XML" > /dev/null << EOF
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-spectramatcher">
    <comment>SpectraMatcher Project File</comment>
    <glob pattern="*.smp"/>
  </mime-type>
</mime-info>
EOF
    sudo update-mime-database /usr/share/mime
    xdg-mime default spectramatcher.desktop application/x-spectramatcher
    sudo xdg-mime default spectramatcher.desktop application/x-spectramatcher
}


# ===== Install Icon =====
install_icon() {
    echo "Installing file icon..."

    ICON_BASENAME="application-x-spectramatcher"
    ICON_SIZES=(16 24 32 48 64)
    ICON_THEMES=(hicolor)

    for size in "${ICON_SIZES[@]}"; do
        find /usr/share/icons -type d \( -path "*mime*${size}*" -o -path "*${size}*mime*" \) | while read -r dir; do
#            echo "$BINARY_DIR/resources/SpectraMatcher_${size}.png to: $dir"
            sudo cp "$BINARY_DIR/resources/SpectraMatcher_${size}.png" "$dir/$ICON_BASENAME.png"
        done
        sudo mkdir -p "/usr/share/icons/hicolor/${size}x${size}/apps"
        sudo cp "$BINARY_DIR/resources/SpectraMatcher_${size}.png" "/usr/share/icons/hicolor/${size}x${size}/apps/spectramatcher.png"
    done

    sudo gtk-update-icon-cache /usr/share/icons/hicolor
}


# ===== Run All =====
install_dependencies
install_binary
install_icon
install_desktop_file
ask_desktop_shortcut
install_mime_type
