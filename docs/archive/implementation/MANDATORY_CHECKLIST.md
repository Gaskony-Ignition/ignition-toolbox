# MANDATORY PRE-RELEASE CHECKLIST

**DO NOT TELL THE USER CHANGES ARE READY WITHOUT COMPLETING ALL STEPS BELOW**

## Recommended: Use Automated Scripts

For version updates and server management, use these scripts (created to ensure reliability):

```bash
# Stop server cleanly
./stop_server.sh

# Start server with validation
./start_server.sh

# Update version + rebuild + restart (all-in-one)
./update_version.sh 2.0.2
```

## Manual Process (If Not Using Scripts)

### 1. Stop Server Cleanly
- [ ] Stop all running server instances: `./stop_server.sh`
- [ ] Verify port 5000 is free (should show "Port 5000 is free")
- [ ] Verify no hanging processes remain

### 2. Version Update
- [ ] Update `/git/ignition-playground/VERSION`
- [ ] Update `/git/ignition-playground/ignition_toolkit/__init__.py` (__version__ and __build_date__)
- [ ] Update `/git/ignition-playground/frontend/package.json` (version field)
- [ ] Add change description to version comment in __init__.py

### 3. Frontend Build
- [ ] Run: `cd /git/ignition-playground/frontend && npm run build`
- [ ] Verify build succeeded (no errors)
- [ ] Check that dist/ folder updated

### 4. Server Startup
- [ ] Start server: `./start_server.sh`
- [ ] Verify pre-flight checks pass
- [ ] Wait for "Application startup complete" message

### 5. Server Verification
- [ ] Check health endpoint: `curl -s http://localhost:5000/health | python3 -m json.tool`
- [ ] Verify version matches in health response
- [ ] Verify **only ONE** uvicorn process running: `ps aux | grep "uvicorn.*ignition_toolkit" | grep -v grep`
- [ ] Check WebSocket connection in browser console (should show "Connected")

### 6. UI Accessibility
- [ ] Open browser to http://localhost:5000
- [ ] Verify "Connected" status in top-right (green indicator)
- [ ] Check browser console for errors
- [ ] Verify UI version matches (bottom of sidebar or top bar)

### 7. Changes Testing
- [ ] Test the specific change made (run relevant playbook/feature)
- [ ] Verify fix actually works
- [ ] Test auto-reconnect: Watch status indicator while server reloads
- [ ] Verify no regressions introduced

## Version Number Rules

When updating version (from X.Y.Z):
- Bug fixes: Increment Z (e.g., 2.0.0 → 2.0.1)
- New features: Increment Y, reset Z (e.g., 2.0.1 → 2.1.0)
- Breaking changes: Increment X, reset Y and Z (e.g., 2.1.0 → 3.0.0)

## Server Management Scripts

### stop_server.sh
Comprehensive shutdown that:
- Kills all uvicorn processes for this project
- Kills hanging curl health check processes
- Forces clear port 5000
- Verifies clean shutdown

### start_server.sh
Verified startup that:
- Checks no server already running
- Verifies port 5000 is free
- Sets environment variables
- Starts uvicorn with --reload flag
- Provides clear feedback

### update_version.sh
All-in-one update procedure:
1. Stops server cleanly
2. Updates VERSION file
3. Updates __init__.py (version + build date)
4. Updates frontend/package.json
5. Rebuilds frontend
6. Starts server
7. Waits for health check
8. Verifies version

Usage: `./update_version.sh 2.0.2`

## WebSocket Auto-Reconnect (v2.0.1+)

The frontend now has robust WebSocket auto-reconnect:
- **Exponential backoff**: 1s → 1.5s → 2.25s → ... → max 30s
- **Status indicator**: Shows connecting/connected/reconnecting/disconnected
- **Automatic reconnection**: Reconnects when server reloads
- **Visual feedback**: Pulsing yellow indicator during reconnect attempts

## Critical Rules

1. **NEVER create multiple server instances** - Always use `./stop_server.sh` first
2. **NEVER leave hanging processes** - Scripts now handle cleanup automatically
3. **ALWAYS verify only ONE server running** - Check with `ps aux | grep uvicorn`
4. **ALWAYS wait for server ready** - Don't announce until health check passes

## Quick Command Reference

```bash
# Recommended: Use automated update script
./update_version.sh 2.0.2

# Manual commands (if needed)
./stop_server.sh
cd /git/ignition-playground/frontend && npm run build
./start_server.sh

# Verify system state
ps aux | grep "uvicorn.*ignition_toolkit" | grep -v grep  # Should show ONE process
curl -s http://localhost:5000/health | python3 -m json.tool
lsof -i :5000  # Should show uvicorn and node (Playwright)
```

## NEVER SKIP THIS CHECKLIST

User explicitly requested this checklist be followed EVERY TIME before announcing changes are ready.
**Rock-solid reliability** is the #1 priority. Failure to follow causes frustration and wasted time.
