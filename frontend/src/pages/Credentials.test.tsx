/**
 * Smoke tests for the Credentials page
 *
 * Goals:
 * - Page renders without crashing
 * - "Add Credential" button is present
 * - Shows empty state when no credentials exist
 * - Shows credential rows when credentials are returned
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Credentials } from './Credentials';

// ---------------------------------------------------------------------------
// Mock the API client
// ---------------------------------------------------------------------------
vi.mock('../api/client', () => ({
  api: {
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
// Mock child dialogs so they don't add deep dependency trees
// ---------------------------------------------------------------------------
vi.mock('../components/AddCredentialDialog', () => ({
  AddCredentialDialog: ({ open }: { open: boolean }) =>
    open ? <div data-testid="add-credential-dialog">AddCredentialDialog</div> : null,
}));

vi.mock('../components/EditCredentialDialog', () => ({
  EditCredentialDialog: ({ open }: { open: boolean }) =>
    open ? <div data-testid="edit-credential-dialog">EditCredentialDialog</div> : null,
}));

// ---------------------------------------------------------------------------
// Mock logger (avoids import.meta.env issues in tests)
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

function renderCredentials(queryClient?: QueryClient) {
  const qc = queryClient ?? makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Credentials />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// Sample credential data
const sampleCredentials = [
  {
    name: 'prod-gateway',
    username: 'admin',
    gateway_url: 'https://prod.example.com:8088',
    description: 'Production gateway',
  },
  {
    name: 'dev-gateway',
    username: 'developer',
    gateway_url: 'http://dev.example.com:8088',
    description: 'Dev gateway',
  },
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Credentials page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderCredentials();
    expect(document.body).toBeTruthy();
  });

  it('shows the page heading', () => {
    renderCredentials();
    expect(screen.getByText('Gateway Credentials')).toBeInTheDocument();
  });

  it('shows "Add Credential" button', () => {
    renderCredentials();
    expect(
      screen.getByRole('button', { name: /add new credential/i })
    ).toBeInTheDocument();
  });

  it('shows loading indicator while credentials are being fetched', async () => {
    // Make the API hang forever so we stay in loading state
    const { api } = await import('../api/client');
    vi.mocked(api.credentials.list).mockReturnValue(new Promise(() => {}));

    renderCredentials();

    // Loading spinner text is present while the query is in-flight
    expect(screen.getByText(/loading credentials/i)).toBeInTheDocument();
  });

  it('shows empty state when no credentials exist', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.credentials.list).mockResolvedValue([]);

    renderCredentials();

    await waitFor(() => {
      expect(
        screen.getByText(/no credentials yet/i)
      ).toBeInTheDocument();
    });
  });

  it('shows credential rows when credentials are returned', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.credentials.list).mockResolvedValue(sampleCredentials as any);

    renderCredentials();

    await waitFor(() => {
      expect(screen.getByText('prod-gateway')).toBeInTheDocument();
      expect(screen.getByText('dev-gateway')).toBeInTheDocument();
    });
  });

  it('shows usernames in the credentials table', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.credentials.list).mockResolvedValue(sampleCredentials as any);

    renderCredentials();

    await waitFor(() => {
      expect(screen.getByText('admin')).toBeInTheDocument();
      expect(screen.getByText('developer')).toBeInTheDocument();
    });
  });

  it('shows gateway URLs as chips in the table', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.credentials.list).mockResolvedValue(sampleCredentials as any);

    renderCredentials();

    await waitFor(() => {
      expect(screen.getByText('https://prod.example.com:8088')).toBeInTheDocument();
    });
  });

  it('shows edit and delete action buttons for each credential', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.credentials.list).mockResolvedValue(sampleCredentials as any);

    renderCredentials();

    await waitFor(() => {
      // There should be one Edit button per credential
      const editButtons = screen.getAllByRole('button', { name: /edit/i });
      expect(editButtons.length).toBeGreaterThanOrEqual(sampleCredentials.length);

      // There should be one Delete button per credential
      const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
      expect(deleteButtons.length).toBeGreaterThanOrEqual(sampleCredentials.length);
    });
  });

  it('shows an error alert when the API fails', async () => {
    const { api } = await import('../api/client');
    vi.mocked(api.credentials.list).mockRejectedValue(new Error('Network error'));

    renderCredentials();

    await waitFor(() => {
      expect(screen.getByText(/failed to load credentials/i)).toBeInTheDocument();
    });
  });
});
