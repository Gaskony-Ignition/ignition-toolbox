# Platform-Specific Build System

**Version:** 4.0.2
**Last Updated:** 2025-10-31
**Status:** Production Ready - Phase 1 Complete ✅

## Overview

The Ignition Automation Toolkit now supports building platform-specific portable distributions for Linux and Windows. This document explains the new build system, directory structure, and usage.

## Architecture

### Directory Structure

```
ignition-playground/
├── platform-config/              # Platform-specific configurations
│   ├── linux/
│   │   ├── requirements.txt      # Linux Python dependencies
│   │   ├── system-deps.txt       # Linux system packages
│   │   ├── launcher.sh.template  # Linux launcher script
│   │   └── README.md            # Linux setup guide
│   ├── windows/
│   │   ├── requirements.txt      # Windows Python dependencies
│   │   ├── system-deps.txt       # Windows system requirements
│   │   ├── launcher.bat.template # Windows launcher script
│   │   └── README.md            # Windows setup guide
│   └── common/
│       ├── requirements.txt      # Shared dependencies
│       └── README.md            # Common dependencies guide
├── scripts/
│   ├── create_portable.py        # Enhanced with --platform argument
│   └── build/
│       ├── build_linux.py        # Linux build wrapper
│       ├── build_windows.py      # Windows build wrapper
│       ├── build_all.py          # Build all platforms
│       └── build_config.yaml     # Build configuration reference
```

### Key Features

1. **Platform Detection** - Automatic platform detection with manual override
2. **Template-Based Launchers** - Dynamic launcher generation from templates
3. **Dependency Separation** - Common, Linux-specific, and Windows-specific dependencies
4. **Build Orchestration** - Simplified platform-specific build scripts
5. **Full Runtime Bundles** - Optional inclusion of Python runtime and browsers

## Quick Start

### Building for Linux (Current Platform)

```bash
# Simple portable build (source distribution)
python3 scripts/build/build_linux.py

# Full runtime bundle (no Python needed on target)
python3 scripts/build/build_linux.py --include-runtime
```

### Building for Windows

```bash
# Simple portable build
python3 scripts/build/build_windows.py

# Full runtime bundle
python3 scripts/build/build_windows.py --include-runtime
```

### Building for All Platforms

```bash
# Build both Linux and Windows distributions
python3 scripts/build/build_all.py

# Build both with full runtime
python3 scripts/build/build_all.py --include-runtime
```

## Detailed Usage

### Enhanced create_portable.py

The core `scripts/create_portable.py` script now includes platform-specific support:

```bash
# Syntax
python3 scripts/create_portable.py [OPTIONS]

# Options
--platform {linux,windows,auto}   # Target platform (default: auto-detect)
--format {tar,zip,both}            # Archive format (default: both)
--include-runtime                  # Include full runtime bundle
--output-dir PATH                  # Custom output directory
```

**Examples:**

```bash
# Auto-detect platform and create tar.gz
python3 scripts/create_portable.py

# Build Linux distribution explicitly
python3 scripts/create_portable.py --platform linux --format tar

# Build Windows distribution with runtime
python3 scripts/create_portable.py --platform windows --format zip --include-runtime
```

### Output Artifacts

**Source Distributions** (no runtime):
- `dist/ignition-toolkit-v4.0.2-linux-portable.tar.gz` (~50MB)
- `dist/ignition-toolkit-v4.0.2-windows-portable.zip` (~50MB)

**Full Runtime Bundles**:
- `dist/ignition-toolkit-v4.0.2-linux-linux-x64-full.tar.gz` (~850MB)
- `dist/ignition-toolkit-v4.0.2-windows-windows-x64-full.zip` (~850MB)

## Platform-Specific Details

### Linux Distribution

**Included:**
- Python packages: `python-xlib`, `pyatspi`
- System dependencies documented in `platform-config/linux/system-deps.txt`
- Launcher: `run.sh`

**System Requirements:**
```bash
# Install system dependencies
xargs -a platform-config/linux/system-deps.txt sudo apt-get install -y
```

**Required Packages:**
- xdotool (X11 automation)
- imagemagick (image processing)
- default-jre (Java for Designer)
- libatspi2.0-dev, python3-gi, libx11-dev (development libraries)

**WSL2 Support:**
The Linux distribution includes WSL2 detection and guidance in the launcher. WSL2 users should:
1. Install an X server on Windows (e.g., VcXsrv, X410)
2. Set `DISPLAY` environment variable
3. Follow WSL2-specific documentation (to be created in Phase 2)

### Windows Distribution

**Included:**
- Python package: `pywinauto`
- System dependencies documented in `platform-config/windows/system-deps.txt`
- Launcher: `run.bat`

**System Requirements:**
- PowerShell 5.0+ (included in Windows 10+)
- .NET Framework 4.5+ (included in Windows 10+)
- Java Runtime Environment 11+ (manual installation)

**Installation:**
No manual dependency installation required for PowerShell and .NET. Java installation instructions are provided in launcher output if missing.

## Launcher Templates

### Template Variables

Launcher templates support variable substitution:

| Variable | Description | Example |
|----------|-------------|---------|
| `{TOOLKIT_VERSION}` | Current toolkit version | `4.0.2` |
| `{PYTHON_VERSION}` | Python version used | `3.10` |

### Template Locations

- Linux: `platform-config/linux/launcher.sh.template`
- Windows: `platform-config/windows/launcher.bat.template`

### Template Features

**Linux Launcher:**
- WSL2 detection and X server guidance
- System dependency checking with install instructions
- Virtual environment activation
- Playwright browser installation
- Server startup with port configuration

**Windows Launcher:**
- PowerShell, .NET, and Java version checking
- Virtual environment activation
- Playwright browser installation
- Server startup with port configuration
- Detailed error messages with resolution steps

## Development Workflow

### Adding New Platform-Specific Dependencies

**1. Python Dependencies:**

```bash
# Add to platform-config/linux/requirements.txt or platform-config/windows/requirements.txt
echo "new-package>=1.0.0" >> platform-config/linux/requirements.txt
```

**2. System Dependencies:**

```bash
# Add to platform-config/linux/system-deps.txt
echo "new-system-package" >> platform-config/linux/system-deps.txt
```

**3. Test Build:**

```bash
python3 scripts/build/build_linux.py
```

### Modifying Launchers

1. Edit template: `platform-config/{platform}/launcher.{sh|bat}.template`
2. Use `{VARIABLE}` syntax for substitutions
3. Test with: `python3 scripts/create_portable.py --platform {platform}`
4. Verify output: `dist/ignition-toolkit-v*/run.{sh|bat}`

### Testing Portable Distributions

```bash
# Extract to temporary location
mkdir -p /tmp/test-portable
cd /tmp/test-portable
tar -xzf dist/ignition-toolkit-v4.0.2-linux-portable.tar.gz

# Test launcher
cd ignition-toolkit-v4.0.2-linux-portable
./run.sh
```

## CI/CD Integration (Phase 3)

**Planned GitHub Actions workflows:**

1. **`.github/workflows/build-linux.yml`**
   - Trigger: Push to main, PR
   - Build Linux portable distribution
   - Run tests
   - Upload artifacts

2. **`.github/workflows/build-windows.yml`**
   - Trigger: Push to main, PR
   - Build Windows portable distribution
   - Run tests
   - Upload artifacts

3. **`.github/workflows/release.yml`**
   - Trigger: Git tag (v*.*.*)
   - Build all platforms
   - Create GitHub release
   - Attach portable archives

## Troubleshooting

### Build Errors

**"Platform template not found"**
- Ensure `platform-config/{platform}/` directory exists
- Verify `launcher.{sh|bat}.template` file is present

**"Permission denied" (Linux)**
```bash
chmod +x scripts/build/*.py
chmod +x scripts/create_portable.py
```

**"Python not found" (Windows)**
- Install Python 3.10+ from python.org
- Ensure Python is in PATH
- Restart terminal

### Runtime Errors

**"Missing system dependencies" (Linux)**
```bash
# Install all required packages
xargs -a platform-config/linux/system-deps.txt sudo apt-get install -y
```

**"Playwright browser not found"**
```bash
# Manual installation
export PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers
python -m playwright install chromium
```

## Future Enhancements (Phases 2-4)

### Phase 2: Documentation (Planned)
- Platform-specific deployment guides
- WSL2-specific documentation
- Troubleshooting expansion
- Video tutorials

### Phase 3: Testing & CI/CD (Planned)
- Automated GitHub Actions builds
- Platform-specific test suites
- Release automation
- Artifact signing

### Phase 4: Quality Improvements (Planned)
- Pre-flight system dependency checker
- Platform-specific error messages with solutions
- Installation command recommendations
- Automated testing of portable archives

## References

- **Build Configuration:** `scripts/build/build_config.yaml`
- **Platform README Files:**
  - Linux: `platform-config/linux/README.md`
  - Windows: `platform-config/windows/README.md`
  - Common: `platform-config/common/README.md`
- **Main README:** `README.md`
- **Architecture Decisions:** `ARCHITECTURE.md`
- **Roadmap:** `docs/ROADMAP.md`

## Support

**Questions:**
- See platform-specific README files in `platform-config/`
- Check `docs/` directory for additional documentation
- Review ARCHITECTURE.md for design decisions

**Issues:**
- Report platform-specific build issues on GitHub
- Include platform details, error messages, and steps to reproduce
- Attach relevant log files if available

---

**Last Reviewed:** 2025-10-31
**Next Review:** Phase 2 completion
**Maintainer:** Nigel G
