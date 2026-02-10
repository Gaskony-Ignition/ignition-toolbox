import { contextBridge, ipcRenderer } from 'electron';
import type { UpdateStatus } from './services/auto-updater';

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object

// Define valid event channels for security
const validEventChannels = [
  'backend:status',
  'backend:error',
  'backend:log',
  'update:checking',
  'update:available',
  'update:not-available',
  'update:progress',
  'update:downloaded',
  'update:error',
] as const;

type ValidEventChannel = typeof validEventChannels[number];

contextBridge.exposeInMainWorld('electronAPI', {
  // App info
  getVersion: (): Promise<string> => ipcRenderer.invoke('app:getVersion'),
  getPlatform: (): string => process.platform,

  // Backend communication
  getBackendUrl: (): Promise<string> => ipcRenderer.invoke('app:getBackendUrl'),
  getWebSocketUrl: (): Promise<string> => ipcRenderer.invoke('app:getWebSocketUrl'),
  getWebSocketApiKey: (): Promise<string> => ipcRenderer.invoke('app:getWebSocketApiKey'),
  getBackendStatus: (): Promise<{ running: boolean; port: number | null }> =>
    ipcRenderer.invoke('app:getBackendStatus'),
  restartBackend: (): Promise<void> => ipcRenderer.invoke('app:restartBackend'),

  // Native dialogs
  openFileDialog: (options: {
    title?: string;
    filters?: { name: string; extensions: string[] }[];
    properties?: ('openFile' | 'openDirectory' | 'multiSelections')[];
  }): Promise<string[] | null> => ipcRenderer.invoke('dialog:openFile', options),

  saveFileDialog: (options: {
    title?: string;
    defaultPath?: string;
    filters?: { name: string; extensions: string[] }[];
  }): Promise<string | null> => ipcRenderer.invoke('dialog:saveFile', options),

  // Shell operations
  openExternal: (url: string): Promise<void> => ipcRenderer.invoke('shell:openExternal', url),
  openPath: (path: string): Promise<string> => ipcRenderer.invoke('shell:openPath', path),

  // Settings
  getSetting: (key: string): Promise<unknown> => ipcRenderer.invoke('settings:get', key),
  setSetting: (key: string, value: unknown): Promise<void> =>
    ipcRenderer.invoke('settings:set', key, value),
  getAllSettings: (): Promise<Record<string, unknown>> => ipcRenderer.invoke('settings:getAll'),

  // Updates
  checkForUpdates: (): Promise<UpdateStatus> => ipcRenderer.invoke('updates:check'),
  downloadUpdate: (): Promise<{ success: boolean }> => ipcRenderer.invoke('updates:download'),
  installUpdate: (): Promise<{ success: boolean }> => ipcRenderer.invoke('updates:install'),
  getUpdateStatus: (): Promise<UpdateStatus> => ipcRenderer.invoke('updates:getStatus'),

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
