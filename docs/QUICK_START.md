# Quick Start Guide

## Getting Started in 60 Seconds

### Windows

1. **Download** `ignition-toolkit-v4.0.2-windows-portable.zip` (or full runtime bundle)
2. **Extract** to any folder (e.g., `C:\Tools\ignition-toolkit`)
3. **Double-click** `run.bat`
4. **Wait** (first run: 3-5 minutes for setup, subsequent runs: instant)
5. **Done!** Browser opens automatically to http://localhost:5000

### Linux / WSL2

1. **Download** `ignition-toolkit-v4.0.2-linux-portable.tar.gz` (or full runtime bundle)
2. **Extract**: `tar -xzf ignition-toolkit-*.tar.gz`
3. **Run**: `cd ignition-toolkit-* && ./run.sh`
4. **Wait** (first run: 3-5 minutes for setup, subsequent runs: instant)
5. **Done!** Browser opens automatically to http://localhost:5000

## What Happens on First Run?

### Portable Distribution (Requires Python 3.10+)

**You'll see this output:**

```
========================================
Ignition Automation Toolkit v4.0.2
========================================

Checking system dependencies...
[OK] PowerShell found
[OK] .NET Framework found
[OK] Java Runtime found

Setting up Python environment...
Virtual environment not found - creating (first run only)...
This may take 3-5 minutes...

Creating virtual environment...
[OK] Virtual environment created
Installing dependencies...
[OK] Dependencies installed

Checking Playwright browsers...
Installing Playwright browsers (first run only)...
[OK] Playwright browsers installed

Starting Ignition Automation Toolkit...
Server will be available at: http://localhost:5000

Press Ctrl+C to stop the server

Server is running. Browser should have opened automatically.
If not, navigate to: http://localhost:5000
```

**Timeline:**
- System checks: ~5 seconds
- Creating venv: ~30 seconds
- Installing dependencies: ~2-3 minutes
- Downloading Playwright: ~1-2 minutes
- **Total: 3-5 minutes** (one-time only!)

### Full Runtime Bundle (No Python Required!)

**You'll see this output:**

```
========================================
Ignition Automation Toolkit v4.0.2
========================================

Checking system dependencies...
[OK] Java Runtime found

[OK] Virtual environment found
[OK] Virtual environment activated

[OK] Playwright browsers already installed

Starting Ignition Automation Toolkit...

Server is running. Browser should have opened automatically.
```

**Timeline:**
- System checks: ~3 seconds
- Server startup: ~5 seconds
- **Total: <10 seconds**

## What Happens on Subsequent Runs?

Just double-click `run.bat` (Windows) or `./run.sh` (Linux) and:

1. System checks (3 seconds)
2. Activate venv (instant)
3. Start server (5 seconds)
4. Browser opens automatically
5. **Total: <10 seconds**

## Prerequisites

### Portable Distribution

**Windows:**
- Python 3.10+ ([download](https://www.python.org/downloads/))
- Java JRE 11+ ([download](https://adoptium.net/)) - for Designer automation
- PowerShell 5.0+ (included in Windows 10+)

**Linux:**
- Python 3.10+: `sudo apt-get install python3.10 python3.10-venv`
- Java JRE 11+: `sudo apt-get install default-jre`
- System dependencies: `xdotool imagemagick`

**WSL2:**
- Same as Linux requirements
- X server on Windows (VcXsrv or X410) - for GUI applications
- See [WSL2 Deployment Guide](deployment/wsl2_deployment.md)

### Full Runtime Bundle

**Windows:**
- Java JRE 11+ ([download](https://adoptium.net/)) - for Designer automation
- PowerShell 5.0+ (included in Windows 10+)

**Linux:**
- Java JRE 11+
- System dependencies: `xdotool imagemagick`

## File Structure After First Run

```
ignition-toolkit-v4.0.2-windows-portable/
├── run.bat                    # ← Double-click this!
├── venv/                      # Python environment (auto-created)
├── .playwright-browsers/      # Chromium browser (auto-downloaded)
├── ignition_toolkit/          # Python package
├── playbooks/                 # YAML playbook library
│   ├── gateway/               # Gateway-only playbooks
│   ├── perspective/           # Perspective-only playbooks
│   └── examples/              # Example playbooks
├── frontend/dist/             # React web interface
├── docs/                      # Documentation
└── .env.example               # Configuration template
```

## Configuration (Optional)

To customize settings, copy `.env.example` to `.env` and edit:

```bash
# Windows
copy .env.example .env
notepad .env

# Linux
cp .env.example .env
nano .env
```

**Common settings:**

```ini
# Change port if 5000 is in use
API_PORT=5001

# Restrict to localhost only (default: accessible on network)
API_HOST=127.0.0.1

# Set your Ignition Gateway URL
IGNITION_GATEWAY_URL=http://192.168.1.100:8088

# Optional: Enable AI features
ANTHROPIC_API_KEY=sk-ant-...
```

## Troubleshooting

### "Python not found" (Windows)

1. Install Python from https://www.python.org/downloads/
2. **Important:** Check "Add Python to PATH" during installation
3. Restart terminal/command prompt
4. Try again

### "Java not found"

1. Install Java from https://adoptium.net/
2. Verify: `java -version`
3. If still not found, add to PATH manually

### "Port 5000 already in use"

**Windows:**
```powershell
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

**Linux:**
```bash
lsof -i :5000
kill -9 <PID>
```

Or change the port in `.env`:
```ini
API_PORT=5001
```

### Browser doesn't open automatically

Just manually navigate to: http://localhost:5000

### WSL2: "Cannot open display"

See [WSL2 Deployment Guide](deployment/wsl2_deployment.md) for X server setup.

## Next Steps

1. **Browse playbooks** at http://localhost:5000
2. **Run example playbooks** in the `playbooks/examples/` folder
3. **Duplicate and customize** existing playbooks
4. **Add credentials** via Credentials page (encrypted at rest)
5. **Read playbook syntax** in [docs/playbook_syntax.md](playbook_syntax.md)

## Support

- **Documentation:** [docs/getting_started.md](getting_started.md)
- **Platform Builds:** [docs/PLATFORM_BUILDS.md](PLATFORM_BUILDS.md)
- **Deployment Guides:**
  - [Linux](deployment/linux_deployment.md)
  - [Windows](deployment/windows_deployment.md)
  - [WSL2](deployment/wsl2_deployment.md)
- **Issues:** https://github.com/yourusername/ignition-toolkit/issues

---

**TL;DR:** Extract, double-click launcher, wait 3-5 minutes (first run), done!
