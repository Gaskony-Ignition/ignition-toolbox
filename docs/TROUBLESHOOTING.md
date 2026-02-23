# Troubleshooting Guide

Common issues and solutions for Ignition Toolbox.

---

## Table of Contents

1. [CloudDesigner Issues](#clouddesigner-issues)
2. [Playbook Execution Issues](#playbook-execution-issues)
3. [Connection Issues](#connection-issues)
4. [Installation Issues](#installation-issues)
5. [Debug Mode](#debug-mode)

---

## CloudDesigner Issues

### Container won't start

**Symptoms:**
- Clicking "Start Designer Container" does nothing
- No logs appear in the debug panel

**Solutions:**

1. **Check Docker is running:**
   - Open Docker Desktop or run `docker --version` in terminal
   - For WSL users: ensure Docker is accessible via `wsl docker --version`

2. **Check credential selection:**
   - Ensure a credential with a gateway URL is selected in the header dropdown
   - The gateway URL must be accessible from Docker (use host IP, not `localhost`)

3. **Check the debug panel:**
   - Expand "Show Debug Info" section on the Designer page
   - Look for error messages in the logs

4. **Try cleanup:**
   - Click "Cleanup All" to remove stale containers
   - Then try starting again

### Container starts but Designer doesn't load

**Symptoms:**
- Container shows as "Running"
- Browser shows connection error at localhost:8080

**Solutions:**

1. **Wait for full startup:**
   - First run can take several minutes while images are pulled
   - Watch the logs for "Designer ready" message

2. **Check port availability:**
   - Ensure port 8080 is not in use by another application
   - Run `netstat -an | grep 8080` to check

3. **Check Docker network:**
   - Run `docker ps` to see container status
   - Run `docker logs clouddesigner-guacamole-1` for Guacamole logs

### WSL Docker not detected

**Symptoms:**
- "Docker not installed" message on Windows with WSL

**Solutions:**

1. **Verify WSL Docker:**
   ```bash
   wsl docker --version
   ```

2. **Check WSL default distro:**
   ```bash
   wsl --list --verbose
   ```
   Ensure the distro with Docker is set as default.

3. **Restart WSL:**
   ```bash
   wsl --shutdown
   ```
   Then try again.

---

## Playbook Execution Issues

### Playbook fails immediately

**Symptoms:**
- Execution shows "Failed" status instantly
- No steps are executed

**Solutions:**

1. **Check YAML syntax:**
   - Validate the playbook YAML file
   - Look for indentation errors or missing required fields

2. **Check credential:**
   - Ensure the credential selected has valid username/password
   - Test the gateway URL is accessible

3. **Check step types:**
   - Ensure all step types in the playbook are valid
   - Review the step type documentation

### Browser steps fail

**Symptoms:**
- Steps involving Playwright/browser fail
- "Browser not found" or "Timeout" errors

**Solutions:**

1. **Install browsers:**
   - Run `npx playwright install chromium` in the backend directory
   - For packaged app, browsers should be pre-installed

2. **Increase timeout:**
   - Edit the playbook and increase step timeout values
   - Default timeout is 30 seconds

3. **Check selectors:**
   - View step selectors may have changed
   - Use browser DevTools to verify element selectors

### Step times out

**Symptoms:**
- Step shows "Timeout" error after waiting

**Solutions:**

1. **Check network:**
   - Ensure the gateway is accessible
   - Check for firewall blocking connections

2. **Increase timeout:**
   - Add `timeout: 60` (or higher) to the step configuration

3. **Check element visibility:**
   - The element may be hidden or not rendered
   - Add a `wait` step before the failing step

---

## Connection Issues

### WebSocket disconnected

**Symptoms:**
- Real-time updates stop working
- "WebSocket disconnected" message

**Solutions:**

1. **Refresh the page:**
   - WebSocket will automatically reconnect on page load

2. **Check backend:**
   - Ensure the Python backend is still running
   - Check for errors in the backend console

3. **Check firewall:**
   - Ensure WebSocket connections are allowed on the backend port

### API requests fail

**Symptoms:**
- Operations fail silently
- Network errors in browser console

**Solutions:**

1. **Check backend status:**
   - Look for the Python backend process
   - Check the backend console for errors

2. **Check CORS:**
   - In development, ensure CORS origins are configured
   - The packaged app uses `allow_origins=["*"]`

3. **Check port:**
   - Backend port may have changed (dynamic in Electron)
   - Restart the application

### Gateway connection refused

**Symptoms:**
- "Connection refused" when connecting to Ignition gateway

**Solutions:**

1. **Verify gateway URL:**
   - Check the URL format: `http://hostname:port`
   - Default Ignition port is 8088

2. **Check network:**
   - Ping the gateway host
   - Check firewall rules

3. **Check gateway status:**
   - Ensure Ignition gateway is running
   - Check gateway web interface is accessible

---

## Installation Issues

### App won't start

**Symptoms:**
- Application doesn't open
- Crashes immediately after launch

**Solutions:**

1. **Check system requirements:**
   - Windows 10/11 64-bit
   - Node.js 20+ (for development)
   - Python 3.10+ (for development)

2. **Reinstall:**
   - Uninstall the application
   - Delete `%APPDATA%\ignition-toolbox`
   - Reinstall from latest release

3. **Check logs:**
   - Windows: `%APPDATA%\ignition-toolbox\logs`
   - Look for error messages

### Auto-update fails

**Symptoms:**
- "Update available" but download fails
- Update installs but app reverts

**Solutions:**

1. **Manual update:**
   - Download latest release from GitHub
   - Install over existing version

2. **Check internet:**
   - Ensure GitHub releases are accessible
   - Check proxy/firewall settings

3. **Clear update cache:**
   - Delete `%APPDATA%\ignition-toolbox\updates`
   - Restart and try again

---

## Debug Mode

### Enabling Debug Logging

**Backend:**
Set environment variable before starting:
```bash
LOG_LEVEL=DEBUG python run_backend.py
```

**Frontend:**
Open browser DevTools (F12) and check Console tab.

### Log Locations

| Component | Location |
|-----------|----------|
| Backend logs | Console output + in-memory (viewable in UI) |
| Electron logs | `%APPDATA%\ignition-toolbox\logs` |
| Frontend logs | Browser DevTools Console |

### Viewing Backend Logs

1. Go to any page with playbook execution
2. Expand "Show Debug Info" or similar debug section
3. Logs are displayed in reverse chronological order (newest first)

### Reporting Issues

When reporting issues, please include:

1. **Version:** Found in Settings → About
2. **Platform:** Windows version, WSL version if applicable
3. **Steps to reproduce:** What you did before the error
4. **Error messages:** Full error text from logs
5. **Screenshots:** If applicable

Report issues at: https://github.com/Gaskony-Ignition/ignition-toolbox/issues

---

## Quick Reference

| Issue | First Step |
|-------|------------|
| CloudDesigner won't start | Check Docker + credential selection |
| Playbook fails | Check YAML syntax + credentials |
| WebSocket disconnected | Refresh page |
| API errors | Check backend is running |
| Gateway connection refused | Verify gateway URL + network |

---

*Last updated: February 2026*
