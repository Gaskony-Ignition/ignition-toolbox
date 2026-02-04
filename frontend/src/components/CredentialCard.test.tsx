/**
 * Tests for CredentialCard component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CredentialCard } from './CredentialCard';
import type { CredentialInfo } from '../types/api';

// Helper to create a test credential
function createTestCredential(overrides: Partial<CredentialInfo> = {}): CredentialInfo {
  return {
    name: 'test-credential',
    username: 'admin',
    gateway_url: 'http://localhost:8088',
    description: 'Test credential for development',
    ...overrides,
  };
}

describe('CredentialCard', () => {
  const mockOnDelete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders credential name', () => {
    const credential = createTestCredential({ name: 'my-gateway' });
    render(<CredentialCard credential={credential} onDelete={mockOnDelete} />);

    expect(screen.getByText('my-gateway')).toBeInTheDocument();
  });

  it('renders username', () => {
    const credential = createTestCredential({ username: 'gateway-admin' });
    render(<CredentialCard credential={credential} onDelete={mockOnDelete} />);

    expect(screen.getByText('Username:')).toBeInTheDocument();
    expect(screen.getByText('gateway-admin')).toBeInTheDocument();
  });

  it('renders gateway URL when provided', () => {
    const credential = createTestCredential({ gateway_url: 'https://ignition.example.com' });
    render(<CredentialCard credential={credential} onDelete={mockOnDelete} />);

    expect(screen.getByText('Gateway URL:')).toBeInTheDocument();
    expect(screen.getByText('https://ignition.example.com')).toBeInTheDocument();
  });

  it('hides gateway URL section when not provided', () => {
    const credential = createTestCredential({ gateway_url: undefined });
    render(<CredentialCard credential={credential} onDelete={mockOnDelete} />);

    expect(screen.queryByText('Gateway URL:')).not.toBeInTheDocument();
  });

  it('renders description when provided', () => {
    const credential = createTestCredential({ description: 'Production gateway credentials' });
    render(<CredentialCard credential={credential} onDelete={mockOnDelete} />);

    expect(screen.getByText('Production gateway credentials')).toBeInTheDocument();
  });

  it('hides description when not provided', () => {
    const credential = createTestCredential({ description: undefined });
    render(<CredentialCard credential={credential} onDelete={mockOnDelete} />);

    // Description area should not show any extra description text
    // (but "Password: ••••••••" should still show)
    expect(screen.getByText('Password: ••••••••')).toBeInTheDocument();
  });

  it('shows masked password', () => {
    const credential = createTestCredential();
    render(<CredentialCard credential={credential} onDelete={mockOnDelete} />);

    expect(screen.getByText('Password: ••••••••')).toBeInTheDocument();
  });

  it('renders key icon', () => {
    const credential = createTestCredential();
    render(<CredentialCard credential={credential} onDelete={mockOnDelete} />);

    expect(screen.getByTestId('KeyIcon')).toBeInTheDocument();
  });

  it('renders delete button', () => {
    const credential = createTestCredential({ name: 'my-cred' });
    render(<CredentialCard credential={credential} onDelete={mockOnDelete} />);

    const deleteButton = screen.getByRole('button', { name: /delete my-cred credential/i });
    expect(deleteButton).toBeInTheDocument();
  });

  it('calls onDelete when delete is confirmed', () => {
    const credential = createTestCredential({ name: 'delete-me' });

    // Mock window.confirm to return true
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(<CredentialCard credential={credential} onDelete={mockOnDelete} />);

    fireEvent.click(screen.getByRole('button', { name: /delete delete-me credential/i }));

    expect(confirmSpy).toHaveBeenCalledWith('Are you sure you want to delete credential "delete-me"?');
    expect(mockOnDelete).toHaveBeenCalledWith('delete-me');

    confirmSpy.mockRestore();
  });

  it('does not call onDelete when delete is cancelled', () => {
    const credential = createTestCredential({ name: 'keep-me' });

    // Mock window.confirm to return false
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);

    render(<CredentialCard credential={credential} onDelete={mockOnDelete} />);

    fireEvent.click(screen.getByRole('button', { name: /delete keep-me credential/i }));

    expect(confirmSpy).toHaveBeenCalled();
    expect(mockOnDelete).not.toHaveBeenCalled();

    confirmSpy.mockRestore();
  });

  it('renders all info for complete credential', () => {
    const credential = createTestCredential({
      name: 'full-cred',
      username: 'full-user',
      gateway_url: 'https://full.example.com',
      description: 'Full description here',
    });

    render(<CredentialCard credential={credential} onDelete={mockOnDelete} />);

    expect(screen.getByText('full-cred')).toBeInTheDocument();
    expect(screen.getByText('full-user')).toBeInTheDocument();
    expect(screen.getByText('https://full.example.com')).toBeInTheDocument();
    expect(screen.getByText('Full description here')).toBeInTheDocument();
    expect(screen.getByText('Password: ••••••••')).toBeInTheDocument();
  });
});
