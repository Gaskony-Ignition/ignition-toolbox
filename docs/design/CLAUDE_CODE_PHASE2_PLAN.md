# Claude Code Integration - Phase 2 Implementation Plan

**Status:** Planned (Not Yet Implemented)
**Estimated Effort:** 7-11 hours
**Current Version:** Phase 1 (Manual Launch) is complete in v2.2.0

## Overview

Phase 2 transforms the Claude Code integration from a manual copy-paste workflow into a fully embedded terminal experience with WebSocket proxying and real-time interaction.

## Architecture

### Current State (Phase 1)
- User clicks "Claude Code" button
- Dialog shows pre-generated command
- User copies command and runs in external terminal
- User manually returns to UI to resume execution

### Target State (Phase 2)
- User clicks "Claude Code" button
- Embedded terminal opens directly in UI
- Claude Code process spawns automatically with full context
- Real-time terminal interaction (no copy/paste)
- Playbook changes auto-reload in UI
- One-click experience, seamless workflow

## Components

### 1. Backend WebSocket Proxy

**File:** `ignition_toolkit/api/app.py`

**Purpose:** Proxy WebSocket connections to Claude Code PTY process

**Dependencies:**
```bash
pip install python-pty
```

**Implementation:**

```python
import pty
import os
import subprocess
import asyncio
from typing import Dict
from fastapi import WebSocket, WebSocketDisconnect

# Global process tracker
claude_code_processes: Dict[str, subprocess.Popen] = {}

@app.websocket("/ws/claude-code/{execution_id}")
async def claude_code_terminal(websocket: WebSocket, execution_id: str):
    """
    WebSocket endpoint for embedded Claude Code terminal.

    Spawns a Claude Code process with PTY and proxies stdin/stdout
    between the WebSocket client and the process.
    """
    await websocket.accept()

    try:
        # Get execution context
        engine = active_engines.get(execution_id)
        if not engine:
            await websocket.send_json({"error": "Execution not found"})
            await websocket.close()
            return

        execution_state = engine.get_current_execution()
        if not execution_state:
            await websocket.send_json({"error": "Execution state unavailable"})
            await websocket.close()
            return

        # Find playbook file
        playbook_name = execution_state.playbook_name
        playbooks_dir = Path("./playbooks")
        playbook_path = None

        for yaml_file in playbooks_dir.rglob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    playbook_data = yaml.safe_load(f)
                    if playbook_data and playbook_data.get('name') == playbook_name:
                        playbook_path = str(yaml_file.absolute())
                        break
            except Exception:
                continue

        if not playbook_path:
            await websocket.send_json({"error": f"Playbook file not found for '{playbook_name}'"})
            await websocket.close()
            return

        # Build context message (same as Phase 1)
        context_parts = [
            f"# Playbook Execution Debug Session",
            f"",
            f"**Execution ID:** {execution_id}",
            f"**Playbook:** {playbook_name}",
            f"**Status:** {execution_state.status.value}",
            f"**Current Step:** {execution_state.current_step_index + 1 if execution_state.current_step_index is not None else 'N/A'}",
            f"",
        ]

        if execution_state.step_results:
            context_parts.append("## Step Results:")
            for idx, result in enumerate(execution_state.step_results, 1):
                status_emoji = "✅" if result.get("status") == "success" else "❌"
                context_parts.append(f"{status_emoji} **Step {idx}:** {result.get('step_name', 'Unknown')}")
                if result.get("error"):
                    context_parts.append(f"   Error: {result['error']}")

        if execution_state.parameters:
            context_parts.append("")
            context_parts.append("## Parameters:")
            for key, value in execution_state.parameters.items():
                display_value = "***" if any(s in key.lower() for s in ["password", "token", "key", "secret"]) else value
                context_parts.append(f"- {key}: {display_value}")

        context_message = "\n".join(context_parts) + "\n\nYou are debugging a paused Ignition Automation Toolkit playbook execution. The playbook YAML file is open for editing. With user approval, edit the playbook to resolve issues."

        # Spawn Claude Code process with PTY
        master_fd, slave_fd = pty.openpty()

        process = subprocess.Popen(
            ["claude-code", "-p", playbook_path, "-m", context_message],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            preexec_fn=os.setsid,
            close_fds=True
        )

        # Store process for lifecycle management
        claude_code_processes[execution_id] = {
            'process': process,
            'master_fd': master_fd,
            'slave_fd': slave_fd
        }

        os.close(slave_fd)  # Parent doesn't need slave end

        logger.info(f"Started Claude Code process for execution {execution_id} (PID: {process.pid})")

        # Task: Forward output from PTY to WebSocket
        async def forward_output():
            loop = asyncio.get_event_loop()
            while process.poll() is None:
                try:
                    # Read from PTY (non-blocking)
                    output = await loop.run_in_executor(None, os.read, master_fd, 4096)
                    if output:
                        await websocket.send_bytes(output)
                    else:
                        await asyncio.sleep(0.01)
                except OSError as e:
                    logger.error(f"PTY read error: {e}")
                    break
                except Exception as e:
                    logger.error(f"Output forwarding error: {e}")
                    break

            # Process terminated
            logger.info(f"Claude Code process {process.pid} terminated")

        # Task: Forward input from WebSocket to PTY
        async def forward_input():
            try:
                while True:
                    data = await websocket.receive_bytes()
                    os.write(master_fd, data)
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for execution {execution_id}")
            except Exception as e:
                logger.error(f"Input forwarding error: {e}")

        # Run both tasks concurrently
        await asyncio.gather(
            forward_output(),
            forward_input(),
            return_exceptions=True
        )

    except Exception as e:
        logger.exception(f"Claude Code terminal error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass

    finally:
        # Cleanup
        if execution_id in claude_code_processes:
            proc_info = claude_code_processes[execution_id]
            process = proc_info['process']
            master_fd = proc_info['master_fd']

            try:
                # Terminate process
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            except Exception as e:
                logger.error(f"Process cleanup error: {e}")

            try:
                os.close(master_fd)
            except:
                pass

            del claude_code_processes[execution_id]
            logger.info(f"Cleaned up Claude Code session for execution {execution_id}")

        try:
            await websocket.close()
        except:
            pass


@app.post("/api/executions/{execution_id}/claude-code/stop")
async def stop_claude_code_session(execution_id: str):
    """
    Manually stop a running Claude Code session.

    Useful for cleanup or when user wants to exit terminal.
    """
    if execution_id in claude_code_processes:
        proc_info = claude_code_processes[execution_id]
        process = proc_info['process']

        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

        try:
            os.close(proc_info['master_fd'])
        except:
            pass

        del claude_code_processes[execution_id]

        return {"status": "stopped", "execution_id": execution_id}

    return {"status": "not_found", "execution_id": execution_id}


# Add startup event to clean up any orphaned processes
@app.on_event("startup")
async def cleanup_orphaned_claude_code_processes():
    """Clean up any Claude Code processes that weren't properly terminated"""
    import psutil

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'claude-code' in ' '.join(proc.info['cmdline'] or []):
                logger.warning(f"Found orphaned Claude Code process (PID: {proc.info['pid']}), terminating...")
                proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
```

### 2. Frontend Embedded Terminal

**File:** `frontend/src/components/EmbeddedTerminal.tsx`

**Purpose:** xterm.js terminal component with WebSocket connection

**Dependencies:**
```bash
npm install xterm xterm-addon-fit xterm-addon-web-links
```

**Implementation:**

```typescript
/**
 * EmbeddedTerminal - Full terminal emulator with WebSocket connection
 *
 * Provides a real terminal experience for Claude Code sessions.
 */

import { useEffect, useRef, useState } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { WebLinksAddon } from 'xterm-addon-web-links';
import { Box, Alert, CircularProgress, Typography } from '@mui/material';
import 'xterm/css/xterm.css';

interface EmbeddedTerminalProps {
  executionId: string;
  onClose?: () => void;
  onError?: (error: string) => void;
}

export function EmbeddedTerminal({
  executionId,
  onClose,
  onError,
}: EmbeddedTerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const terminal = useRef<Terminal | null>(null);
  const fitAddon = useRef<FitAddon | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<'connecting' | 'connected' | 'error' | 'closed'>('connecting');
  const [errorMessage, setErrorMessage] = useState<string>('');

  useEffect(() => {
    if (!terminalRef.current) return;

    // Initialize terminal with custom theme
    terminal.current = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      theme: {
        background: '#1e1e1e',
        foreground: '#d4d4d4',
        cursor: '#ffffff',
        selection: '#264f78',
        black: '#000000',
        red: '#cd3131',
        green: '#0dbc79',
        yellow: '#e5e510',
        blue: '#2472c8',
        magenta: '#bc3fbc',
        cyan: '#11a8cd',
        white: '#e5e5e5',
        brightBlack: '#666666',
        brightRed: '#f14c4c',
        brightGreen: '#23d18b',
        brightYellow: '#f5f543',
        brightBlue: '#3b8eea',
        brightMagenta: '#d670d6',
        brightCyan: '#29b8db',
        brightWhite: '#e5e5e5',
      },
      rows: 30,
      cols: 120,
      scrollback: 1000,
    });

    // Add addons
    fitAddon.current = new FitAddon();
    terminal.current.loadAddon(fitAddon.current);
    terminal.current.loadAddon(new WebLinksAddon());

    // Mount terminal
    terminal.current.open(terminalRef.current);
    fitAddon.current.fit();

    // Welcome message
    terminal.current.writeln('\r\n🤖 \x1b[1;36mIgnition Automation Toolkit - Claude Code Integration\x1b[0m\r\n');
    terminal.current.writeln('Connecting to Claude Code session...\r\n');

    // Connect WebSocket
    const wsUrl = `ws://${window.location.hostname}:5000/ws/claude-code/${executionId}`;
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      setStatus('connected');
      terminal.current?.writeln('\x1b[1;32m✅ Connected to Claude Code!\x1b[0m\r\n');
      terminal.current?.writeln('You can now interact with Claude to debug your playbook.\r\n');
    };

    ws.current.onmessage = (event) => {
      if (event.data instanceof Blob) {
        // Binary data from PTY
        event.data.arrayBuffer().then((buffer) => {
          const decoder = new TextDecoder();
          terminal.current?.write(decoder.decode(buffer));
        });
      } else if (typeof event.data === 'string') {
        // JSON messages (errors, etc.)
        try {
          const msg = JSON.parse(event.data);
          if (msg.error) {
            setStatus('error');
            setErrorMessage(msg.error);
            terminal.current?.writeln(`\r\n\x1b[1;31m❌ Error: ${msg.error}\x1b[0m\r\n`);
            onError?.(msg.error);
          }
        } catch {
          // Plain text message
          terminal.current?.write(event.data);
        }
      }
    };

    ws.current.onerror = (event) => {
      setStatus('error');
      const errMsg = 'WebSocket connection failed';
      setErrorMessage(errMsg);
      terminal.current?.writeln(`\r\n\x1b[1;31m❌ ${errMsg}\x1b[0m\r\n`);
      onError?.(errMsg);
    };

    ws.current.onclose = () => {
      setStatus('closed');
      terminal.current?.writeln('\r\n\x1b[1;33m⚠️  Claude Code session ended\x1b[0m\r\n');
      onClose?.();
    };

    // Forward keyboard input to WebSocket
    terminal.current.onData((data) => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(new TextEncoder().encode(data));
      }
    });

    // Handle window resize
    const handleResize = () => {
      fitAddon.current?.fit();
    };
    window.addEventListener('resize', handleResize);

    // Initial fit
    setTimeout(() => fitAddon.current?.fit(), 100);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);

      if (ws.current) {
        ws.current.close();
        ws.current = null;
      }

      if (terminal.current) {
        terminal.current.dispose();
        terminal.current = null;
      }
    };
  }, [executionId, onClose, onError]);

  if (status === 'connecting') {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          gap: 2,
        }}
      >
        <CircularProgress />
        <Typography>Connecting to Claude Code...</Typography>
      </Box>
    );
  }

  if (status === 'error') {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        <Typography variant="body2" fontWeight="bold">
          Connection Error
        </Typography>
        <Typography variant="body2">{errorMessage}</Typography>
        <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
          Make sure Claude Code is installed and the server is running.
        </Typography>
      </Alert>
    );
  }

  return (
    <Box
      sx={{
        width: '100%',
        height: '100%',
        bgcolor: '#1e1e1e',
        position: 'relative',
        '& .xterm': {
          padding: '10px',
          height: '100%',
        },
        '& .xterm-viewport': {
          backgroundColor: '#1e1e1e !important',
        },
      }}
    >
      <div ref={terminalRef} style={{ width: '100%', height: '100%' }} />
    </Box>
  );
}
```

### 3. Update ClaudeCodeDialog

**File:** `frontend/src/components/ClaudeCodeDialog.tsx`

**Changes:** Add toggle between manual and embedded modes

```typescript
import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  ToggleButtonGroup,
  ToggleButton,
  Box,
} from '@mui/material';
import { Terminal as TerminalIcon, Code as CodeIcon } from '@mui/icons-material';
import { EmbeddedTerminal } from './EmbeddedTerminal';

// Add mode state
const [mode, setMode] = useState<'embedded' | 'manual'>('embedded');

// In DialogContent, add mode toggle:
<Box sx={{ mb: 2 }}>
  <ToggleButtonGroup
    value={mode}
    exclusive
    onChange={(e, value) => value && setMode(value)}
    size="small"
    fullWidth
  >
    <ToggleButton value="embedded">
      <TerminalIcon sx={{ mr: 1 }} />
      Embedded Terminal
    </ToggleButton>
    <ToggleButton value="manual">
      <CodeIcon sx={{ mr: 1 }} />
      Manual Command
    </ToggleButton>
  </ToggleButtonGroup>
</Box>

{/* Conditional rendering based on mode */}
{mode === 'embedded' ? (
  <Box sx={{ height: '600px', border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
    <EmbeddedTerminal
      executionId={executionId}
      onClose={() => setClaudeCodeDialogOpen(false)}
      onError={(error) => console.error('Terminal error:', error)}
    />
  </Box>
) : (
  // Existing manual mode UI (Phase 1 command copy)
  sessionMutation.data && (
    <>
      {/* Existing manual mode content */}
    </>
  )
)}
```

### 4. Hot-Reload Playbook Changes (Optional Enhancement)

**File:** `ignition_toolkit/api/app.py`

**Purpose:** Watch playbook files and notify UI of changes

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class PlaybookChangeHandler(FileSystemEventHandler):
    """Watch for playbook file changes and notify via WebSocket"""

    def __init__(self, ws_manager):
        self.ws_manager = ws_manager

    def on_modified(self, event):
        if event.src_path.endswith('.yaml'):
            playbook_path = Path(event.src_path)
            logger.info(f"Playbook modified: {playbook_path}")

            # Notify all connected clients
            asyncio.create_task(
                self.ws_manager.broadcast_json({
                    'type': 'playbook_modified',
                    'path': str(playbook_path),
                    'timestamp': datetime.now().isoformat()
                })
            )

# Start file watcher on startup
@app.on_event("startup")
async def start_playbook_watcher():
    playbooks_dir = Path("./playbooks")
    event_handler = PlaybookChangeHandler(ws_manager)
    observer = Observer()
    observer.schedule(event_handler, str(playbooks_dir), recursive=True)
    observer.start()
    logger.info("Started playbook file watcher")
```

## Benefits

1. **Seamless UX**: No copy/paste, everything in one window
2. **Real-time Interaction**: See Claude's responses immediately
3. **Auto-reload**: Playbook changes refresh UI automatically
4. **Better Process Management**: Clean lifecycle, no orphaned processes
5. **One-Click Launch**: Instant debugging experience
6. **Professional Feel**: Matches modern IDE terminal integrations

## Testing Checklist

- [ ] WebSocket connection establishes successfully
- [ ] Terminal displays Claude Code output correctly
- [ ] Keyboard input is forwarded to Claude Code process
- [ ] Terminal resizes correctly on window resize
- [ ] Process terminates cleanly on disconnect
- [ ] Multiple simultaneous sessions work independently
- [ ] Orphaned processes are cleaned up on server restart
- [ ] Error messages display clearly
- [ ] Manual mode still works (Phase 1 fallback)
- [ ] Copy/paste works in terminal
- [ ] Colors and formatting render correctly
- [ ] Links are clickable (via web-links addon)

## Known Challenges

1. **PTY on Windows**: Python `pty` module doesn't work on Windows
   - Solution: Use `pywinpty` or `conpty` for Windows support

2. **Process Cleanup**: Zombie processes if not handled properly
   - Solution: Proper signal handling and cleanup in finally blocks

3. **Binary Data Handling**: WebSocket binary frames need encoding
   - Solution: Use TextEncoder/TextDecoder for proper UTF-8 handling

4. **Terminal Size**: xterm.js needs manual resize on window changes
   - Solution: FitAddon handles this automatically with event listener

## Migration Path

Phase 1 users can upgrade seamlessly:
- Phase 1 manual mode remains available as fallback
- Toggle button allows switching between modes
- No breaking changes to existing functionality

## Security Considerations

1. **Process Isolation**: Each execution gets its own PTY
2. **Authentication**: Reuse existing execution_id validation
3. **Resource Limits**: Add timeouts to prevent runaway processes
4. **Input Sanitization**: PTY handles this naturally
5. **File Path Validation**: Ensure playbook paths are within allowed directories

## Future Enhancements (Phase 3)

- **Session Recording**: Record terminal sessions for playback
- **Collaborative Sessions**: Multiple users in same terminal
- **AI Suggestions**: Real-time hints as user types
- **Syntax Highlighting**: Highlight YAML in terminal output
- **Auto-save**: Save playbook changes automatically

---

**Last Updated:** 2025-10-27
**Status:** Implementation Plan (Not Started)
**Prerequisites:** Phase 1 (v2.2.0) must be complete
**Next Steps:** Start implementation in dedicated session
