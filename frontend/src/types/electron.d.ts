/**
 * Type definitions for Electron API exposed via preload script
 */

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

  // Updates
  checkForUpdates: () => Promise<UpdateStatus>;
  downloadUpdate: () => Promise<{ success: boolean }>;
  installUpdate: () => Promise<{ success: boolean }>;
  getUpdateStatus: () => Promise<UpdateStatus>;

  // Event listeners
  on: (channel: string, callback: (data: unknown) => void) => () => void;
  off: (channel: string, callback: (data: unknown) => void) => void;

  // CloudDesigner
  cloudDesigner?: {
    openWindow: () => Promise<boolean>;
  };

  // Chat (Toolbox Assistant)
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
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI;
  }
}

export {};
