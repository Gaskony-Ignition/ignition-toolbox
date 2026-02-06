## Getting Started with Ignition Automation Toolkit

This guide will help you get up and running with the Ignition Automation Toolkit on Windows, Linux, or macOS.

## Installation

### Prerequisites

- Python 3.10 or higher
- pip
- Node.js 18+ (for frontend development)
- Ignition Gateway (for Gateway automation)

### Platform-Specific Notes

**Windows:**
- Use PowerShell or Command Prompt
- Activate venv with: `venv\Scripts\activate`
- Some features may require Visual C++ Build Tools

**Linux/macOS:**
- Use bash or zsh
- Activate venv with: `source venv/bin/activate`
- Linux may need: `sudo apt install python3-dev python3-venv`

### Quick Install (Cross-Platform)

The easiest way to install on any platform is using the Python task runner:

```bash
# Clone repository
git clone git@github.com:nigelgwork/ignition-playground.git
cd ignition-playground

# Install using Python task runner (works on all platforms)
python tasks.py install        # Install package in development mode
python tasks.py install-dev    # Install with dev dependencies
python tasks.py init           # Initialize credential vault

# Verify installation
python -m ignition_toolkit.cli --version
```

**Alternative: Using Makefile (Linux/macOS only)**

```bash
make install
make install-dev
make init
```

**Alternative: Manual Installation (All Platforms)**

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install package
pip install -e .

# Install Playwright browsers
playwright install chromium

# Verify installation
ignition-toolkit --version
```

## Quick Start

### 1. Initialize

```bash
# Initialize credential vault and directories
ignition-toolkit init
```

This creates:
- `~/.ignition-toolkit/` - Credential vault
- `./data/` - Database and artifacts
- `./playbooks/` - Playbook library

### 2. Add Credentials

```bash
# Add Gateway credential
ignition-toolkit credential add gateway_admin \
  --username admin \
  --password your_password \
  --description "Gateway Admin Credential"

# List credentials
ignition-toolkit credential list
```

### 3. List Available Playbooks

```bash
ignition-toolkit playbook list
```

### 4. Run a Playbook

```bash
# Run health check playbook
ignition-toolkit playbook run \
  playbooks/examples/simple_health_check.yaml \
  --param gateway_url=http://localhost:8088 \
  --param gateway_credential=gateway_admin
```

### 5. Start Web UI

**Option 1: Using Python CLI (Cross-Platform)**

```bash
# Start the web server
ignition-toolkit server start

# Check server status
ignition-toolkit server status

# Stop server
ignition-toolkit server stop
```

**Option 2: Using Python Task Runner**

```bash
# Start server
python tasks.py dev

# Check status (in another terminal)
python tasks.py status

# Stop server
python tasks.py stop
```

**Option 3: Using PowerShell Scripts (Windows)**

```powershell
.\scripts\start-server.ps1
.\scripts\check-server.ps1
.\scripts\stop-server.ps1
```

**Option 4: Using Makefile (Linux/macOS)**

```bash
make dev      # Start server
make status   # Check status
make stop     # Stop server
```

Open browser to http://localhost:5000

## Next Steps

- [Playbook Syntax](playbook_syntax.md) - Learn to write playbooks
- [Running Playbooks](RUNNING_PLAYBOOKS.md) - Execution guide
- [Playbook Library](PLAYBOOK_LIBRARY.md) - Browse and install playbooks
- [Playbook Best Practices](PLAYBOOK_BEST_PRACTICES.md) - Writing good playbooks

## Common Tasks

### Run Playbook with Parameters

```bash
ignition-toolkit playbook run my_playbook.yaml \
  --param param1=value1 \
  --param param2=value2
```

### Export Playbook for Sharing

```bash
ignition-toolkit playbook export \
  playbooks/gateway/module_upgrade.yaml \
  --output shared/module_upgrade.json
```

### Import Shared Playbook

```bash
ignition-toolkit playbook import \
  module_upgrade.json \
  --output-dir ./playbooks/imported
```

## Troubleshooting

### Package Import Errors

```bash
pip install -e . --force-reinstall
```

### Playwright Issues

```bash
playwright install --force chromium
```

### Database Issues

```bash
rm -f ./data/toolkit.db
# Restart - will recreate
```

## Getting Help

- Check the documentation in `docs/`
- Review example playbooks in `playbooks/`
- See `TESTING_GUIDE.md` for validation steps
