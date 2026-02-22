/**
 * Single source of truth for all Electron IPC channel names.
 *
 * Import from this file in both the main process (handlers.ts, auto-updater.ts)
 * and the renderer-facing preload script (preload.ts).
 */

/** Channels used with ipcMain.handle / ipcRenderer.invoke (request-response) */
export const IPC_CHANNELS = {
  // App info
  APP_GET_VERSION: 'app:getVersion',
  APP_GET_BACKEND_URL: 'app:getBackendUrl',
  APP_GET_WS_URL: 'app:getWebSocketUrl',
  APP_GET_WS_API_KEY: 'app:getWebSocketApiKey',
  APP_GET_BACKEND_STATUS: 'app:getBackendStatus',
  APP_RESTART_BACKEND: 'app:restartBackend',

  // Dialogs
  DIALOG_OPEN_FILE: 'dialog:openFile',
  DIALOG_SAVE_FILE: 'dialog:saveFile',

  // Shell
  SHELL_OPEN_EXTERNAL: 'shell:openExternal',
  SHELL_OPEN_PATH: 'shell:openPath',

  // Settings
  SETTINGS_GET: 'settings:get',
  SETTINGS_SET: 'settings:set',
  SETTINGS_GET_ALL: 'settings:getAll',

  // Updates
  UPDATES_CHECK: 'updates:check',
  UPDATES_DOWNLOAD: 'updates:download',
  UPDATES_INSTALL: 'updates:install',
  UPDATES_GET_STATUS: 'updates:getStatus',
} as const;

/** Channels used with ipcRenderer.on / mainWindow.webContents.send (one-way events) */
export const EVENT_CHANNELS = {
  BACKEND_STATUS: 'backend:status',
  BACKEND_ERROR: 'backend:error',
  BACKEND_LOG: 'backend:log',
  UPDATE_CHECKING: 'update:checking',
  UPDATE_AVAILABLE: 'update:available',
  UPDATE_NOT_AVAILABLE: 'update:not-available',
  UPDATE_PROGRESS: 'update:progress',
  UPDATE_DOWNLOADED: 'update:downloaded',
  UPDATE_ERROR: 'update:error',
} as const;

export type ValidEventChannel = (typeof EVENT_CHANNELS)[keyof typeof EVENT_CHANNELS];
