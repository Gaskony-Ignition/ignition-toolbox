/**
 * Tests for ExecutionControls component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ExecutionControls } from './ExecutionControls';

// Mock the API client - ExecutionControls calls API methods directly
vi.mock('../api/client', () => ({
  api: {
    executions: {
      pause: vi.fn().mockResolvedValue({ status: 'paused', execution_id: 'test-id' }),
      resume: vi.fn().mockResolvedValue({ status: 'running', execution_id: 'test-id' }),
      skip: vi.fn().mockResolvedValue({ status: 'running', execution_id: 'test-id' }),
      cancel: vi.fn().mockResolvedValue({ status: 'cancelled', execution_id: 'test-id' }),
    },
  },
}));

// Import the mocked api so tests can assert on calls
import { api } from '../api/client';

describe('ExecutionControls', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ----- Rendering based on status -----

  it('renders without crashing for running status', () => {
    render(<ExecutionControls executionId="exec-123" status="running" />);
    expect(screen.getByText('Skip')).toBeInTheDocument();
  });

  it('shows Skip, Pause, and Cancel buttons when status is running', () => {
    render(<ExecutionControls executionId="exec-123" status="running" />);

    expect(screen.getByText('Skip')).toBeInTheDocument();
    expect(screen.getByText('Pause')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('shows Skip, Resume, and Cancel buttons when status is paused', () => {
    render(<ExecutionControls executionId="exec-123" status="paused" />);

    expect(screen.getByText('Skip')).toBeInTheDocument();
    expect(screen.getByText('Resume')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('does not show Resume button when status is running', () => {
    render(<ExecutionControls executionId="exec-123" status="running" />);

    expect(screen.queryByText('Resume')).not.toBeInTheDocument();
  });

  it('does not show Pause button when status is paused', () => {
    render(<ExecutionControls executionId="exec-123" status="paused" />);

    expect(screen.queryByText('Pause')).not.toBeInTheDocument();
  });

  it('renders buttons for completed status (buttons present but disabled)', () => {
    render(<ExecutionControls executionId="exec-123" status="completed" />);

    // Buttons are rendered but disabled because isActive is false
    const skipBtn = screen.getByText('Skip').closest('button');
    const cancelBtn = screen.getByText('Cancel').closest('button');

    expect(skipBtn).toBeDisabled();
    expect(cancelBtn).toBeDisabled();
  });

  it('renders buttons for failed status (buttons present but disabled)', () => {
    render(<ExecutionControls executionId="exec-123" status="failed" />);

    const skipBtn = screen.getByText('Skip').closest('button');
    const cancelBtn = screen.getByText('Cancel').closest('button');

    expect(skipBtn).toBeDisabled();
    expect(cancelBtn).toBeDisabled();
  });

  // ----- Enabled state for running -----

  it('buttons are enabled for running status when not disabled', () => {
    render(<ExecutionControls executionId="exec-123" status="running" />);

    const skipBtn = screen.getByText('Skip').closest('button');
    const pauseBtn = screen.getByText('Pause').closest('button');
    const cancelBtn = screen.getByText('Cancel').closest('button');

    expect(skipBtn).not.toBeDisabled();
    expect(pauseBtn).not.toBeDisabled();
    expect(cancelBtn).not.toBeDisabled();
  });

  it('all buttons are disabled when disabled prop is true for running status', () => {
    render(<ExecutionControls executionId="exec-123" status="running" disabled={true} />);

    const skipBtn = screen.getByText('Skip').closest('button');
    const pauseBtn = screen.getByText('Pause').closest('button');
    const cancelBtn = screen.getByText('Cancel').closest('button');

    expect(skipBtn).toBeDisabled();
    expect(pauseBtn).toBeDisabled();
    expect(cancelBtn).toBeDisabled();
  });

  // ----- Pause button -----

  it('calls api.executions.pause with correct executionId when Pause clicked', async () => {
    render(<ExecutionControls executionId="exec-pause-test" status="running" />);

    fireEvent.click(screen.getByText('Pause'));

    await waitFor(() => {
      expect(api.executions.pause).toHaveBeenCalledWith('exec-pause-test');
    });
  });

  // ----- Resume button -----

  it('calls api.executions.resume with correct executionId when Resume clicked', async () => {
    render(<ExecutionControls executionId="exec-resume-test" status="paused" />);

    fireEvent.click(screen.getByText('Resume'));

    await waitFor(() => {
      expect(api.executions.resume).toHaveBeenCalledWith('exec-resume-test');
    });
  });

  // ----- Skip button -----

  it('calls api.executions.skip with correct executionId when Skip clicked', async () => {
    render(<ExecutionControls executionId="exec-skip-test" status="running" />);

    fireEvent.click(screen.getByText('Skip'));

    await waitFor(() => {
      expect(api.executions.skip).toHaveBeenCalledWith('exec-skip-test');
    });
  });

  // ----- Cancel button -----

  it('calls api.executions.cancel with correct executionId when Cancel clicked', async () => {
    render(<ExecutionControls executionId="exec-cancel-test" status="running" />);

    fireEvent.click(screen.getByText('Cancel'));

    await waitFor(() => {
      expect(api.executions.cancel).toHaveBeenCalledWith('exec-cancel-test');
    });
  });

  it('does not call cancel again if cancel already in progress (debounce)', async () => {
    // Make cancel take a long time to simulate in-progress state
    let resolveCancel!: () => void;
    const slowCancel = new Promise<{ status: string; execution_id: string }>((resolve) => {
      resolveCancel = () => resolve({ status: 'cancelled', execution_id: 'exec-123' });
    });
    vi.mocked(api.executions.cancel).mockReturnValueOnce(slowCancel);

    render(<ExecutionControls executionId="exec-123" status="running" />);

    const cancelBtn = screen.getByText('Cancel').closest('button')!;
    fireEvent.click(cancelBtn);

    // Try clicking again while first request is in flight
    fireEvent.click(cancelBtn);

    // Resolve the first cancel
    resolveCancel();

    await waitFor(() => {
      // cancel should only have been called once
      expect(api.executions.cancel).toHaveBeenCalledTimes(1);
    });
  });

  // ----- Button labels confirm tooltip context -----
  // MUI Tooltip renders its title in a portal (not as HTML title attr), so we
  // verify the correct buttons are present with the right labels, which is the
  // observable behaviour the tooltips are clarifying.

  it('Skip button is present in running state with correct text label', () => {
    render(<ExecutionControls executionId="exec-123" status="running" />);

    expect(screen.getByText('Skip')).toBeInTheDocument();
  });

  it('Pause button is present in running state with correct text label', () => {
    render(<ExecutionControls executionId="exec-123" status="running" />);

    expect(screen.getByText('Pause')).toBeInTheDocument();
  });

  it('Resume button is present in paused state with correct text label', () => {
    render(<ExecutionControls executionId="exec-123" status="paused" />);

    expect(screen.getByText('Resume')).toBeInTheDocument();
  });

  it('Cancel button is present in running state with correct text label', () => {
    render(<ExecutionControls executionId="exec-123" status="running" />);

    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });
});
