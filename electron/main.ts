import { app, BrowserWindow, ipcMain, dialog, shell } from 'electron';
import * as path from 'path';
import { PythonBackend } from './services/python-backend';
import { registerIpcHandlers } from './ipc/handlers';
import { initAutoUpdater } from './services/auto-updater';

// Handle creating/removing shortcuts on Windows when installing/uninstalling
if (require('electron-squirrel-startup')) {
  app.quit();
}

let mainWindow: BrowserWindow | null = null;
let pythonBackend: PythonBackend | null = null;

const isDev = !app.isPackaged;

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 768,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
    show: false,
    backgroundColor: '#01050d', // Dark background matching Warp theme
  });

  // Show window when ready to prevent visual flash
  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
  });

  // Load the app
  if (isDev) {
    // Development: load from Vite dev server
    mainWindow.loadURL('http://localhost:3000');
    mainWindow.webContents.openDevTools();
  } else {
    // Production: load built frontend
    mainWindow.loadFile(path.join(__dirname, '../frontend/dist/index.html'));
  }

  // Handle external links
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

async function startPythonBackend(): Promise<void> {
  pythonBackend = new PythonBackend();

  try {
    await pythonBackend.start();
    console.log(`Python backend started on port ${pythonBackend.getPort()}`);
  } catch (error) {
    console.error('Failed to start Python backend:', error);
    dialog.showErrorBox(
      'Backend Error',
      'Failed to start the Python backend. Please ensure Python is installed and try again.'
    );
    app.quit();
  }
}

async function stopPythonBackend(): Promise<void> {
  if (pythonBackend) {
    await pythonBackend.stop();
    pythonBackend = null;
  }
}

// App lifecycle
app.whenReady().then(async () => {
  // Start Python backend first
  await startPythonBackend();

  // Register IPC handlers
  registerIpcHandlers(pythonBackend!);

  // Create main window
  createWindow();

  // Initialize auto-updater (only in production)
  if (!isDev && mainWindow) {
    initAutoUpdater(mainWindow);
  }

  app.on('activate', () => {
    // On macOS, re-create window when dock icon is clicked
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', async () => {
  await stopPythonBackend();

  // On macOS, keep app running until explicitly quit
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', async () => {
  await stopPythonBackend();
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
});

process.on('unhandledRejection', (reason) => {
  console.error('Unhandled rejection:', reason);
});

// Export for IPC handlers
export function getMainWindow(): BrowserWindow | null {
  return mainWindow;
}

export function getPythonBackend(): PythonBackend | null {
  return pythonBackend;
}
