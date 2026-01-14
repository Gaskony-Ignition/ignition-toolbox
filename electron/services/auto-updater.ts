import { autoUpdater } from 'electron-updater';
import { BrowserWindow, dialog } from 'electron';
import { getSetting, setSetting } from './settings';
import log from 'electron-log';

// Configure logging for auto-updater
autoUpdater.logger = log;

export interface UpdateInfo {
  version: string;
  releaseDate: string;
  releaseNotes?: string;
}

export interface UpdateStatus {
  checking: boolean;
  available: boolean;
  downloading: boolean;
  downloaded: boolean;
  progress?: number;
  error?: string;
  updateInfo?: UpdateInfo;
}

let updateStatus: UpdateStatus = {
  checking: false,
  available: false,
  downloading: false,
  downloaded: false,
};

let mainWindow: BrowserWindow | null = null;

/**
 * Initialize the auto-updater
 */
export function initAutoUpdater(window: BrowserWindow): void {
  mainWindow = window;

  // Configure auto-updater
  autoUpdater.autoDownload = false; // Manual download
  autoUpdater.autoInstallOnAppQuit = true;

  // Set up GitHub private repo token if available
  const githubToken = getSetting('githubToken');
  if (githubToken) {
    autoUpdater.setFeedURL({
      provider: 'github',
      owner: 'nigelgwork',
      repo: 'ignition-toolbox',
      private: true,
      token: githubToken as string,
    });
  }

  // Event handlers
  autoUpdater.on('checking-for-update', () => {
    updateStatus = { ...updateStatus, checking: true };
    sendStatusToRenderer('update:checking', updateStatus);
  });

  autoUpdater.on('update-available', (info) => {
    updateStatus = {
      ...updateStatus,
      checking: false,
      available: true,
      updateInfo: {
        version: info.version,
        releaseDate: info.releaseDate,
        releaseNotes: info.releaseNotes as string | undefined,
      },
    };
    sendStatusToRenderer('update:available', updateStatus);

    // Check if user has skipped this version
    const skippedVersion = getSetting('skippedVersion');
    if (skippedVersion === info.version) {
      console.log(`Update ${info.version} was previously skipped`);
      return;
    }

    // Show update notification
    showUpdateDialog(info);
  });

  autoUpdater.on('update-not-available', () => {
    updateStatus = {
      ...updateStatus,
      checking: false,
      available: false,
    };
    sendStatusToRenderer('update:not-available', updateStatus);
  });

  autoUpdater.on('download-progress', (progress) => {
    updateStatus = {
      ...updateStatus,
      downloading: true,
      progress: progress.percent,
    };
    sendStatusToRenderer('update:progress', updateStatus);
  });

  autoUpdater.on('update-downloaded', (info) => {
    updateStatus = {
      ...updateStatus,
      downloading: false,
      downloaded: true,
      progress: 100,
    };
    sendStatusToRenderer('update:downloaded', updateStatus);

    // Show install dialog
    showInstallDialog(info);
  });

  autoUpdater.on('error', (error) => {
    updateStatus = {
      ...updateStatus,
      checking: false,
      downloading: false,
      error: error.message,
    };
    sendStatusToRenderer('update:error', updateStatus);
    console.error('Auto-updater error:', error);
  });

  // Check for updates on startup if enabled
  const checkOnStartup = getSetting('checkForUpdatesOnStartup');
  if (checkOnStartup !== false) {
    // Delay initial check to let app fully load
    setTimeout(() => {
      checkForUpdates().catch(console.error);
    }, 5000);
  }
}

/**
 * Send status update to renderer process
 */
function sendStatusToRenderer(channel: string, status: UpdateStatus): void {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send(channel, status);
  }
}

/**
 * Show dialog when update is available
 */
async function showUpdateDialog(info: { version: string; releaseNotes?: string | string[] | null }): Promise<void> {
  if (!mainWindow) return;

  const result = await dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: 'Update Available',
    message: `A new version (${info.version}) is available.`,
    detail: 'Would you like to download it now?',
    buttons: ['Download', 'Skip This Version', 'Later'],
    defaultId: 0,
    cancelId: 2,
  });

  if (result.response === 0) {
    // Download
    downloadUpdate();
  } else if (result.response === 1) {
    // Skip this version
    setSetting('skippedVersion', info.version);
  }
}

/**
 * Show dialog when update is downloaded
 */
async function showInstallDialog(info: { version: string }): Promise<void> {
  if (!mainWindow) return;

  const result = await dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: 'Update Ready',
    message: `Version ${info.version} has been downloaded.`,
    detail: 'The update will be installed when you quit the application. Would you like to restart now?',
    buttons: ['Restart Now', 'Later'],
    defaultId: 0,
    cancelId: 1,
  });

  if (result.response === 0) {
    quitAndInstall();
  }
}

/**
 * Check for updates
 */
export async function checkForUpdates(): Promise<UpdateStatus> {
  try {
    await autoUpdater.checkForUpdates();
  } catch (error) {
    console.error('Failed to check for updates:', error);
    updateStatus = {
      ...updateStatus,
      checking: false,
      error: (error as Error).message,
    };
  }
  return updateStatus;
}

/**
 * Download the available update
 */
export function downloadUpdate(): void {
  autoUpdater.downloadUpdate();
}

/**
 * Quit and install the downloaded update
 */
export function quitAndInstall(): void {
  autoUpdater.quitAndInstall();
}

/**
 * Set GitHub token for private repo updates
 */
export function setGitHubToken(token: string | null): void {
  setSetting('githubToken', token);

  if (token) {
    autoUpdater.setFeedURL({
      provider: 'github',
      owner: 'nigelgwork',
      repo: 'ignition-toolbox',
      private: true,
      token,
    });
  }
}

/**
 * Get current update status
 */
export function getUpdateStatus(): UpdateStatus {
  return updateStatus;
}
