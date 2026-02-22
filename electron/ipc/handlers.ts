import { ipcMain, dialog, shell, app, BrowserWindow } from 'electron';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { PythonBackend } from '../services/python-backend';
import { getSetting, setSetting, getAllSettings } from '../services/settings';
import {
  checkForUpdates,
  downloadUpdate,
  quitAndInstall,
  getUpdateStatus,
} from '../services/auto-updater';

import { openExternalUrl } from '../utils/platform';
import { IPC_CHANNELS } from './channels';

export function registerIpcHandlers(pythonBackend: PythonBackend): void {
  // App info handlers
  ipcMain.handle(IPC_CHANNELS.APP_GET_VERSION, () => {
    return app.getVersion();
  });

  ipcMain.handle(IPC_CHANNELS.APP_GET_BACKEND_URL, () => {
    return pythonBackend.getBaseUrl();
  });

  ipcMain.handle(IPC_CHANNELS.APP_GET_WS_URL, () => {
    return pythonBackend.getWebSocketUrl();
  });

  ipcMain.handle(IPC_CHANNELS.APP_GET_WS_API_KEY, () => {
    return pythonBackend.getWebSocketApiKey();
  });

  ipcMain.handle(IPC_CHANNELS.APP_GET_BACKEND_STATUS, () => {
    return pythonBackend.getStatus();
  });

  ipcMain.handle(IPC_CHANNELS.APP_RESTART_BACKEND, async () => {
    await pythonBackend.restart();
  });

  // Dialog handlers
  ipcMain.handle(
    IPC_CHANNELS.DIALOG_OPEN_FILE,
    async (
      event,
      options: {
        title?: string;
        filters?: { name: string; extensions: string[] }[];
        properties?: ('openFile' | 'openDirectory' | 'multiSelections')[];
      }
    ) => {
      const window = BrowserWindow.fromWebContents(event.sender);
      const result = await dialog.showOpenDialog(window!, {
        title: options.title ?? 'Open File',
        filters: options.filters ?? [{ name: 'All Files', extensions: ['*'] }],
        properties: options.properties ?? ['openFile'],
      });

      if (result.canceled) {
        return null;
      }

      return result.filePaths;
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.DIALOG_SAVE_FILE,
    async (
      event,
      options: {
        title?: string;
        defaultPath?: string;
        filters?: { name: string; extensions: string[] }[];
      }
    ) => {
      const window = BrowserWindow.fromWebContents(event.sender);
      const result = await dialog.showSaveDialog(window!, {
        title: options.title ?? 'Save File',
        defaultPath: options.defaultPath,
        filters: options.filters ?? [{ name: 'All Files', extensions: ['*'] }],
      });

      if (result.canceled) {
        return null;
      }

      return result.filePath;
    }
  );

  // Shell handlers
  ipcMain.handle(IPC_CHANNELS.SHELL_OPEN_EXTERNAL, async (_, url: string) => {
    // Validate URL for security
    try {
      const parsed = new URL(url);
      if (!['http:', 'https:', 'mailto:'].includes(parsed.protocol)) {
        throw new Error(`Invalid protocol: ${parsed.protocol}`);
      }
      await openExternalUrl(url);
    } catch (error) {
      console.error('Failed to open external URL:', error);
      throw error;
    }
  });

  ipcMain.handle(IPC_CHANNELS.SHELL_OPEN_PATH, async (_, filePath: string) => {
    const resolved = path.resolve(filePath);

    // Block executable files
    const blockedExtensions = ['.exe', '.bat', '.cmd', '.ps1', '.sh', '.com', '.msi', '.vbs', '.wsf'];
    const ext = path.extname(resolved).toLowerCase();
    if (blockedExtensions.includes(ext)) {
      throw new Error(`Opening executable files is not allowed: ${ext}`);
    }

    // Validate path is within safe directories
    const safeRoots = [
      app.getPath('userData'),
      app.getPath('home'),
      app.getPath('documents'),
      app.getPath('downloads'),
      app.getPath('desktop'),
      os.tmpdir(),
    ];

    const isInSafeDir = safeRoots.some((root) => resolved.startsWith(root));
    if (!isInSafeDir) {
      throw new Error(`Path is outside allowed directories: ${resolved}`);
    }

    // Verify path exists
    if (!fs.existsSync(resolved)) {
      throw new Error(`Path does not exist: ${resolved}`);
    }

    return shell.openPath(resolved);
  });

  // Settings handlers
  ipcMain.handle(IPC_CHANNELS.SETTINGS_GET, (_, key: string) => {
    return getSetting(key as keyof ReturnType<typeof getAllSettings>);
  });

  ipcMain.handle(IPC_CHANNELS.SETTINGS_SET, (_, key: string, value: unknown) => {
    setSetting(key as keyof ReturnType<typeof getAllSettings>, value as never);
  });

  ipcMain.handle(IPC_CHANNELS.SETTINGS_GET_ALL, () => {
    return getAllSettings();
  });

  // Update handlers
  ipcMain.handle(IPC_CHANNELS.UPDATES_CHECK, async () => {
    return checkForUpdates();
  });

  ipcMain.handle(IPC_CHANNELS.UPDATES_DOWNLOAD, async () => {
    downloadUpdate();
    return { success: true };
  });

  ipcMain.handle(IPC_CHANNELS.UPDATES_INSTALL, async () => {
    quitAndInstall();
    return { success: true };
  });

  ipcMain.handle(IPC_CHANNELS.UPDATES_GET_STATUS, () => {
    return getUpdateStatus();
  });

  console.log('IPC handlers registered');
}
