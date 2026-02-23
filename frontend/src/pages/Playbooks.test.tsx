/**
 * Smoke tests for the Playbooks page
 *
 * Goals:
 * - Page renders without crashing
 * - Shows loading state when fetching
 * - Shows empty state when no playbooks exist
 * - Shows playbook cards when playbooks are returned
 * - Key action buttons (Browse Library, Create New, Import) are present
 *
 * NOTE on DnD Kit in JSDOM:
 * @dnd-kit/core's PointerSensor registers pointer event listeners that never
 * fire in JSDOM, causing test workers to hang when Playbooks is statically
 * imported. All DnD Kit packages are fully stubbed. The Playbooks component
 * itself is loaded via dynamic import to avoid module-initialization deadlocks
 * caused by the combined static-import + vi.mock hoisting in JSDOM.
 *
 * NOTE on DndContext/SortableContext fragment wrapping:
 * These context mocks must wrap children in React.Fragment rather than
 * returning `children` directly. React 19 may loop when a component returns
 * a non-element (array) directly as its output, causing OOM in JSDOM.
 *
 * NOTE on useStore.getState:
 * Playbooks.tsx calls useStore.getState().selectedCredential inside event
 * handlers. The mock exposes this via a static getState() method.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { PlaybookInfo } from '../types/api';

// ---------------------------------------------------------------------------
// DnD Kit stubs — hoisted before all imports by Vitest
// ---------------------------------------------------------------------------
vi.mock('@dnd-kit/core', () => ({
  DndContext: ({ children }: { children: React.ReactNode }) =>
    React.createElement(React.Fragment, null, children),
  closestCenter: () => null,
  KeyboardSensor: class KeyboardSensor {},
  PointerSensor: class PointerSensor {},
  useSensor: () => ({}),
  useSensors: () => [],
  useDroppable: () => ({ setNodeRef: () => {}, isOver: false }),
}));

vi.mock('@dnd-kit/sortable', () => ({
  arrayMove: (arr: unknown[], from: number, to: number) => {
    const r = [...arr]; r.splice(to, 0, r.splice(from, 1)[0]); return r;
  },
  SortableContext: ({ children }: { children: React.ReactNode }) =>
    React.createElement(React.Fragment, null, children),
  sortableKeyboardCoordinates: () => ({}),
  verticalListSortingStrategy: () => ({}),
  useSortable: () => ({
    attributes: {}, listeners: {}, setNodeRef: () => {},
    transform: null, transition: undefined, isDragging: false,
  }),
}));

vi.mock('@dnd-kit/utilities', () => ({
  CSS: { Transform: { toString: () => '' } },
}));

// ---------------------------------------------------------------------------
// API client
// ---------------------------------------------------------------------------
vi.mock('../api/client', () => ({
  api: {
    playbooks: { list: vi.fn().mockResolvedValue([]) },
    executions: { start: vi.fn().mockResolvedValue({ execution_id: 'exec-1' }) },
    getBaseUrl: vi.fn().mockReturnValue('http://localhost:5000'),
  },
}));

// ---------------------------------------------------------------------------
// Zustand store — expose getState() for handleExecute compatibility
// ---------------------------------------------------------------------------
const storeState = {
  setActiveExecutionId: vi.fn(),
  setPlaybookSubTab: vi.fn(),
  playbookGridColumns: 4,
  selectedCredential: null as null | { name: string; gateway_url: string },
};

const mockUseStore = Object.assign(
  (selector: (s: typeof storeState) => unknown) => selector(storeState),
  { getState: () => storeState },
);

vi.mock('../store', () => ({
  useStore: mockUseStore,
}));

// ---------------------------------------------------------------------------
// TIMING — disable polling
// ---------------------------------------------------------------------------
vi.mock('../config/timing', () => ({
  TIMING: {
    POLLING: { PLAYBOOKS: false, PLAYBOOK_UPDATES: false },
    UI: {},
    WEBSOCKET: {},
  },
}));

// ---------------------------------------------------------------------------
// Heavy dialogs
// ---------------------------------------------------------------------------
vi.mock('../components/PlaybookExecutionDialog', () => ({ PlaybookExecutionDialog: () => null }));
vi.mock('../components/PlaybookStepsDialog', () => ({ PlaybookStepsDialog: () => null }));
vi.mock('../components/PlaybookLibraryDialog', () => ({ PlaybookLibraryDialog: () => null }));
vi.mock('../components/PlaybookEditorDialog', () => ({ PlaybookEditorDialog: () => null }));
vi.mock('../components/CreatePlaybookDialog', () => ({ CreatePlaybookDialog: () => null }));
vi.mock('../components/SubmitToLibraryDialog', () => ({ SubmitToLibraryDialog: () => null }));

// PlaybookCard stub — renders name + Run button for assertion
vi.mock('../components/PlaybookCard', () => ({
  PlaybookCard: ({ playbook }: { playbook: { name: string; path: string } }) =>
    React.createElement(
      'div', { 'data-testid': `card-${playbook.path}` },
      React.createElement('span', null, playbook.name),
      React.createElement('button', { 'aria-label': `Run ${playbook.name}` }, 'Run'),
    ),
}));

// ---------------------------------------------------------------------------
// Import/export helpers and logger
// ---------------------------------------------------------------------------
vi.mock('./PlaybookImportExport', () => ({ handleExport: vi.fn(), handleImport: vi.fn() }));
vi.mock('../utils/logger', () => ({
  createLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchInterval: false,
        refetchOnWindowFocus: false,
        refetchIntervalInBackground: false,
        gcTime: 0,
        staleTime: Infinity,
      },
      mutations: { retry: false },
    },
  });
}

// Use dynamic import to avoid module-initialization deadlock from static import
// combined with vi.mock hoisting in the JSDOM environment.
async function renderPlaybooks(props: { domainFilter?: 'gateway' | 'designer' | 'perspective' } = {}) {
  const { Playbooks } = await import('./Playbooks');
  return render(
    React.createElement(
      QueryClientProvider, { client: makeQueryClient() },
      React.createElement(MemoryRouter, null,
        React.createElement(Playbooks, props),
      ),
    ),
  );
}

function makePlaybook(overrides: Partial<PlaybookInfo> = {}): PlaybookInfo {
  return {
    name: 'Sample Playbook',
    path: 'gateway/sample_playbook.yaml',
    version: '1.0.0',
    description: 'A sample playbook for testing',
    parameter_count: 0, step_count: 3,
    parameters: [], steps: [],
    domain: 'gateway', group: null, revision: 1,
    verified: false, enabled: true,
    last_modified: '2025-01-15T10:00:00Z', verified_at: null,
    origin: 'built-in', duplicated_from: null,
    created_at: '2025-01-01T00:00:00Z', relevant_timeouts: [],
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Playbooks page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Stub the raw fetch call the playbook-updates query makes at mount time
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ updates: [] }),
    }));
  });

  it('renders without crashing', { timeout: 20000 }, async () => {
    await act(async () => { await renderPlaybooks(); });
    expect(document.body).toBeTruthy();
  });

  it('shows the page heading', { timeout: 20000 }, async () => {
    await renderPlaybooks();
    expect(screen.getByText('Playbooks')).toBeInTheDocument();
  });

  it('shows "Browse Library" button', { timeout: 20000 }, async () => {
    await renderPlaybooks();
    // MUI Tooltip sets aria-label to the tooltip title on its internal clone element,
    // so the accessible name is the full tooltip description, not the button text.
    expect(screen.getByRole('button', { name: /browse.*playbooks from repository/i })).toBeInTheDocument();
  });

  it('shows "Create New" button', { timeout: 20000 }, async () => {
    await renderPlaybooks();
    // MUI Tooltip sets aria-label to the tooltip title ("Create a new playbook from template").
    expect(screen.getByRole('button', { name: /create a new playbook/i })).toBeInTheDocument();
  });

  it('shows "Import" button', { timeout: 20000 }, async () => {
    await renderPlaybooks();
    expect(screen.getByRole('button', { name: /import/i })).toBeInTheDocument();
  });

  it('shows "Drag Mode" toggle button', { timeout: 20000 }, async () => {
    await renderPlaybooks();
    expect(screen.getByRole('button', { name: /drag mode/i })).toBeInTheDocument();
  });

  it('shows loading spinner while playbooks are being fetched', { timeout: 20000 }, async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.playbooks.list).mockReturnValue(new Promise(() => {}));
    await renderPlaybooks();
    expect(screen.getByLabelText(/loading playbooks/i)).toBeInTheDocument();
  });

  it('shows empty state when no playbooks exist', { timeout: 20000 }, async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.playbooks.list).mockResolvedValue([]);
    await renderPlaybooks();
    await waitFor(() => {
      expect(screen.getByText(/no playbooks found/i)).toBeInTheDocument();
    }, { timeout: 12000 });
  });

  it('shows an error alert when the API fails', { timeout: 20000 }, async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.playbooks.list).mockRejectedValue(new Error('Connection refused'));
    await renderPlaybooks();
    await waitFor(() => {
      expect(screen.getByText(/failed to load playbooks/i)).toBeInTheDocument();
    }, { timeout: 12000 });
  });

  it('renders playbook cards when playbooks are returned', { timeout: 20000 }, async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.playbooks.list).mockResolvedValue([
      makePlaybook({ name: 'Alpha Playbook', path: 'gateway/alpha.yaml' }),
      makePlaybook({ name: 'Beta Playbook', path: 'gateway/beta.yaml' }),
    ]);
    await renderPlaybooks();
    await waitFor(() => {
      expect(screen.getByText('Alpha Playbook')).toBeInTheDocument();
      expect(screen.getByText('Beta Playbook')).toBeInTheDocument();
    }, { timeout: 12000 });
  });

  it('shows a Run button for each playbook card', { timeout: 20000 }, async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.playbooks.list).mockResolvedValue([
      makePlaybook({ name: 'Alpha Playbook', path: 'gateway/alpha.yaml' }),
      makePlaybook({ name: 'Beta Playbook', path: 'gateway/beta.yaml' }),
    ]);
    await renderPlaybooks();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /run alpha playbook/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /run beta playbook/i })).toBeInTheDocument();
    }, { timeout: 12000 });
  });

  it('shows gateway category section in unfiltered view', { timeout: 20000 }, async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.playbooks.list).mockResolvedValue([
      makePlaybook({ name: 'GW Playbook', path: 'gateway/gw.yaml', domain: 'gateway' }),
    ]);
    await renderPlaybooks();
    await waitFor(() => {
      expect(screen.getByText(/gateway/i)).toBeInTheDocument();
    }, { timeout: 12000 });
  });

  it('renders in domainFilter=gateway mode', { timeout: 20000 }, async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.playbooks.list).mockResolvedValue([
      makePlaybook({ name: 'GW Playbook', path: 'gateway/gw.yaml', domain: 'gateway' }),
    ]);
    await renderPlaybooks({ domainFilter: 'gateway' });
    await waitFor(() => {
      expect(screen.getByText('GW Playbook')).toBeInTheDocument();
    }, { timeout: 12000 });
  });

  it('shows domain-specific heading when domainFilter is set', { timeout: 20000 }, async () => {
    await renderPlaybooks({ domainFilter: 'designer' });
    expect(screen.getByText(/designer playbooks/i)).toBeInTheDocument();
  });

  it('shows empty state when filtered domain has no playbooks', { timeout: 20000 }, async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.playbooks.list).mockResolvedValue([
      makePlaybook({ name: 'GW Playbook', path: 'gateway/gw.yaml', domain: 'gateway' }),
    ]);
    await renderPlaybooks({ domainFilter: 'designer' });
    await waitFor(() => {
      expect(screen.getByText(/no designer playbooks found/i)).toBeInTheDocument();
    }, { timeout: 12000 });
  });
});
