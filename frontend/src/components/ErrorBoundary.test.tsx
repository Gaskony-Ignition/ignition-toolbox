/**
 * Tests for ErrorBoundary and ErrorFallback components
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary } from './ErrorBoundary';
import { ErrorFallback } from './ErrorFallback';

// Component that throws an error for testing
function ThrowError({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error('Test error message');
  }
  return <div>No error</div>;
}

// Component that throws only on first render (for reset testing)
let throwOnce = true;
function ThrowOnce() {
  if (throwOnce) {
    throwOnce = true; // Will be reset in beforeEach
    throw new Error('Test error message');
  }
  return <div>No error</div>;
}

describe('ErrorBoundary', () => {
  // Suppress console.error during tests since we expect errors
  const originalError = console.error;
  beforeEach(() => {
    console.error = vi.fn();
    throwOnce = true; // Reset the flag for ThrowOnce component
  });

  afterEach(() => {
    console.error = originalError;
  });

  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <div>Child content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Child content')).toBeInTheDocument();
  });

  it('renders fallback UI when child throws error', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText(/Test error message/)).toBeInTheDocument();
  });

  it('logs error to console', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(console.error).toHaveBeenCalled();
  });

  it('provides reset functionality via Try Again button', () => {
    render(
      <ErrorBoundary>
        <ThrowOnce />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    // Set flag to not throw on next render
    throwOnce = false;

    // Click Try Again button - this resets ErrorBoundary and re-renders children
    fireEvent.click(screen.getByRole('button', { name: /try again/i }));

    // Now the child should render without throwing
    expect(screen.getByText('No error')).toBeInTheDocument();
  });
});

describe('ErrorFallback', () => {
  const mockOnReset = vi.fn();
  const mockError = new Error('Test error');
  const mockErrorInfo = {
    componentStack: '\n    at ThrowError\n    at ErrorBoundary',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays error message', () => {
    render(
      <ErrorFallback
        error={mockError}
        errorInfo={mockErrorInfo}
        onReset={mockOnReset}
      />
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText(/Test error/)).toBeInTheDocument();
  });

  it('displays component stack trace', () => {
    render(
      <ErrorFallback
        error={mockError}
        errorInfo={mockErrorInfo}
        onReset={mockOnReset}
      />
    );

    expect(screen.getByText(/at ThrowError/)).toBeInTheDocument();
  });

  it('calls onReset when Try Again is clicked', () => {
    render(
      <ErrorFallback
        error={mockError}
        errorInfo={mockErrorInfo}
        onReset={mockOnReset}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /try again/i }));
    expect(mockOnReset).toHaveBeenCalledTimes(1);
  });

  it('has Reload Page button', () => {
    render(
      <ErrorFallback
        error={mockError}
        errorInfo={mockErrorInfo}
        onReset={mockOnReset}
      />
    );

    expect(screen.getByRole('button', { name: /reload page/i })).toBeInTheDocument();
  });

  it('handles null error gracefully', () => {
    render(
      <ErrorFallback
        error={null}
        errorInfo={null}
        onReset={mockOnReset}
      />
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    // Should not show error details when error is null
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows support message', () => {
    render(
      <ErrorFallback
        error={mockError}
        errorInfo={mockErrorInfo}
        onReset={mockOnReset}
      />
    );

    expect(screen.getByText(/contact support/i)).toBeInTheDocument();
  });
});
