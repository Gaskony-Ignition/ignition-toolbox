# Windows Launcher Issue - Troubleshooting Guide

**Date**: 2025-10-31
**Version**: 4.0.5 (Issue reported)
**Resolution Date**: 2025-11-01
**Resolution Version**: 4.0.8 (Final fix with comprehensive logging)
**Status**: 🔍 INVESTIGATING (Enhanced debugging added)

## Resolution Summary

**Issue**: Windows launcher closed immediately, preventing server from starting and showing no error messages.

**Root Causes Identified**:
1. Interactive Java prompt caused immediate exit (v4.0.5)
2. Background server startup (`start /B`) hid all error messages (v4.0.6)

**Fixes Applied**:

### v4.0.6 (Partial Fix)
- Removed interactive Java prompt
- Replaced with informational message
- Java check now non-blocking

### v4.0.7 (Partial Fix - Still Failing)
- **Removed `start /B` background mode** - This was hiding all startup errors
- **Server now runs in foreground** - All errors immediately visible to user
- **Added debug output** - Shows Python path, module, working directory
- **Browser auto-opens after 5 seconds** - Background helper process
- **Helpful error messages** - Shows common fixes (port conflicts, dependencies, etc.)
- **Window stays open** - User can read error messages if server fails

**Problem**: Terminal still closes immediately with no visible errors

### v4.0.8 (Enhanced Debugging) 🔍
- **Comprehensive logging system** - Creates `launcher_debug.log` IMMEDIATELY
- **16 logging checkpoints** - Every step logged with timestamps
- **Persistent log file** - Survives even if window closes instantly
- **All errors captured** - Python, pip, server startup all logged
- **Step-by-step tracing** - Can see exactly where script fails
- **Enhanced error messages** - Points users to log file for diagnosis

**Purpose**: Even if the window closes instantly, `launcher_debug.log` will show:
1. Which step the launcher reached before failing
2. Any error messages from Python, pip, or the server
3. Exact directory paths and environment details
4. Timestamps showing how long each step took
5. Complete server output including any import errors

**Next Steps**: User should run v4.0.8 and provide the contents of `launcher_debug.log`

---

## Issue Description

The Windows launcher (`run.bat`) closes immediately after user presses 'y' to continue without Java, and the server does not start.

### Symptoms:
1. User runs `run.bat`
2. System checks pass (PowerShell ✓, .NET ✓)
3. Java check fails (expected - not installed)
4. Prompt: "Continue anyway? (y/N):"
5. User presses 'y'
6. **Terminal window closes immediately**
7. No server starts
8. `http://localhost:5000` unreachable

### Expected Behavior:
1. After pressing 'y', should continue with:
   - "Setting up Python environment..."
   - "Virtual environment found" or "Creating virtual environment..."
   - "Checking Playwright browsers..."
   - "Starting Ignition Automation Toolkit..."
   - "Server will be available at: http://localhost:5000"
2. Browser should open automatically
3. Server accessible at http://localhost:5000

## Troubleshooting Steps for Tomorrow

### 1. Check Batch Script Syntax
Look at `platform-config/windows/launcher.bat.template` around line 48-49:
```batch
set /p CONTINUE="Continue anyway? (y/N): "
if /i not "!CONTINUE!"=="y" exit /b 1
```

**Potential Issue**: The `exit /b 1` might be executing even when user presses 'y'

**Test**: Add debug output:
```batch
echo DEBUG: User entered: %CONTINUE%
set /p CONTINUE="Continue anyway? (y/N): "
echo DEBUG: CONTINUE value is: !CONTINUE!
if /i not "!CONTINUE!"=="y" (
    echo DEBUG: Exiting because continue is not y
    exit /b 1
)
echo DEBUG: Continuing with setup
```

### 2. Check Variable Expansion
The script uses `setlocal enabledelayedexpansion` but might have variable expansion issues.

**Test**: Replace line 48-49 with:
```batch
set /p CONTINUE="Continue anyway? (y/N): "
if /i "%CONTINUE%"=="y" goto :continue_setup
if /i "%CONTINUE%"=="Y" goto :continue_setup
exit /b 1
:continue_setup
echo Continuing with setup...
```

### 3. Manual Server Start Test
**To isolate the issue**, try running the server manually on Windows:

```cmd
cd C:\path\to\extracted\ignition-toolkit-v4.0.5-windows-x64-full
venv\Scripts\activate.bat
python -m ignition_toolkit.cli serve
```

This will show if the issue is:
- The launcher script logic (if manual start works)
- The Python environment (if manual start also fails)

### 4. Check for Python Errors
Look for any Python import errors or missing dependencies:

```cmd
venv\Scripts\python.exe -c "import ignition_toolkit; print('Import successful')"
```

### 5. Check Venv Activation
The launcher might not be activating the venv correctly:

**Current code** (line 97):
```batch
call venv\Scripts\activate.bat
```

**Test**: Add verification:
```batch
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated
where python
python --version
```

## Quick Fixes to Try

### Fix 1: Remove Background Process
**Current code** (line 136):
```batch
start /B venv\Scripts\python.exe -m ignition_toolkit.cli serve
```

**Try instead**:
```batch
echo Starting server (foreground mode for debugging)...
venv\Scripts\python.exe -m ignition_toolkit.cli serve
pause
```

This will:
- Run server in foreground (you'll see errors)
- Keep window open with `pause`

### Fix 2: Add Debug Pause Points
Add `pause` commands throughout the script to see where it fails:

```batch
echo Checking system dependencies...
pause

echo Setting up Python environment...
pause

echo Starting server...
pause
```

## Files to Check

1. **Launcher Template**: `/git/ignition-playground/platform-config/windows/launcher.bat.template`
   - Lines 48-49: Java prompt handling
   - Lines 96-103: Venv activation
   - Lines 134-136: Server start

2. **Built Launcher**: `C:\extracted\ignition-toolkit-v4.0.5-windows-x64-full\run.bat`
   - Verify template substitution worked correctly
   - Check for any corruption during ZIP extraction

3. **Python Entry Point**: `/git/ignition-playground/ignition_toolkit/cli.py`
   - Verify the `serve` command exists and works

## Comparison with Linux

The Linux version (`launcher.sh.template`) works correctly. Compare:

**Linux** (line 146):
```bash
./venv/bin/python -m ignition_toolkit.cli serve &
SERVER_PID=$!
```

**Windows** (line 136):
```batch
start /B venv\Scripts\python.exe -m ignition_toolkit.cli serve
```

Both use the same approach (`python -m`), so the issue is likely:
- Windows-specific batch script syntax
- Variable expansion in the Java prompt section
- Background process handling with `start /B`

## Recommended Immediate Fix

Replace lines 46-50 in `launcher.bat.template` with:

```batch
) else (
    echo [OK] Java Runtime found
)

echo.
echo NOTE: Java is not required for Gateway and Perspective automation
echo       Java is only needed for Designer automation
echo.
REM Continue without prompting for now - Java is optional
```

This removes the interactive prompt that's causing issues.

## Log Files to Collect

When testing tomorrow, collect:
1. Full console output (copy/paste or screenshot)
2. Output of `venv\Scripts\python.exe -m ignition_toolkit.cli serve`
3. Windows Event Viewer logs (if any)
4. Contents of `data/` directory (any log files)

## Next Session Tasks

- [ ] Test manual server start: `venv\Scripts\python.exe -m ignition_toolkit.cli serve`
- [ ] Add debug echoes to identify exact failure point
- [ ] Test without background process (`start /B`)
- [ ] Compare working Linux script vs Windows script
- [ ] Rebuild Windows distribution with fixes
- [ ] Verify on actual Windows machine

---

**Commit with this issue**: da87116
**GitHub URL**: https://github.com/nigelgwork/ignition-playground/commit/da87116
