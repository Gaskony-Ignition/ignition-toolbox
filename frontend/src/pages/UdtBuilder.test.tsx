/**
 * Smoke tests for the UDT Builder page
 *
 * Goals:
 * - Templates load and render as picker cards
 * - Selecting a template renders its dynamic questionnaire form
 * - Filling a minimal Motor form and clicking Preview builds successfully,
 *   enabling the Copy/Download buttons and rendering the JSON preview
 * - A 422 validation error surfaces both an inline field error and (for
 *   clauses that don't name a field) a summary alert
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { UdtBuilder } from './UdtBuilder';
import type { UdtTemplateMeta, UdtBuildResult } from '../types/api';

// ---------------------------------------------------------------------------
// Mock the API client
// ---------------------------------------------------------------------------
vi.mock('../api/client', () => ({
  api: {
    udt: {
      getTemplates: vi.fn(),
      build: vi.fn(),
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

function renderUdtBuilder() {
  const qc = makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <UdtBuilder />
    </QueryClientProvider>
  );
}

const MOTOR_TEMPLATE: UdtTemplateMeta = {
  id: 'motor',
  label: 'Motor',
  description: 'Rotating equipment with run/stop command and running feedback.',
  questionnaire: [
    {
      name: 'device_path',
      type: 'string',
      required: true,
      default: null,
      description: "OPC device path root, e.g. '[default]PLC1/Motors/M101'.",
    },
    {
      name: 'has_speed_feedback',
      type: 'boolean',
      required: false,
      default: true,
      description: 'Does the motor report analog speed feedback?',
    },
  ],
  naming_styles: ['camelCase', 'PascalCase'],
  default_naming_style: 'camelCase',
};

const VALVE_TEMPLATE: UdtTemplateMeta = {
  id: 'valve',
  label: 'Valve',
  description: 'Open/close valve with status/command/config folders.',
  questionnaire: [
    {
      name: 'device_path',
      type: 'string',
      required: true,
      default: null,
      description: 'OPC device path root.',
    },
  ],
  naming_styles: ['camelCase', 'PascalCase'],
  default_naming_style: 'camelCase',
};

const BUILD_RESULT: UdtBuildResult = {
  udt: {
    name: 'Motor',
    tagType: 'UdtType',
    tags: [{ name: 'running', tagType: 'AtomicTag' }],
  },
  filename: 'Motor.json',
};

describe('UdtBuilder page', () => {
  beforeEach(() => {
    vi.mocked(api.udt.getTemplates).mockReset();
    vi.mocked(api.udt.build).mockReset();
  });

  it('renders template picker cards once templates load', async () => {
    vi.mocked(api.udt.getTemplates).mockResolvedValue([MOTOR_TEMPLATE, VALVE_TEMPLATE]);
    renderUdtBuilder();

    expect(await screen.findByTestId('template-card-motor')).toBeInTheDocument();
    expect(screen.getByTestId('template-card-valve')).toBeInTheDocument();
    expect(screen.getByText('Motor')).toBeInTheDocument();
    expect(screen.getByText('Valve')).toBeInTheDocument();
  });

  it('renders the dynamic questionnaire form after selecting a template', async () => {
    vi.mocked(api.udt.getTemplates).mockResolvedValue([MOTOR_TEMPLATE]);
    renderUdtBuilder();

    await userEvent.click(await screen.findByTestId('template-card-motor'));

    expect(screen.getByLabelText('device_path')).toBeInTheDocument();
    expect(screen.getByText(/has_speed_feedback/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /preview/i })).toBeInTheDocument();
  });

  it('fills a minimal motor form, previews, and enables copy/download', async () => {
    vi.mocked(api.udt.getTemplates).mockResolvedValue([MOTOR_TEMPLATE]);
    vi.mocked(api.udt.build).mockResolvedValue(BUILD_RESULT);
    renderUdtBuilder();

    await userEvent.click(await screen.findByTestId('template-card-motor'));

    const downloadButtonBefore = screen.getByRole('button', { name: /^download$/i });
    expect(downloadButtonBefore).toBeDisabled();

    await userEvent.type(screen.getByLabelText('device_path'), 'defaultPLC1/Motors/M101');
    await userEvent.click(screen.getByRole('button', { name: /preview/i }));

    await waitFor(() => expect(api.udt.build).toHaveBeenCalledTimes(1));
    expect(api.udt.build).toHaveBeenCalledWith(
      'motor',
      expect.objectContaining({ device_path: 'defaultPLC1/Motors/M101' }),
      'camelCase'
    );

    // Preview JSON rendered (JsonViewer collapses nodes past depth 2 by
    // default, so assert on the root-level "tagType" value rather than
    // digging into the nested tags[0] object) + action buttons enabled
    await waitFor(() => expect(screen.getByText(/"UdtType"/)).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /download motor\.json/i })).not.toBeDisabled();
    expect(screen.getByRole('button', { name: /copy json/i })).not.toBeDisabled();
  });

  it('shows an inline field error and a summary alert on a 422 validation failure', async () => {
    vi.mocked(api.udt.getTemplates).mockResolvedValue([MOTOR_TEMPLATE]);
    vi.mocked(api.udt.build).mockRejectedValue(
      new APIError(
        "Invalid answers: missing required field 'device_path'; unknown field(s): bogus",
        422
      )
    );
    renderUdtBuilder();

    await userEvent.click(await screen.findByTestId('template-card-motor'));
    await userEvent.click(screen.getByRole('button', { name: /preview/i }));

    // Inline error next to the device_path field
    expect(await screen.findByText(/missing required field 'device_path'/i)).toBeInTheDocument();
    // Leftover clause (doesn't name a known field) falls back to the summary alert
    expect(screen.getByText(/unknown field\(s\): bogus/i)).toBeInTheDocument();
  });

  it('shows a generic alert for a non-validation API error', async () => {
    vi.mocked(api.udt.getTemplates).mockResolvedValue([MOTOR_TEMPLATE]);
    vi.mocked(api.udt.build).mockRejectedValue(new APIError('Unknown template', 404));
    renderUdtBuilder();

    await userEvent.click(await screen.findByTestId('template-card-motor'));
    await userEvent.click(screen.getByRole('button', { name: /preview/i }));

    expect(await screen.findByText('Unknown template')).toBeInTheDocument();
  });
});
