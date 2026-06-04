#!/bin/bash

echo "==================================================="
echo "  A.L.O.N.E. Headless Assistant Unix Installer     "
echo "==================================================="
echo ""

# Step 1: Create directories
echo "[*] Creating ~/.alone/ local directories..."
mkdir -p "$HOME/.alone/memory"
mkdir -p "../data/screenshots"
mkdir -p "../data/generated_code"
echo "[+] Local directories created successfully."
echo ""

# Step 2: Install dependencies
echo "[*] Installing requirements from requirements.txt..."
cd ..
./venv/bin/pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[!] Dependency installation failed."
    exit 1
fi
echo "[+] Requirements successfully installed."
echo ""

# Step 3: Autostart registration
OS_TYPE=$(uname)
if [ "$OS_TYPE" == "Darwin" ]; then
    # macOS launchd configuration
    echo "[*] Registering macOS LaunchAgent for autostart..."
    PLIST_PATH="$HOME/Library/LaunchAgents/com.alone.assistant.plist"
    cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.alone.assistant</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(pwd)/venv/bin/python</string>
        <string>$(pwd)/main.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>$(pwd)</string>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
EOF
    launchctl load "$PLIST_PATH"
    echo "[+] LaunchAgent successfully loaded!"
else
    # Linux Desktop Autostart configuration
    echo "[*] Registering Linux Desktop Entry for autostart..."
    AUTOSTART_DIR="$HOME/.config/autostart"
    mkdir -p "$AUTOSTART_DIR"
    DESKTOP_ENTRY="$AUTOSTART_DIR/alone.desktop"
    cat <<EOF > "$DESKTOP_ENTRY"
[Desktop Entry]
Type=Application
Exec=$(pwd)/venv/bin/python $(pwd)/main.py
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=ALONE
Comment=Headless Local-First Voice Assistant
EOF
    chmod +x "$DESKTOP_ENTRY"
    echo "[+] Desktop entry created in $DESKTOP_ENTRY!"
fi

echo ""
echo "==================================================="
echo "  A.L.O.N.E. Installation Complete, Sir.           "
echo "==================================================="
