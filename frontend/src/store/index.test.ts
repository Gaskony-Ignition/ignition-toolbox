/**
 * Tests for Zustand store
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useStore } from './index';
import { act } from '@testing-library/react';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('useStore', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
    // Reset store state
    useStore.setState({
      executionUpdates: new Map(),
      currentScreenshots: new Map(),
      isWSConnected: false,
      wsConnectionStatus: 'connecting',
      theme: 'dark',
      playbookGridColumns: 5,
      globalCredential: null,
      selectedCredential: null,
      sessionCredentials: [],
      updateStatus: { available: false, downloaded: false },
    });
  });

  describe('execution updates', () => {
    it('stores execution updates by ID', () => {
      const store = useStore.getState();
      const update = {
        execution_id: 'exec-123',
        playbook_name: 'Test Playbook',
        status: 'running',
        current_step_index: 1,
        total_steps: 5,
        error: null,
        started_at: '2024-01-01T00:00:00Z',
        completed_at: null,
        step_results: [],
      };

      act(() => {
        store.setExecutionUpdate('exec-123', update);
      });

      const newState = useStore.getState();
      expect(newState.executionUpdates.get('exec-123')).toEqual(update);
    });
  });

  describe('screenshot frames', () => {
    it('stores screenshot frames by execution ID', () => {
      const store = useStore.getState();
      const frame = {
        executionId: 'exec-123',
        screenshot: 'base64data',
        timestamp: '2024-01-01T00:00:00Z',
      };

      act(() => {
        store.setScreenshotFrame('exec-123', frame);
      });

      const newState = useStore.getState();
      expect(newState.currentScreenshots.get('exec-123')).toEqual(frame);
    });
  });

  describe('WebSocket connection status', () => {
    it('updates connection status', () => {
      const store = useStore.getState();

      act(() => {
        store.setWSConnectionStatus('connected');
      });

      const newState = useStore.getState();
      expect(newState.wsConnectionStatus).toBe('connected');
      expect(newState.isWSConnected).toBe(true);
    });

    it('sets isWSConnected to false when disconnected', () => {
      const store = useStore.getState();

      act(() => {
        store.setWSConnectionStatus('disconnected');
      });

      const newState = useStore.getState();
      expect(newState.wsConnectionStatus).toBe('disconnected');
      expect(newState.isWSConnected).toBe(false);
    });
  });

  describe('theme', () => {
    it('defaults to dark theme', () => {
      const state = useStore.getState();
      expect(state.theme).toBe('dark');
    });

    it('updates theme and saves to localStorage', () => {
      const store = useStore.getState();

      act(() => {
        store.setTheme('light');
      });

      const newState = useStore.getState();
      expect(newState.theme).toBe('light');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'light');
    });
  });

  describe('playbook grid columns', () => {
    it('defaults to 5 columns', () => {
      const state = useStore.getState();
      expect(state.playbookGridColumns).toBe(5);
    });

    it('updates columns and saves to localStorage', () => {
      const store = useStore.getState();

      act(() => {
        store.setPlaybookGridColumns(4);
      });

      const newState = useStore.getState();
      expect(newState.playbookGridColumns).toBe(4);
      expect(localStorageMock.setItem).toHaveBeenCalledWith('playbookGridColumns', '4');
    });
  });

  describe('global credential', () => {
    it('defaults to null', () => {
      const state = useStore.getState();
      expect(state.globalCredential).toBeNull();
    });

    it('updates global credential', () => {
      const store = useStore.getState();

      act(() => {
        store.setGlobalCredential('my-credential');
      });

      const newState = useStore.getState();
      expect(newState.globalCredential).toBe('my-credential');
    });
  });

  describe('session credentials', () => {
    it('adds session credentials', () => {
      const store = useStore.getState();
      const credential = {
        name: 'temp-cred',
        username: 'admin',
        password: 'secret',
        isSessionOnly: true as const,
      };

      act(() => {
        store.addSessionCredential(credential);
      });

      const newState = useStore.getState();
      expect(newState.sessionCredentials).toHaveLength(1);
      expect(newState.sessionCredentials[0].name).toBe('temp-cred');
    });

    it('removes session credentials by name', () => {
      const store = useStore.getState();
      const credential = {
        name: 'temp-cred',
        username: 'admin',
        password: 'secret',
        isSessionOnly: true as const,
      };

      act(() => {
        store.addSessionCredential(credential);
        store.removeSessionCredential('temp-cred');
      });

      const newState = useStore.getState();
      expect(newState.sessionCredentials).toHaveLength(0);
    });
  });

  describe('update status', () => {
    it('defaults to no update available', () => {
      const state = useStore.getState();
      expect(state.updateStatus.available).toBe(false);
      expect(state.updateStatus.downloaded).toBe(false);
    });

    it('updates update status', () => {
      const store = useStore.getState();

      act(() => {
        store.setUpdateStatus({ available: true, downloaded: false, version: '1.5.0' });
      });

      const newState = useStore.getState();
      expect(newState.updateStatus.available).toBe(true);
      expect(newState.updateStatus.version).toBe('1.5.0');
    });
  });
});
