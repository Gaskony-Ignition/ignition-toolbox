import { contextBridge, ipcRenderer } from 'electron';

// Update status interface
interface UpdateStatus {
  checking: boolean;
  available: boolean;
  downloading: boolean;
  downloaded: boolean;
  progress?: number;
  error?: string;
  updateInfo?: {
    version: string;
    releaseDate: string;
    releaseNotes?: string;
  };
}

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
  'chat:stream',
] as const;

type ValidEventChannel = typeof validEventChannels[number];

contextBridge.exposeInMainWorld('electronAPI', {
  // App info
  getVersion: (): Promise<string> => ipcRenderer.invoke('app:getVersion'),
  getPlatform: (): string => process.platform,

  // Backend communication
  getBackendUrl: (): Promise<string> => ipcRenderer.invoke('app:getBackendUrl'),
  getWebSocketUrl: (): Promise<string> => ipcRenderer.invoke('app:getWebSocketUrl'),
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

  // Chat (Toolbox Assistant)
  chat: {
    checkAvailability: (): Promise<boolean> => ipcRenderer.invoke('chat:checkAvailability'),
    execute: (prompt: string): Promise<{ success: boolean; output: string; error?: string }> =>
      ipcRenderer.invoke('chat:execute', prompt),
    cancel: (): Promise<{ success: boolean }> => ipcRenderer.invoke('chat:cancel'),
    getContext: (): Promise<{
      playbookCount: number;
      recentExecutions: { name: string; status: string }[];
      cloudDesignerStatus: string;
    } | null> => ipcRenderer.invoke('chat:getContext'),
  },

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
      chat: {
        checkAvailability: () => Promise<boolean>;
        execute: (prompt: string) => Promise<{ success: boolean; output: string; error?: string }>;
        cancel: () => Promise<{ success: boolean }>;
        getContext: () => Promise<{
          playbookCount: number;
          recentExecutions: { name: string; status: string }[];
          cloudDesignerStatus: string;
        } | null>;
      };
      on: (channel: ValidEventChannel, callback: (data: unknown) => void) => () => void;
      off: (channel: ValidEventChannel, callback: (data: unknown) => void) => void;
    };
  }
}
