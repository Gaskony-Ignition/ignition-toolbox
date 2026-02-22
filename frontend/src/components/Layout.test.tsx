/**
 * Tests for Layout component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './Layout';

// Mock the API client — prevent real HTTP calls
vi.mock('../api/client', () => ({
  api: {
    credentials: {
      list: vi.fn().mockResolvedValue([]),
    },
    cloudDesigner: {
      getStatus: vi.fn().mockResolvedValue({ status: 'stopped' }),
    },
  },
}));

// Mock package.json version import
vi.mock('../../package.json', () => ({
  default: { version: '3.0.1' },
}));

// electronAPI is NOT present by default (non-Electron environment) — isElectron() returns false
// so the update-listener useEffect is skipped cleanly.

// ---- Helpers ----

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        // Avoid "act" warnings from background refetches
        staleTime: Infinity,
      },
    },
  });
}

function renderLayout(children: React.ReactNode = <div>page content</div>) {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <Layout>{children}</Layout>
    </QueryClientProvider>
  );
}

describe('Layout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderLayout();
    expect(screen.getByText('Ignition Toolbox')).toBeInTheDocument();
  });

  it('renders the app logo/title', () => {
    renderLayout();
    expect(screen.getByText('Ignition Toolbox')).toBeInTheDocument();
  });

  it('renders main navigation tabs', () => {
    renderLayout();
    expect(screen.getByRole('button', { name: /playbooks/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /browser designer/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /api/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /stacks/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /udts/i })).toBeInTheDocument();
  });

  it('renders the version number', () => {
    renderLayout();
    expect(screen.getByText('v3.0.1')).toBeInTheDocument();
  });

  it('renders the credential selector button', () => {
    renderLayout();
    // The credential dropdown button defaults to "Select Credential"
    expect(screen.getByRole('button', { name: /select credential/i })).toBeInTheDocument();
  });

  it('renders children content', () => {
    renderLayout(<div>Hello World Content</div>);
    expect(screen.getByText('Hello World Content')).toBeInTheDocument();
  });

  it('renders playbook sub-tabs when Playbooks tab is active (default)', () => {
    renderLayout();
    // Playbooks is the default tab — sub-tabs should be visible.
    // Sub-tabs: Gateway, Designer, Perspective, Active Execution
    expect(screen.getByRole('button', { name: /gateway/i })).toBeInTheDocument();
    // "Designer" sub-tab exists (main nav has "Browser Designer", sub-tab has "Designer")
    const designerButtons = screen.getAllByRole('button', { name: /designer/i });
    expect(designerButtons.length).toBeGreaterThanOrEqual(2); // main tab + sub-tab
    expect(screen.getByRole('button', { name: /active execution/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /perspective/i })).toBeInTheDocument();
  });

  it('switches to API tab when the API button is clicked', () => {
    renderLayout();

    const apiButton = screen.getByRole('button', { name: /^api$/i });
    fireEvent.click(apiButton);

    // After switching to API tab, playbook sub-tabs should NOT be visible
    expect(screen.queryByRole('button', { name: /active execution/i })).not.toBeInTheDocument();
  });

  it('shows stack sub-tabs when Stacks tab is clicked', () => {
    renderLayout();

    const stacksButton = screen.getByRole('button', { name: /stacks/i });
    fireEvent.click(stacksButton);

    expect(screen.getByRole('button', { name: /services/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /integrations/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /preview/i })).toBeInTheDocument();
  });

  it('does not show update button when no update is available', () => {
    renderLayout();
    expect(screen.queryByRole('button', { name: /update available/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /install & restart/i })).not.toBeInTheDocument();
  });

  it('does not show active execution indicator when no executions are running', () => {
    renderLayout();
    // The active execution icon button only appears when activeExecutions.length > 0
    // With an empty executionUpdates map, it should not be rendered
    expect(screen.queryByRole('button', { name: /execution running/i })).not.toBeInTheDocument();
  });
});
