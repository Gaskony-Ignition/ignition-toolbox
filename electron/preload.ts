import { contextBridge, ipcRenderer } from 'electron';

// IMPORTANT: Preload scripts run in a sandboxed environment (sandbox: true).
// They can only require built-in Electron/Node modules, NOT local files.
// All IPC channel constants must be inlined here.
// Keep these in sync with electron/ipc/channels.ts (the main process source of truth).

/** IPC invoke channels (must match IPC_CHANNELS in channels.ts) */
const IPC_CHANNELS = {
  APP_GET_VERSION: 'app:getVersion',
  APP_GET_BACKEND_URL: 'app:getBackendUrl',
  APP_GET_WS_URL: 'app:getWebSocketUrl',
  APP_GET_WS_API_KEY: 'app:getWebSocketApiKey',
  APP_GET_BACKEND_STATUS: 'app:getBackendStatus',
  APP_RESTART_BACKEND: 'app:restartBackend',
  DIALOG_OPEN_FILE: 'dialog:openFile',
  DIALOG_SAVE_FILE: 'dialog:saveFile',
  SHELL_OPEN_EXTERNAL: 'shell:openExternal',
  SHELL_OPEN_PATH: 'shell:openPath',
  SETTINGS_GET: 'settings:get',
  SETTINGS_SET: 'settings:set',
  SETTINGS_GET_ALL: 'settings:getAll',
  UPDATES_CHECK: 'updates:check',
  UPDATES_DOWNLOAD: 'updates:download',
  UPDATES_INSTALL: 'updates:install',
  UPDATES_GET_STATUS: 'updates:getStatus',
} as const;

/** Event channels (must match EVENT_CHANNELS in channels.ts) */
const EVENT_CHANNELS = {
  BACKEND_STATUS: 'backend:status',
  BACKEND_ERROR: 'backend:error',
  BACKEND_LOG: 'backend:log',
  UPDATE_CHECKING: 'update:checking',
  UPDATE_AVAILABLE: 'update:available',
  UPDATE_NOT_AVAILABLE: 'update:not-available',
  UPDATE_PROGRESS: 'update:progress',
  UPDATE_DOWNLOADED: 'update:downloaded',
  UPDATE_ERROR: 'update:error',
} as const;

type ValidEventChannel = (typeof EVENT_CHANNELS)[keyof typeof EVENT_CHANNELS];

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object

// Define valid event channels for security
const validEventChannels: string[] = Object.values(EVENT_CHANNELS);

interface UpdateStatus {
  available: boolean;
  downloaded: boolean;
  checking: boolean;
  error: string | null;
  updateInfo?: {
    version: string;
    releaseNotes?: string;
  };
}

contextBridge.exposeInMainWorld('electronAPI', {
  // App info
  getVersion: (): Promise<string> => ipcRenderer.invoke(IPC_CHANNELS.APP_GET_VERSION),
  getPlatform: (): string => process.platform,

  // Backend communication
  getBackendUrl: (): Promise<string> => ipcRenderer.invoke(IPC_CHANNELS.APP_GET_BACKEND_URL),
  getWebSocketUrl: (): Promise<string> => ipcRenderer.invoke(IPC_CHANNELS.APP_GET_WS_URL),
  getWebSocketApiKey: (): Promise<string> => ipcRenderer.invoke(IPC_CHANNELS.APP_GET_WS_API_KEY),
  getBackendStatus: (): Promise<{ running: boolean; port: number | null }> =>
    ipcRenderer.invoke(IPC_CHANNELS.APP_GET_BACKEND_STATUS),
  restartBackend: (): Promise<void> => ipcRenderer.invoke(IPC_CHANNELS.APP_RESTART_BACKEND),

  // Native dialogs
  openFileDialog: (options: {
    title?: string;
    filters?: { name: string; extensions: string[] }[];
    properties?: ('openFile' | 'openDirectory' | 'multiSelections')[];
  }): Promise<string[] | null> => ipcRenderer.invoke(IPC_CHANNELS.DIALOG_OPEN_FILE, options),

  saveFileDialog: (options: {
    title?: string;
    defaultPath?: string;
    filters?: { name: string; extensions: string[] }[];
  }): Promise<string | null> => ipcRenderer.invoke(IPC_CHANNELS.DIALOG_SAVE_FILE, options),

  // Shell operations
  openExternal: (url: string): Promise<void> => ipcRenderer.invoke(IPC_CHANNELS.SHELL_OPEN_EXTERNAL, url),
  openPath: (path: string): Promise<string> => ipcRenderer.invoke(IPC_CHANNELS.SHELL_OPEN_PATH, path),

  // Settings
  getSetting: (key: string): Promise<unknown> => ipcRenderer.invoke(IPC_CHANNELS.SETTINGS_GET, key),
  setSetting: (key: string, value: unknown): Promise<void> =>
    ipcRenderer.invoke(IPC_CHANNELS.SETTINGS_SET, key, value),
  getAllSettings: (): Promise<Record<string, unknown>> => ipcRenderer.invoke(IPC_CHANNELS.SETTINGS_GET_ALL),

  // Updates
  checkForUpdates: (): Promise<UpdateStatus> => ipcRenderer.invoke(IPC_CHANNELS.UPDATES_CHECK),
  downloadUpdate: (): Promise<{ success: boolean }> => ipcRenderer.invoke(IPC_CHANNELS.UPDATES_DOWNLOAD),
  installUpdate: (): Promise<{ success: boolean }> => ipcRenderer.invoke(IPC_CHANNELS.UPDATES_INSTALL),
  getUpdateStatus: (): Promise<UpdateStatus> => ipcRenderer.invoke(IPC_CHANNELS.UPDATES_GET_STATUS),

  // Event listeners (for backend status updates)
  on: (channel: ValidEventChannel, callback: (data: unknown) => void): (() => void) => {
    if (!validEventChannels.includes(channel)) {
      console.warn(`Invalid event channel: ${channel}`);
      return () => {};
    }

    const subscription = (_event: Electron.IpcRendererEvent, data: unknown) => callback(data);
    ipcRenderer.on(channel, subscription);

    // Return unsubscribe function
    return () => {
      ipcRenderer.removeListener(channel, subscription);
    };
  },

  off: (channel: ValidEventChannel, callback: (data: unknown) => void): void => {
    if (!validEventChannels.includes(channel)) {
      console.warn(`Invalid event channel: ${channel}`);
      return;
    }
    ipcRenderer.removeListener(channel, callback as (...args: unknown[]) => void);
  },
});

// Type definitions for the exposed API
declare global {
  interface Window {
    electronAPI: {
      getVersion: () => Promise<string>;
      getPlatform: () => string;
      getBackendUrl: () => Promise<string>;
      getWebSocketUrl: () => Promise<string>;
      getWebSocketApiKey: () => Promise<string>;
      getBackendStatus: () => Promise<{ running: boolean; port: number | null }>;
      restartBackend: () => Promise<void>;
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
      openExternal: (url: string) => Promise<void>;
      openPath: (path: string) => Promise<string>;
      getSetting: (key: string) => Promise<unknown>;
      setSetting: (key: string, value: unknown) => Promise<void>;
      getAllSettings: () => Promise<Record<string, unknown>>;
      checkForUpdates: () => Promise<UpdateStatus>;
      downloadUpdate: () => Promise<{ success: boolean }>;
      installUpdate: () => Promise<{ success: boolean }>;
      getUpdateStatus: () => Promise<UpdateStatus>;
      on: (channel: ValidEventChannel, callback: (data: unknown) => void) => () => void;
      off: (channel: ValidEventChannel, callback: (data: unknown) => void) => void;
    };
  }
}
