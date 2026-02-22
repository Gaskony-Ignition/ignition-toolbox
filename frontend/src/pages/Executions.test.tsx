/**
 * Smoke tests for the Executions page
 *
 * Goals:
 * - Page renders without crashing
 * - Shows loading state initially
 * - Shows "No executions" empty state when list is empty
 * - Shows execution rows when executions are returned
 * - Action buttons (pause/resume/cancel) are accessible for relevant statuses
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Executions } from './Executions';

// ---------------------------------------------------------------------------
// Mock the API client
// ---------------------------------------------------------------------------
vi.mock('../api/client', () => ({
  api: {
    executions: {
      list: vi.fn().mockResolvedValue([]),
      pause: vi.fn(),
      resume: vi.fn(),
      skip: vi.fn(),
      cancel: vi.fn(),
      delete: vi.fn(),
    },
    getBaseUrl: vi.fn().mockReturnValue('http://localhost:5000'),
  },
}));

// ---------------------------------------------------------------------------
// Mock the Zustand store - the Executions page reads executionUpdates from it
// ---------------------------------------------------------------------------
vi.mock('../store', () => ({
  useStore: (selector: (state: any) => any) => {
    const state = {
      executionUpdates: new Map(),
      setActiveExecutionId: vi.fn(),
      setPlaybookSubTab: vi.fn(),
    };
    return selector(state);
  },
}));

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

function renderExecutions(queryClient?: QueryClient) {
  const qc = queryClient ?? makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Executions />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Sample execution data
// ---------------------------------------------------------------------------

function makeExecution(overrides: Record<string, unknown> = {}) {
  return {
    execution_id: 'exec-abc123',
    playbook_name: 'Test Playbook',
    status: 'running',
    started_at: '2025-01-15T10:00:00Z',
    completed_at: null,
    current_step_index: 1,
    total_steps: 5,
    error: null,
    debug_mode: false,
    step_results: [],
    domain: 'gateway',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Executions page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderExecutions();
    expect(document.body).toBeTruthy();
  });

  it('shows the page heading', () => {
    renderExecutions();
    expect(screen.getByText('Executions')).toBeInTheDocument();
  });

  it('shows status filter toggle buttons', () => {
    renderExecutions();
    expect(
      screen.getByRole('group', { name: /filter executions by status/i })
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /show all executions/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /show running executions/i })).toBeInTheDocument();
  });

  it('shows a Refresh button', () => {
    renderExecutions();
    expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
  });

  it('shows loading indicator while executions are being fetched', async () => {
    const { api } = await import('../api/client');
    // Keep the query in-flight indefinitely so we stay in loading state
    vi.mocked(api.executions.list).mockReturnValue(new Promise(() => {}));

    renderExecutions();

    expect(screen.getByText(/loading executions/i)).toBeInTheDocument();
  });

  it('shows empty state when no executions exist', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.executions.list).mockResolvedValue([]);

    renderExecutions();

    await waitFor(() => {
      expect(
        screen.getByText(/no executions yet/i)
      ).toBeInTheDocument();
    });
  });

  it('shows execution row with playbook name when executions are returned', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.executions.list).mockResolvedValue([makeExecution()] as any);

    renderExecutions();

    await waitFor(() => {
      expect(screen.getByText('Test Playbook')).toBeInTheDocument();
    });
  });

  it('shows status chip for a running execution', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.executions.list).mockResolvedValue([makeExecution({ status: 'running' })] as any);

    renderExecutions();

    await waitFor(() => {
      expect(screen.getByText('RUNNING')).toBeInTheDocument();
    });
  });

  it('shows pause action button for a running execution', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.executions.list).mockResolvedValue([makeExecution({ status: 'running' })] as any);

    renderExecutions();

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /pause test playbook/i })
      ).toBeInTheDocument();
    });
  });

  it('shows cancel action button for a running execution', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.executions.list).mockResolvedValue([makeExecution({ status: 'running' })] as any);

    renderExecutions();

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /cancel test playbook/i })
      ).toBeInTheDocument();
    });
  });

  it('shows resume and skip buttons for a paused execution', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.executions.list).mockResolvedValue([
      makeExecution({ status: 'paused', execution_id: 'exec-paused' }),
    ] as any);

    renderExecutions();

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /resume test playbook/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /skip step in test playbook/i })
      ).toBeInTheDocument();
    });
  });

  it('does not show pause/cancel buttons for a completed execution', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.executions.list).mockResolvedValue([
      makeExecution({ status: 'completed', completed_at: '2025-01-15T10:05:00Z' }),
    ] as any);

    renderExecutions();

    await waitFor(() => {
      expect(screen.getByText('Test Playbook')).toBeInTheDocument();
    });

    expect(screen.queryByRole('button', { name: /pause test playbook/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /cancel test playbook/i })).not.toBeInTheDocument();
  });

  it('shows view-details button for each execution row', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.executions.list).mockResolvedValue([makeExecution()] as any);

    renderExecutions();

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /view test playbook details/i })
      ).toBeInTheDocument();
    });
  });

  it('renders multiple executions as separate rows', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.executions.list).mockResolvedValue([
      makeExecution({ execution_id: 'exec-1', playbook_name: 'Alpha Playbook' }),
      makeExecution({ execution_id: 'exec-2', playbook_name: 'Beta Playbook' }),
    ] as any);

    renderExecutions();

    await waitFor(() => {
      expect(screen.getByText('Alpha Playbook')).toBeInTheDocument();
      expect(screen.getByText('Beta Playbook')).toBeInTheDocument();
    });
  });

  it('shows an error alert when the API fails', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.executions.list).mockRejectedValue(new Error('Server down'));

    renderExecutions();

    await waitFor(() => {
      expect(screen.getByText(/failed to load executions/i)).toBeInTheDocument();
    });
  });
});
