/**
 * WebSocket hook for real-time execution updates
 * Features: Auto-reconnect with exponential backoff, connection status tracking
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import type { WebSocketMessage, ExecutionUpdate, ScreenshotFrame } from '../types/api';
import { createLogger } from '../utils/logger';

const logger = createLogger('WebSocket');

// WebSocket URL - supports both web and Electron modes
// In Electron: constructed from IPC-provided backend URL
// In browser: use window.location
let WS_URL = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:5000/ws/executions';
const WS_API_KEY = import.meta.env.VITE_WS_API_KEY || 'dev-key-change-in-production';
let _wsInitialized = false;
let _wsInitPromise: Promise<void> | null = null;

// Initialize Electron WebSocket URL if available
export async function initializeWebSocketUrl(): Promise<void> {
  if (_wsInitialized) return;

  if (window.electronAPI?.getWebSocketUrl) {
    try {
      const baseWsUrl = await window.electronAPI.getWebSocketUrl();
      WS_URL = `${baseWsUrl}/ws/executions`;
      logger.info('Using Electron WebSocket URL:', WS_URL);
    } catch (error) {
      logger.error('Failed to get Electron WebSocket URL:', error);
      // Fallback to default
      WS_URL = 'ws://127.0.0.1:5000/ws/executions';
    }
  } else if (window.location.protocol !== 'file:') {
    // Web mode - use current location
    WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/executions`;
  }

  _wsInitialized = true;
}

// Get initialization promise
export function getWsInitPromise(): Promise<void> {
  if (!_wsInitPromise) {
    _wsInitPromise = initializeWebSocketUrl();
  }
  return _wsInitPromise;
}

// Initialize on module load
_wsInitPromise = initializeWebSocketUrl();

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
        logger.info(' Connected successfully');
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

          // Handle batched messages (unwrap and process each)
          if (message.type === 'batch' && Array.isArray(message.messages)) {
            for (const batchedMessage of message.messages) {
              processMessage(batchedMessage);
            }
          } else {
            processMessage(message);
          }
        } catch (error) {
          logger.error(' Failed to parse message:', error);
        }
      };

      // Process individual WebSocket messages
      function processMessage(message: WebSocketMessage) {
        if (message.type === 'execution_update' && message.data) {
          callbacksRef.current.onExecutionUpdate?.(message.data as ExecutionUpdate);
        } else if (message.type === 'screenshot_frame' && message.data) {
          callbacksRef.current.onScreenshotFrame?.(message.data as ScreenshotFrame);
        } else if (message.type === 'pong' || message.type === 'keepalive') {
          // Heartbeat response - connection is alive
          logger.debug(' Heartbeat received');
        } else if (message.type === 'error') {
          logger.error(' Server error:', message.error);
        }
      }

      ws.onerror = (event) => {
        logger.error(' Connection error:', event);
        setConnectionStatus('disconnected');
        callbacksRef.current.onError?.(event);
      };

      ws.onclose = (event) => {
        logger.info(' Disconnected', event.code, event.reason);
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

          logger.info(
            `Reconnecting in ${Math.round(nextDelay / 1000)}s (attempt ${reconnectAttemptsRef.current})...`
          );

          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, nextDelay);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      logger.error(' Connection failed:', error);
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
