/**
 * Smoke tests for the Perspective Project Audit page
 *
 * Goals:
 * - Page renders without crashing, shows the drop zone by default
 * - Selecting a zip file triggers the audit and renders the executive
 *   summary + aggregated findings table on success
 * - Aggregated rows expand to show example locations
 * - API errors surface as an Alert
 * - "Download report (.md)" calls the client's download method with the
 *   same file that was analysed
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Audit } from './Audit';
import type { AuditReport } from '../types/api';

// ---------------------------------------------------------------------------
// Mock the API client
// ---------------------------------------------------------------------------
vi.mock('../api/client', () => ({
  api: {
    audit: {
      runPerspectiveAudit: vi.fn(),
      downloadPerspectiveAuditMarkdown: vi.fn(),
    },
  },
  APIError: class APIError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
    getDisplayMessage() {
      return this.message;
    }
  },
}));

import { api, APIError } from '../api/client';

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

function renderAudit() {
  const qc = makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <Audit />
    </QueryClientProvider>
  );
}

function makeZipFile(name = 'MyProject.zip'): File {
  return new File(['PK\x03\x04'], name, { type: 'application/zip' });
}

const SAMPLE_REPORT: AuditReport = {
  project_name: 'MyProject',
  generated_at: '2026-07-04T12:00:00Z',
  inventory: {
    view_count: 5,
    component_count: 470,
    component_count_by_type: {},
    binding_count: 379,
    views: ['Home', 'Popup/Confirm'],
  },
  summary: {
    total_findings: 262,
    by_severity: { critical: 0, high: 1, medium: 0, info: 261 },
    by_rule_family: { consistency: 261, bindings: 1 },
  },
  aggregated_findings: [
    {
      rule_id: 'consistency-hardcoded-color',
      severity: 'info',
      view: 'Home',
      count: 261,
      example_locations: ['Home > root/Label_1', 'Home > root/Label_2', 'Home > root/Label_3'],
      message: '261 components in Home trigger this rule.',
      recommendation: 'Move hardcoded colors into a style class or theme variable.',
    },
    {
      rule_id: 'bindings-fast-polling',
      severity: 'high',
      view: 'Navigation/Header',
      count: 1,
      example_locations: ['Navigation/Header > root/Alarms'],
      message: 'Alarms polls every 2000 ms.',
      recommendation: 'Increase the polling rate or switch to a tag binding.',
    },
  ],
  findings: [],
};

describe('Audit page', () => {
  beforeEach(() => {
    vi.mocked(api.audit.runPerspectiveAudit).mockReset();
    vi.mocked(api.audit.downloadPerspectiveAuditMarkdown).mockReset();
  });

  it('renders the drop zone by default', () => {
    renderAudit();

    expect(screen.getByText(/drop a perspective project export/i)).toBeInTheDocument();
    expect(screen.getByText(/perspective project audit/i)).toBeInTheDocument();
  });

  it('runs the audit and shows the executive summary + aggregated findings on success', async () => {
    vi.mocked(api.audit.runPerspectiveAudit).mockResolvedValue(SAMPLE_REPORT);
    renderAudit();

    const input = screen.getByTestId('audit-file-input') as HTMLInputElement;
    await userEvent.upload(input, makeZipFile());

    await waitFor(() => expect(api.audit.runPerspectiveAudit).toHaveBeenCalledTimes(1));

    // Executive summary
    await waitFor(() => expect(screen.getByText('MyProject')).toBeInTheDocument());
    expect(screen.getByText(/5 views/)).toBeInTheDocument();
    expect(screen.getByText(/470 components/)).toBeInTheDocument();
    expect(screen.getByText(/379 bindings/)).toBeInTheDocument();

    // Aggregated findings — 261 raw findings collapsed into one row
    expect(screen.getByText('consistency-hardcoded-color')).toBeInTheDocument();
    expect(screen.getByText('261')).toBeInTheDocument();
    expect(screen.getByText('bindings-fast-polling')).toBeInTheDocument();
  });

  it('expands an aggregated row to show example locations', async () => {
    vi.mocked(api.audit.runPerspectiveAudit).mockResolvedValue(SAMPLE_REPORT);
    renderAudit();

    await userEvent.upload(screen.getByTestId('audit-file-input'), makeZipFile());
    await waitFor(() => expect(screen.getByText('consistency-hardcoded-color')).toBeInTheDocument());

    expect(screen.queryByText('Home > root/Label_1')).not.toBeInTheDocument();

    const expandButtons = screen.getAllByLabelText('Expand details');
    await userEvent.click(expandButtons[0]);

    expect(await screen.findByText('Home > root/Label_1')).toBeInTheDocument();
  });

  it('shows an error alert when the audit fails', async () => {
    vi.mocked(api.audit.runPerspectiveAudit).mockRejectedValue(
      new APIError("'notes.txt' is not a valid zip file.", 400)
    );
    renderAudit();

    await userEvent.upload(screen.getByTestId('audit-file-input'), makeZipFile('not-a-real-zip.zip'));

    expect(await screen.findByText(/not a valid zip file/i)).toBeInTheDocument();
  });

  it('downloads the markdown report using the same uploaded file', async () => {
    vi.mocked(api.audit.runPerspectiveAudit).mockResolvedValue(SAMPLE_REPORT);
    vi.mocked(api.audit.downloadPerspectiveAuditMarkdown).mockResolvedValue(undefined);
    renderAudit();

    const file = makeZipFile();
    await userEvent.upload(screen.getByTestId('audit-file-input'), file);
    await waitFor(() => expect(screen.getByText('MyProject')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /download report/i }));

    await waitFor(() =>
      expect(api.audit.downloadPerspectiveAuditMarkdown).toHaveBeenCalledWith(file)
    );
  });

  it('resets back to the drop zone via "Audit another project"', async () => {
    vi.mocked(api.audit.runPerspectiveAudit).mockResolvedValue(SAMPLE_REPORT);
    renderAudit();

    await userEvent.upload(screen.getByTestId('audit-file-input'), makeZipFile());
    await waitFor(() => expect(screen.getByText('MyProject')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /audit another project/i }));

    expect(screen.getByText(/drop a perspective project export/i)).toBeInTheDocument();
  });
});
