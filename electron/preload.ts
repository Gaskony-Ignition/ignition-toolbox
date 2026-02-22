import { contextBridge, ipcRenderer } from 'electron';
import type { UpdateStatus } from './services/auto-updater';
import { IPC_CHANNELS, EVENT_CHANNELS } from './ipc/channels';
import type { ValidEventChannel } from './ipc/channels';

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object

// Define valid event channels for security
const validEventChannels = Object.values(EVENT_CHANNELS);

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
