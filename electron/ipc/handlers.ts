import { ipcMain, dialog, shell, app, BrowserWindow } from 'electron';
import { exec } from 'child_process';
import * as fs from 'fs';
import { PythonBackend } from '../services/python-backend';
import { getSetting, setSetting, getAllSettings } from '../services/settings';
import {
  checkForUpdates,
  downloadUpdate,
  quitAndInstall,
  getUpdateStatus,
} from '../services/auto-updater';
import { getClaudeExecutor } from '../services/claude-executor';
import { getContextBuilder } from '../services/context-builder';

// Check if running in WSL2
function isWSL(): boolean {
  if (process.platform !== 'linux') return false;
  try {
    const release = fs.readFileSync('/proc/version', 'utf8').toLowerCase();
    return release.includes('microsoft') || release.includes('wsl');
  } catch {
    return false;
  }
}

// Open URL in default browser, handling WSL2 environments
async function openExternalUrl(url: string): Promise<void> {
  if (isWSL()) {
    // In WSL2, use cmd.exe to open URLs in Windows default browser
    return new Promise((resolve, reject) => {
      const escapedUrl = url.replace(/"/g, '\\"');
      exec(`cmd.exe /c start "" "${escapedUrl}"`, (error) => {
        if (error) {
          console.error('Failed to open URL via cmd.exe:', error);
          exec(`wslview "${escapedUrl}"`, (err2) => {
            if (err2) {
              reject(err2);
            } else {
              resolve();
            }
          });
        } else {
          resolve();
        }
      });
    });
  } else {
    return shell.openExternal(url);
  }
}

export function registerIpcHandlers(pythonBackend: PythonBackend): void {
  // App info handlers
  ipcMain.handle('app:getVersion', () => {
    return app.getVersion();
  });

  ipcMain.handle('app:getBackendUrl', () => {
    return pythonBackend.getBaseUrl();
  });

  ipcMain.handle('app:getWebSocketUrl', () => {
    return pythonBackend.getWebSocketUrl();
  });

  ipcMain.handle('app:getBackendStatus', () => {
    return pythonBackend.getStatus();
  });

  ipcMain.handle('app:restartBackend', async () => {
    await pythonBackend.restart();
  });

  // Dialog handlers
  ipcMain.handle(
    'dialog:openFile',
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
    'dialog:saveFile',
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
  ipcMain.handle('shell:openExternal', async (_, url: string) => {
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

  ipcMain.handle('shell:openPath', async (_, path: string) => {
    return shell.openPath(path);
  });

  // Settings handlers
  ipcMain.handle('settings:get', (_, key: string) => {
    return getSetting(key as keyof ReturnType<typeof getAllSettings>);
  });

  ipcMain.handle('settings:set', (_, key: string, value: unknown) => {
    setSetting(key as keyof ReturnType<typeof getAllSettings>, value as never);
  });

  ipcMain.handle('settings:getAll', () => {
    return getAllSettings();
  });

  // Update handlers
  ipcMain.handle('updates:check', async () => {
    return checkForUpdates();
  });

  ipcMain.handle('updates:download', async () => {
    downloadUpdate();
    return { success: true };
  });

  ipcMain.handle('updates:install', async () => {
    quitAndInstall();
    return { success: true };
  });

  ipcMain.handle('updates:getStatus', () => {
    return getUpdateStatus();
  });

  // Chat handlers (Toolbox Assistant)
  ipcMain.handle('chat:checkAvailability', async () => {
    const executor = getClaudeExecutor();
    return executor.checkAvailability();
  });

  ipcMain.handle('chat:execute', async (event, prompt: string) => {
    const executor = getClaudeExecutor();
    const backendPort = pythonBackend.getPort();

    // Build system prompt with context
    let systemPrompt: string | undefined;
    if (backendPort) {
      try {
        const contextBuilder = getContextBuilder(backendPort);
        systemPrompt = await contextBuilder.buildSystemPrompt();
      } catch (error) {
        console.error('[Chat] Failed to build context:', error);
      }
    }

    // Stream callback to send chunks to renderer
    const onStream = (chunk: string) => {
      const window = BrowserWindow.fromWebContents(event.sender);
      if (window) {
        event.sender.send('chat:stream', chunk);
      }
    };

    const result = await executor.executeQuery(prompt, systemPrompt, onStream);
    return result;
  });

  ipcMain.handle('chat:cancel', () => {
    const executor = getClaudeExecutor();
    executor.cancelExecution();
    return { success: true };
  });

  ipcMain.handle('chat:getContext', async () => {
    const backendPort = pythonBackend.getPort();
    if (!backendPort) {
      return null;
    }

    try {
      const contextBuilder = getContextBuilder(backendPort);
      return contextBuilder.getDisplayContext();
    } catch (error) {
      console.error('[Chat] Failed to get context:', error);
      return null;
    }
  });

  console.log('IPC handlers registered');
}
