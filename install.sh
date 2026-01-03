#!/bin/bash

# Installation script for Wallpaper Picker

set -e

echo "Installing Wallpaper Picker..."

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3."
    exit 1
fi

# Install system dependencies
echo "Installing system dependencies..."
if command -v apt-get &> /dev/null; then
    # Ubuntu/Debian
    sudo apt-get update
    sudo apt-get install -y python3-pip python3-gi libgirepository1.0-dev \
        gir1.2-gtk-4.0 gir1.2-adw-1 feh nitrogen
elif command -v dnf &> /dev/null; then
    # Fedora
    sudo dnf install -y python3-pip python3-gobject gtk4 libadwaita-devel \
        feh nitrogen
elif command -v pacman &> /dev/null; then
    # Arch
    sudo pacman -S --needed python python-pip python-gobject gtk4 \
        libadwaita feh nitrogen
else
    echo "Warning: Could not detect package manager. Please install manually."
    echo "Required: python3, python3-gobject, gtk4, libadwaita, feh, nitrogen"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install --user -r requirements.txt

# Create directories
echo "Creating directories..."
mkdir -p ~/.config/wallpicker
mkdir -p ~/.local/share/wallpicker/wallpapers
mkdir -p ~/.cache/wallpicker/thumbs

# Create desktop entry
echo "Creating desktop entry..."
cat > ~/.local/share/applications/wallpicker.desktop << EOF
[Desktop Entry]
Name=Wallpaper Picker
Comment=Browse and set wallpapers from Wallhaven and local files
Exec=$(pwd)/main.py
Icon=preferences-desktop-wallpaper
Type=Application
Categories=Utility;Graphics;
Terminal=false
StartupNotify=true
EOF

echo "Installation complete!"
echo "Run with: python3 main.py"
