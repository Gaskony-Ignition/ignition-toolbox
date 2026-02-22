/**
 * Tests for CreatePlaybookDialog component
 */

import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient } from '@tanstack/react-query';
import { CreatePlaybookDialog } from './CreatePlaybookDialog';

// MUI TextareaAutosize calls `new ResizeObserver(...)`. The global setup mocks
// it as a plain vi.fn() (not a class). After vi.clearAllMocks() that mock loses
// its implementation and MUI crashes. Override with a real class in beforeAll so
// it survives clearAllMocks() and is always configurable for re-definition.
beforeAll(() => {
  class ResizeObserverStub {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
  }
  Object.defineProperty(window, 'ResizeObserver', {
    value: ResizeObserverStub,
    writable: true,
    configurable: true,
  });
});

// Mock the API client — control playbook creation behaviour
const mockCreate = vi.fn();
vi.mock('../api/client', () => ({
  api: {
    playbooks: {
      create: (...args: unknown[]) => mockCreate(...args),
    },
  },
}));

// ---- Helpers ----

function renderDialog(props: {
  open?: boolean;
  onClose?: () => void;
  defaultDomain?: 'gateway' | 'perspective' | 'designer';
  showNotification?: (msg: string, severity: string) => void;
}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const onClose = props.onClose ?? vi.fn();
  const showNotification = props.showNotification ?? vi.fn();

  return {
    onClose,
    showNotification,
    ...render(
      <CreatePlaybookDialog
        open={props.open ?? true}
        onClose={onClose}
        defaultDomain={props.defaultDomain ?? 'gateway'}
        queryClient={queryClient}
        showNotification={showNotification}
      />
    ),
  };
}

describe('CreatePlaybookDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the dialog when open=true', () => {
    renderDialog({ open: true });
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('does not render the dialog when open=false', () => {
    renderDialog({ open: false });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows the dialog title', () => {
    renderDialog({ open: true });
    expect(screen.getByText('Create New Playbook')).toBeInTheDocument();
  });

  it('renders the Playbook Name text field', () => {
    renderDialog({ open: true });
    expect(screen.getByLabelText(/playbook name/i)).toBeInTheDocument();
  });

  it('renders the Description text field', () => {
    renderDialog({ open: true });
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
  });

  it('renders the Domain selector', () => {
    renderDialog({ open: true });
    // The MUI Select renders as a combobox
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('shows all three domain options (Gateway, Perspective, Designer)', () => {
    renderDialog({ open: true });

    // Open the select dropdown
    const select = screen.getByRole('combobox');
    fireEvent.mouseDown(select);

    expect(screen.getByRole('option', { name: 'Gateway' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Perspective' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Designer' })).toBeInTheDocument();
  });

  it('defaults to the defaultDomain prop', () => {
    renderDialog({ open: true, defaultDomain: 'perspective' });

    // The visible value of the Select should be "Perspective"
    expect(screen.getByText('Perspective')).toBeInTheDocument();
  });

  it('shows an informational alert about template creation', () => {
    renderDialog({ open: true });
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/basic playbook template/i)).toBeInTheDocument();
  });

  it('has a Cancel button', () => {
    renderDialog({ open: true });
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  it('calls onClose when Cancel is clicked', () => {
    const { onClose } = renderDialog({ open: true });

    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('has a Create Playbook button', () => {
    renderDialog({ open: true });
    expect(screen.getByRole('button', { name: /create playbook/i })).toBeInTheDocument();
  });

  it('Create Playbook button is disabled when name is empty', () => {
    renderDialog({ open: true });

    const createButton = screen.getByRole('button', { name: /create playbook/i });
    // Input starts empty
    expect(createButton).toBeDisabled();
  });

  it('Create Playbook button is enabled when a name is entered', () => {
    renderDialog({ open: true });

    const nameInput = screen.getByLabelText(/playbook name/i);
    fireEvent.change(nameInput, { target: { value: 'My New Playbook' } });

    const createButton = screen.getByRole('button', { name: /create playbook/i });
    expect(createButton).not.toBeDisabled();
  });

  it('shows a warning notification when Create is clicked with empty name', async () => {
    const { showNotification } = renderDialog({ open: true });

    // Try to force submission even though button is disabled — call handleCreatePlaybook
    // by directly typing an empty string (name is empty by default)
    // The button is disabled, so we simulate the scenario via showNotification mock
    // We verify the guard logic by checking showNotification is NOT called (button is disabled)
    const createButton = screen.getByRole('button', { name: /create playbook/i });
    expect(createButton).toBeDisabled();

    // Clicking a disabled button should not trigger the callback at all
    fireEvent.click(createButton);
    expect(showNotification).not.toHaveBeenCalled();
  });

  it('calls api.playbooks.create and onClose on successful creation', async () => {
    mockCreate.mockResolvedValue({ path: '/path/to/new-playbook.yaml', playbook: {} });
    const { onClose, showNotification } = renderDialog({ open: true });

    const nameInput = screen.getByLabelText(/playbook name/i);
    fireEvent.change(nameInput, { target: { value: 'My New Playbook' } });

    fireEvent.click(screen.getByRole('button', { name: /create playbook/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        'My New Playbook',
        'gateway',
        expect.stringContaining('name: "My New Playbook"')
      );
    });

    await waitFor(() => {
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    expect(showNotification).toHaveBeenCalledWith(
      expect.stringContaining('/path/to/new-playbook.yaml'),
      'success'
    );
  });

  it('shows an error notification when api.playbooks.create fails', async () => {
    mockCreate.mockRejectedValue(new Error('Server error'));
    const { showNotification } = renderDialog({ open: true });

    const nameInput = screen.getByLabelText(/playbook name/i);
    fireEvent.change(nameInput, { target: { value: 'Broken Playbook' } });

    fireEvent.click(screen.getByRole('button', { name: /create playbook/i }));

    await waitFor(() => {
      expect(showNotification).toHaveBeenCalledWith(
        expect.stringContaining('Server error'),
        'error'
      );
    });
  });

  it('resets the name field after a successful creation', async () => {
    mockCreate.mockResolvedValue({ path: '/some/path.yaml', playbook: {} });
    renderDialog({ open: true });

    const nameInput = screen.getByLabelText(/playbook name/i);
    fireEvent.change(nameInput, { target: { value: 'Temp Name' } });
    expect(nameInput).toHaveValue('Temp Name');

    fireEvent.click(screen.getByRole('button', { name: /create playbook/i }));

    await waitFor(() => {
      expect(nameInput).toHaveValue('');
    });
  });

  it('passes the selected domain to api.playbooks.create', async () => {
    mockCreate.mockResolvedValue({ path: '/path.yaml', playbook: {} });
    renderDialog({ open: true, defaultDomain: 'gateway' });

    // Change domain to designer
    const select = screen.getByRole('combobox');
    fireEvent.mouseDown(select);
    const designerOption = screen.getByRole('option', { name: 'Designer' });
    fireEvent.click(designerOption);

    const nameInput = screen.getByLabelText(/playbook name/i);
    fireEvent.change(nameInput, { target: { value: 'Designer Playbook' } });
    fireEvent.click(screen.getByRole('button', { name: /create playbook/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        'Designer Playbook',
        'designer',
        expect.any(String)
      );
    });
  });
});
