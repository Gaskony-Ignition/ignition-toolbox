/**
 * Centralized backend configuration for the Electron app.
 *
 * The Python backend port is discovered dynamically at startup (from the range below).
 * The frontend learns the actual port via IPC (app:getBackendUrl / app:getWebSocketUrl).
 * These constants provide the defaults and fallbacks used throughout the app.
 */

export const BACKEND_HOST = '127.0.0.1';

export const BACKEND_PORT_RANGE = {
  START: 5000,
  END: 5099,
} as const;

/** Default/fallback port when the actual port is not yet known */
export const DEFAULT_BACKEND_PORT = BACKEND_PORT_RANGE.START;

export function getBackendHttpUrl(port: number = DEFAULT_BACKEND_PORT): string {
  return `http://${BACKEND_HOST}:${port}`;
}

export function getBackendWsUrl(port: number = DEFAULT_BACKEND_PORT): string {
  return `ws://${BACKEND_HOST}:${port}`;
}
