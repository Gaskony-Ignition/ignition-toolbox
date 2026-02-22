/**
 * Smoke tests for the Settings page
 *
 * Goals:
 * - Page renders without crashing
 * - Shows "Settings" page heading
 * - Shows all navigation list items in the sidebar
 * - First tab (Gateway Credentials) content is visible by default
 * - Clicking a nav item shows that tab's content
 * - About tab shows app version/name
 * - Appearance tab shows theme toggle
 * - Updates tab shows expected content
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Settings } from './Settings';

// ---------------------------------------------------------------------------
// Mock the API client
// ---------------------------------------------------------------------------
vi.mock('../api/client', () => ({
  api: {
    health: vi.fn().mockResolvedValue({ status: 'healthy', version: '3.0.1' }),
    credentials: {
      list: vi.fn().mockResolvedValue([]),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
    getBaseUrl: vi.fn().mockReturnValue('http://localhost:5000'),
  },
}));

// ---------------------------------------------------------------------------
// Mock the Zustand store
// ---------------------------------------------------------------------------
vi.mock('../store', () => ({
  useStore: (selector: (state: any) => any) => {
    const state = {
      theme: 'dark',
      setTheme: vi.fn(),
      playbookGridColumns: 5,
      setPlaybookGridColumns: vi.fn(),
      executionUpdates: new Map(),
      setPlaybookSubTab: vi.fn(),
    };
    return selector(state);
  },
}));

// ---------------------------------------------------------------------------
// Mock logger
// ---------------------------------------------------------------------------
vi.mock('../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

// ---------------------------------------------------------------------------
// Mock the Credentials page (it has its own deep tree)
// ---------------------------------------------------------------------------
vi.mock('./Credentials', () => ({
  Credentials: () => <div data-testid="credentials-tab">Credentials Component</div>,
}));

// ---------------------------------------------------------------------------
// Mock DiagnosticsPanel sub-components
// ---------------------------------------------------------------------------
vi.mock('../components/DiagnosticsPanel', () => ({
  DiagnosticsSection: () => <div data-testid="diagnostics-section">Diagnostics</div>,
  DataManagementSection: () => <div data-testid="data-management-section">Data Management</div>,
  LogsSection: () => <div data-testid="logs-section">Logs</div>,
}));

// ---------------------------------------------------------------------------
// Mock global fetch (used in Settings for GitHub token and health)
// ---------------------------------------------------------------------------
const mockFetch = vi.fn().mockResolvedValue({
  ok: true,
  json: () => Promise.resolve({ configured: false, preview: null }),
});
vi.stubGlobal('fetch', mockFetch);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderSettings(queryClient?: QueryClient) {
  const qc = queryClient ?? makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Settings />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Settings page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Re-stub fetch after clearAllMocks
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ configured: false, preview: null }),
    });
    vi.stubGlobal('fetch', mockFetch);
  });

  it('renders without crashing', () => {
    renderSettings();
    expect(document.body).toBeTruthy();
  });

  it('shows the Settings page heading', () => {
    renderSettings();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('shows Gateway Credentials nav item in the sidebar', () => {
    renderSettings();
    expect(screen.getByText('Gateway Credentials')).toBeInTheDocument();
  });

  it('shows Diagnostics nav item in the sidebar', () => {
    renderSettings();
    expect(screen.getByText('Diagnostics')).toBeInTheDocument();
  });

  it('shows Data Management nav item in the sidebar', () => {
    renderSettings();
    expect(screen.getByText('Data Management')).toBeInTheDocument();
  });

  it('shows Logs nav item in the sidebar', () => {
    renderSettings();
    expect(screen.getByText('Logs')).toBeInTheDocument();
  });

  it('shows Updates nav item in the sidebar', () => {
    renderSettings();
    expect(screen.getByText('Updates')).toBeInTheDocument();
  });

  it('shows Appearance nav item in the sidebar', () => {
    renderSettings();
    expect(screen.getByText('Appearance')).toBeInTheDocument();
  });

  it('shows About nav item in the sidebar', () => {
    renderSettings();
    expect(screen.getByText('About')).toBeInTheDocument();
  });

  it('shows Gateway Credentials tab content by default (first tab)', () => {
    renderSettings();
    expect(screen.getByTestId('credentials-tab')).toBeInTheDocument();
  });

  it('clicking Diagnostics tab shows diagnostics content', async () => {
    const user = userEvent.setup();
    renderSettings();

    await user.click(screen.getByText('Diagnostics'));

    await waitFor(() => {
      expect(screen.getByTestId('diagnostics-section')).toBeInTheDocument();
    });
  });

  it('clicking Data Management tab shows data management content', async () => {
    const user = userEvent.setup();
    renderSettings();

    await user.click(screen.getByText('Data Management'));

    await waitFor(() => {
      expect(screen.getByTestId('data-management-section')).toBeInTheDocument();
    });
  });

  it('clicking Appearance tab shows theme options', async () => {
    const user = userEvent.setup();
    renderSettings();

    await user.click(screen.getByText('Appearance'));

    await waitFor(() => {
      expect(screen.getByText(/appearance/i, { selector: 'h6' })).toBeInTheDocument();
    });
  });

  it('Appearance tab shows Dark Mode or Light Mode label', async () => {
    const user = userEvent.setup();
    renderSettings();

    await user.click(screen.getByText('Appearance'));

    await waitFor(() => {
      // The mocked store returns theme='dark', so we expect 'Dark Mode'
      expect(screen.getByText('Dark Mode')).toBeInTheDocument();
    });
  });

  it('clicking About tab shows app name and version info', async () => {
    const user = userEvent.setup();
    renderSettings();

    await user.click(screen.getByText('About'));

    await waitFor(() => {
      expect(screen.getByText('Ignition Toolbox')).toBeInTheDocument();
    });
  });

  it('About tab shows version information', async () => {
    const user = userEvent.setup();
    renderSettings();

    await user.click(screen.getByText('About'));

    await waitFor(() => {
      // Should show version from package.json (format: "Version X.X.X")
      // Use getAllByText since multiple elements may contain "version" text
      const versionElements = screen.getAllByText(/version/i);
      expect(versionElements.length).toBeGreaterThan(0);
    });
  });

  it('clicking Updates tab shows Software Updates heading (non-Electron shows Desktop Only)', async () => {
    const user = userEvent.setup();
    renderSettings();

    await user.click(screen.getByText('Updates'));

    await waitFor(() => {
      // In test environment (no window.electronAPI), shows "Desktop Only Feature"
      expect(
        screen.getByText(/software updates/i) ||
        screen.getByText(/desktop only/i)
      ).toBeInTheDocument();
    });
  });

  it('clicking Logs tab shows logs section content', async () => {
    const user = userEvent.setup();
    renderSettings();

    await user.click(screen.getByText('Logs'));

    await waitFor(() => {
      expect(screen.getByTestId('logs-section')).toBeInTheDocument();
    });
  });
});
