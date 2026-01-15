# WSL2 Deployment Guide

**Version:** 4.0.2
**Platform:** Windows Subsystem for Linux 2 (WSL2)
**Last Updated:** 2025-10-31

## Overview

This guide covers deploying the Ignition Automation Toolkit on Windows Subsystem for Linux 2 (WSL2). WSL2 users should use the **Linux portable distribution** with additional configuration for GUI applications.

## Why WSL2?

**Advantages:**
- Native Linux environment on Windows
- Better performance than WSL1
- Full system call compatibility
- Easy file access between Windows and Linux
- Ideal for developers familiar with Linux tools

**Considerations:**
- Requires X server on Windows for GUI applications (Playwright browser)
- Additional setup vs native Windows or Linux
- Slightly higher complexity

## Prerequisites

### Windows Side

1. **Windows Version:**
   - Windows 10 version 2004+ (Build 19041+)
   - Windows 11 (all versions)

2. **WSL2 Installed:**
   ```powershell
   # Check WSL version
   wsl --list --verbose

   # Should show "VERSION 2" for your distribution
   ```

3. **Install WSL2 (if needed):**
   ```powershell
   # As Administrator
   wsl --install

   # Or install specific distribution
   wsl --install -d Ubuntu-22.04
   ```

4. **X Server for Windows:**
   Choose one:
   - **VcXsrv** (recommended, free): https://sourceforge.net/projects/vcxsrv/
   - **X410** (paid, Microsoft Store): https://www.microsoft.com/store/apps/9NLP712ZMN9Q
   - **MobaXterm** (free, includes X server): https://mobaxterm.mobatek.net/

### Linux Side (WSL2 Distribution)

Use **Ubuntu 22.04 LTS** (recommended) or compatible distribution:
```bash
# Check distribution
cat /etc/os-release
```

## Installation

### Step 1: Install X Server on Windows

#### Using VcXsrv (Recommended)

1. Download and install VcXsrv from https://sourceforge.net/projects/vcxsrv/

2. Launch XLaunch (start menu → VcXsrv → XLaunch)

3. Configuration wizard:
   - **Display settings:** Multiple windows, Display number: 0
   - **Client startup:** Start no client
   - **Extra settings:**
     - ✅ Clipboard
     - ✅ Primary Selection
     - ✅ Native opengl
     - ✅ **Disable access control** (important!)
   - Click "Finish"

4. Save configuration:
   - File → Save configuration as `config.xlaunch`
   - Place in Startup folder for auto-start:
     ```
     C:\Users\{YourName}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\
     ```

#### Using X410

1. Install from Microsoft Store
2. Launch X410 (will run in system tray)
3. Right-click tray icon → Settings
4. Enable "Allow Public Access"

### Step 2: Configure WSL2 Environment

Open WSL2 terminal (Ubuntu or your distribution):

```bash
# Get Windows host IP (for X server connection)
export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0

# Add to bash profile for persistence
echo 'export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '"'"'{print $2}'"'"'):0' >> ~/.bashrc

# Reload
source ~/.bashrc

# Verify
echo $DISPLAY
# Should show something like: 172.x.x.x:0
```

### Step 3: Install System Dependencies

```bash
# Update package lists
sudo apt-get update

# Install required system packages
sudo apt-get install -y \
    xdotool \
    imagemagick \
    default-jre \
    libatspi2.0-dev \
    python3-gi \
    libx11-dev \
    x11-apps

# Test X server connection
xeyes
# Should open a window with eyes following your cursor
# If this works, X server is configured correctly!
```

### Step 4: Install Ignition Toolkit

Download **Linux portable distribution**:

```bash
# Navigate to home directory
cd ~

# Create apps directory
mkdir -p ~/apps
cd ~/apps

# Download Linux distribution
wget https://github.com/your-org/ignition-toolkit/releases/download/v4.0.2/ignition-toolkit-v4.0.2-linux-portable.tar.gz

# Extract
tar -xzf ignition-toolkit-v4.0.2-linux-portable.tar.gz
cd ignition-toolkit-v4.0.2-linux-portable

# Make launcher executable
chmod +x run.sh
```

### Step 5: First Run

```bash
# Start toolkit
./run.sh
```

**What happens:**
1. Launcher detects WSL2 environment
2. Verifies DISPLAY variable is set
3. Creates Python virtual environment
4. Installs dependencies
5. Downloads Playwright browser
6. Starts server
7. Opens browser window via X server

**Expected output:**
```
========================================
Ignition Automation Toolkit v4.0.2
========================================

WSL2 detected
Make sure you have an X server running on Windows (e.g., VcXsrv, X410)
Set DISPLAY environment variable if not already set
Setting DISPLAY=172.x.x.x:0

Checking system dependencies...
✓ xdotool found
✓ convert found
✓ java found

Activating virtual environment...
Virtual environment activated

Starting Ignition Automation Toolkit...
Server will be available at: http://localhost:5000
```

### Step 6: Access Web Interface

**From WSL2:**
Open browser in WSL2 (will display via X server):
```bash
# Firefox (if installed)
firefox http://localhost:5000 &

# Or use toolkit's built-in browser launch
```

**From Windows:**
Open any Windows browser and navigate to:
```
http://localhost:5000
```

This works because WSL2 shares the network with Windows!

## Configuration

### Environment Variables

Create/edit `.env` file in toolkit directory:

```bash
cd ~/apps/ignition-toolkit-v4.0.2-linux-portable
nano .env
```

**Important WSL2-specific settings:**

```ini
# Server (accessible from Windows)
API_HOST=0.0.0.0        # Important: allows Windows access
API_PORT=5000

# Display (X server)
DISPLAY=:0              # Usually set automatically by run.sh

# Ignition Gateway
IGNITION_GATEWAY_URL=http://localhost:8088

# Playwright browsers
PLAYWRIGHT_BROWSERS_PATH=./.playwright-browsers
```

### Windows Firewall

WSL2 uses Hyper-V networking. You may need to allow WSL2 through Windows Firewall:

```powershell
# Run in PowerShell as Administrator
New-NetFirewallRule -DisplayName "WSL2" -Direction Inbound -InterfaceAlias "vEthernet (WSL)" -Action Allow
```

## Accessing Files Between Windows and WSL2

### From WSL2 to Windows

Windows drives are mounted at `/mnt/`:

```bash
# Access Windows C: drive
cd /mnt/c/Users/YourName/Documents

# Access Windows D: drive
cd /mnt/d/
```

### From Windows to WSL2

WSL2 filesystem accessible via network path:

```
\\wsl$\Ubuntu-22.04\home\yourname\
```

Or in File Explorer:
1. Address bar: `\\wsl$`
2. Navigate to your distribution
3. Bookmark for easy access

### Best Practices

**For playbooks:** Store in WSL2 filesystem for better performance:
```bash
~/apps/ignition-toolkit-v4.0.2-linux-portable/playbooks/
```

**For logs/output:** Can use either location:
```bash
# WSL2 (faster)
~/.ignition-toolkit/

# Windows (easier access from Windows apps)
/mnt/c/Users/YourName/ignition-toolkit-data/
```

## Troubleshooting

### X Server Issues

**"Cannot open display"**

1. Verify X server is running on Windows:
   - VcXsrv: Check system tray for X icon
   - X410: Check system tray

2. Check DISPLAY variable:
   ```bash
   echo $DISPLAY
   # Should show: 172.x.x.x:0 or similar
   ```

3. Test X server:
   ```bash
   xeyes
   # Should open a window
   ```

4. Verify firewall:
   ```powershell
   # Windows PowerShell
   New-NetFirewallRule -DisplayName "VcXsrv" -Direction Inbound -Program "C:\Program Files\VcXsrv\vcxsrv.exe" -Action Allow
   ```

5. Check X server settings:
   - VcXsrv: Ensure "Disable access control" is checked
   - X410: Enable "Allow Public Access"

**"Connection refused"**

```bash
# Get Windows IP
cat /etc/resolv.conf | grep nameserver

# Set DISPLAY manually
export DISPLAY=<WINDOWS_IP>:0

# Test
xeyes
```

### Network Issues

**Cannot access from Windows browser:**

1. Check server is listening on 0.0.0.0:
   ```bash
   # In toolkit directory
   grep API_HOST .env
   # Should show: API_HOST=0.0.0.0
   ```

2. Verify server is running:
   ```bash
   netstat -tulpn | grep 5000
   ```

3. Try Windows localhost:
   ```
   http://localhost:5000
   ```

### Performance Issues

**Slow file access:**
- Store toolkit files in WSL2 filesystem (not `/mnt/c/`)
- Use Linux paths: `~/apps/` instead of `/mnt/c/Users/...`

**High resource usage:**
- Limit WSL2 memory in `.wslconfig`:

Create `C:\Users\{YourName}\.wslconfig`:
```ini
[wsl2]
memory=4GB
processors=2
```

Then restart WSL2:
```powershell
wsl --shutdown
```

### Browser Issues

**Playwright browser won't start:**

1. Verify X server is working:
   ```bash
   xeyes  # Should display
   ```

2. Reinstall browser:
   ```bash
   export PLAYWRIGHT_BROWSERS_PATH=./.playwright-browsers
   ./venv/bin/python -m playwright install chromium
   ```

3. Check browser dependencies:
   ```bash
   ./venv/bin/playwright install-deps chromium
   ```

## Advanced Configuration

### WSL2 Integration with Windows Terminal

Add profile to Windows Terminal for easy access:

1. Open Windows Terminal settings (Ctrl+,)
2. Add new profile:

```json
{
    "guid": "{generate-new-guid}",
    "name": "Ignition Toolkit (WSL2)",
    "commandline": "wsl.exe -d Ubuntu-22.04 -e bash -c 'cd ~/apps/ignition-toolkit-v4.0.2-linux-portable && ./run.sh'",
    "hidden": false,
    "icon": "🔧"
}
```

### Auto-Start X Server and Toolkit

**1. Auto-start VcXsrv:**
- Save VcXsrv config to Startup folder (see Step 1)

**2. Auto-start toolkit via Windows Task Scheduler:**

Create batch file `C:\Scripts\start-toolkit-wsl2.bat`:
```bat
@echo off
wsl -d Ubuntu-22.04 -e bash -c "cd ~/apps/ignition-toolkit-v4.0.2-linux-portable && ./run.sh"
```

Create scheduled task:
```powershell
# As Administrator
$action = New-ScheduledTaskAction -Execute "C:\Scripts\start-toolkit-wsl2.bat"
$trigger = New-ScheduledTaskTrigger -AtLogon
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive
Register-ScheduledTask -TaskName "Ignition Toolkit WSL2" -Action $action -Trigger $trigger -Principal $principal
```

## Comparison: WSL2 vs Native

| Feature | WSL2 | Native Linux | Native Windows |
|---------|------|--------------|----------------|
| Setup Complexity | Medium | Low | Low |
| Performance | Good | Excellent | Excellent |
| File Access | Windows + Linux | Linux only | Windows only |
| GUI Apps | Via X Server | Native | Native |
| Designer Automation | ✅ (via X11) | ✅ | ✅ (Better) |
| Best For | Linux devs on Windows | Dedicated Linux | Windows users |

**Recommendation:**
- Use **WSL2** if you: prefer Linux tools, develop cross-platform, want flexibility
- Use **Native Windows** if you: want simplest setup, Windows-only environment
- Use **Native Linux** if you: have dedicated Linux machine, need best performance

## Support

**WSL2-Specific Issues:**
- WSL2 Documentation: https://docs.microsoft.com/windows/wsl/
- VcXsrv Issues: https://sourceforge.net/p/vcxsrv/wiki/
- X410 Support: https://x410.dev/cookbook/

**Toolkit Issues:**
- General Documentation: `docs/getting_started.md`
- Linux Guide: `docs/deployment/linux_deployment.md`
- Platform Builds: `docs/PLATFORM_BUILDS.md`

---

**Last Reviewed:** 2025-10-31
**Applies to Version:** 4.0.2+
**Platform:** WSL2 (Windows 10 20H2+, Windows 11)
