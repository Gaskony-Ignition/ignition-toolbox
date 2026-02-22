/**
 * Tests for ExecutionTimeline component
 *
 * Goals:
 * - Renders without crashing with no steps
 * - Shows "No steps executed yet" empty state
 * - Renders a list of steps by name
 * - Shows completed steps with completed-at timestamp
 * - Shows error content for failed steps when expanded
 * - Shows step name or fallback "Step N"
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ExecutionTimeline } from './ExecutionTimeline';
import type { StepResult } from '../types/api';

// ---------------------------------------------------------------------------
// Mock logger (if imported transitively)
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
// Sample data
// ---------------------------------------------------------------------------

const completedStep: StepResult = {
  step_id: 'step-1',
  step_name: 'Login to Gateway',
  status: 'completed',
  started_at: '2024-01-01T10:00:00Z',
  completed_at: '2024-01-01T10:00:05Z',
  error: null,
  output: {},
};

const runningStep: StepResult = {
  step_id: 'step-2',
  step_name: 'Navigate to Page',
  status: 'running',
  started_at: '2024-01-01T10:00:05Z',
  completed_at: null,
  error: null,
  output: {},
};

const failedStep: StepResult = {
  step_id: 'step-3',
  step_name: 'Assert Element Visible',
  status: 'failed',
  started_at: '2024-01-01T10:00:10Z',
  completed_at: '2024-01-01T10:00:12Z',
  error: 'Element not found: #submit-button',
  output: {},
};

const pendingStep: StepResult = {
  step_id: 'step-4',
  step_name: 'Logout',
  status: 'pending',
  started_at: null,
  completed_at: null,
  error: null,
  output: {},
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ExecutionTimeline', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing with an empty steps array', () => {
    render(<ExecutionTimeline steps={[]} />);
    expect(document.body).toBeTruthy();
  });

  it('shows "No steps executed yet" when steps array is empty', () => {
    render(<ExecutionTimeline steps={[]} />);
    expect(screen.getByText(/no steps executed yet/i)).toBeInTheDocument();
  });

  it('renders step names for a list of steps', () => {
    render(<ExecutionTimeline steps={[completedStep, runningStep]} />);
    expect(screen.getByText('Login to Gateway')).toBeInTheDocument();
    expect(screen.getByText('Navigate to Page')).toBeInTheDocument();
  });

  it('shows completed step with a completed-at timestamp', () => {
    render(<ExecutionTimeline steps={[completedStep]} />);
    expect(screen.getByText(/completed at/i)).toBeInTheDocument();
  });

  it('does not show completed-at for a running step', () => {
    render(<ExecutionTimeline steps={[runningStep]} />);
    expect(screen.queryByText(/completed at/i)).not.toBeInTheDocument();
  });

  it('does not show completed-at for a pending step', () => {
    render(<ExecutionTimeline steps={[pendingStep]} />);
    expect(screen.queryByText(/completed at/i)).not.toBeInTheDocument();
  });

  it('shows error content when a failed step is expanded', () => {
    render(<ExecutionTimeline steps={[failedStep]} />);
    // Click on the step header to expand it (it has an error so hasDetails=true)
    const stepHeader = screen.getByText('Assert Element Visible');
    fireEvent.click(stepHeader);
    expect(screen.getByText('Element not found: #submit-button')).toBeInTheDocument();
  });

  it('falls back to "Step N" label when step has no name', () => {
    const noNameStep: StepResult = {
      ...completedStep,
      step_name: undefined as unknown as string,
      step_id: 'step-x',
    };
    render(<ExecutionTimeline steps={[noNameStep]} />);
    expect(screen.getByText('Step 1')).toBeInTheDocument();
  });

  it('renders multiple steps without crashing', () => {
    render(
      <ExecutionTimeline
        steps={[completedStep, runningStep, failedStep, pendingStep]}
        currentStepIndex={1}
      />
    );
    expect(screen.getByText('Login to Gateway')).toBeInTheDocument();
    expect(screen.getByText('Navigate to Page')).toBeInTheDocument();
    expect(screen.getByText('Assert Element Visible')).toBeInTheDocument();
    expect(screen.getByText('Logout')).toBeInTheDocument();
  });

  it('renders in compact mode without crashing', () => {
    render(<ExecutionTimeline steps={[completedStep, runningStep]} compact />);
    expect(screen.getByText('Login to Gateway')).toBeInTheDocument();
  });
});
