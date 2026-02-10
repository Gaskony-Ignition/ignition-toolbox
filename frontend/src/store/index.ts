/**
 * Zustand store for global state management
 */

import { create } from 'zustand';
import type { ExecutionUpdate, CredentialInfo, ScreenshotFrame } from '../types/api';

// Initialize theme from localStorage or default to 'dark'
const getInitialTheme = (): 'dark' | 'light' => {
  const stored = localStorage.getItem('theme');
  return (stored === 'light' || stored === 'dark') ? stored : 'dark';
};

// Initialize playbook grid columns from localStorage or default to 5
export type PlaybookGridColumns = 3 | 4 | 5 | 6;
const getInitialPlaybookGridColumns = (): PlaybookGridColumns => {
  const stored = localStorage.getItem('playbookGridColumns');
  const parsed = stored ? parseInt(stored, 10) : 5;
  return (parsed === 3 || parsed === 4 || parsed === 5 || parsed === 6) ? parsed : 5;
};

// Session-only credential (not saved to vault)
interface SessionCredential {
  name: string;
  username: string;
  password: string;
  gateway_url?: string;
  description?: string;
  isSessionOnly: true;
}

// Update status from Electron auto-updater
interface UpdateStatus {
  available: boolean;
  downloaded: boolean;
  version?: string;
}

interface AppState {
  // Execution updates from WebSocket
  executionUpdates: Map<string, ExecutionUpdate>;
  setExecutionUpdate: (executionId: string, update: ExecutionUpdate) => void;

  // Screenshot frames from WebSocket
  currentScreenshots: Map<string, ScreenshotFrame>;
  setScreenshotFrame: (executionId: string, frame: ScreenshotFrame) => void;

  // WebSocket connection status
  isWSConnected: boolean;
  setWSConnected: (connected: boolean) => void;
  wsConnectionStatus: 'connected' | 'connecting' | 'disconnected' | 'reconnecting';
  setWSConnectionStatus: (status: 'connected' | 'connecting' | 'disconnected' | 'reconnecting') => void;

  // Theme mode
  theme: 'dark' | 'light';
  setTheme: (theme: 'dark' | 'light') => void;

  // Playbook grid columns
  playbookGridColumns: PlaybookGridColumns;
  setPlaybookGridColumns: (columns: PlaybookGridColumns) => void;

  // Global credential name (for header dropdown)
  globalCredential: string | null;
  setGlobalCredential: (name: string | null) => void;

  // Global credential selection (full credential object)
  selectedCredential: CredentialInfo | SessionCredential | null;
  setSelectedCredential: (credential: CredentialInfo | SessionCredential | null) => void;

  // Session-only credentials (stored in memory only)
  sessionCredentials: SessionCredential[];
  addSessionCredential: (credential: SessionCredential) => void;
  removeSessionCredential: (name: string) => void;

  // Update status
  updateStatus: UpdateStatus;
  setUpdateStatus: (status: UpdateStatus) => void;
}

export const useStore = create<AppState>((set) => ({
  executionUpdates: new Map(),
  setExecutionUpdate: (executionId, update) =>
    set((state) => {
      const newUpdates = new Map(state.executionUpdates);
      newUpdates.set(executionId, update);
      return { executionUpdates: newUpdates };
    }),

  currentScreenshots: new Map(),
  setScreenshotFrame: (executionId, frame) =>
    set((state) => {
      const newScreenshots = new Map(state.currentScreenshots);
      newScreenshots.set(executionId, frame);
      return { currentScreenshots: newScreenshots };
    }),

  isWSConnected: false,
  setWSConnected: (connected) => set({ isWSConnected: connected }),

  wsConnectionStatus: 'connecting',
  setWSConnectionStatus: (status) => set({
    wsConnectionStatus: status,
    isWSConnected: status === 'connected'
  }),

  theme: getInitialTheme(),
  setTheme: (theme) => {
    localStorage.setItem('theme', theme);
    set({ theme });
  },

  playbookGridColumns: getInitialPlaybookGridColumns(),
  setPlaybookGridColumns: (columns) => {
    localStorage.setItem('playbookGridColumns', columns.toString());
    set({ playbookGridColumns: columns });
  },

  globalCredential: null,
  setGlobalCredential: (name) => set({ globalCredential: name }),

  selectedCredential: null,
  setSelectedCredential: (credential) => set({ selectedCredential: credential }),

  sessionCredentials: [],
  addSessionCredential: (credential) =>
    set((state) => ({
      sessionCredentials: [...state.sessionCredentials, credential],
    })),
  removeSessionCredential: (name) =>
    set((state) => ({
      sessionCredentials: state.sessionCredentials.filter((c) => c.name !== name),
    })),

  updateStatus: { available: false, downloaded: false },
  setUpdateStatus: (status) => set({ updateStatus: status }),
}));

// Export SessionCredential type for use in other components
export type { SessionCredential };
