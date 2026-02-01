#!/bin/bash
# designer-desktop/scripts/launch-designer.sh
#
# Launches the Ignition Designer with auto-login support.
# Reads credentials from environment variables or credentials file.

set -e

LAUNCHER_DIR="/home/designer/.local/share/designerlauncher"
LOG_FILE="/tmp/launch-designer.log"
CREDENTIALS_FILE="/tmp/designer-credentials.env"

# Source credentials file if it exists (written by start-desktop.sh)
# This is more reliable than environment variable inheritance through VNC/XFCE
if [ -f "$CREDENTIALS_FILE" ]; then
    source "$CREDENTIALS_FILE"
fi

# Configuration from arguments (override) or environment/file
GATEWAY_URL="${1:-$IGNITION_GATEWAY_URL}"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "=========================================="
log "CloudDesigner Auto-Launch"
log "=========================================="

# Check if launcher exists
if [ ! -f "$LAUNCHER_DIR/designerlauncher.sh" ]; then
    log "ERROR: Designer launcher not found at $LAUNCHER_DIR"
    log "The launcher should have been initialized by start-desktop.sh"
    exit 1
fi

# Build launcher arguments
LAUNCHER_ARGS=""

# Add gateway URL if provided
if [ -n "$GATEWAY_URL" ]; then
    log "Gateway URL: $GATEWAY_URL"
    LAUNCHER_ARGS="$LAUNCHER_ARGS -g $GATEWAY_URL"
else
    log "WARNING: No gateway URL provided"
fi

# Add credentials for auto-login if provided
if [ -n "$IGNITION_USERNAME" ] && [ -n "$IGNITION_PASSWORD" ]; then
    log "Auto-login enabled for user: $IGNITION_USERNAME"
    LAUNCHER_ARGS="$LAUNCHER_ARGS -u $IGNITION_USERNAME -p $IGNITION_PASSWORD"
else
    log "No credentials provided - manual login required"
    log "  IGNITION_USERNAME is ${IGNITION_USERNAME:+set}${IGNITION_USERNAME:-not set}"
    log "  IGNITION_PASSWORD is ${IGNITION_PASSWORD:+set}${IGNITION_PASSWORD:-not set}"
fi

log "Launcher args: $LAUNCHER_ARGS"
log "Launching designer..."

# Use the bundled launcher which has its own Java runtime
cd "$LAUNCHER_DIR"
exec ./designerlauncher.sh $LAUNCHER_ARGS "$@"
