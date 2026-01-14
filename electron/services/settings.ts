import Store from 'electron-store';

// Define settings schema
interface SettingsSchema {
  // Window state
  windowBounds: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  windowMaximized: boolean;

  // App settings
  theme: 'dark' | 'light';
  autoStart: boolean;
  minimizeToTray: boolean;

  // Backend settings
  backendPort: number | null;

  // Update settings
  autoUpdate: boolean;
  checkForUpdatesOnStartup: boolean;
  skippedVersion: string | null;

  // GitHub token for private repo updates
  githubToken: string | null;
}

const defaults: SettingsSchema = {
  windowBounds: {
    x: 0,
    y: 0,
    width: 1400,
    height: 900,
  },
  windowMaximized: false,
  theme: 'dark',
  autoStart: false,
  minimizeToTray: false,
  backendPort: null,
  autoUpdate: true,
  checkForUpdatesOnStartup: true,
  skippedVersion: null,
  githubToken: null,
};

// Create store instance
const store = new Store<SettingsSchema>({
  name: 'settings',
  defaults,
});

export function getSetting<K extends keyof SettingsSchema>(key: K): SettingsSchema[K] {
  return store.get(key);
}

export function setSetting<K extends keyof SettingsSchema>(
  key: K,
  value: SettingsSchema[K]
): void {
  store.set(key, value);
}

export function getAllSettings(): SettingsSchema {
  return store.store;
}

export function resetSettings(): void {
  store.clear();
}

export { store, SettingsSchema };
