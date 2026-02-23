import { autoUpdater } from 'electron-updater';
import { BrowserWindow } from 'electron';
import { getSetting, getGithubToken, setGithubToken as saveGithubToken } from './settings';
import log from 'electron-log';
import { EVENT_CHANNELS } from '../ipc/channels';

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

  // Configure auto-updater - user-initiated only, no forced behavior
  autoUpdater.autoDownload = false; // Manual download
  autoUpdater.autoInstallOnAppQuit = false; // Don't auto-install on quit - let user decide

  // Set up GitHub private repo token if available (decrypted via safeStorage)
  const githubToken = getGithubToken();
  if (githubToken) {
    autoUpdater.setFeedURL({
      provider: 'github',
      owner: 'Gaskony-Ignition',
      repo: 'ignition-toolbox',
      private: true,
      token: githubToken,
    });
  }

  // Event handlers
  autoUpdater.on('checking-for-update', () => {
    updateStatus = { ...updateStatus, checking: true };
    sendStatusToRenderer(EVENT_CHANNELS.UPDATE_CHECKING, updateStatus);
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
    sendStatusToRenderer(EVENT_CHANNELS.UPDATE_AVAILABLE, updateStatus);

    // Check if user has skipped this version
    const skippedVersion = getSetting('skippedVersion');
    if (skippedVersion === info.version) {
      console.log(`Update ${info.version} was previously skipped`);
      return;
    }

    // Don't show popup - user will see indicator in header and go to Settings > Updates
    console.log(`Update available: ${info.version}`);
  });

  autoUpdater.on('update-not-available', () => {
    updateStatus = {
      ...updateStatus,
      checking: false,
      available: false,
    };
    sendStatusToRenderer(EVENT_CHANNELS.UPDATE_NOT_AVAILABLE, updateStatus);
  });

  autoUpdater.on('download-progress', (progress) => {
    updateStatus = {
      ...updateStatus,
      downloading: true,
      progress: progress.percent,
    };
    sendStatusToRenderer(EVENT_CHANNELS.UPDATE_PROGRESS, updateStatus);
  });

  autoUpdater.on('update-downloaded', (info) => {
    updateStatus = {
      ...updateStatus,
      downloading: false,
      downloaded: true,
      progress: 100,
    };
    sendStatusToRenderer(EVENT_CHANNELS.UPDATE_DOWNLOADED, updateStatus);

    // Don't show popup - user will install from Settings > Updates
    console.log(`Update downloaded: ${info.version}`);
  });

  autoUpdater.on('error', (error) => {
    updateStatus = {
      ...updateStatus,
      checking: false,
      downloading: false,
      error: error.message,
    };
    sendStatusToRenderer(EVENT_CHANNELS.UPDATE_ERROR, updateStatus);
    console.error('Auto-updater error:', error);
  });

  // Check for updates on startup only if explicitly enabled (opt-in)
  const checkOnStartup = getSetting('checkForUpdatesOnStartup');
  if (checkOnStartup === true) {
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
 * Set GitHub token for private repo updates (encrypted via safeStorage)
 */
export function setGitHubToken(token: string | null): void {
  saveGithubToken(token);

  if (token) {
    autoUpdater.setFeedURL({
      provider: 'github',
      owner: 'Gaskony-Ignition',
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
