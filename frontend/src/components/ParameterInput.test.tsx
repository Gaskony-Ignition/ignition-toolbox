/**
 * Tests for ParameterInput component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ParameterInput } from './ParameterInput';
import type { ParameterInfo, CredentialInfo } from '../types/api';

// Mock FolderBrowserDialog to avoid complex API dependency
vi.mock('./FolderBrowserDialog', () => ({
  default: ({ open, onClose, onSelect }: { open: boolean; onClose: () => void; onSelect: (path: string) => void }) =>
    open ? (
      <div data-testid="folder-browser-dialog">
        <button onClick={() => onSelect('/selected/path')}>Select</button>
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}));

// Helper to create a ParameterInfo object
function createParam(overrides: Partial<ParameterInfo> = {}): ParameterInfo {
  return {
    name: 'test_param',
    type: 'string',
    required: false,
    default: null,
    description: '',
    ...overrides,
  };
}

// Helper credentials for credential tests
const testCredentials: CredentialInfo[] = [
  { name: 'cred-prod', username: 'admin' },
  { name: 'cred-dev', username: 'developer' },
];

describe('ParameterInput', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Ensure no electronAPI by default
    Object.defineProperty(window, 'electronAPI', {
      value: undefined,
      writable: true,
      configurable: true,
    });
  });

  // ----- String type -----

  it('renders a text field for string type', () => {
    const param = createParam({ name: 'gateway_url', type: 'string' });
    render(<ParameterInput parameter={param} value="" onChange={mockOnChange} />);

    const input = screen.getByRole('textbox', { name: 'gateway_url' });
    expect(input).toBeInTheDocument();
  });

  it('calls onChange with correct name and value for string input', () => {
    const param = createParam({ name: 'gateway_url', type: 'string' });
    render(<ParameterInput parameter={param} value="" onChange={mockOnChange} />);

    const input = screen.getByRole('textbox', { name: 'gateway_url' });
    fireEvent.change(input, { target: { value: 'http://localhost:8088' } });

    expect(mockOnChange).toHaveBeenCalledWith('gateway_url', 'http://localhost:8088');
  });

  it('shows current value in string text field', () => {
    const param = createParam({ name: 'my_param', type: 'string' });
    render(<ParameterInput parameter={param} value="existing-value" onChange={mockOnChange} />);

    const input = screen.getByRole('textbox', { name: 'my_param' });
    expect(input).toHaveValue('existing-value');
  });

  it('uses default as placeholder for string input when provided', () => {
    const param = createParam({ name: 'my_param', type: 'string', default: 'default-val' });
    render(<ParameterInput parameter={param} value="" onChange={mockOnChange} />);

    const input = screen.getByRole('textbox', { name: 'my_param' });
    expect(input).toHaveAttribute('placeholder', 'default-val');
  });

  // ----- Boolean type -----

  it('renders a switch for boolean type', () => {
    const param = createParam({ name: 'enabled', type: 'boolean' });
    render(<ParameterInput parameter={param} value="false" onChange={mockOnChange} />);

    // MUI Switch renders with role="switch"
    const switchEl = screen.getByRole('switch');
    expect(switchEl).toBeInTheDocument();
  });

  it('switch is unchecked when value is "false"', () => {
    const param = createParam({ name: 'enabled', type: 'boolean' });
    render(<ParameterInput parameter={param} value="false" onChange={mockOnChange} />);

    const switchEl = screen.getByRole('switch');
    expect(switchEl).not.toBeChecked();
  });

  it('switch is checked when value is "true"', () => {
    const param = createParam({ name: 'enabled', type: 'boolean' });
    render(<ParameterInput parameter={param} value="true" onChange={mockOnChange} />);

    const switchEl = screen.getByRole('switch');
    expect(switchEl).toBeChecked();
  });

  it('calls onChange with "true" when switch is toggled on', () => {
    const param = createParam({ name: 'enabled', type: 'boolean' });
    render(<ParameterInput parameter={param} value="false" onChange={mockOnChange} />);

    const switchEl = screen.getByRole('switch');
    fireEvent.click(switchEl);

    expect(mockOnChange).toHaveBeenCalledWith('enabled', 'true');
  });

  it('calls onChange with "false" when switch is toggled off', () => {
    const param = createParam({ name: 'enabled', type: 'boolean' });
    render(<ParameterInput parameter={param} value="true" onChange={mockOnChange} />);

    const switchEl = screen.getByRole('switch');
    fireEvent.click(switchEl);

    expect(mockOnChange).toHaveBeenCalledWith('enabled', 'false');
  });

  it('shows False/True labels for generic boolean', () => {
    const param = createParam({ name: 'enabled', type: 'boolean' });
    render(<ParameterInput parameter={param} value="false" onChange={mockOnChange} />);

    expect(screen.getByText('False')).toBeInTheDocument();
    expect(screen.getByText('True')).toBeInTheDocument();
  });

  it('shows Signed/Unsigned labels for module_type parameter', () => {
    const param = createParam({ name: 'unsigned_module_type', type: 'boolean' });
    render(<ParameterInput parameter={param} value="false" onChange={mockOnChange} />);

    expect(screen.getByText('Signed')).toBeInTheDocument();
    expect(screen.getByText('Unsigned')).toBeInTheDocument();
  });

  // ----- File type -----

  it('renders a text field for file type', () => {
    const param = createParam({ name: 'module_file', type: 'file' });
    render(<ParameterInput parameter={param} value="" onChange={mockOnChange} />);

    const input = screen.getByRole('textbox', { name: 'module_file file path' });
    expect(input).toBeInTheDocument();
  });

  it('shows placeholder "Enter file path..." for file type', () => {
    const param = createParam({ name: 'module_file', type: 'file' });
    render(<ParameterInput parameter={param} value="" onChange={mockOnChange} />);

    const input = screen.getByRole('textbox', { name: 'module_file file path' });
    expect(input).toHaveAttribute('placeholder', 'Enter file path...');
  });

  it('calls onChange when file path text field is edited', () => {
    const param = createParam({ name: 'module_file', type: 'file' });
    render(<ParameterInput parameter={param} value="" onChange={mockOnChange} />);

    const input = screen.getByRole('textbox', { name: 'module_file file path' });
    fireEvent.change(input, { target: { value: '/tmp/module.modl' } });

    expect(mockOnChange).toHaveBeenCalledWith('module_file', '/tmp/module.modl');
  });

  // ----- Credential type -----

  it('renders a select/dropdown for credential type', () => {
    const param = createParam({ name: 'credential', type: 'credential' });
    render(
      <ParameterInput
        parameter={param}
        value=""
        credentials={testCredentials}
        onChange={mockOnChange}
      />
    );

    const combobox = screen.getByRole('combobox');
    expect(combobox).toBeInTheDocument();
  });

  it('displays credentials in the dropdown', () => {
    const param = createParam({ name: 'credential', type: 'credential' });
    render(
      <ParameterInput
        parameter={param}
        value=""
        credentials={testCredentials}
        onChange={mockOnChange}
      />
    );

    // The select element text should be visible in the accessible name or placeholder
    // Opening the combobox to inspect options
    const combobox = screen.getByRole('combobox');
    fireEvent.mouseDown(combobox);

    expect(screen.getByText('cred-prod (admin)')).toBeInTheDocument();
    expect(screen.getByText('cred-dev (developer)')).toBeInTheDocument();
  });

  // ----- Path parameter (string with browse button) -----

  it('renders browse folder button for path-named parameters', () => {
    const param = createParam({ name: 'output_path', type: 'string' });
    render(<ParameterInput parameter={param} value="" onChange={mockOnChange} />);

    const browseBtn = screen.getByTitle('Browse folders');
    expect(browseBtn).toBeInTheDocument();
  });

  it('does not render browse folder button for non-path parameters', () => {
    const param = createParam({ name: 'gateway_url', type: 'string' });
    render(<ParameterInput parameter={param} value="" onChange={mockOnChange} />);

    expect(screen.queryByTitle('Browse folders')).not.toBeInTheDocument();
  });

  it('opens folder browser dialog when browse button clicked in web mode', () => {
    const param = createParam({ name: 'output_directory', type: 'string' });
    render(<ParameterInput parameter={param} value="" onChange={mockOnChange} />);

    const browseBtn = screen.getByTitle('Browse folders');
    fireEvent.click(browseBtn);

    expect(screen.getByTestId('folder-browser-dialog')).toBeInTheDocument();
  });

  it('uses electronAPI to open folder dialog when in Electron', async () => {
    const mockOpenFileDialog = vi.fn().mockResolvedValue(['/electron/selected/path']);
    Object.defineProperty(window, 'electronAPI', {
      value: { openFileDialog: mockOpenFileDialog },
      writable: true,
      configurable: true,
    });

    const param = createParam({ name: 'output_path', type: 'string' });
    render(<ParameterInput parameter={param} value="" onChange={mockOnChange} />);

    const browseBtn = screen.getByTitle('Browse folders');
    fireEvent.click(browseBtn);

    // Wait for async operation
    await vi.waitFor(() => {
      expect(mockOpenFileDialog).toHaveBeenCalledWith({
        title: 'Select Folder',
        properties: ['openDirectory'],
      });
    });
  });

  // ----- Required field indicator -----

  it('shows asterisk for required parameters', () => {
    const param = createParam({ name: 'required_param', type: 'string', required: true });
    render(<ParameterInput parameter={param} value="" onChange={mockOnChange} />);

    const label = screen.getByText(/required_param \*/);
    expect(label).toBeInTheDocument();
  });

  it('does not show asterisk for optional parameters', () => {
    const param = createParam({ name: 'optional_param', type: 'string', required: false });
    render(<ParameterInput parameter={param} value="" onChange={mockOnChange} />);

    expect(screen.queryByText(/optional_param \*/)).not.toBeInTheDocument();
    expect(screen.getByText('optional_param')).toBeInTheDocument();
  });

  // ----- Description -----

  it('shows description text when provided', () => {
    const param = createParam({
      name: 'my_param',
      type: 'string',
      description: 'This is a helpful description',
    });
    render(<ParameterInput parameter={param} value="" onChange={mockOnChange} />);

    expect(screen.getByText('This is a helpful description')).toBeInTheDocument();
  });

  it('does not render description when empty', () => {
    const param = createParam({ name: 'my_param', type: 'string', description: '' });
    render(<ParameterInput parameter={param} value="" onChange={mockOnChange} />);

    // No spurious description text
    expect(screen.queryByText('This is a helpful description')).not.toBeInTheDocument();
  });
});
