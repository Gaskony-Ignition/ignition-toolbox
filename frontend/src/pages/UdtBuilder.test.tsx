/**
 * Tests for the UDT Builder composer wizard
 *
 * Goals (phase C2 — replaces the old questionnaire-flow tests):
 * - Preset cards render and prefill the wizard when selected
 * - "Start blank" seeds a DevicePath String parameter
 * - Wizard step navigation (Basics -> Structure -> Alarms -> History -> Review, and back)
 * - Adding a folder + tag in Structure builds the right composition payload
 *   sent to api.udt.compose
 * - Live-lint findings render grouped by severity
 * - A 422 structural error renders as a blocking error in the lint panel
 * - Download uses the response's filename
 * - An empty preset list shows the broken-installation warning
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { UdtBuilder } from './UdtBuilder';
import type { UdtPreset, UdtComposeResponse } from '../types/api';

// ---------------------------------------------------------------------------
// Mock the API client
// ---------------------------------------------------------------------------
vi.mock('../api/client', () => ({
  api: {
    udt: {
      getTemplates: vi.fn(),
      build: vi.fn(),
      getPresets: vi.fn(),
      compose: vi.fn(),
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

const DEBOUNCE_WAIT_OPTS = { timeout: 3000 };

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

const MOTOR_PRESET: UdtPreset = {
  id: 'motor',
  label: 'Motor',
  description: 'Rotating equipment with run/stop command and running feedback.',
  composition: {
    type_name: 'Motor',
    description: 'Rotating equipment.',
    naming_style: 'camelCase',
    parameters: [
      { name: 'DevicePath', data_type: 'String', default_value: '', description: 'OPC device path root.' },
    ],
    members: [
      {
        kind: 'folder',
        name: 'status',
        members: [
          {
            kind: 'tag',
            name: 'running',
            value_source: 'opc',
            data_type: 'Boolean',
            opc_item_path: 'ns=1;s={DevicePath}/Running',
            opc_server: 'Ignition OPC UA Server',
          },
        ],
      },
    ],
  },
};

const COMPOSE_RESULT: UdtComposeResponse = {
  udt: { name: 'Motor', tagType: 'UdtType', tags: [{ name: 'running', tagType: 'AtomicTag' }] },
  filename: 'Motor_udt.json',
  findings: [
    {
      rule_id: 'udt-missing-documentation',
      severity: 'medium',
      location: 'status/running',
      message: 'Tag is missing documentation.',
      recommendation: 'Add a documentation string.',
    },
    {
      rule_id: 'udt-history-not-deliberate',
      severity: 'info',
      location: 'status/running',
      message: 'History is not enabled.',
      recommendation: 'Consider enabling history if this tag is worth trending.',
    },
  ],
};

const EMPTY_COMPOSE_RESULT: UdtComposeResponse = {
  udt: { name: 'X', tagType: 'UdtType' },
  filename: 'X_udt.json',
  findings: [],
};

describe('UdtBuilder composer wizard', () => {
  beforeEach(() => {
    vi.mocked(api.udt.getPresets).mockReset();
    vi.mocked(api.udt.compose).mockReset();
    window.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    window.URL.revokeObjectURL = vi.fn();
  });

  it('renders preset cards once loaded and prefills the wizard when one is selected', async () => {
    vi.mocked(api.udt.getPresets).mockResolvedValue([MOTOR_PRESET]);
    vi.mocked(api.udt.compose).mockResolvedValue(COMPOSE_RESULT);
    renderUdtBuilder();

    expect(await screen.findByTestId('preset-card-motor')).toBeInTheDocument();
    expect(screen.getByTestId('preset-card-blank')).toBeInTheDocument();

    await userEvent.click(screen.getByTestId('preset-card-motor'));

    // Basics step, prefilled from the preset's composition
    expect(await screen.findByLabelText('Type name')).toHaveValue('Motor');
  });

  it('seeds a DevicePath parameter when starting blank', async () => {
    vi.mocked(api.udt.getPresets).mockResolvedValue([]);
    renderUdtBuilder();

    await userEvent.click(await screen.findByTestId('preset-card-blank'));

    expect(await screen.findByLabelText('Type name')).toHaveValue('');
    expect(screen.getByLabelText('Parameter 1 name')).toHaveValue('DevicePath');
  });

  it('shows a broken-installation warning when the preset list loads empty', async () => {
    vi.mocked(api.udt.getPresets).mockResolvedValue([]);
    renderUdtBuilder();

    expect(await screen.findByText(/no udt presets were found/i)).toBeInTheDocument();
    expect(screen.getByText(/broken installation/i)).toBeInTheDocument();
    expect(screen.getByTestId('preset-card-blank')).toBeInTheDocument();
    expect(screen.queryByTestId(/^preset-card-(?!blank)/)).not.toBeInTheDocument();
  });

  it('navigates Basics -> Structure -> Alarms -> History -> Review and back', async () => {
    vi.mocked(api.udt.getPresets).mockResolvedValue([]);
    vi.mocked(api.udt.compose).mockResolvedValue(EMPTY_COMPOSE_RESULT);
    renderUdtBuilder();

    await userEvent.click(await screen.findByTestId('preset-card-blank'));

    // Basics: fill in a valid type name so Structure becomes reachable
    const typeNameField = screen.getByLabelText('Type name');
    await userEvent.type(typeNameField, 'ConveyorMotor');
    await userEvent.click(screen.getByTestId('wizard-next'));

    // Structure
    expect(await screen.findByTestId('add-root-tag')).toBeInTheDocument();
    await userEvent.click(screen.getByTestId('add-root-tag'));
    expect(await screen.findByLabelText('Tag name')).toHaveValue('newTag');

    // Alarms reachable now that a member exists
    await userEvent.click(screen.getByTestId('wizard-next'));
    expect(await screen.findByTestId('alarm-card-newTag')).toBeInTheDocument();

    // History
    await userEvent.click(screen.getByTestId('wizard-next'));
    await waitFor(() => expect(screen.getByText('newTag')).toBeInTheDocument());

    // Review
    await userEvent.click(screen.getByTestId('wizard-next'));
    expect(await screen.findByText(/Preview/i)).toBeInTheDocument();

    // Back to Basics via the stepper button (already-visited steps are free to revisit)
    await userEvent.click(screen.getByRole('button', { name: 'Basics' }));
    expect(await screen.findByLabelText('Type name')).toHaveValue('ConveyorMotor');
  }, 20000);

  it('adding a folder and a tag inside it builds the expected composition payload', async () => {
    vi.mocked(api.udt.getPresets).mockResolvedValue([]);
    vi.mocked(api.udt.compose).mockResolvedValue(EMPTY_COMPOSE_RESULT);
    renderUdtBuilder();

    await userEvent.click(await screen.findByTestId('preset-card-blank'));
    await userEvent.type(screen.getByLabelText('Type name'), 'ConveyorMotor');
    await userEvent.click(screen.getByTestId('wizard-next'));

    await userEvent.click(await screen.findByTestId('add-root-folder'));
    const folderNameField = await screen.findByLabelText('Folder name');
    await userEvent.clear(folderNameField);
    await userEvent.type(folderNameField, 'status');

    await userEvent.click(await screen.findByLabelText('Add tag to status'));
    const tagNameField = await screen.findByLabelText('Tag name');
    await userEvent.clear(tagNameField);
    await userEvent.type(tagNameField, 'speed');

    await waitFor(
      () =>
        expect(api.udt.compose).toHaveBeenLastCalledWith(
          expect.objectContaining({
            type_name: 'ConveyorMotor',
            members: [
              expect.objectContaining({
                kind: 'folder',
                name: 'status',
                members: [expect.objectContaining({ kind: 'tag', name: 'speed' })],
              }),
            ],
          })
        ),
      DEBOUNCE_WAIT_OPTS
    );
  }, 20000);

  it('renders live-lint findings grouped by severity', async () => {
    vi.mocked(api.udt.getPresets).mockResolvedValue([MOTOR_PRESET]);
    vi.mocked(api.udt.compose).mockResolvedValue(COMPOSE_RESULT);
    renderUdtBuilder();

    await userEvent.click(await screen.findByTestId('preset-card-motor'));
    await userEvent.click(await screen.findByTestId('wizard-next'));

    const lintPanel = await screen.findByTestId('lint-panel');
    await waitFor(() => expect(within(lintPanel).getByText('Medium: 1')).toBeInTheDocument(), DEBOUNCE_WAIT_OPTS);
    expect(within(lintPanel).getByText('Info: 1')).toBeInTheDocument();
    expect(within(lintPanel).getByText(/missing documentation/i)).toBeInTheDocument();
    expect(within(lintPanel).getByText(/history is not enabled/i)).toBeInTheDocument();
  }, 20000);

  it('renders a 422 structural error as a blocking error in the lint panel', async () => {
    vi.mocked(api.udt.getPresets).mockResolvedValue([MOTOR_PRESET]);
    vi.mocked(api.udt.compose).mockRejectedValue(
      new APIError("Invalid composition: type name must not be blank; duplicate sibling name 'running'", 422)
    );
    renderUdtBuilder();

    await userEvent.click(await screen.findByTestId('preset-card-motor'));
    await userEvent.click(await screen.findByTestId('wizard-next'));

    const blocking = await screen.findByTestId('lint-blocking-errors', undefined, DEBOUNCE_WAIT_OPTS);
    expect(within(blocking).getByText(/type name must not be blank/i)).toBeInTheDocument();
    expect(within(blocking).getByText(/duplicate sibling name 'running'/i)).toBeInTheDocument();

    // Composition/user state is preserved despite the error — still on Structure, preset data intact
    expect(screen.getByTestId('add-root-tag')).toBeInTheDocument();
  }, 20000);

  it('downloads using the filename from the compose response', async () => {
    vi.mocked(api.udt.getPresets).mockResolvedValue([MOTOR_PRESET]);
    vi.mocked(api.udt.compose).mockResolvedValue(COMPOSE_RESULT);
    renderUdtBuilder();

    await userEvent.click(await screen.findByTestId('preset-card-motor'));
    // Basics -> Structure -> Alarms -> History -> Review
    await userEvent.click(screen.getByTestId('wizard-next'));
    await userEvent.click(await screen.findByTestId('wizard-next'));
    await userEvent.click(await screen.findByTestId('wizard-next'));
    await userEvent.click(await screen.findByTestId('wizard-next'));

    const downloadButton = await screen.findByRole(
      'button',
      { name: /download Motor_udt\.json/i },
      DEBOUNCE_WAIT_OPTS
    );
    expect(downloadButton).not.toBeDisabled();

    let capturedFilename: string | undefined;
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(function (this: HTMLAnchorElement) {
        capturedFilename = this.download;
      });

    await userEvent.click(downloadButton);

    expect(capturedFilename).toBe('Motor_udt.json');
    clickSpy.mockRestore();
  }, 20000);
});
