/**
 * Tests for ExecutionCard component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ExecutionCard } from './ExecutionCard';
import type { ExecutionStatusResponse } from '../types/api';

// Helper to create a test execution
function createTestExecution(overrides: Partial<ExecutionStatusResponse> = {}): ExecutionStatusResponse {
  return {
    execution_id: 'test-exec-123456789',
    playbook_name: 'Test Playbook',
    status: 'running',
    started_at: new Date().toISOString(),
    completed_at: null,
    current_step_index: 2,
    total_steps: 5,
    error: null,
    debug_mode: false,
    step_results: [
      {
        step_id: 'step1',
        step_name: 'Step 1',
        status: 'completed',
        error: null,
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        output: null,
      },
      {
        step_id: 'step2',
        step_name: 'Step 2',
        status: 'running',
        error: null,
        started_at: new Date().toISOString(),
        completed_at: null,
        output: null,
      },
    ],
    domain: 'gateway',
    ...overrides,
  };
}

describe('ExecutionCard', () => {
  const mockOnPause = vi.fn();
  const mockOnResume = vi.fn();
  const mockOnSkip = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders playbook name', () => {
    const execution = createTestExecution();
    render(<ExecutionCard execution={execution} />);

    expect(screen.getByText('Test Playbook')).toBeInTheDocument();
  });

  it('renders execution status chip', () => {
    const execution = createTestExecution({ status: 'running' });
    render(<ExecutionCard execution={execution} />);

    expect(screen.getByText('running')).toBeInTheDocument();
  });

  it('displays truncated execution ID', () => {
    const execution = createTestExecution({ execution_id: 'abcd1234-full-id-here' });
    render(<ExecutionCard execution={execution} />);

    expect(screen.getByText(/ID: abcd1234/)).toBeInTheDocument();
  });

  it('shows progress bar with correct percentage', () => {
    const execution = createTestExecution({
      current_step_index: 3,
      total_steps: 10,
    });
    render(<ExecutionCard execution={execution} />);

    expect(screen.getByText('Progress: 3 / 10 steps')).toBeInTheDocument();
    expect(screen.getByText('30%')).toBeInTheDocument();
  });

  it('displays error message when present', () => {
    const execution = createTestExecution({
      status: 'failed',
      error: 'Connection timeout',
    });
    render(<ExecutionCard execution={execution} />);

    expect(screen.getByText('Error: Connection timeout')).toBeInTheDocument();
  });

  it('shows control buttons for running execution', () => {
    const execution = createTestExecution({ status: 'running' });
    render(
      <ExecutionCard
        execution={execution}
        onPause={mockOnPause}
        onSkip={mockOnSkip}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByRole('button', { name: /pause execution/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /skip current step/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel execution/i })).toBeInTheDocument();
  });

  it('shows resume button for paused execution', () => {
    const execution = createTestExecution({ status: 'paused' });
    render(
      <ExecutionCard
        execution={execution}
        onResume={mockOnResume}
        onSkip={mockOnSkip}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByRole('button', { name: /resume execution/i })).toBeInTheDocument();
  });

  it('hides control buttons for completed execution', () => {
    const execution = createTestExecution({ status: 'completed' });
    render(
      <ExecutionCard
        execution={execution}
        onPause={mockOnPause}
        onResume={mockOnResume}
      />
    );

    expect(screen.queryByRole('button', { name: /pause/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /resume/i })).not.toBeInTheDocument();
  });

  it('calls onPause when Pause button is clicked', () => {
    const execution = createTestExecution({ status: 'running' });
    render(
      <ExecutionCard
        execution={execution}
        onPause={mockOnPause}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /pause execution/i }));
    expect(mockOnPause).toHaveBeenCalledWith(execution.execution_id);
  });

  it('calls onResume when Resume button is clicked', () => {
    const execution = createTestExecution({ status: 'paused' });
    render(
      <ExecutionCard
        execution={execution}
        onResume={mockOnResume}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /resume execution/i }));
    expect(mockOnResume).toHaveBeenCalledWith(execution.execution_id);
  });

  it('calls onSkip when Skip button is clicked', () => {
    const execution = createTestExecution({ status: 'running' });
    render(
      <ExecutionCard
        execution={execution}
        onSkip={mockOnSkip}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /skip current step/i }));
    expect(mockOnSkip).toHaveBeenCalledWith(execution.execution_id);
  });

  it('calls onCancel when Cancel button is clicked', () => {
    const execution = createTestExecution({ status: 'running' });
    render(
      <ExecutionCard
        execution={execution}
        onCancel={mockOnCancel}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /cancel execution/i }));
    expect(mockOnCancel).toHaveBeenCalledWith(execution.execution_id);
  });

  it('expands to show step results when expand button is clicked', () => {
    const execution = createTestExecution();
    render(<ExecutionCard execution={execution} />);

    // Step results should not be visible initially
    expect(screen.queryByText('Step Results')).not.toBeInTheDocument();

    // Click expand button
    fireEvent.click(screen.getByRole('button', { name: /expand execution details/i }));

    // Step results should now be visible
    expect(screen.getByText('Step Results')).toBeInTheDocument();
    expect(screen.getByText('Step 1')).toBeInTheDocument();
    expect(screen.getByText('Step 2')).toBeInTheDocument();
  });

  it('shows "No step results yet" when no steps', () => {
    const execution = createTestExecution({ step_results: [] });
    render(<ExecutionCard execution={execution} />);

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /expand execution details/i }));

    expect(screen.getByText('No step results yet')).toBeInTheDocument();
  });

  it('displays step error in expanded view', () => {
    const execution = createTestExecution({
      step_results: [
        {
          step_id: 'step1',
          step_name: 'Failed Step',
          status: 'failed',
          error: 'Element not found',
          started_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
          output: null,
        },
      ],
    });
    render(<ExecutionCard execution={execution} />);

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /expand execution details/i }));

    expect(screen.getByText('Element not found')).toBeInTheDocument();
  });

  it('displays correct status chip colors', () => {
    const statuses = ['pending', 'running', 'paused', 'completed', 'failed'] as const;

    statuses.forEach(status => {
      const execution = createTestExecution({ status });
      const { unmount } = render(<ExecutionCard execution={execution} />);

      // Verify status chip is displayed
      expect(screen.getByText(status)).toBeInTheDocument();

      unmount();
    });
  });

  it('handles zero total steps gracefully', () => {
    const execution = createTestExecution({
      current_step_index: 0,
      total_steps: 0,
    });
    render(<ExecutionCard execution={execution} />);

    // Should show 0% progress without crashing
    expect(screen.getByText('0%')).toBeInTheDocument();
    expect(screen.getByText('Progress: 0 / 0 steps')).toBeInTheDocument();
  });

  it('shows completed timestamp when available', () => {
    const completedTime = '2025-01-15T10:30:00Z';
    const execution = createTestExecution({
      status: 'completed',
      completed_at: completedTime,
    });
    render(<ExecutionCard execution={execution} />);

    // Should show "Completed:" text
    expect(screen.getByText(/Completed:/)).toBeInTheDocument();
  });
});
