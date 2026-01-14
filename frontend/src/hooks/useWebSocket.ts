/**
 * WebSocket hook for real-time execution updates
 * Features: Auto-reconnect with exponential backoff, connection status tracking
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import type { WebSocketMessage, ExecutionUpdate, ScreenshotFrame } from '../types/api';

// WebSocket URL - supports both web and Electron modes
// In Electron: constructed from IPC-provided backend URL
// In browser: use window.location
let WS_URL = import.meta.env.VITE_WS_URL ||
  `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/executions`;
const WS_API_KEY = import.meta.env.VITE_WS_API_KEY || 'dev-key-change-in-production';

// Initialize Electron WebSocket URL if available
async function initializeWebSocketUrl(): Promise<void> {
  if (window.electronAPI?.getWebSocketUrl) {
    try {
      const baseWsUrl = await window.electronAPI.getWebSocketUrl();
      WS_URL = `${baseWsUrl}/ws/executions`;
      console.log('Using Electron WebSocket URL:', WS_URL);
    } catch (error) {
      console.error('Failed to get Electron WebSocket URL:', error);
    }
  }
}

// Initialize on module load (non-blocking)
initializeWebSocketUrl();

const INITIAL_RECONNECT_DELAY = 1000; // 1 second
const MAX_RECONNECT_DELAY = 30000; // 30 seconds
const RECONNECT_BACKOFF_MULTIPLIER = 1.5;

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'reconnecting';

interface UseWebSocketOptions {
  onExecutionUpdate?: (update: ExecutionUpdate) => void;
  onScreenshotFrame?: (frame: ScreenshotFrame) => void;
  onError?: (error: Event) => void;
  onOpen?: () => void;
  onClose?: () => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | undefined>(undefined);
  const reconnectDelayRef = useRef<number>(INITIAL_RECONNECT_DELAY);
  const reconnectAttemptsRef = useRef<number>(0);
  const intentionalCloseRef = useRef<boolean>(false);
  const heartbeatIntervalRef = useRef<number | undefined>(undefined);

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('connecting');

  const { onExecutionUpdate, onScreenshotFrame, onError, onOpen, onClose } = options;

  // Store callbacks in refs to avoid dependency issues
  const callbacksRef = useRef({ onExecutionUpdate, onScreenshotFrame, onError, onOpen, onClose });

  // Update refs when callbacks change (without triggering reconnects)
  useEffect(() => {
    callbacksRef.current = { onExecutionUpdate, onScreenshotFrame, onError, onOpen, onClose };
  }, [onExecutionUpdate, onScreenshotFrame, onError, onOpen, onClose]);

  const connect = useCallback(() => {
    // Don't connect if already connected or intentionally closed
    if (wsRef.current?.readyState === WebSocket.OPEN || intentionalCloseRef.current) {
      return;
    }

    // Clear any pending reconnect timeouts
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = undefined;
    }

    setConnectionStatus(reconnectAttemptsRef.current > 0 ? 'reconnecting' : 'connecting');

    try {
      const ws = new WebSocket(`${WS_URL}?api_key=${WS_API_KEY}`);

      ws.onopen = () => {
        console.log('[WebSocket] Connected successfully');
        setConnectionStatus('connected');

        // Reset reconnect state on successful connection
        reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;
        reconnectAttemptsRef.current = 0;

        callbacksRef.current.onOpen?.();

        // Start heartbeat to keep connection alive
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
        }
        heartbeatIntervalRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
          }
        }, 15000); // Send ping every 15 seconds (matches server keepalive)
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          if (message.type === 'execution_update' && message.data) {
            callbacksRef.current.onExecutionUpdate?.(message.data as ExecutionUpdate);
          } else if (message.type === 'screenshot_frame' && message.data) {
            callbacksRef.current.onScreenshotFrame?.(message.data as ScreenshotFrame);
          } else if (message.type === 'pong') {
            // Heartbeat response - connection is alive
            console.debug('[WebSocket] Heartbeat received');
          } else if (message.type === 'error') {
            console.error('[WebSocket] Server error:', message.error);
          }
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      ws.onerror = (event) => {
        console.error('[WebSocket] Connection error:', event);
        setConnectionStatus('disconnected');
        callbacksRef.current.onError?.(event);
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected', event.code, event.reason);
        setConnectionStatus('disconnected');

        // Clear heartbeat interval
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = undefined;
        }

        callbacksRef.current.onClose?.();

        // Only auto-reconnect if not intentionally closed
        if (!intentionalCloseRef.current) {
          reconnectAttemptsRef.current += 1;

          // Calculate next reconnect delay with exponential backoff
          const nextDelay = Math.min(
            reconnectDelayRef.current * RECONNECT_BACKOFF_MULTIPLIER,
            MAX_RECONNECT_DELAY
          );
          reconnectDelayRef.current = nextDelay;

          console.log(
            `[WebSocket] Reconnecting in ${Math.round(nextDelay / 1000)}s (attempt ${reconnectAttemptsRef.current})...`
          );

          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, nextDelay);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('[WebSocket] Connection failed:', error);
      setConnectionStatus('disconnected');
    }
  }, []); // ✅ NO dependencies - callbacks stored in refs

  const disconnect = useCallback(() => {
    // Mark as intentional close to prevent auto-reconnect
    intentionalCloseRef.current = true;

    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = undefined;
    }

    // Clear heartbeat interval
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = undefined;
    }

    // Close WebSocket connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setConnectionStatus('disconnected');
  }, []);

  useEffect(() => {
    // Reset intentional close flag when component mounts
    intentionalCloseRef.current = false;
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    connectionStatus,
    isConnected: connectionStatus === 'connected',
    disconnect,
    reconnect: connect,
  };
}
