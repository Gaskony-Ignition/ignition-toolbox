/**
 * EmbeddedShellTerminal - Embedded terminal that opens in playbooks directory
 *
 * Opens a real bash shell in the playbooks folder for running Claude Code manually.
 * Can be popped out into a separate window for easier operation.
 */

import { useEffect, useRef, useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Alert,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Terminal as TerminalIcon,
  OpenInNew as PopOutIcon,
  Info as InfoIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { createLogger } from '../utils/logger';

const logger = createLogger('EmbeddedShellTerminal');

interface EmbeddedShellTerminalProps {
  open: boolean;
  onClose: () => void;
  executionId?: string;  // Optional, not currently used but kept for future context
}

export function EmbeddedShellTerminal({
  open,
  onClose,
}: EmbeddedShellTerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [showInstructions, setShowInstructions] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playbooksPath, setPlaybooksPath] = useState<string>('./playbooks'); // Default

  // PORTABILITY: Fetch playbooks path from config API on mount
  useEffect(() => {
    fetch('/api/config')
      .then(res => res.json())
      .then(config => {
        if (config.paths?.playbooks_dir) {
          setPlaybooksPath(config.paths.playbooks_dir);
        }
      })
      .catch(err => {
        logger.warn('Failed to fetch config, using default playbooks path:', err);
        // Keep default './playbooks'
      });
  }, []);

  // Open in new window
  const handlePopOut = () => {
    const width = 1000;
    const height = 600;
    const left = (window.screen.width - width) / 2;
    const top = (window.screen.height - height) / 2;

    const newWindow = window.open(
      '',
      'ClaudeCodeTerminal',
      `width=${width},height=${height},left=${left},top=${top},menubar=no,toolbar=no,location=no,status=no`
    );

    if (newWindow) {
      newWindow.document.write(`
        <!DOCTYPE html>
        <html>
          <head>
            <title>Claude Code Terminal</title>
            <link rel="stylesheet" href="/xterm.css">
            <style>
              body { margin: 0; padding: 0; background: #000; overflow: hidden; }
              #terminal { width: 100vw; height: 100vh; }
            </style>
          </head>
          <body>
            <div id="terminal"></div>
          </body>
        </html>
      `);
      newWindow.document.close();

      // Close the dialog since we're opening in new window
      onClose();
    }
  };

  useEffect(() => {
    logger.debug('useEffect triggered', { open, hasTerminalRef: !!terminalRef.current });

    if (!open) {
      logger.debug('Dialog not open, skipping initialization');
      return;
    }

    // Wait for terminal ref to be ready (it won't be on first render)
    if (!terminalRef.current) {
      logger.debug('Terminal ref not ready yet, will retry...');
      // Use a small timeout to wait for the DOM to be ready
      const retryTimer = setTimeout(() => {
        logger.debug('Retrying after ref should be ready');
        // Force re-render by setting a dummy state
        setError(null);
      }, 100);
      return () => clearTimeout(retryTimer);
    }

    logger.debug('Starting terminal initialization');

    // Create terminal instance
    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      theme: {
        background: '#1e1e1e',
        foreground: '#d4d4d4',
        cursor: '#ffffff',
      },
      rows: 24,
      cols: 80,
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    term.open(terminalRef.current);
    fitAddon.fit();

    logger.debug('Terminal opened and fitted');

    // Connect to WebSocket for shell
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/shell?path=${encodeURIComponent(playbooksPath)}`;

    logger.debug('Creating WebSocket connection', { wsUrl });

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    logger.debug('WebSocket object created, readyState:', ws.readyState);

    ws.onopen = () => {
      logger.debug('WebSocket opened successfully');
      setIsConnected(true);
      setError(null);
      term.writeln('\x1b[1;32m✓ Connected to shell\x1b[0m');
      term.writeln(`\x1b[1;36mWorking directory: ${playbooksPath}\x1b[0m`);
      term.writeln('');
      term.writeln('\x1b[1;33mTo start Claude Code, run: claude-code\x1b[0m');
      term.writeln('\x1b[1;33mFor instructions, click "Show Instructions" button\x1b[0m');
      term.writeln('');
    };

    ws.onmessage = (event) => {
      logger.debug('WebSocket message received:', event.data);
      try {
        const data = JSON.parse(event.data);
        if (data.output) {
          term.write(data.output);
        }
      } catch (error) {
        logger.error('Error parsing message:', error);
      }
    };

    ws.onerror = (error) => {
      logger.error('WebSocket error:', error);
      setError('Failed to connect to terminal server');
      term.writeln('\x1b[1;31m✗ Connection error\x1b[0m');
    };

    ws.onclose = (event) => {
      logger.debug('WebSocket closed', { code: event.code, reason: event.reason });
      setIsConnected(false);
      term.writeln('');
      term.writeln('\x1b[1;33m⚠ Connection closed\x1b[0m');
    };

    // Send input from terminal to WebSocket
    const disposable = term.onData((data) => {
      logger.debug('User input, WebSocket state:', ws.readyState);
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ input: data }));
        logger.debug('Sent input to server');
      } else {
        logger.warn('WebSocket not open, cannot send input');
      }
    });

    // Handle window resize
    const handleResize = () => {
      fitAddon.fit();
    };
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      logger.debug('Cleanup function called');
      disposable.dispose();
      window.removeEventListener('resize', handleResize);
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
      term.dispose();
    };
  }, [open, playbooksPath]);

  logger.debug('Render', { open, isConnected, error });

  return (
    <>
      <Dialog
        open={open}
        onClose={onClose}
        maxWidth="lg"
        fullWidth
        PaperProps={{
          sx: {
            height: '80vh',
            maxHeight: '80vh',
          },
        }}
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, pb: 1 }}>
          <TerminalIcon />
          <Box sx={{ flexGrow: 1 }}>Claude Code Terminal</Box>

          <Tooltip title="Show Instructions">
            <IconButton
              size="small"
              onClick={() => setShowInstructions(!showInstructions)}
              color={showInstructions ? 'primary' : 'default'}
            >
              <InfoIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title="Open in New Window">
            <IconButton size="small" onClick={handlePopOut}>
              <PopOutIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title="Close">
            <IconButton size="small" onClick={onClose}>
              <CloseIcon />
            </IconButton>
          </Tooltip>
        </DialogTitle>

        <DialogContent sx={{ p: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {error && (
            <Alert severity="error" sx={{ m: 2, mb: 0 }}>
              {error}
            </Alert>
          )}

          {showInstructions && (
            <Alert severity="info" icon={<InfoIcon />} sx={{ m: 2, mb: 0 }}>
              <Box>
                <strong>Quick Start:</strong>
                <ol style={{ margin: '8px 0 0 0', paddingLeft: '20px' }}>
                  <li>Type <code>claude-code</code> (or <code>claude-work</code>) to start Claude Code</li>
                  <li>Read <code>CLAUDE_CODE_INSTRUCTIONS.md</code> for playbook syntax and patterns</li>
                  <li>Claude Code can read, edit, and create playbook YAML files</li>
                  <li>Use <code>ls</code> to see available playbooks in gateway/, perspective/, designer/</li>
                </ol>
              </Box>
            </Alert>
          )}

          <Box
            ref={terminalRef}
            sx={{
              flexGrow: 1,
              backgroundColor: '#1e1e1e',
              p: 1,
              overflow: 'hidden',
              '& .xterm': {
                height: '100%',
                padding: '8px',
              },
            }}
          />
        </DialogContent>

        <DialogActions sx={{ px: 3, py: 2 }}>
          <Box sx={{ flexGrow: 1, display: 'flex', gap: 1, alignItems: 'center' }}>
            {isConnected ? (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: 'success.main' }}>
                <Box
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    bgcolor: 'success.main',
                  }}
                />
                <span style={{ fontSize: '0.875rem' }}>Connected</span>
              </Box>
            ) : (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: 'text.secondary' }}>
                <Box
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    bgcolor: 'text.secondary',
                  }}
                />
                <span style={{ fontSize: '0.875rem' }}>Disconnected</span>
              </Box>
            )}
          </Box>
          <Button onClick={() => setShowInstructions(!showInstructions)} variant="outlined">
            {showInstructions ? 'Hide' : 'Show'} Instructions
          </Button>
          <Button onClick={handlePopOut} variant="outlined" startIcon={<PopOutIcon />}>
            Pop Out
          </Button>
          <Button onClick={onClose} variant="contained">
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
