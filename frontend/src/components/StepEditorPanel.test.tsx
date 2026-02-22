/**
 * Tests for StepEditorPanel component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { StepEditorPanel } from './StepEditorPanel';
import type { StepTypeInfo, CredentialInfo } from '../types/api';

// Helper: create a minimal StepTypeInfo
function createStepType(overrides: Partial<StepTypeInfo> = {}): StepTypeInfo {
  return {
    type: 'gateway.navigate',
    domain: 'gateway',
    description: 'Navigate to a URL',
    parameters: [],
    ...overrides,
  };
}

// Helper: create a minimal step config
function createStep(overrides: Partial<{
  id: string;
  name: string;
  type: string;
  parameters: Record<string, any>;
  timeout?: number;
  retry_count?: number;
  retry_delay?: number;
  on_failure?: string;
}> = {}) {
  return {
    id: 'step_1',
    name: 'My Step',
    type: 'gateway.navigate',
    parameters: {},
    ...overrides,
  };
}

const testCredentials: CredentialInfo[] = [
  { name: 'prod-cred', username: 'admin' },
];

describe('StepEditorPanel', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ----- Null stepType (no type selected) -----

  it('shows placeholder message when stepType is null', () => {
    render(
      <StepEditorPanel
        stepType={null}
        step={createStep()}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText('Select a step type to configure parameters')).toBeInTheDocument();
  });

  // ----- Basic rendering with stepType -----

  it('renders without crashing when stepType is provided', () => {
    const stepType = createStepType();
    render(
      <StepEditorPanel
        stepType={stepType}
        step={createStep()}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    // Should render step ID and name fields (MUI v7 TextField, find via label text)
    expect(screen.getByRole('textbox', { name: /Step ID/i })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /Step Name/i })).toBeInTheDocument();
  });

  it('displays the step ID value', () => {
    const stepType = createStepType();
    render(
      <StepEditorPanel
        stepType={stepType}
        step={createStep({ id: 'my_step_id' })}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    const idField = screen.getByRole('textbox', { name: /Step ID/i });
    expect(idField).toHaveValue('my_step_id');
  });

  it('displays the step name value', () => {
    const stepType = createStepType();
    render(
      <StepEditorPanel
        stepType={stepType}
        step={createStep({ name: 'Navigate to Dashboard' })}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    const nameField = screen.getByRole('textbox', { name: /Step Name/i });
    expect(nameField).toHaveValue('Navigate to Dashboard');
  });

  // ----- Step ID/Name change callbacks -----

  it('calls onChange when step ID is edited', () => {
    const stepType = createStepType();
    const step = createStep({ id: 'old_id' });
    render(
      <StepEditorPanel
        stepType={stepType}
        step={step}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    const idField = screen.getByRole('textbox', { name: /Step ID/i });
    fireEvent.change(idField, { target: { value: 'new_id' } });

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'new_id' })
    );
  });

  it('calls onChange when step name is edited', () => {
    const stepType = createStepType();
    const step = createStep({ name: 'Old Name' });
    render(
      <StepEditorPanel
        stepType={stepType}
        step={step}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    const nameField = screen.getByRole('textbox', { name: /Step Name/i });
    fireEvent.change(nameField, { target: { value: 'New Name' } });

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'New Name' })
    );
  });

  // ----- Required and optional parameters -----

  it('shows "Required Parameters" section when there are required params', () => {
    const stepType = createStepType({
      parameters: [
        {
          name: 'url',
          type: 'string',
          required: true,
          default: null,
          description: 'Target URL',
        },
      ],
    });
    render(
      <StepEditorPanel
        stepType={stepType}
        step={createStep()}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText('Required Parameters')).toBeInTheDocument();
    expect(screen.getByText('url')).toBeInTheDocument();
  });

  it('shows "Optional Parameters" accordion when there are optional params', () => {
    const stepType = createStepType({
      parameters: [
        {
          name: 'wait_ms',
          type: 'integer',
          required: false,
          default: '500',
          description: 'Wait time in ms',
        },
      ],
    });
    render(
      <StepEditorPanel
        stepType={stepType}
        step={createStep()}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText(/Optional Parameters/)).toBeInTheDocument();
  });

  it('does not show "Required Parameters" section when there are no required params', () => {
    const stepType = createStepType({
      parameters: [
        {
          name: 'opt_param',
          type: 'string',
          required: false,
          default: null,
          description: 'Optional',
        },
      ],
    });
    render(
      <StepEditorPanel
        stepType={stepType}
        step={createStep()}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    expect(screen.queryByText('Required Parameters')).not.toBeInTheDocument();
  });

  it('does not show "Optional Parameters" accordion when all params are required', () => {
    const stepType = createStepType({
      parameters: [
        {
          name: 'url',
          type: 'string',
          required: true,
          default: null,
          description: 'Target URL',
        },
      ],
    });
    render(
      <StepEditorPanel
        stepType={stepType}
        step={createStep()}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    expect(screen.queryByText(/Optional Parameters/)).not.toBeInTheDocument();
  });

  // ----- Parameter type rendering inside StepEditorPanel -----

  it('renders boolean parameter as a switch', () => {
    const stepType = createStepType({
      parameters: [
        {
          name: 'debug_mode',
          type: 'boolean',
          required: true,
          default: false,
          description: 'Enable debug',
        },
      ],
    });
    render(
      <StepEditorPanel
        stepType={stepType}
        step={createStep({ parameters: { debug_mode: false } })}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    // MUI Switch renders with role="switch"
    expect(screen.getByRole('switch')).toBeInTheDocument();
  });

  it('renders credential parameter as a select with credentials', () => {
    const stepType = createStepType({
      parameters: [
        {
          name: 'credential',
          type: 'credential',
          required: true,
          default: null,
          description: 'Select credential',
        },
      ],
    });
    render(
      <StepEditorPanel
        stepType={stepType}
        step={createStep({ parameters: { credential: '' } })}
        credentials={testCredentials}
        onChange={mockOnChange}
      />
    );

    const combobox = screen.getByRole('combobox');
    expect(combobox).toBeInTheDocument();
    fireEvent.mouseDown(combobox);
    expect(screen.getByText('prod-cred (admin)')).toBeInTheDocument();
  });

  it('renders integer parameter as a number input', () => {
    const stepType = createStepType({
      parameters: [
        {
          name: 'port',
          type: 'integer',
          required: true,
          default: 8080,
          description: 'Port number',
        },
      ],
    });
    render(
      <StepEditorPanel
        stepType={stepType}
        step={createStep({ parameters: { port: 8080 } })}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    // number input doesn't have textbox role, find by querying spinbutton
    const numInput = screen.getByRole('spinbutton');
    expect(numInput).toBeInTheDocument();
    expect(numInput).toHaveAttribute('type', 'number');
  });

  it('renders file parameter with a browse button', () => {
    const stepType = createStepType({
      parameters: [
        {
          name: 'module_path',
          type: 'file',
          required: true,
          default: null,
          description: 'Path to module file',
        },
      ],
    });
    render(
      <StepEditorPanel
        stepType={stepType}
        step={createStep({ parameters: { module_path: '' } })}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByTitle('Browse files')).toBeInTheDocument();
  });

  it('renders enum parameter as a select dropdown', () => {
    const stepType = createStepType({
      parameters: [
        {
          name: 'action',
          type: 'string',
          required: true,
          default: 'click',
          description: 'Action to perform',
          options: ['click', 'hover', 'type'],
        },
      ],
    });
    render(
      <StepEditorPanel
        stepType={stepType}
        step={createStep({ parameters: { action: 'click' } })}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    const combobox = screen.getByRole('combobox');
    expect(combobox).toBeInTheDocument();
    fireEvent.mouseDown(combobox);
    expect(screen.getByRole('option', { name: 'click' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'hover' })).toBeInTheDocument();
  });

  // ----- Step Options accordion -----

  it('always renders the "Step Options" accordion', () => {
    const stepType = createStepType();
    render(
      <StepEditorPanel
        stepType={stepType}
        step={createStep()}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText('Step Options')).toBeInTheDocument();
  });

  it('shows on_failure options in Step Options accordion when expanded', () => {
    const stepType = createStepType();
    render(
      <StepEditorPanel
        stepType={stepType}
        step={createStep()}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    // Expand Step Options accordion
    fireEvent.click(screen.getByText('Step Options'));

    // The currently selected value is "abort" which renders its label text in the Select
    // The full option text for 'abort' should be visible as the selected value
    expect(screen.getByText('Abort - Stop playbook execution')).toBeInTheDocument();

    // Open the on_failure select to see all options
    const onFailureSelect = screen.getByRole('combobox');
    fireEvent.mouseDown(onFailureSelect);

    expect(screen.getByRole('option', { name: 'Continue - Proceed to next step' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Rollback - Attempt cleanup' })).toBeInTheDocument();
  });

  it('shows timeout field in Step Options when expanded', () => {
    const stepType = createStepType();
    render(
      <StepEditorPanel
        stepType={stepType}
        step={createStep({ timeout: 120 })}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    fireEvent.click(screen.getByText('Step Options'));

    expect(screen.getByLabelText(/Timeout/)).toBeInTheDocument();
  });

  // ----- Type chip -----

  it('shows type chip on required parameters', () => {
    const stepType = createStepType({
      parameters: [
        {
          name: 'url',
          type: 'string',
          required: true,
          default: null,
          description: '',
        },
      ],
    });
    render(
      <StepEditorPanel
        stepType={stepType}
        step={createStep({ parameters: { url: '' } })}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    // The Chip shows the parameter type
    expect(screen.getByText('string')).toBeInTheDocument();
  });

  // ----- Required indicator -----

  it('shows required asterisk on required parameters', () => {
    const stepType = createStepType({
      parameters: [
        {
          name: 'gateway_url',
          type: 'string',
          required: true,
          default: null,
          description: '',
        },
      ],
    });
    render(
      <StepEditorPanel
        stepType={stepType}
        step={createStep({ parameters: { gateway_url: '' } })}
        credentials={[]}
        onChange={mockOnChange}
      />
    );

    // The asterisk is in a <span> with color style - check it's present in the DOM
    // The component renders: {parameter.name}{parameter.required && <span style={...}> *</span>}
    const asteriskSpan = document.querySelector('span[style*="color: rgb(255, 68, 68)"]') ??
      document.querySelector('span[style*="color:#ff4444"]') ??
      document.querySelector('span[style*="color: #ff4444"]');
    expect(asteriskSpan).not.toBeNull();
  });
});
