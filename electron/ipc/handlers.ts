import { ipcMain, dialog, shell, app, BrowserWindow } from 'electron';
import { PythonBackend } from '../services/python-backend';
import { getSetting, setSetting, getAllSettings } from '../services/settings';
import {
  checkForUpdates,
  downloadUpdate,
  quitAndInstall,
  getUpdateStatus,
} from '../services/auto-updater';

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
      await shell.openExternal(url);
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

  // CloudDesigner popup window
  ipcMain.handle('clouddesigner:openWindow', async () => {
    const targetUrl = 'http://localhost:8080';
    console.log(`CloudDesigner: Opening window for ${targetUrl}`);

    const designerWindow = new BrowserWindow({
      width: 1920,
      height: 1080,
      title: `Ignition Designer - Loading ${targetUrl}`,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        webSecurity: false,
        allowRunningInsecureContent: true,
        webviewTag: true,
        plugins: true,
        experimentalFeatures: true,
      },
    });

    // Open DevTools docked to right for debugging
    designerWindow.webContents.openDevTools({ mode: 'right' });

    // First show a diagnostic page, then navigate to target
    const diagnosticHtml = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>CloudDesigner Loading...</title>
        <style>
          body { background: #1a1a2e; color: #fff; font-family: system-ui; padding: 40px; }
          .log { background: #0a0a1e; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 12px; max-height: 400px; overflow: auto; }
          .log div { margin: 4px 0; }
          .info { color: #6eb5ff; }
          .success { color: #6bff6b; }
          .error { color: #ff6b6b; }
          .warn { color: #ffb86b; }
          h1 { color: #6eb5ff; }
        </style>
      </head>
      <body>
        <h1>CloudDesigner Diagnostic</h1>
        <p>Target URL: <strong>${targetUrl}</strong></p>
        <h3>Event Log:</h3>
        <div id="log" class="log"></div>
        <script>
          function log(msg, type = 'info') {
            const div = document.createElement('div');
            div.className = type;
            div.textContent = new Date().toISOString().substr(11, 12) + ' - ' + msg;
            document.getElementById('log').appendChild(div);
            console.log('[CloudDesigner] ' + msg);
          }
          log('Diagnostic page loaded', 'success');
          log('Will attempt to navigate to: ${targetUrl}');
          window.cloudDesignerLog = log;
        </script>
      </body>
      </html>
    `;

    // Load diagnostic page first
    await designerWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(diagnosticHtml)}`);

    // Log events to both main process and inject into page
    const logToPage = (msg: string, type = 'info') => {
      console.log(`CloudDesigner: ${msg}`);
      designerWindow.webContents.executeJavaScript(
        `window.cloudDesignerLog && window.cloudDesignerLog(${JSON.stringify(msg)}, ${JSON.stringify(type)})`
      ).catch(() => {});
    };

    designerWindow.webContents.on('did-start-loading', () => {
      logToPage('did-start-loading', 'info');
    });

    designerWindow.webContents.on('did-stop-loading', () => {
      logToPage('did-stop-loading', 'info');
    });

    designerWindow.webContents.on('did-finish-load', () => {
      const url = designerWindow.webContents.getURL();
      logToPage(`did-finish-load - URL: ${url}`, 'success');
      designerWindow.setTitle(`Ignition Designer - ${url}`);
    });

    designerWindow.webContents.on('did-fail-load', (_event, errorCode, errorDescription, validatedURL) => {
      logToPage(`FAILED - Code: ${errorCode}, Desc: ${errorDescription}, URL: ${validatedURL}`, 'error');
      designerWindow.setTitle(`Ignition Designer - FAILED`);
    });

    designerWindow.webContents.on('dom-ready', () => {
      logToPage('dom-ready', 'info');
    });

    designerWindow.webContents.on('did-navigate', (_event, url) => {
      logToPage(`did-navigate to ${url}`, 'info');
    });

    designerWindow.webContents.on('render-process-gone', (_event, details) => {
      logToPage(`render-process-gone - reason: ${details.reason}`, 'error');
    });

    designerWindow.webContents.on('certificate-error', (event, url, error, _certificate, callback) => {
      logToPage(`certificate-error for ${url}: ${error}`, 'warn');
      if (url.includes('localhost')) {
        event.preventDefault();
        callback(true);
      } else {
        callback(false);
      }
    });

    // Wait a moment then navigate to target
    logToPage('Waiting 2 seconds before navigating...', 'info');
    await new Promise(resolve => setTimeout(resolve, 2000));

    logToPage(`Now navigating to ${targetUrl}...`, 'info');
    designerWindow.loadURL(targetUrl);

    return true;
  });

  console.log('IPC handlers registered');
}
