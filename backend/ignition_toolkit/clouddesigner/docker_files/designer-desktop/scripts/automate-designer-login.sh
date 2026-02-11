#!/bin/bash
# designer-desktop/scripts/automate-designer-login.sh
#
# Automates clicking "Open Designer" and logging in using xdotool.
#
# Prerequisites:
#   - start-desktop.sh pre-writes designer-launcher.json with the gateway URL
#   - The Designer Launcher starts with the gateway already configured
#
# Automation steps:
# 1. Wait for Designer Launcher window to appear
# 2. Select the gateway card and open Designer (keyboard: Tab + Enter)
# 3. Wait for login dialog (Designer downloads on first launch, 30-120s)
# 4. Enter credentials and submit login
#
# Screenshots are saved to /tmp/automation-screenshots/ for debugging.
#
# NOTE: Do NOT use set -e here. xdotool commands fail frequently in GUI
# automation (windows not found, focus issues, etc.) and individual failures
# should not abort the entire automation flow.

LOG_FILE="/tmp/automate-designer.log"
CREDENTIALS_FILE="/tmp/designer-credentials.env"
SCREENSHOT_DIR="/tmp/automation-screenshots"

mkdir -p "$SCREENSHOT_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

screenshot() {
    local name="$1"
    local filename="${SCREENSHOT_DIR}/$(date +%Y%m%d_%H%M%S)_${name}.png"
    if command -v scrot &> /dev/null; then
        DISPLAY=:1 scrot "$filename" 2>/dev/null || true
        log "Screenshot saved: $filename"
    fi
}

log "=========================================="
log "Designer Launcher Automation Starting"
log "=========================================="

if [ -f "$CREDENTIALS_FILE" ]; then
    source "$CREDENTIALS_FILE"
    log "Loaded credentials from $CREDENTIALS_FILE"
else
    log "ERROR: Credentials file not found: $CREDENTIALS_FILE"
    exit 1
fi

if [ -z "$IGNITION_GATEWAY_URL" ]; then
    log "No gateway URL provided - skipping automation"
    exit 0
fi

log "Gateway URL: $IGNITION_GATEWAY_URL"
log "Username: ${IGNITION_USERNAME:-not set}"

export DISPLAY=:1

# ============================================
# Step 1: Wait for Designer Launcher window
# ============================================
log "Step 1: Waiting for Designer Launcher window..."
LAUNCHER_WINDOW=""
MAX_WAIT=90
WAITED=0

while [ -z "$LAUNCHER_WINDOW" ] && [ $WAITED -lt $MAX_WAIT ]; do
    sleep 2
    WAITED=$((WAITED + 2))
    LAUNCHER_WINDOW=$(xdotool search --name "Designer Launcher" 2>/dev/null | head -1) || true
    if [ -z "$LAUNCHER_WINDOW" ]; then
        LAUNCHER_WINDOW=$(xdotool search --name "Ignition" 2>/dev/null | head -1) || true
    fi
    log "Waiting... ($WAITED/$MAX_WAIT seconds)"
done

if [ -z "$LAUNCHER_WINDOW" ]; then
    log "ERROR: Designer Launcher window not found after ${MAX_WAIT}s"
    screenshot "timeout_no_window"
    exit 1
fi

log "Found Designer Launcher window: $LAUNCHER_WINDOW"
xdotool windowactivate --sync "$LAUNCHER_WINDOW"
sleep 3

screenshot "01_launcher_ready"

# ============================================
# Step 2: Open Designer
# ============================================
# The gateway is pre-configured via designer-launcher.json (written by
# start-desktop.sh). The launcher should show the gateway card already.
# We use keyboard navigation to select and open it since xdotool mouse
# coordinates are unreliable with Java Swing windows.
log "Step 2: Opening Designer via keyboard navigation"

# Give the launcher extra time to render the gateway card
sleep 2

# Strategy: Use keyboard shortcut or double-click the gateway card.
# Java Swing Designer Launcher: the gateway card is the main focusable
# element. We try multiple approaches:

# Approach 1: Double-click the center of the gateway card area
# The gateway card occupies the center of the launcher window
eval $(xdotool getwindowgeometry --shell "$LAUNCHER_WINDOW")
log "Window geometry: X=$X, Y=$Y, WIDTH=$WIDTH, HEIGHT=$HEIGHT"

# Move window to origin for predictable coordinates
xdotool windowmove --sync "$LAUNCHER_WINDOW" 0 0
sleep 0.5
eval $(xdotool getwindowgeometry --shell "$LAUNCHER_WINDOW")
log "Adjusted geometry: X=$X, Y=$Y, WIDTH=$WIDTH, HEIGHT=$HEIGHT"

# Gateway card is roughly in the upper-center of the window content area
# (below the header bar, above the bottom button row)
CARD_X=$((WIDTH / 2))
CARD_Y=$((HEIGHT / 2))
log "Double-clicking gateway card at ($CARD_X, $CARD_Y)"
xdotool mousemove --sync $CARD_X $CARD_Y
sleep 0.3
xdotool click --repeat 2 --delay 100 1
sleep 2

screenshot "02a_after_double_click"

# Check if designer download/launch started (a new window or dialog may appear)
PROGRESS_WINDOW=$(xdotool search --name "Downloading" 2>/dev/null | head -1) || true
LOGIN_WINDOW=$(xdotool search --name "Login" 2>/dev/null | head -1) || true

if [ -n "$PROGRESS_WINDOW" ] || [ -n "$LOGIN_WINDOW" ]; then
    log "Designer launch triggered by double-click"
else
    log "Double-click didn't trigger launch, trying keyboard approach"

    # Approach 2: Re-focus launcher and use keyboard
    xdotool windowactivate --sync "$LAUNCHER_WINDOW"
    sleep 0.5

    # Tab through UI elements. In the Designer Launcher, the gateway card
    # should be selectable. After selecting it, Enter should open Designer.
    # First, try clicking the card area to select it, then press Enter.
    xdotool mousemove --sync $CARD_X $CARD_Y
    sleep 0.2
    xdotool click 1
    sleep 0.5
    xdotool key Return
    sleep 2

    screenshot "02b_after_click_enter"

    # Check again
    PROGRESS_WINDOW=$(xdotool search --name "Downloading" 2>/dev/null | head -1) || true
    LOGIN_WINDOW=$(xdotool search --name "Login" 2>/dev/null | head -1) || true

    if [ -z "$PROGRESS_WINDOW" ] && [ -z "$LOGIN_WINDOW" ]; then
        log "Keyboard approach didn't trigger launch, trying Open Designer button click"

        # Approach 3: Try clicking the "Open Designer" button area
        # Button row is at the bottom of the window. Try several Y positions.
        xdotool windowactivate --sync "$LAUNCHER_WINDOW"
        sleep 0.5

        for Y_PCT in 92 90 88 85; do
            for X_PCT in 88 85 80 75; do
                BTN_X=$((WIDTH * X_PCT / 100))
                BTN_Y=$((HEIGHT * Y_PCT / 100))
                log "Trying button click at ($BTN_X, $BTN_Y) [${X_PCT}%, ${Y_PCT}%]"
                xdotool mousemove --sync $BTN_X $BTN_Y
                sleep 0.2
                xdotool click 1
                sleep 1

                # Quick check if something happened
                PROGRESS_WINDOW=$(xdotool search --name "Downloading" 2>/dev/null | head -1) || true
                LOGIN_WINDOW=$(xdotool search --name "Login" 2>/dev/null | head -1) || true
                if [ -n "$PROGRESS_WINDOW" ] || [ -n "$LOGIN_WINDOW" ]; then
                    log "Button click succeeded at ($BTN_X, $BTN_Y)"
                    break 2
                fi
            done
        done

        screenshot "02c_after_button_clicks"
    fi
fi

screenshot "03_after_open_designer"

# Check if we need to handle login
if [ -z "$IGNITION_USERNAME" ] || [ -z "$IGNITION_PASSWORD" ]; then
    log "No credentials provided - stopping automation after opening Designer"
    screenshot "04_no_credentials"
    exit 0
fi

# ============================================
# Step 3: Wait for login dialog
# ============================================
# The Designer downloads from the gateway on first launch, which can take
# 30-120 seconds depending on network speed. Poll for the login dialog.
log "Step 3: Waiting for login dialog (Designer may be downloading)..."

LOGIN_WINDOW=""
LOGIN_MAX_WAIT=180
LOGIN_WAITED=0

while [ -z "$LOGIN_WINDOW" ] && [ $LOGIN_WAITED -lt $LOGIN_MAX_WAIT ]; do
    sleep 3
    LOGIN_WAITED=$((LOGIN_WAITED + 3))

    for pattern in "Login" "Sign In" "Authentication" "Credentials"; do
        LOGIN_WINDOW=$(xdotool search --name "$pattern" 2>/dev/null | head -1) || true
        if [ -n "$LOGIN_WINDOW" ]; then
            log "Found login dialog ($pattern): $LOGIN_WINDOW after ${LOGIN_WAITED}s"
            break 2
        fi
    done

    # Check if Designer opened directly (no login needed — e.g. trial mode)
    # Exclude the launcher window (its title "Ignition Designer Launcher" also matches)
    DESIGNER_WINDOW=$(xdotool search --name "Ignition Designer" 2>/dev/null | grep -v "^${LAUNCHER_WINDOW}$" | head -1) || true
    if [ -n "$DESIGNER_WINDOW" ]; then
        log "Designer opened without login after ${LOGIN_WAITED}s"
        screenshot "05_designer_no_login"
        log "Automation complete - Designer is open"
        exit 0
    fi

    if [ $((LOGIN_WAITED % 15)) -eq 0 ]; then
        log "Still waiting for login dialog... ($LOGIN_WAITED/${LOGIN_MAX_WAIT}s)"
        screenshot "04_waiting_${LOGIN_WAITED}s"
    fi
done

if [ -z "$LOGIN_WINDOW" ]; then
    log "WARNING: Login dialog not found after ${LOGIN_MAX_WAIT}s"
    screenshot "05_no_login_dialog"
    log "Automation stopping - manual login may be required"
    exit 0
fi

# ============================================
# Step 4: Enter credentials and login
# ============================================
log "Step 4: Entering credentials"
screenshot "06_login_dialog_found"

xdotool windowactivate --sync "$LOGIN_WINDOW"
sleep 1

# Type username
xdotool type --clearmodifiers --delay 30 "$IGNITION_USERNAME"
log "Entered username: $IGNITION_USERNAME"
sleep 0.5
screenshot "07_username_entered"

# Tab to password field and type password
xdotool key Tab
sleep 0.3
xdotool type --clearmodifiers --delay 30 "$IGNITION_PASSWORD"
log "Entered password"
sleep 0.5
screenshot "08_password_entered"

# Submit login
xdotool key Return
log "Submitted login"
sleep 5
screenshot "09_login_submitted"

# Wait for Designer to fully open
log "Waiting for Designer to open..."
DESIGNER_WINDOW=""
DESIGNER_MAX_WAIT=60
DESIGNER_WAITED=0

while [ -z "$DESIGNER_WINDOW" ] && [ $DESIGNER_WAITED -lt $DESIGNER_MAX_WAIT ]; do
    sleep 3
    DESIGNER_WAITED=$((DESIGNER_WAITED + 3))
    DESIGNER_WINDOW=$(xdotool search --name "Ignition Designer" 2>/dev/null | grep -v "^${LAUNCHER_WINDOW}$" | head -1) || true
done

if [ -n "$DESIGNER_WINDOW" ]; then
    log "Designer opened successfully after login"
else
    log "Designer window not detected (may still be loading)"
fi

screenshot "10_final_state"

log "=========================================="
log "Automation complete"
log "=========================================="
log "Screenshots saved to: $SCREENSHOT_DIR"
