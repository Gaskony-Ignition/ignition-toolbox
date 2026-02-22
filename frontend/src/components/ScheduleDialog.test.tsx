/**
 * Tests for ScheduleDialog component
 *
 * Goals:
 * - Renders nothing when open=false
 * - Shows dialog when open=true
 * - Shows the playbook name in the dialog title
 * - Shows schedule type options
 * - Cancel button calls onClose
 * - Shows preview text for the selected schedule
 * - Shows warning when no savedConfig
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ScheduleDialog from './ScheduleDialog';
import type { PlaybookInfo } from '../types/api';

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
// ResizeObserver - MUI Select uses it; ensure it is a proper constructor
// ---------------------------------------------------------------------------
class ResizeObserverMock {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
window.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver;

// ---------------------------------------------------------------------------
// Mock global fetch for the handleSave call
// ---------------------------------------------------------------------------
const mockFetch = vi.fn().mockResolvedValue({
  ok: true,
  json: () => Promise.resolve({ id: 1 }),
});
global.fetch = mockFetch;

// ---------------------------------------------------------------------------
// Sample data
// ---------------------------------------------------------------------------

const samplePlaybook: PlaybookInfo = {
  name: 'My Test Playbook',
  path: 'playbooks/my_test_playbook.yaml',
  description: 'A test playbook',
  tags: [],
  step_count: 3,
  category: 'gateway',
};

const sampleSavedConfig = {
  parameters: { gateway_url: 'http://localhost:8088' },
  gateway_url: 'http://localhost:8088',
  credential_name: 'admin-cred',
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ScheduleDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 1 }),
    });
  });

  it('renders nothing (dialog not in DOM) when open=false', () => {
    render(
      <ScheduleDialog
        open={false}
        onClose={vi.fn()}
        playbook={samplePlaybook}
        savedConfig={sampleSavedConfig}
      />
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows the dialog when open=true', () => {
    render(
      <ScheduleDialog
        open={true}
        onClose={vi.fn()}
        playbook={samplePlaybook}
        savedConfig={sampleSavedConfig}
      />
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('shows the playbook name in the dialog title', () => {
    render(
      <ScheduleDialog
        open={true}
        onClose={vi.fn()}
        playbook={samplePlaybook}
        savedConfig={sampleSavedConfig}
      />
    );
    expect(screen.getByText(/schedule playbook: my test playbook/i)).toBeInTheDocument();
  });

  it('shows schedule type select control', () => {
    render(
      <ScheduleDialog
        open={true}
        onClose={vi.fn()}
        playbook={samplePlaybook}
        savedConfig={sampleSavedConfig}
      />
    );
    // MUI renders the label text in multiple elements; use getAllByText
    const scheduleTypeLabels = screen.getAllByText('Schedule Type');
    expect(scheduleTypeLabels.length).toBeGreaterThanOrEqual(1);
  });

  it('shows schedule type options when dropdown is opened', async () => {
    render(
      <ScheduleDialog
        open={true}
        onClose={vi.fn()}
        playbook={samplePlaybook}
        savedConfig={sampleSavedConfig}
      />
    );

    fireEvent.mouseDown(screen.getByRole('combobox'));

    await waitFor(() => {
      expect(screen.getByRole('option', { name: /interval/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /daily/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /weekly/i })).toBeInTheDocument();
    });
  });

  it('calls onClose when Cancel is clicked', () => {
    const onClose = vi.fn();
    render(
      <ScheduleDialog
        open={true}
        onClose={onClose}
        playbook={samplePlaybook}
        savedConfig={sampleSavedConfig}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('shows schedule preview text', async () => {
    render(
      <ScheduleDialog
        open={true}
        onClose={vi.fn()}
        playbook={samplePlaybook}
        savedConfig={sampleSavedConfig}
      />
    );
    // Default schedule type is 'daily' which shows "Every day at HH:MM"
    await waitFor(() => {
      expect(screen.getByText(/schedule preview/i)).toBeInTheDocument();
      expect(screen.getByText(/every day at/i)).toBeInTheDocument();
    });
  });

  it('shows warning when no savedConfig is provided', () => {
    render(
      <ScheduleDialog
        open={true}
        onClose={vi.fn()}
        playbook={samplePlaybook}
        savedConfig={null}
      />
    );
    expect(
      screen.getByText(/no saved configuration/i)
    ).toBeInTheDocument();
  });

  it('shows the schedule name field pre-filled with playbook name', async () => {
    render(
      <ScheduleDialog
        open={true}
        onClose={vi.fn()}
        playbook={samplePlaybook}
        savedConfig={sampleSavedConfig}
      />
    );
    await waitFor(() => {
      const nameField = screen.getByLabelText(/schedule name/i) as HTMLInputElement;
      expect(nameField.value).toContain('My Test Playbook');
    });
  });
});
