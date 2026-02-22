/**
 * Smoke tests for the ExecutionDetail page
 *
 * Goals:
 * - Page renders without crashing (no executionId)
 * - Shows "Invalid execution ID" empty state when executionId is undefined
 * - Shows loading state while query is in-flight
 * - Shows execution name/status when data is returned
 * - Shows error state when API fails
 * - Shows step progress section when execution has steps
 * - Status chip shows correct text for "running" status
 * - Status chip shows correct text for "completed" status
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ExecutionDetail } from './ExecutionDetail';

// ---------------------------------------------------------------------------
// Mock the API client
// ---------------------------------------------------------------------------
vi.mock('../api/client', () => ({
  api: {
    executions: {
      get: vi.fn().mockResolvedValue(null),
      enableDebug: vi.fn(),
      disableDebug: vi.fn(),
      resume: vi.fn(),
    },
    logs: {
      getForExecution: vi.fn().mockResolvedValue({ logs: [], total: 0, filtered: 0 }),
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
// Mock heavy child components
// ---------------------------------------------------------------------------
vi.mock('../components/LiveBrowserView', () => ({
  LiveBrowserView: () => <div data-testid="live-browser-view" />,
}));

vi.mock('../components/ExecutionControls', () => ({
  ExecutionControls: () => <div data-testid="execution-controls" />,
}));

vi.mock('../components/DebugPanel', () => ({
  DebugPanel: () => <div data-testid="debug-panel" />,
}));

vi.mock('../components/PlaybookCodeViewer', () => ({
  PlaybookCodeViewer: () => <div data-testid="playbook-code-viewer" />,
}));

vi.mock('../components/ExecutionTimeline', () => ({
  ExecutionTimeline: () => <div data-testid="execution-timeline" />,
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

function renderExecutionDetail(executionId?: string, queryClient?: QueryClient) {
  const qc = queryClient ?? makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ExecutionDetail executionId={executionId} />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Sample execution data
// ---------------------------------------------------------------------------

const sampleRunningExecution = {
  id: 'exec-123',
  execution_id: 'exec-123',
  playbook_name: 'Test Playbook',
  status: 'running',
  started_at: '2024-01-01T10:00:00',
  completed_at: null,
  total_steps: 5,
  current_step_index: 2,
  debug_mode: false,
  domain: 'gateway',
  error: null,
  step_results: [
    { step_id: 'step1', step_name: 'Open Browser', status: 'completed', duration_ms: 100, completed_at: '2024-01-01T10:00:01', error: null, output: null },
    { step_id: 'step2', step_name: 'Navigate to Page', status: 'completed', duration_ms: 200, completed_at: '2024-01-01T10:00:02', error: null, output: null },
    { step_id: 'step3', step_name: 'Click Button', status: 'running', duration_ms: null, completed_at: null, error: null, output: null },
  ],
};

const sampleCompletedExecution = {
  ...sampleRunningExecution,
  status: 'completed',
  completed_at: '2024-01-01T10:05:00',
  current_step_index: 4,
  step_results: sampleRunningExecution.step_results.map((s) => ({
    ...s,
    status: 'completed',
    completed_at: '2024-01-01T10:05:00',
  })),
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ExecutionDetail page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing when no executionId provided', () => {
    renderExecutionDetail(undefined);
    expect(document.body).toBeTruthy();
  });

  it('shows invalid state message when executionId is undefined', () => {
    renderExecutionDetail(undefined);
    expect(screen.getByText(/invalid execution id/i)).toBeInTheDocument();
  });

  it('shows loading state when query is in-flight', async () => {
    const { api } = await import('../api/client');
    // Keep the query in-flight indefinitely
    vi.mocked(api.executions.get).mockReturnValue(new Promise(() => {}));

    renderExecutionDetail('exec-123');

    expect(screen.getByText(/loading execution details/i)).toBeInTheDocument();
  });

  it('shows execution name when execution data is returned', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.executions.get).mockResolvedValue(sampleRunningExecution as any);

    renderExecutionDetail('exec-123');

    await waitFor(() => {
      expect(screen.getByText('Test Playbook')).toBeInTheDocument();
    });
  });

  it('shows error state when API fails', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.executions.get).mockRejectedValue(new Error('Network failure'));

    renderExecutionDetail('exec-123');

    await waitFor(() => {
      expect(screen.getByText(/failed to load execution/i)).toBeInTheDocument();
    });
  });

  it('shows step progress section when execution has steps', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.executions.get).mockResolvedValue(sampleRunningExecution as any);

    renderExecutionDetail('exec-123');

    await waitFor(() => {
      expect(screen.getByText('Step Progress')).toBeInTheDocument();
    });
  });

  it('shows status chip with "running" text for a running execution', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.executions.get).mockResolvedValue(sampleRunningExecution as any);

    renderExecutionDetail('exec-123');

    await waitFor(() => {
      expect(screen.getByText('running')).toBeInTheDocument();
    });
  });

  it('shows status chip with "completed" text for a completed execution', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.executions.get).mockResolvedValue(sampleCompletedExecution as any);

    renderExecutionDetail('exec-123');

    await waitFor(() => {
      expect(screen.getByText('completed')).toBeInTheDocument();
    });
  });

  it('shows the execution ID in the header', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.executions.get).mockResolvedValue(sampleRunningExecution as any);

    renderExecutionDetail('exec-123');

    await waitFor(() => {
      expect(screen.getByText(/exec-123/)).toBeInTheDocument();
    });
  });

  it('shows "Execution not found" when API returns null and no WebSocket update', async () => {
    const { api } = await import('../api/client');
    // API returns null — the component's !execution guard renders "Execution not found"
    vi.mocked(api.executions.get).mockResolvedValue(null as any);

    renderExecutionDetail('exec-123');

    await waitFor(() => {
      expect(screen.getByText(/execution not found/i)).toBeInTheDocument();
    });
  });
});
