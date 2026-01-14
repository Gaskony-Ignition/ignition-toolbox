# Designer Playbooks

**Status: Available (v3.1.0+)**

This directory contains playbooks for Ignition Designer desktop application automation.

## Overview

Designer playbooks enable automated testing and setup of Ignition Designer across Windows, Linux, and WSL2 environments. These playbooks automate:
- Clicking "Launch Designer" button on Gateway webpage
- Designer application launch (via pre-installed Designer Launcher)
- Login automation using global credentials
- Project selection and opening
- Screenshot capture for verification

## Available Playbook

### launch_designer.yaml

Single comprehensive playbook that handles the complete Designer launch workflow.

**How it works:**
1. Opens Gateway webpage in browser (using Gateway URL from credential vault)
2. Clicks "Launch Designer" button
3. Button triggers the installed Designer Launcher application
4. Waits for Designer window to appear
5. Auto-fills credentials and logs in (uses **localgateway credential** automatically)
6. Opens specified project or stops for manual selection

**Parameters:**
- `project_name` (optional) - Project to open (leave empty for manual selection)

**Note:** Gateway URL, username, and password are automatically retrieved from the `localgateway` credential in the vault!

**Prerequisites:**
1. Add your Gateway credentials with Gateway URL:
   ```bash
   ignition-toolkit credential add localgateway \
     --username admin \
     --password your_password \
     --gateway-url http://localhost:9088 \
     --description "My Local Gateway"
   ```

**Usage via UI:**
1. Ensure `localgateway` credential is configured (see Prerequisites above)
2. Click "Configure" on the Launch Designer playbook
3. (Optional) Enter project name, or leave empty to select manually
4. Click "Execute"

**Usage via CLI:**
```bash
# No parameters needed if you want manual project selection
ignition-toolkit playbook run playbooks/designer/launch_designer.yaml

# With project name
ignition-toolkit playbook run playbooks/designer/launch_designer.yaml \
  --param project_name="MyProject"
```

## Setup Requirements

### Install Designer Automation Dependencies

**Windows:**
```bash
pip install "ignition-toolkit[designer]"
# Installs: pywinauto>=0.6.8
```

**Linux:**
```bash
pip install "ignition-toolkit[designer]"
# Installs: python-xlib>=0.33, pyatspi>=2.38.2

# Also install system tools:
sudo apt install xdotool imagemagick
```

**WSL2:**
```bash
# Same as Linux, plus X server (VcXsrv or WSLg)
pip install "ignition-toolkit[designer]"
sudo apt install xdotool imagemagick
```

## How It Works

Designer playbooks combine browser automation (for Gateway web UI) with desktop automation (for Designer application):

1. **Browser steps**: Navigate to Gateway, click "Launch Designer" button
2. **Protocol handler**: Browser triggers `designer://` protocol, launching Designer Launcher
3. **Designer launch**: Designer Launcher opens the Designer application
4. **Window detection**: Wait for Designer window to appear
5. **Login automation**: Auto-fill credentials and login (Windows/Linux native only)
6. **Project selection**: Open specified project or wait for manual selection

**IMPORTANT - WSL Limitation:**
- Browser automation (steps 1-3) works in WSL and successfully launches Designer on Windows
- Desktop automation (steps 5-6) requires native Windows Python, not WSL Python
- When running from WSL, Designer will launch but you must log in manually
- For full automation, run the toolkit from Windows PowerShell/CMD instead of WSL

## Platform-Specific Details

### Windows
- Uses **pywinauto** for window automation
- Detects Designer at: `C:\Program Files\Inductive Automation\Designer Launcher\`
- Supports both JNLP and native launcher executables

### Linux
- Uses **python-xlib** for window detection
- Uses **xdotool** for keyboard/mouse automation
- Uses **ImageMagick** for screenshots
- Detects Designer at: `/opt/ignition-designer`, `~/.local/ignition-designer`

### WSL2
- Can access Windows Designer installation via `/mnt/c/`
- Requires X server for GUI display
- Automatically detects WSL environment

## Future Enhancements

Planned Designer automation capabilities:
- Project configuration automation
- Tag database operations
- UDT creation and management
- Template deployment
- Script library updates
- Resource import/export
- View/Window creation

## Troubleshooting

**Designer window not detected:**
- Check that Designer actually launched (look for process)
- Verify window title matches expected patterns
- Try increasing timeout values

**Login automation fails:**
- Ensure credentials are correct
- Check that login dialog appears (window detection issue)
- Try running manually first to verify Designer works

**Platform-specific issues:**
- Windows: Ensure pywinauto installed (`pip show pywinauto`)
- Linux: Ensure xdotool installed (`which xdotool`)
- WSL2: Ensure X server running (`echo $DISPLAY` should show value)

### launch_designer_shortcut.yaml (NEW - WSL/PowerShell Method)

**Status: Production Ready (v3.44.13+)**

Alternative launch method using Windows shortcut command from WSL with PowerShell automation.

**How it works:**
1. Takes Designer launcher shortcut command as parameter
2. Launches Designer from WSL using PowerShell
3. Waits for login window
4. Auto-fills credentials using PowerShell SendKeys
5. Waits for project selection window
6. Searches and opens specified project using mouse automation

**All-in-one step:** Unlike the browser-based method, this uses a single `designer.launch_shortcut` step that handles launch, login, and project opening.

**Parameters:**
- `designer_shortcut` (required) - Full Designer launcher command
- `project_name` (required) - Project to open
- `gateway_credential` (required) - Gateway credential from vault (dropdown selector)

**Prerequisites:**
1. Add your Designer credentials:
   ```bash
   ignition-toolkit credential add localgateway \
     --username admin \
     --password your_password
   ```

2. Get your Designer shortcut command:
   - Right-click Designer Launcher shortcut → Properties
   - Copy the full Target value including arguments
   - Example: `C:\Program Files\Inductive Automation\Designer Launcher\designerlauncher.exe -Dapp.home=C:\Users\Name\.ignition\clientlauncher-data -Dapplication=LocalDocker`

**Usage via CLI:**
```bash
ignition-toolkit playbook run playbooks/designer/launch_designer_shortcut.yaml \
  --param designer_shortcut="C:\Program Files\Inductive Automation\Designer Launcher\designerlauncher.exe -Dapp.home=C:\Users\Name\.ignition\clientlauncher-data -Dapplication=LocalDocker" \
  --param project_name="Test" \
  --param gateway_credential="localgateway"
```

**Advantages over browser method:**
- Works from WSL without native Windows Python
- Faster (no browser overhead)
- More reliable (direct PowerShell automation)
- Single step instead of multiple steps

### launch_local_docker_designer.yaml (Example - Pre-configured)

**Status: Production Ready (v3.44.13+)**

Pre-configured example specifically for LocalDocker application with sensible defaults.

**Parameters:**
- `project_name` (required) - Project to open
- `designer_shortcut` (optional) - Defaults to LocalDocker setup
- `gateway_credential` (required) - Gateway credential from vault (dropdown selector)

**Usage via CLI:**
```bash
# Minimal usage
ignition-toolkit playbook run playbooks/designer/launch_local_docker_designer.yaml \
  --param project_name="Test" \
  --param gateway_credential="localgateway"

# Custom credential
ignition-toolkit playbook run playbooks/designer/launch_local_docker_designer.yaml \
  --param project_name="MyProject" \
  --param gateway_credential="my_gateway"
```

## Related Documentation

- See `/docs/playbook_syntax.md` for full playbook syntax
- See `CHANGELOG.md` for v3.1.0 Designer automation release notes
- See `tests/test_designer.py` for testing examples
