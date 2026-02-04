/**
 * Tests for PlaybookCard component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PlaybookCard } from './PlaybookCard';
import type { PlaybookInfo } from '../types/api';

// Mock the store
vi.mock('../store', () => ({
  useStore: vi.fn(() => ({
    selectedCredential: null,
  })),
}));

// Mock the API client
vi.mock('../api/client', () => ({
  api: {
    playbooks: {
      verify: vi.fn(),
      unverify: vi.fn(),
      enable: vi.fn(),
      disable: vi.fn(),
      updateMetadata: vi.fn(),
      delete: vi.fn(),
      duplicate: vi.fn(),
    },
  },
}));

// Mock ScheduleDialog
vi.mock('./ScheduleDialog', () => ({
  default: () => null,
}));

// Helper to create a test playbook
function createTestPlaybook(overrides: Partial<PlaybookInfo> = {}): PlaybookInfo {
  return {
    name: 'Test Playbook',
    path: 'gateway/test-playbook.yaml',
    version: '1.0',
    description: 'A test playbook for testing',
    parameter_count: 2,
    step_count: 5,
    parameters: [
      { name: 'gateway_url', type: 'string', required: true, default: null, description: '' },
      { name: 'custom_param', type: 'string', required: true, default: null, description: '' },
    ],
    steps: [
      { id: 'step1', name: 'Step 1', type: 'gateway.wait_ready', timeout: 30, retry_count: 3 },
      { id: 'step2', name: 'Step 2', type: 'gateway.navigate', timeout: 30, retry_count: 0 },
    ],
    domain: 'gateway',
    group: 'Test Group',
    revision: 1,
    verified: false,
    enabled: true,
    last_modified: '2025-01-01T00:00:00Z',
    verified_at: null,
    origin: 'built-in',
    duplicated_from: null,
    created_at: '2025-01-01T00:00:00Z',
    ...overrides,
  };
}

// Helper to render with QueryClient
function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
}

describe('PlaybookCard', () => {
  const mockOnConfigure = vi.fn();
  const mockOnExecute = vi.fn();
  const mockOnExport = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders playbook name and description', () => {
    const playbook = createTestPlaybook();
    renderWithQueryClient(
      <PlaybookCard
        playbook={playbook}
        onConfigure={mockOnConfigure}
      />
    );

    expect(screen.getByText('Test Playbook')).toBeInTheDocument();
    expect(screen.getByText('A test playbook for testing')).toBeInTheDocument();
  });

  it('displays version and step count chips', () => {
    const playbook = createTestPlaybook({ version: '2.0', revision: 3, step_count: 10 });
    renderWithQueryClient(
      <PlaybookCard
        playbook={playbook}
        onConfigure={mockOnConfigure}
      />
    );

    expect(screen.getByText('v2.0.r3')).toBeInTheDocument();
    expect(screen.getByText('10 steps')).toBeInTheDocument();
  });

  it('shows verified chip when playbook is verified', () => {
    const playbook = createTestPlaybook({ verified: true });
    renderWithQueryClient(
      <PlaybookCard
        playbook={playbook}
        onConfigure={mockOnConfigure}
      />
    );

    expect(screen.getByText('Verified')).toBeInTheDocument();
  });

  it('shows disabled chip when playbook is disabled', () => {
    const playbook = createTestPlaybook({ enabled: false });
    renderWithQueryClient(
      <PlaybookCard
        playbook={playbook}
        onConfigure={mockOnConfigure}
      />
    );

    expect(screen.getByText('Disabled')).toBeInTheDocument();
  });

  it('shows warning icon for unverified playbooks', () => {
    const playbook = createTestPlaybook({ verified: false });
    renderWithQueryClient(
      <PlaybookCard
        playbook={playbook}
        onConfigure={mockOnConfigure}
      />
    );

    expect(screen.getByTestId('WarningIcon')).toBeInTheDocument();
  });

  it('calls onConfigure when Configure button is clicked', () => {
    const playbook = createTestPlaybook();
    renderWithQueryClient(
      <PlaybookCard
        playbook={playbook}
        onConfigure={mockOnConfigure}
      />
    );

    const configureButton = screen.getByRole('button', { name: /configure.*playbook/i });
    fireEvent.click(configureButton);

    expect(mockOnConfigure).toHaveBeenCalledWith(playbook);
  });

  it('disables Execute button when playbook is disabled', () => {
    const playbook = createTestPlaybook({ enabled: false });
    renderWithQueryClient(
      <PlaybookCard
        playbook={playbook}
        onConfigure={mockOnConfigure}
        onExecute={mockOnExecute}
      />
    );

    const executeButton = screen.getByRole('button', { name: /execute.*playbook/i });
    expect(executeButton).toBeDisabled();
  });

  it('disables Execute button when parameters are not configured', () => {
    const playbook = createTestPlaybook({
      parameters: [
        { name: 'custom_param', type: 'string', required: true, default: null, description: '' },
      ],
    });
    renderWithQueryClient(
      <PlaybookCard
        playbook={playbook}
        onConfigure={mockOnConfigure}
        onExecute={mockOnExecute}
      />
    );

    const executeButton = screen.getByRole('button', { name: /execute.*playbook/i });
    expect(executeButton).toBeDisabled();
  });

  it('enables Execute button for playbook with no parameters and global credential', async () => {
    // Mock store to return a credential
    const { useStore } = await import('../store');
    vi.mocked(useStore).mockReturnValue({
      selectedCredential: { name: 'test-cred', url: 'http://test', username: 'user' },
    });

    const playbook = createTestPlaybook({
      parameters: [],
      parameter_count: 0,
    });
    renderWithQueryClient(
      <PlaybookCard
        playbook={playbook}
        onConfigure={mockOnConfigure}
        onExecute={mockOnExecute}
      />
    );

    const executeButton = screen.getByRole('button', { name: /execute.*playbook/i });
    expect(executeButton).not.toBeDisabled();
  });

  it('has debug mode toggle', () => {
    const playbook = createTestPlaybook();
    renderWithQueryClient(
      <PlaybookCard
        playbook={playbook}
        onConfigure={mockOnConfigure}
      />
    );

    // Verify debug label is present
    expect(screen.getByText('Debug')).toBeInTheDocument();

    // Find the debug icon
    expect(screen.getByTestId('BugReportIcon')).toBeInTheDocument();
  });

  it('shows menu when menu button is clicked', () => {
    const playbook = createTestPlaybook();
    renderWithQueryClient(
      <PlaybookCard
        playbook={playbook}
        onConfigure={mockOnConfigure}
        onExport={mockOnExport}
      />
    );

    // Find and click menu button
    const menuButton = screen.getByTestId('MoreVertIcon').closest('button');
    expect(menuButton).toBeInTheDocument();

    fireEvent.click(menuButton!);

    // Menu items should be visible
    expect(screen.getByText('Show Details')).toBeInTheDocument();
    expect(screen.getByText('Edit Playbook')).toBeInTheDocument();
    expect(screen.getByText('Duplicate Playbook')).toBeInTheDocument();
  });

  it('displays truncated path', () => {
    const playbook = createTestPlaybook({ path: 'gateway/category/test-playbook.yaml' });
    renderWithQueryClient(
      <PlaybookCard
        playbook={playbook}
        onConfigure={mockOnConfigure}
      />
    );

    // Should show last two parts of path
    expect(screen.getByText('category/test-playbook.yaml')).toBeInTheDocument();
  });

  it('has schedule mode toggle', () => {
    const playbook = createTestPlaybook();
    renderWithQueryClient(
      <PlaybookCard
        playbook={playbook}
        onConfigure={mockOnConfigure}
      />
    );

    // Verify schedule label is present
    expect(screen.getByText('Schedule')).toBeInTheDocument();

    // Find the schedule icon
    expect(screen.getByTestId('ScheduleIcon')).toBeInTheDocument();
  });

  it('opens details dialog when Show Details is clicked', () => {
    const playbook = createTestPlaybook();
    renderWithQueryClient(
      <PlaybookCard
        playbook={playbook}
        onConfigure={mockOnConfigure}
        onExport={mockOnExport}
      />
    );

    // Open menu
    const menuButton = screen.getByTestId('MoreVertIcon').closest('button');
    fireEvent.click(menuButton!);

    // Click Show Details
    fireEvent.click(screen.getByText('Show Details'));

    // Dialog should be open
    expect(screen.getByText('Test Playbook - Details')).toBeInTheDocument();
  });
});
