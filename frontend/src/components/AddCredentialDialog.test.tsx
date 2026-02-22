/**
 * Tests for AddCredentialDialog component
 *
 * Goals:
 * - Renders nothing when open=false
 * - Shows dialog when open=true
 * - Shows required form fields
 * - Submit is disabled when required fields are empty
 * - Cancel button calls onClose
 * - onSubmit is called with correct data on valid submit
 * - Session-only toggle changes button label
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AddCredentialDialog } from './AddCredentialDialog';

// ---------------------------------------------------------------------------
// Mock the store (AddCredentialDialog uses useStore for addSessionCredential)
// ---------------------------------------------------------------------------
const mockAddSessionCredential = vi.fn();

vi.mock('../store', () => ({
  useStore: (selector: (state: { addSessionCredential: typeof mockAddSessionCredential }) => unknown) =>
    selector({ addSessionCredential: mockAddSessionCredential }),
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
// ResizeObserver - MUI TextareaAutosize uses it; ensure proper constructor
// ---------------------------------------------------------------------------
class ResizeObserverMock {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
window.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const defaultProps = {
  open: true,
  onClose: vi.fn(),
  onSubmit: vi.fn(),
  isLoading: false,
  error: null,
};

function renderDialog(overrides: Partial<typeof defaultProps> = {}) {
  const props = { ...defaultProps, ...overrides };
  return render(<AddCredentialDialog {...props} />);
}

// Helper: get a textbox by its placeholder text or accessible name
function getInput(placeholder: string) {
  return screen.getByPlaceholderText(placeholder);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AddCredentialDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    defaultProps.onClose = vi.fn();
    defaultProps.onSubmit = vi.fn();
  });

  it('renders nothing (no dialog) when open=false', () => {
    renderDialog({ open: false });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows the dialog when open=true', () => {
    renderDialog({ open: true });
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Add New Credential')).toBeInTheDocument();
  });

  it('shows the Name field by label text', () => {
    renderDialog();
    // MUI TextField label text is visible on screen
    expect(screen.getByText('Name')).toBeInTheDocument();
    // The input itself has a placeholder
    expect(getInput('gateway_admin')).toBeInTheDocument();
  });

  it('shows the Username field', () => {
    renderDialog();
    expect(screen.getByText('Username')).toBeInTheDocument();
    expect(getInput('admin')).toBeInTheDocument();
  });

  it('shows the Password field', () => {
    renderDialog();
    expect(screen.getByText('Password')).toBeInTheDocument();
    // Password inputs have no placeholder in this component, find by type
    const passwordInput = document.querySelector('input[type="password"]');
    expect(passwordInput).toBeInTheDocument();
  });

  it('shows the Gateway URL field', () => {
    renderDialog();
    // MUI renders the label text in multiple elements; use getAllByText
    const gatewayUrlLabels = screen.getAllByText('Gateway URL (Optional)');
    expect(gatewayUrlLabels.length).toBeGreaterThanOrEqual(1);
    expect(getInput('http://localhost:8088')).toBeInTheDocument();
  });

  it('submit button is disabled when required fields are empty', () => {
    renderDialog();
    const submitBtn = screen.getByRole('button', { name: /save credential/i });
    expect(submitBtn).toBeDisabled();
  });

  it('submit button becomes enabled when required fields are filled', async () => {
    renderDialog();

    fireEvent.change(getInput('gateway_admin'), { target: { value: 'my-cred' } });
    fireEvent.change(getInput('admin'), { target: { value: 'admin' } });
    const passwordInput = document.querySelector('input[type="password"]')!;
    fireEvent.change(passwordInput, { target: { value: 'secret' } });

    await waitFor(() => {
      const submitBtn = screen.getByRole('button', { name: /save credential/i });
      expect(submitBtn).not.toBeDisabled();
    });
  });

  it('calls onClose when Cancel is clicked', () => {
    const onClose = vi.fn();
    renderDialog({ onClose });
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('calls onSubmit with correct data on valid submit', async () => {
    const onSubmit = vi.fn();
    renderDialog({ onSubmit });

    fireEvent.change(getInput('gateway_admin'), { target: { value: 'prod-cred' } });
    fireEvent.change(getInput('admin'), { target: { value: 'admin' } });
    const passwordInput = document.querySelector('input[type="password"]')!;
    fireEvent.change(passwordInput, { target: { value: 'mypassword' } });
    fireEvent.change(getInput('http://localhost:8088'), {
      target: { value: 'http://localhost:8088' },
    });

    fireEvent.click(screen.getByRole('button', { name: /save credential/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledTimes(1);
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'prod-cred',
          username: 'admin',
          password: 'mypassword',
          gateway_url: 'http://localhost:8088',
        })
      );
    });
  });

  it('shows error alert when error prop is provided and not session-only', () => {
    renderDialog({ error: 'Credential name already exists' });
    expect(screen.getByText('Credential name already exists')).toBeInTheDocument();
  });

  it('shows "Session Only" toggle label', () => {
    renderDialog();
    expect(screen.getByText(/session only/i)).toBeInTheDocument();
  });

  it('changes submit button label to "Add (Session Only)" when session-only switch is toggled', async () => {
    renderDialog();
    // MUI Switch renders an input[type="checkbox"] internally
    const switchInput = document.querySelector('input[type="checkbox"]') as HTMLInputElement;
    expect(switchInput).toBeInTheDocument();
    fireEvent.click(switchInput);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /add \(session only\)/i })).toBeInTheDocument();
    });
  });
});
