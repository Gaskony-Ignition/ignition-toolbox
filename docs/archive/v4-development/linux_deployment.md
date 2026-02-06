# Linux Deployment Guide

**Version:** 4.0.2
**Platform:** Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+, CentOS 8+)
**Last Updated:** 2025-10-31

## Overview

This guide covers deploying the Ignition Automation Toolkit on Linux systems. The toolkit is distributed as a portable `.tar.gz` archive that can be extracted and run anywhere.

## System Requirements

### Minimum Requirements
- **OS:** Linux with kernel 4.4+ (glibc 2.23+)
- **RAM:** 2GB (4GB recommended)
- **Disk Space:**
  - Source distribution: 100MB (+ 2GB for first run setup)
  - Full runtime bundle: 1GB
- **Python:** Not required for full runtime bundle; 3.10+ for source distribution
- **Network:** Internet access for:
  - First-run dependency installation (source distribution only)
  - Connecting to Ignition Gateway
  - Optional: AI features (Anthropic API)

### Tested Distributions
- ✅ Ubuntu 20.04 LTS, 22.04 LTS, 24.04 LTS
- ✅ Debian 11 (Bullseye), 12 (Bookworm)
- ✅ RHEL 8, 9
- ✅ CentOS 8 Stream, 9 Stream
- ✅ Fedora 38+
- ✅ Arch Linux (latest)

## Quick Start

### Option 1: Full Runtime Bundle (Recommended)

**No Python installation required!**

```bash
# 1. Download and extract
wget https://github.com/your-org/ignition-toolkit/releases/download/v4.0.2/ignition-toolkit-v4.0.2-linux-linux-x64-full.tar.gz
tar -xzf ignition-toolkit-v4.0.2-linux-linux-x64-full.tar.gz
cd ignition-toolkit-v4.0.2-linux-linux-x64-full

# 2. Run (everything is bundled)
./run.sh
```

The toolkit will start immediately - no setup required!

### Option 2: Source Distribution

**Requires Python 3.10+**

```bash
# 1. Download and extract
wget https://github.com/your-org/ignition-toolkit/releases/download/v4.0.2/ignition-toolkit-v4.0.2-linux-portable.tar.gz
tar -xzf ignition-toolkit-v4.0.2-linux-portable.tar.gz
cd ignition-toolkit-v4.0.2-linux-portable

# 2. First run (installs dependencies)
./run.sh
```

First run will:
- Create Python virtual environment
- Install all dependencies
- Download Playwright browser (~300MB)
- Start the server

## Detailed Installation

### Pre-Installation Steps

#### 1. Install System Dependencies

**Ubuntu/Debian:**
```bash
# Install system packages
sudo apt-get update
sudo apt-get install -y xdotool imagemagick default-jre libatspi2.0-dev python3-gi libx11-dev

# Optional: Python 3.10+ (if using source distribution)
sudo apt-get install -y python3.10 python3.10-venv python3-pip
```

**RHEL/CentOS/Fedora:**
```bash
# Install system packages
sudo dnf install -y xdotool ImageMagick java-11-openjdk at-spi2-core-devel python3-gobject libX11-devel

# Optional: Python 3.10+ (if using source distribution)
sudo dnf install -y python3.10 python3-pip
```

**Arch Linux:**
```bash
# Install system packages
sudo pacman -S xdotool imagemagick jre-openjdk at-spi2-core python-gobject libx11

# Optional: Python (if using source distribution)
sudo pacman -S python python-pip
```

#### 2. Verify Prerequisites

```bash
# Check system dependencies
which xdotool    # Should return path
which convert    # ImageMagick
java -version    # Should show Java 11+

# Check Python (source distribution only)
python3 --version  # Should show 3.10 or higher
```

### Installation from Archive

#### Extract Archive

```bash
# Create installation directory
mkdir -p ~/apps
cd ~/apps

# Extract (adjust filename for your distribution type)
tar -xzf ~/Downloads/ignition-toolkit-v4.0.2-linux-*.tar.gz

# Navigate to extracted directory
cd ignition-toolkit-v4.0.2-*
```

#### First Run

```bash
# Make launcher executable (should already be, but just in case)
chmod +x run.sh

# Start the toolkit
./run.sh
```

**What happens on first run:**

**Full Runtime Bundle:**
- Server starts immediately
- Browser opens to http://localhost:5000
- Ready to use!

**Source Distribution:**
- Creates Python virtual environment in `venv/`
- Installs dependencies from `pyproject.toml`
- Downloads Playwright Chromium browser (~300MB)
- Installs platform-specific dependencies
- Starts server
- Browser opens to http://localhost:5000

**Estimated first-run time:**
- Full bundle: <5 seconds
- Source distribution: 3-5 minutes (depending on internet speed)

### Post-Installation Configuration

#### Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit configuration
nano .env  # or vi, vim, etc.
```

**Important settings:**

```bash
# Server Configuration
API_PORT=5000                    # Change if port 5000 is in use
API_HOST=0.0.0.0                # 127.0.0.1 for localhost only

# Ignition Gateway
IGNITION_GATEWAY_URL=http://localhost:8088

# AI Features (Optional)
ANTHROPIC_API_KEY=sk-ant-...    # For AI-assisted features

# Browser Settings
PLAYWRIGHT_BROWSERS_PATH=./.playwright-browsers
SCREENSHOT_FPS=2
SCREENSHOT_QUALITY=80
```

#### Create Desktop Shortcut (Optional)

```bash
# Create .desktop file
cat > ~/.local/share/applications/ignition-toolkit.desktop <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Ignition Automation Toolkit
Comment=Visual acceptance testing for Ignition SCADA
Exec=$HOME/apps/ignition-toolkit-v4.0.2-*/run.sh
Icon=utilities-terminal
Terminal=true
Categories=Development;Utility;
EOF

# Update desktop database
update-desktop-database ~/.local/share/applications/
```

## Running the Toolkit

### Start Server

```bash
cd ~/apps/ignition-toolkit-v4.0.2-*
./run.sh
```

### Access Web Interface

Open browser to: **http://localhost:5000**

Or if you changed `API_PORT` in `.env`:
```
http://localhost:{YOUR_PORT}
```

### Stop Server

Press `Ctrl+C` in the terminal where `run.sh` is running.

### Background Service (Optional)

To run as a background service:

```bash
# Using nohup
nohup ./run.sh > ~/ignition-toolkit.log 2>&1 &

# Check if running
ps aux | grep ignition-toolkit

# Stop background process
pkill -f "ignition-toolkit"
```

**Or create a systemd service:**

```bash
# Create service file
sudo nano /etc/systemd/system/ignition-toolkit.service
```

```ini
[Unit]
Description=Ignition Automation Toolkit
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/apps/ignition-toolkit-v4.0.2-linux-portable
ExecStart=/home/your-username/apps/ignition-toolkit-v4.0.2-linux-portable/run.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable ignition-toolkit
sudo systemctl start ignition-toolkit

# Check status
sudo systemctl status ignition-toolkit

# View logs
sudo journalctl -u ignition-toolkit -f
```

## Firewall Configuration

### Allow Inbound Connections (If Accessing from Network)

**UFW (Ubuntu/Debian):**
```bash
sudo ufw allow 5000/tcp
sudo ufw reload
```

**firewalld (RHEL/CentOS/Fedora):**
```bash
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

**iptables:**
```bash
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
sudo iptables-save
```

## Upgrading

### To New Version

```bash
# 1. Stop current server (Ctrl+C or systemctl stop)

# 2. Download new version
cd ~/apps
wget https://github.com/your-org/ignition-toolkit/releases/download/v4.1.0/ignition-toolkit-v4.1.0-linux-*.tar.gz

# 3. Extract new version
tar -xzf ignition-toolkit-v4.1.0-linux-*.tar.gz

# 4. Copy configuration from old version
cp ignition-toolkit-v4.0.2-*/.env ignition-toolkit-v4.1.0-*/

# 5. Start new version
cd ignition-toolkit-v4.1.0-*
./run.sh
```

### Preserve Data

User data is stored in `~/.ignition-toolkit/`:
- Credentials (encrypted)
- Execution history database
- Configuration files

This data persists across versions.

## Troubleshooting

### Server Won't Start

**"Port 5000 already in use"**
```bash
# Find process using port 5000
sudo lsof -i :5000

# Kill the process
sudo kill -9 <PID>

# Or change port in .env
echo "API_PORT=5001" >> .env
```

**"Permission denied: ./run.sh"**
```bash
chmod +x run.sh
```

**"Python not found" (source distribution)**
```bash
# Install Python 3.10+
sudo apt-get install python3.10 python3.10-venv
```

### Dependencies Issues

**"xdotool: command not found"**
```bash
# Ubuntu/Debian
sudo apt-get install xdotool

# RHEL/CentOS
sudo dnf install xdotool
```

**"Java not found"**
```bash
# Ubuntu/Debian
sudo apt-get install default-jre

# RHEL/CentOS
sudo dnf install java-11-openjdk

# Verify
java -version
```

### Playwright Browser Issues

**"Browser executable doesn't exist"**
```bash
# Reinstall Playwright browsers
export PLAYWRIGHT_BROWSERS_PATH=./.playwright-browsers
./venv/bin/python -m playwright install chromium
```

**"Browser download failed"**
- Check internet connection
- Check firewall/proxy settings
- Try manual download:
  ```bash
  wget https://playwright.azureedge.net/builds/chromium/...
  ```

### Performance Issues

**High CPU usage:**
- Reduce screenshot FPS in `.env`: `SCREENSHOT_FPS=1`
- Lower screenshot quality: `SCREENSHOT_QUALITY=50`

**High memory usage:**
- Close unused playbook executions
- Restart server periodically
- Check for memory leaks with: `ps aux | grep python`

### Permissions Issues

**"Cannot write to ~/.ignition-toolkit"**
```bash
# Fix permissions
chmod -R u+rw ~/.ignition-toolkit
```

**"Cannot create virtual environment"**
```bash
# Install venv package
sudo apt-get install python3.10-venv
```

## Uninstalling

### Remove Application

```bash
# Stop server (Ctrl+C or systemctl stop)

# Remove application directory
rm -rf ~/apps/ignition-toolkit-v4.0.2-*

# Remove systemd service (if configured)
sudo systemctl stop ignition-toolkit
sudo systemctl disable ignition-toolkit
sudo rm /etc/systemd/system/ignition-toolkit.service
sudo systemctl daemon-reload
```

### Remove User Data

```bash
# Remove all user data (credentials, history, configs)
rm -rf ~/.ignition-toolkit

# Remove desktop shortcut
rm ~/.local/share/applications/ignition-toolkit.desktop
update-desktop-database ~/.local/share/applications/
```

## Security Best Practices

1. **Restrict Network Access**
   - Set `API_HOST=127.0.0.1` in `.env` for localhost only
   - Use firewall rules to limit access

2. **Credential Management**
   - Never store credentials in playbook files
   - Use the credential vault (encrypted at rest)
   - Rotate credentials regularly

3. **System Updates**
   - Keep Linux system updated
   - Update toolkit to latest version
   - Monitor security advisories

4. **File Permissions**
   - Toolkit files: `chmod 755` for executables, `644` for data files
   - Credential vault: Automatically secured with `600` permissions

5. **Audit Logging**
   - Review execution logs regularly
   - Monitor `~/.ignition-toolkit/logs/` directory
   - Set up log rotation

## Support and Resources

- **Documentation**: https://github.com/your-org/ignition-toolkit/docs
- **Issues**: https://github.com/your-org/ignition-toolkit/issues
- **Platform Build Guide**: `docs/PLATFORM_BUILDS.md`
- **General Documentation**: `docs/getting_started.md`

---

**Last Reviewed:** 2025-10-31
**Applies to Version:** 4.0.2+
**Platform:** Linux (all distributions)
