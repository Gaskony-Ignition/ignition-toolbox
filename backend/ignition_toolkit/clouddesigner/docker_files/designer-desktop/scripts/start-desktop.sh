#!/bin/bash
# designer-desktop/scripts/start-desktop.sh

set -e

echo "=========================================="
echo "CloudDesigner Desktop Environment"
echo "=========================================="

# Create log directory
mkdir -p /var/log/supervisor

# Write credentials to a file for launch-designer.sh to read
# This is more reliable than environment variable inheritance through VNC/XFCE
CREDENTIALS_FILE="/tmp/designer-credentials.env"
echo "# CloudDesigner credentials - auto-generated" > "$CREDENTIALS_FILE"
echo "IGNITION_GATEWAY_URL=\"$IGNITION_GATEWAY_URL\"" >> "$CREDENTIALS_FILE"
echo "IGNITION_USERNAME=\"$IGNITION_USERNAME\"" >> "$CREDENTIALS_FILE"
echo "IGNITION_PASSWORD=\"$IGNITION_PASSWORD\"" >> "$CREDENTIALS_FILE"
chmod 600 "$CREDENTIALS_FILE"
chown designer:designer "$CREDENTIALS_FILE"
echo "Credentials written to $CREDENTIALS_FILE"
echo "  Gateway URL: ${IGNITION_GATEWAY_URL:-not set}"
echo "  Username: ${IGNITION_USERNAME:-not set}"
echo "  Password: ${IGNITION_PASSWORD:+[set]}"

# Configure VNC password
/usr/local/bin/configure-vnc.sh

# Initialize Designer Launcher in user home (for persistence and updates)
LAUNCHER_DIR="/home/designer/.local/share/designerlauncher"
if [ ! -f "$LAUNCHER_DIR/designerlauncher.sh" ]; then
    echo "Initializing Designer Launcher..."
    mkdir -p "$LAUNCHER_DIR"
    cp -r /opt/designerlauncher-package/* "$LAUNCHER_DIR/"
    chown -R designer:designer "$LAUNCHER_DIR"
    chown -R designer:designer /home/designer/.local
    echo "Designer Launcher initialized at $LAUNCHER_DIR"
fi

# Ensure .ignition directory exists with correct permissions
mkdir -p /home/designer/.ignition/clientlauncher-data
chown -R designer:designer /home/designer/.ignition

# ============================================
# Pre-configure Designer Launcher with gateway
# ============================================
# Write the launcher config JSON so the Designer Launcher starts with the
# gateway already added. This avoids fragile xdotool UI automation for the
# "Add Designer" flow. The automation script only needs to click "Open Designer"
# and handle login.
LAUNCHER_CONFIG="/home/designer/.ignition/clientlauncher-data/designer-launcher.json"
if [ -n "$IGNITION_GATEWAY_URL" ]; then
    # Strip trailing slash from gateway URL
    GW_URL=$(echo "$IGNITION_GATEWAY_URL" | sed 's|/$||')
    # Extract a display name from the URL (hostname:port)
    GW_NAME=$(echo "$GW_URL" | sed 's|https\?://||')

    cat > "$LAUNCHER_CONFIG" << LAUNCHER_EOF
{
  "version": null,
  "global": {
    "autoexit": false,
    "application.view.mode": "CARD"
  },
  "applications": [
    {
      "name": "$GW_NAME",
      "gateway.info": {
        "gateway.name": "$GW_NAME",
        "gateway.address": "$GW_URL",
        "redundant.gateways": []
      },
      "connection.verified": true,
      "autostart": false
    }
  ]
}
LAUNCHER_EOF
    chown designer:designer "$LAUNCHER_CONFIG"
    chmod 644 "$LAUNCHER_CONFIG"
    echo "Designer Launcher pre-configured with gateway: $GW_URL"
else
    echo "No gateway URL provided - Designer Launcher will start unconfigured"
fi

# ============================================
# Restore XFCE autostart (critical for auto-launch)
# ============================================
# The designer-home volume persists /home/designer across container restarts.
# On image rebuild, the volume retains old data and does NOT refresh from the
# new image. XFCE first-run also overwrites ~/.config/xfce4/ and may delete
# the autostart directory. We always restore from /etc/clouddesigner/ which
# is outside the volume mount and always comes fresh from the image.
AUTOSTART_DIR="/home/designer/.config/autostart"
AUTOSTART_SOURCE="/etc/clouddesigner/designer.desktop"
if [ -f "$AUTOSTART_SOURCE" ]; then
    mkdir -p "$AUTOSTART_DIR"
    cp "$AUTOSTART_SOURCE" "$AUTOSTART_DIR/designer.desktop"
    chmod 644 "$AUTOSTART_DIR/designer.desktop"
    chown -R designer:designer /home/designer/.config/autostart
    echo "XFCE autostart restored: $AUTOSTART_DIR/designer.desktop"
else
    echo "WARNING: Autostart source not found at $AUTOSTART_SOURCE"
    echo "Designer will not auto-launch. Use desktop shortcut instead."
fi

# Start supervisor (manages VNC + desktop)
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
