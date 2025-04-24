#!/bin/bash

set -e

# ===== CONFIG =====
APP_NAME="SpectraMatcher"
BINARY="./SpectraMatcher"  # adjust if your Nuitka binary is elsewhere
EXTENSION="spm"
MIME_TYPE="application/x-spectramatcher"
INSTALL_DIR="$HOME/.local/share/spectramatcher"
ICON_SRC="spectramatcher_icon.png"  # your PNG icon
ICON_SIZE="48x48"
ICON_DEST="$HOME/.local/share/icons/hicolor/$ICON_SIZE/mimetypes/application-x-spectramatcher.png"
BIN_DEST="$HOME/.local/bin/$APP_NAME"
DESKTOP_FILE="$HOME/.local/share/applications/${APP_NAME}.desktop"
MIME_XML="$HOME/.local/share/mime/packages/${APP_NAME}.xml"

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
    PKG_MANAGER=$(detect_package_manager)
    echo "📦 Detected package manager: $PKG_MANAGER"

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
            echo "❌ Unknown package manager. Please install dependencies manually:"
            echo "    python3-tk xclip wmctrl"
            exit 1
            ;;
    esac
}

# ===== Copy Executable and Data =====
install_binary() {
    echo "📂 Installing binary and resources..."
    mkdir -p "$INSTALL_DIR"
    cp -r resources "$INSTALL_DIR/" 2>/dev/null || true
    cp "$BINARY" "$BIN_DEST"
    chmod +x "$BIN_DEST"
}

# ===== Create .desktop file =====
install_desktop_file() {
    echo "🖼️ Installing .desktop file..."
    mkdir -p "$(dirname "$DESKTOP_FILE")"
    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=$APP_NAME
Exec=$BIN_DEST %f
Type=Application
MimeType=$MIME_TYPE;
Icon=$APP_NAME
Categories=Science;
Terminal=false
EOF
    update-desktop-database "$(dirname "$DESKTOP_FILE")"
}

# ===== Create MIME type =====
install_mime_type() {
    echo "📄 Registering MIME type..."
    mkdir -p "$(dirname "$MIME_XML")"
    cat > "$MIME_XML" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="$MIME_TYPE">
    <comment>SpectraMatcher Project File</comment>
    <glob pattern="*.$EXTENSION"/>
  </mime-type>
</mime-info>
EOF
    update-mime-database "$HOME/.local/share/mime"
}

# ===== Install Icon =====
install_icon() {
    echo "🖼️ Installing file icon..."
    mkdir -p "$(dirname "$ICON_DEST")"
    cp "$ICON_SRC" "$ICON_DEST"
    gtk-update-icon-cache "$HOME/.local/share/icons/hicolor"
}

# ===== Set default app for file type =====
set_default_app() {
    echo "🔗 Setting default app for *.$EXTENSION files..."
    xdg-mime default "${APP_NAME}.desktop" "$MIME_TYPE"
}

# ===== Run All =====
install_dependencies
install_binary
install_desktop_file
install_mime_type
install_icon
set_default_app

echo "✅ $APP_NAME is now installed and integrated with your desktop!"
echo "📂 Run it by opening .$EXTENSION files or from your app launcher."
