import { useEffect, useRef, useState } from 'react';
import { Box, Alert } from '@mui/material';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import '@xterm/xterm/css/xterm.css';

interface EmbeddedTerminalProps {
  executionId: string;
  onClose?: () => void;
  onError: (error: string) => void;
}

export function EmbeddedTerminal({
  executionId,
  onError,
}: EmbeddedTerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const terminal = useRef<Terminal | null>(null);
  const fitAddon = useRef<FitAddon | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const initializeTerminal = () => {
      if (!terminalRef.current) return;

      try {
        // Initialize terminal with custom theme (Warp Terminal inspired)
        terminal.current = new Terminal({
          cursorBlink: true,
          cursorStyle: 'block',
          fontFamily: '"Fira Code", "Cascadia Code", "Monaco", "Courier New", monospace',
          fontSize: 14,
          lineHeight: 1.2,
          theme: {
            background: '#0D0D0D',
            foreground: '#FFFFFF',
            cursor: '#7AA2F7',
            cursorAccent: '#0D0D0D',
            // Note: 'selection' is not in ITheme for xterm 5.3.0
            // selectionBackground is used instead
            selectionBackground: 'rgba(122, 162, 247, 0.3)',
            black: '#1A1B26',
            red: '#F7768E',
            green: '#9ECE6A',
            yellow: '#E0AF68',
            blue: '#7AA2F7',
            magenta: '#BB9AF7',
            cyan: '#7DCFFF',
            white: '#C0CAF5',
            brightBlack: '#414868',
            brightRed: '#F7768E',
            brightGreen: '#9ECE6A',
            brightYellow: '#E0AF68',
            brightBlue: '#7AA2F7',
            brightMagenta: '#BB9AF7',
            brightCyan: '#7DCFFF',
            brightWhite: '#C0CAF5',
          },
        });

        // Add fit addon
        fitAddon.current = new FitAddon();
        terminal.current.loadAddon(fitAddon.current);

        // Add web links addon
        const webLinksAddon = new WebLinksAddon();
        terminal.current.loadAddon(webLinksAddon);

        // Open terminal in DOM
        terminal.current.open(terminalRef.current);

        // Fit terminal to container
        fitAddon.current.fit();

        // Handle window resize
        const handleResize = () => {
          if (fitAddon.current) {
            fitAddon.current.fit();
          }
        };
        window.addEventListener('resize', handleResize);

        // Connect WebSocket
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.hostname}:5000/ws/claude-code/${executionId}`;

        terminal.current.writeln('\x1b[1;36mConnecting to Claude Code...\x1b[0m');

        ws.current = new WebSocket(wsUrl);
        ws.current.binaryType = 'arraybuffer';

        ws.current.onopen = () => {
          terminal.current?.writeln('\x1b[1;32m✓ Connected to Claude Code session\x1b[0m');
          terminal.current?.writeln('');
        };

        ws.current.onmessage = (event) => {
          if (event.data instanceof ArrayBuffer) {
            // Binary data from PTY - write directly to terminal
            const uint8Array = new Uint8Array(event.data);
            terminal.current?.write(uint8Array);
          } else if (typeof event.data === 'string') {
            // JSON message from server
            try {
              const message = JSON.parse(event.data);

              if (message.type === 'connected') {
                terminal.current?.writeln(`\x1b[1;32m${message.message}\x1b[0m`);
                terminal.current?.writeln(`\x1b[90mPID: ${message.pid}\x1b[0m`);
                terminal.current?.writeln('');
              } else if (message.type === 'error') {
                terminal.current?.writeln(`\x1b[1;31m✗ Error: ${message.message}\x1b[0m`);
                setError(message.message);
                onError(message.message);
              } else if (message.type === 'exit') {
                terminal.current?.writeln('');
                terminal.current?.writeln(`\x1b[1;33m⚠ Claude Code process exited (code: ${message.code})\x1b[0m`);
                setTimeout(() => {
                  if (ws.current) {
                    ws.current.close();
                  }
                }, 1000);
              }
            } catch (e) {
              // Not JSON, ignore
            }
          }
        };

        ws.current.onerror = (error) => {
          console.error('WebSocket error:', error);
          terminal.current?.writeln('\x1b[1;31m✗ WebSocket connection error\x1b[0m');
          setError('WebSocket connection failed');
          onError('WebSocket error');
        };

        ws.current.onclose = () => {
          terminal.current?.writeln('');
          terminal.current?.writeln('\x1b[1;33m⚠ Connection closed\x1b[0m');
        };

        // Forward keyboard input to WebSocket
        terminal.current.onData((data: string) => {
          if (ws.current?.readyState === WebSocket.OPEN) {
            // Convert string to ArrayBuffer for binary WebSocket frame
            const encoder = new TextEncoder();
            const bytes = encoder.encode(data);
            ws.current.send(bytes.buffer);
          }
        });

        // Cleanup function
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
      } catch (err) {
        console.error('Terminal initialization error:', err);
        setError('Failed to initialize terminal');
        onError(err instanceof Error ? err.message : 'Terminal init failed');
      }
    };

    // Initialize after a small delay to ensure DOM is ready
    const timer = setTimeout(initializeTerminal, 100);

    return () => {
      clearTimeout(timer);
      if (ws.current) {
        ws.current.close();
      }
      if (terminal.current) {
        terminal.current.dispose();
      }
    };
  }, [executionId, onError]);

  return (
    <Box sx={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box
        ref={terminalRef}
        sx={{
          flexGrow: 1,
          width: '100%',
          height: '100%',
          backgroundColor: '#0D0D0D',
          borderRadius: 1,
          overflow: 'hidden',
          '& .xterm': {
            height: '100% !important',
            padding: '8px',
          },
          '& .xterm-viewport': {
            backgroundColor: '#0D0D0D !important',
          },
        }}
      />
    </Box>
  );
}
