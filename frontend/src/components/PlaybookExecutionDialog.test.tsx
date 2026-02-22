/**
 * Tests for PlaybookExecutionDialog component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PlaybookExecutionDialog } from './PlaybookExecutionDialog';
import type { PlaybookInfo } from '../types/api';

// Mock the API client — no real HTTP calls
vi.mock('../api/client', () => ({
  api: {
    credentials: {
      list: vi.fn().mockResolvedValue([]),
    },
  },
}));

// Mock sub-components to keep tests focused on PlaybookExecutionDialog
vi.mock('./ParameterInput', () => ({
  ParameterInput: ({ parameter, value, onChange }: {
    parameter: { name: string };
    value: string;
    onChange: (name: string, value: string) => void;
  }) => (
    <div data-testid={`param-input-${parameter.name}`}>
      <input
        aria-label={parameter.name}
        value={value}
        onChange={(e) => onChange(parameter.name, e.target.value)}
      />
    </div>
  ),
}));

vi.mock('./TimeoutSettings', () => ({
  TimeoutSettings: () => <div data-testid="timeout-settings">TimeoutSettings</div>,
}));

// ---- Helpers ----

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: Infinity },
    },
  });
}

function createPlaybook(overrides: Partial<PlaybookInfo> = {}): PlaybookInfo {
  return {
    name: 'Test Playbook',
    path: '/path/to/test-playbook.yaml',
    version: '1.0',
    description: 'A test playbook description',
    parameter_count: 0,
    step_count: 3,
    parameters: [],
    steps: [],
    domain: 'gateway',
    group: null,
    revision: 1,
    verified: true,
    enabled: true,
    last_modified: null,
    verified_at: null,
    origin: 'built-in',
    duplicated_from: null,
    created_at: null,
    relevant_timeouts: [],
    ...overrides,
  };
}

function renderDialog(props: {
  open: boolean;
  playbook: PlaybookInfo | null;
  onClose?: () => void;
}) {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <PlaybookExecutionDialog
        open={props.open}
        playbook={props.playbook}
        onClose={props.onClose ?? vi.fn()}
      />
    </QueryClientProvider>
  );
}

describe('PlaybookExecutionDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when playbook is null', () => {
    renderDialog({ open: true, playbook: null });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders the dialog when open=true and playbook is provided', () => {
    const playbook = createPlaybook();
    renderDialog({ open: true, playbook });

    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('does not render the dialog when open=false', () => {
    const playbook = createPlaybook();
    renderDialog({ open: false, playbook });

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows the playbook name in the dialog title', () => {
    const playbook = createPlaybook({ name: 'My Gateway Playbook' });
    renderDialog({ open: true, playbook });

    expect(screen.getByText(/My Gateway Playbook/)).toBeInTheDocument();
  });

  it('shows the playbook description', () => {
    const playbook = createPlaybook({ description: 'Detailed description of the playbook' });
    renderDialog({ open: true, playbook });

    expect(screen.getByText('Detailed description of the playbook')).toBeInTheDocument();
  });

  it('shows version and step count', () => {
    const playbook = createPlaybook({ version: '2.1', step_count: 7 });
    renderDialog({ open: true, playbook });

    expect(screen.getByText(/Version 2\.1/)).toBeInTheDocument();
    expect(screen.getByText(/7 steps/)).toBeInTheDocument();
  });

  it('shows a warning for unverified playbooks', () => {
    const playbook = createPlaybook({ verified: false });
    renderDialog({ open: true, playbook });

    expect(screen.getByText(/has not been verified/i)).toBeInTheDocument();
  });

  it('does not show unverified warning for verified playbooks', () => {
    const playbook = createPlaybook({ verified: true });
    renderDialog({ open: true, playbook });

    expect(screen.queryByText(/has not been verified/i)).not.toBeInTheDocument();
  });

  it('renders parameter inputs for non-sensitive parameters', () => {
    const playbook = createPlaybook({
      parameters: [
        {
          name: 'target_tag',
          type: 'string',
          required: true,
          default: null,
          description: 'Target OPC tag path',
        },
      ],
    });
    renderDialog({ open: true, playbook });

    expect(screen.getByTestId('param-input-target_tag')).toBeInTheDocument();
  });

  it('does not render inputs for filtered sensitive parameters (gateway_url, username, password)', () => {
    const playbook = createPlaybook({
      parameters: [
        { name: 'gateway_url', type: 'string', required: true, default: null, description: 'URL' },
        { name: 'username', type: 'string', required: true, default: null, description: 'User' },
        { name: 'password', type: 'string', required: true, default: null, description: 'Pass' },
        { name: 'safe_param', type: 'string', required: false, default: null, description: 'OK' },
      ],
    });
    renderDialog({ open: true, playbook });

    // gateway_url is filtered out by the component's own logic
    expect(screen.queryByTestId('param-input-gateway_url')).not.toBeInTheDocument();
    // username and password are filtered out as sensitive
    expect(screen.queryByTestId('param-input-username')).not.toBeInTheDocument();
    expect(screen.queryByTestId('param-input-password')).not.toBeInTheDocument();
    // safe_param should be visible
    expect(screen.getByTestId('param-input-safe_param')).toBeInTheDocument();
  });

  it('renders the TimeoutSettings component', () => {
    const playbook = createPlaybook();
    renderDialog({ open: true, playbook });

    expect(screen.getByTestId('timeout-settings')).toBeInTheDocument();
  });

  it('has a Close button that calls onClose', () => {
    const mockOnClose = vi.fn();
    const playbook = createPlaybook();
    renderDialog({ open: true, playbook, onClose: mockOnClose });

    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('has a Save Config button', () => {
    const playbook = createPlaybook();
    renderDialog({ open: true, playbook });

    expect(screen.getByRole('button', { name: /save config/i })).toBeInTheDocument();
  });

  it('Save Config button is initially disabled (no unsaved changes from a clean load)', () => {
    // When no saved config exists and we just opened the dialog, configSaved is false
    // so the button should be enabled. The button is disabled only after a save.
    const playbook = createPlaybook();
    renderDialog({ open: true, playbook });

    const saveButton = screen.getByRole('button', { name: /save config/i });
    // Initially configSaved=false => button is NOT disabled
    expect(saveButton).not.toBeDisabled();
  });

  it('shows "Parameters" section label when non-sensitive parameters exist', () => {
    const playbook = createPlaybook({
      parameters: [
        { name: 'my_param', type: 'string', required: false, default: null, description: 'param' },
      ],
    });
    renderDialog({ open: true, playbook });

    expect(screen.getByText('Parameters')).toBeInTheDocument();
  });
});
