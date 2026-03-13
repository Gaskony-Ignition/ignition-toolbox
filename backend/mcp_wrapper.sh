#!/usr/bin/env bash
# MCP server wrapper for use from WSL
# Discovers the Windows host IP and starts the MCP server pointing to the Toolbox backend.
#
# Usage in .mcp.json:
#   "command": "/git/ignition-toolbox/backend/mcp_wrapper.sh"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Find the venv python (supports both venv/ and .venv/ conventions)
if [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
  VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
elif [ -x "$SCRIPT_DIR/venv/bin/python" ]; then
  VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"
else
  echo "ERROR: No Python venv found in $SCRIPT_DIR/{.venv,venv}" >&2
  exit 1
fi

# Discover the Windows host IP (default gateway in WSL2)
WIN_HOST=$(ip route show default 2>/dev/null | awk '{print $3}')
if [ -z "$WIN_HOST" ]; then
  WIN_HOST="localhost"
fi

# Try common Toolbox backend ports (5000-5009)
TOOLBOX_URL=""
for port in $(seq 5000 5009); do
  if curl -s --connect-timeout 0.5 "http://${WIN_HOST}:${port}/health" >/dev/null 2>&1; then
    TOOLBOX_URL="http://${WIN_HOST}:${port}"
    break
  fi
done

# Fallback: also try localhost (works if mirrored networking is enabled)
if [ -z "$TOOLBOX_URL" ]; then
  for port in $(seq 5000 5009); do
    if curl -s --connect-timeout 0.5 "http://localhost:${port}/health" >/dev/null 2>&1; then
      TOOLBOX_URL="http://localhost:${port}"
      break
    fi
  done
fi

if [ -z "$TOOLBOX_URL" ]; then
  # Use default - the MCP server will return a helpful error if it can't connect
  TOOLBOX_URL="http://${WIN_HOST}:5000"
fi

export TOOLBOX_API_URL="$TOOLBOX_URL"

cd "$SCRIPT_DIR"
exec "$VENV_PYTHON" -m ignition_toolkit.mcp_server
