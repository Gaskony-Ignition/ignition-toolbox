import Store from 'electron-store';
import { safeStorage } from 'electron';

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

  // GitHub token for private repo updates (encrypted via safeStorage)
  githubToken: string | null;
  // Flag indicating the token has been encrypted with safeStorage
  githubTokenEncrypted: boolean;
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
  githubTokenEncrypted: false,
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

/**
 * Get the GitHub token, decrypting it if stored encrypted.
 * Handles migration from plaintext to encrypted storage.
 */
export function getGithubToken(): string | null {
  const token = store.get('githubToken');
  if (!token) return null;

  const isEncrypted = store.get('githubTokenEncrypted');

  if (isEncrypted) {
    // Decrypt the stored token
    try {
      const buffer = Buffer.from(token, 'base64');
      return safeStorage.decryptString(buffer);
    } catch (error) {
      console.error('Failed to decrypt GitHub token:', error);
      return null;
    }
  }

  // Legacy plaintext token — migrate to encrypted storage
  if (safeStorage.isEncryptionAvailable()) {
    setGithubToken(token);
    console.log('Migrated GitHub token to encrypted storage');
  }

  return token;
}

/**
 * Store the GitHub token encrypted via OS keychain (safeStorage).
 * Falls back to plaintext if encryption is not available.
 */
export function setGithubToken(token: string | null): void {
  if (!token) {
    store.set('githubToken', null);
    store.set('githubTokenEncrypted', false);
    return;
  }

  if (safeStorage.isEncryptionAvailable()) {
    const encrypted = safeStorage.encryptString(token);
    store.set('githubToken', encrypted.toString('base64'));
    store.set('githubTokenEncrypted', true);
  } else {
    // Fallback: store plaintext (e.g. Linux without Secret Service)
    console.warn('safeStorage not available — storing GitHub token unencrypted');
    store.set('githubToken', token);
    store.set('githubTokenEncrypted', false);
  }
}

export { store, SettingsSchema };
