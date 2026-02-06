# Windows Deployment Guide

**Version:** 4.0.2
**Platform:** Windows 10, Windows 11, Windows Server 2019+
**Last Updated:** 2025-10-31

## Overview

This guide covers deploying the Ignition Automation Toolkit on Windows systems. The toolkit is distributed as a portable `.zip` archive that can be extracted and run anywhere without installation.

## System Requirements

### Minimum Requirements
- **OS:** Windows 10 (20H2+) or Windows 11
- **RAM:** 2GB (4GB recommended)
- **Disk Space:**
  - Source distribution: 100MB (+ 2GB for first run setup)
  - Full runtime bundle: 1GB
- **Python:** Not required for full runtime bundle; 3.10+ for source distribution
- **PowerShell:** 5.0+ (included in Windows 10+)
- **.NET Framework:** 4.5+ (included in Windows 10+)
- **Java:** JRE 11+ (for Ignition Designer automation)

### Verified Windows Versions
- ✅ Windows 10 (20H2, 21H1, 21H2, 22H2)
- ✅ Windows 11 (21H2, 22H2, 23H2)
- ✅ Windows Server 2019
- ✅ Windows Server 2022

## Quick Start

### Option 1: Full Runtime Bundle (Recommended)

**No Python installation required!**

1. Download `ignition-toolkit-v4.0.2-windows-windows-x64-full.zip`
2. Extract to desired location (e.g., `C:\Tools\ignition-toolkit`)
3. Double-click `run.bat`
4. Browser opens automatically to http://localhost:5000

### Option 2: Source Distribution

**Requires Python 3.10+**

1. Download `ignition-toolkit-v4.0.2-windows-portable.zip`
2. Extract to desired location
3. Double-click `run.bat`
4. First run installs dependencies (3-5 minutes)
5. Browser opens to http://localhost:5000

## Detailed Installation

### Pre-Installation Steps

#### 1. Check PowerShell Version

```powershell
# Open PowerShell and run:
$PSVersionTable.PSVersion

# Should show Major version 5 or higher
```

If PowerShell is outdated:
- Download from: https://aka.ms/powershell
- Or install via Windows Update

#### 2. Check .NET Framework

```powershell
# Check .NET version
Get-ItemProperty "HKLM:SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full" | Select-Object Version
```

Should show 4.5 or higher. If not, install from:
https://dotnet.microsoft.com/download/dotnet-framework

#### 3. Install Java (Required for Designer Automation)

Download and install Java 11+ from:
- **Adoptium**: https://adoptium.net/ (recommended)
- **Oracle**: https://www.oracle.com/java/technologies/downloads/

Verify installation:
```powershell
java -version
```

#### 4. Install Python (Source Distribution Only)

Download Python 3.10+ from: https://www.python.org/downloads/

**Important during installation:**
- ✅ Check "Add Python to PATH"
- ✅ Check "Install for all users" (optional)

Verify:
```powershell
python --version
```

### Installation from Archive

#### Extract Archive

1. Download the appropriate `.zip` file
2. Right-click → "Extract All..."
3. Choose destination (e.g., `C:\Tools\ignition-toolkit`)
4. Click "Extract"

#### First Run

1. Navigate to extracted directory
2. Double-click `run.bat`

**First run behavior:**

**Full Runtime Bundle:**
- Checks system prerequisites
- Starts server immediately
- Opens browser to http://localhost:5000
- Ready to use!

**Source Distribution:**
- Checks system prerequisites
- Creates Python virtual environment
- Installs dependencies
- Downloads Playwright browser (~300MB)
- Starts server
- Opens browser

**Estimated time:**
- Full bundle: <10 seconds
- Source: 3-5 minutes

### Configure Environment

1. Locate `.env.example` in toolkit directory
2. Copy to `.env`
3. Edit with Notepad++ or preferred editor

**Key settings:**

```ini
# Server Configuration
API_PORT=5000
API_HOST=0.0.0.0          # 127.0.0.1 for localhost only

# Ignition Gateway
IGNITION_GATEWAY_URL=http://localhost:8088

# AI Features (Optional)
ANTHROPIC_API_KEY=sk-ant-...

# Browser Settings
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers
SCREENSHOT_FPS=2
SCREENSHOT_QUALITY=80
```

### Create Desktop Shortcut

1. Right-click `run.bat`
2. Select "Create shortcut"
3. Drag shortcut to Desktop
4. (Optional) Right-click shortcut → Properties → Change Icon

## Running the Toolkit

### Start Server

**Option 1: Double-click `run.bat`**
- Terminal window opens
- Server starts
- Browser opens automatically

**Option 2: From Command Prompt**
```cmd
cd C:\Tools\ignition-toolkit
run.bat
```

**Option 3: From PowerShell**
```powershell
cd C:\Tools\ignition-toolkit
.\run.bat
```

### Access Web Interface

Browser opens automatically to: http://localhost:5000

Or manually navigate to:
- `http://localhost:5000`
- `http://localhost:{YOUR_PORT}` (if changed in `.env`)

### Stop Server

Press `Ctrl+C` in the terminal window, or simply close the window.

### Run as Windows Service (Advanced)

Using NSSM (Non-Sucking Service Manager):

1. Download NSSM: https://nssm.cc/download
2. Extract nssm.exe to a permanent location
3. Open PowerShell as Administrator:

```powershell
# Install service
.\nssm.exe install IgnitionToolkit "C:\Tools\ignition-toolkit\run.bat"

# Configure service
.\nssm.exe set IgnitionToolkit AppDirectory "C:\Tools\ignition-toolkit"
.\nssm.exe set IgnitionToolkit DisplayName "Ignition Automation Toolkit"
.\nssm.exe set IgnitionToolkit Description "Visual acceptance testing for Ignition SCADA"
.\nssm.exe set IgnitionToolkit Start SERVICE_AUTO_START

# Start service
.\nssm.exe start IgnitionToolkit

# Check status
.\nssm.exe status IgnitionToolkit
```

To remove service:
```powershell
.\nssm.exe stop IgnitionToolkit
.\nssm.exe remove IgnitionToolkit confirm
```

## Firewall Configuration

### Windows Defender Firewall

On first run, Windows may show a firewall prompt:
- Click "Allow access"
- Or configure manually:

```powershell
# Allow inbound connections (as Administrator)
New-NetFirewallRule -DisplayName "Ignition Toolkit" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
```

To remove rule:
```powershell
Remove-NetFirewallRule -DisplayName "Ignition Toolkit"
```

### Third-Party Firewalls

If using Norton, McAfee, etc.:
1. Add exception for `python.exe` or `run.bat`
2. Allow TCP port 5000
3. Consult firewall documentation for specific steps

## Upgrading

1. Stop current server (close terminal or Ctrl+C)
2. Download new version
3. Extract to new directory (e.g., `C:\Tools\ignition-toolkit-v4.1.0`)
4. Copy `.env` file from old version to new:
   ```cmd
   copy C:\Tools\ignition-toolkit-v4.0.2\.env C:\Tools\ignition-toolkit-v4.1.0\
   ```
5. Run new version

**User data location:** `C:\Users\{YourUsername}\.ignition-toolkit\`

This data persists across versions (credentials, execution history, configs).

## Troubleshooting

### Server Won't Start

**"Port 5000 is already in use"**
```powershell
# Find process using port
netstat -ano | findstr :5000

# Kill process (replace PID)
taskkill /PID <PID> /F

# Or change port in .env
echo API_PORT=5001 >> .env
```

**"Python not found" (source distribution)**
- Reinstall Python from https://www.python.org
- Ensure "Add to PATH" is checked during installation
- Restart terminal/PowerShell

**"PowerShell execution policy"**
```powershell
# If script execution is disabled
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Java Issues

**"Java not found"**
- Install Java from https://adoptium.net/
- Verify PATH:
  ```powershell
  $env:PATH
  # Should include Java bin directory
  ```
- Add to PATH manually if needed:
  ```powershell
  setx PATH "%PATH%;C:\Program Files\Java\jdk-11\bin"
  ```
- Restart terminal

### Playwright Browser Issues

**"Browser executable doesn't exist"**
```powershell
# Reinstall Playwright browser
cd C:\Tools\ignition-toolkit
$env:PLAYWRIGHT_BROWSERS_PATH=".playwright-browsers"
venv\Scripts\python.exe -m playwright install chromium
```

**"Download failed"**
- Check internet connection
- Check firewall/proxy settings
- Temporarily disable antivirus
- Try manual download from https://playwright.azureedge.net/

### Performance Issues

**High CPU usage:**
- Reduce screenshot FPS in `.env`: `SCREENSHOT_FPS=1`
- Lower quality: `SCREENSHOT_QUALITY=50`

**Slow startup:**
- Add exclusions in Windows Defender:
  - Toolkit directory
  - `venv` directory
  - `.playwright-browsers` directory

**Memory issues:**
- Close unused playbook executions
- Increase virtual memory (pagefile)
- Restart server periodically

### Antivirus False Positives

Windows Defender or other antivirus may flag Python scripts:

**Add Exclusions:**
1. Open Windows Security
2. Virus & threat protection → Manage settings
3. Exclusions → Add exclusion
4. Add folder: `C:\Tools\ignition-toolkit`

## Uninstalling

### Remove Application

1. Stop server (close terminal or Ctrl+C)
2. Delete toolkit directory: `C:\Tools\ignition-toolkit`
3. (Optional) Delete user data:
   ```powershell
   Remove-Item -Recurse -Force "$env:USERPROFILE\.ignition-toolkit"
   ```

### Remove Windows Service (if configured)

```powershell
# Stop and remove service
.\nssm.exe stop IgnitionToolkit
.\nssm.exe remove IgnitionToolkit confirm
```

### Remove Firewall Rules

```powershell
Remove-NetFirewallRule -DisplayName "Ignition Toolkit"
```

## Security Best Practices

1. **Network Access**
   - Set `API_HOST=127.0.0.1` for localhost only
   - Use Windows Firewall to restrict access

2. **Credentials**
   - Never store in playbook files
   - Use encrypted credential vault
   - Rotate regularly

3. **Updates**
   - Keep Windows updated
   - Update toolkit regularly
   - Monitor security advisories

4. **Antivirus**
   - Add trusted exclusions for toolkit directory
   - Scan downloaded archives before extraction

5. **User Permissions**
   - Run as standard user (not Administrator)
   - Use Administrator only for service installation

## Performance Optimization

### Disable Windows Defender Real-Time Scanning

For toolkit directory only (not system-wide):

1. Windows Security → Virus & threat protection
2. Manage settings → Exclusions
3. Add folder exclusions:
   - Toolkit directory
   - `venv\` subdirectory
   - `.playwright-browsers\` subdirectory

### Adjust Power Settings

For laptops:
1. Control Panel → Power Options
2. Select "High performance" plan
3. Advanced settings → Processor power management → Minimum: 100%

### Disable Unnecessary Startup Programs

```powershell
# List startup programs
Get-CimInstance Win32_StartupCommand | Select-Object Name, Command
```

Disable via Task Manager → Startup tab

## Support and Resources

- **Documentation**: https://github.com/your-org/ignition-toolkit/docs
- **Issues**: https://github.com/your-org/ignition-toolkit/issues
- **Platform Build Guide**: `docs/PLATFORM_BUILDS.md`
- **Getting Started**: `docs/getting_started.md`

---

**Last Reviewed:** 2025-10-31
**Applies to Version:** 4.0.2+
**Platform:** Windows 10, 11, Server 2019+
