/**
 * Type definitions for Electron API exposed via preload script
 */

interface ElectronAPI {
  // App info
  getVersion: () => Promise<string>;
  getPlatform: () => string;

  // Backend communication
  getBackendUrl: () => Promise<string>;
  getWebSocketUrl: () => Promise<string>;
  getBackendStatus: () => Promise<{ running: boolean; port: number | null }>;
  restartBackend: () => Promise<void>;

  // Native dialogs
  openFileDialog: (options: {
    title?: string;
    filters?: { name: string; extensions: string[] }[];
    properties?: ('openFile' | 'openDirectory' | 'multiSelections')[];
  }) => Promise<string[] | null>;

  saveFileDialog: (options: {
    title?: string;
    defaultPath?: string;
    filters?: { name: string; extensions: string[] }[];
  }) => Promise<string | null>;

  // Shell operations
  openExternal: (url: string) => Promise<void>;
  openPath: (path: string) => Promise<string>;

  // Settings
  getSetting: (key: string) => Promise<unknown>;
  setSetting: (key: string, value: unknown) => Promise<void>;
  getAllSettings: () => Promise<Record<string, unknown>>;

  // Event listeners
  on: (channel: string, callback: (data: unknown) => void) => () => void;
  off: (channel: string, callback: (data: unknown) => void) => void;
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI;
  }
}

export {};
