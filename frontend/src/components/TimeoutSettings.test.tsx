/**
 * Tests for TimeoutSettings component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TimeoutSettings } from './TimeoutSettings';
import type { TimeoutOverrides } from '../types/api';

describe('TimeoutSettings', () => {
  const mockOnChange = vi.fn();
  const emptyOverrides: TimeoutOverrides = {};

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ----- Basic rendering -----

  it('renders without crashing', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText('Timeout Settings')).toBeInTheDocument();
  });

  it('renders the accordion header with timer icon label', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText('Timeout Settings')).toBeInTheDocument();
  });

  // ----- Hidden when relevantTimeouts is empty array -----

  it('returns null (renders nothing) when relevantTimeouts is an empty array', () => {
    const { container } = render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
        relevantTimeouts={[]}
      />
    );

    expect(container.firstChild).toBeNull();
  });

  // ----- Renders all fields when no relevantTimeouts filter -----

  it('shows all 4 timeout fields when accordion is expanded and no relevantTimeouts filter', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
      />
    );

    // Expand the accordion
    fireEvent.click(screen.getByText('Timeout Settings'));

    expect(screen.getByLabelText(/Gateway Restart/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Module Installation/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Designer Launch/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Browser Operations/)).toBeInTheDocument();
  });

  it('shows all 4 timeout fields when relevantTimeouts is null/undefined', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
        relevantTimeouts={undefined}
      />
    );

    fireEvent.click(screen.getByText('Timeout Settings'));

    expect(screen.getByLabelText(/Gateway Restart/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Module Installation/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Designer Launch/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Browser Operations/)).toBeInTheDocument();
  });

  // ----- Filtering by relevantTimeouts -----

  it('only shows gateway_restart field when relevantTimeouts is ["gateway_restart"]', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
        relevantTimeouts={['gateway_restart']}
      />
    );

    fireEvent.click(screen.getByText('Timeout Settings'));

    expect(screen.getByLabelText(/Gateway Restart/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Module Installation/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Designer Launch/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Browser Operations/)).not.toBeInTheDocument();
  });

  it('only shows module_install field when relevantTimeouts is ["module_install"]', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
        relevantTimeouts={['module_install']}
      />
    );

    fireEvent.click(screen.getByText('Timeout Settings'));

    expect(screen.queryByLabelText(/Gateway Restart/)).not.toBeInTheDocument();
    expect(screen.getByLabelText(/Module Installation/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Designer Launch/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Browser Operations/)).not.toBeInTheDocument();
  });

  it('shows two fields when relevantTimeouts has two entries', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
        relevantTimeouts={['gateway_restart', 'browser_operation']}
      />
    );

    fireEvent.click(screen.getByText('Timeout Settings'));

    expect(screen.getByLabelText(/Gateway Restart/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Module Installation/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Designer Launch/)).not.toBeInTheDocument();
    expect(screen.getByLabelText(/Browser Operations/)).toBeInTheDocument();
  });

  // ----- Default value display in labels -----

  it('shows default value 120s in Gateway Restart label', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
      />
    );

    fireEvent.click(screen.getByText('Timeout Settings'));

    expect(screen.getByLabelText(/Gateway Restart \(default: 120s\)/)).toBeInTheDocument();
  });

  it('shows default value 300s in Module Installation label', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
      />
    );

    fireEvent.click(screen.getByText('Timeout Settings'));

    expect(screen.getByLabelText(/Module Installation \(default: 300s\)/)).toBeInTheDocument();
  });

  it('shows default value 60s in Designer Launch label', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
      />
    );

    fireEvent.click(screen.getByText('Timeout Settings'));

    expect(screen.getByLabelText(/Designer Launch \(default: 60s\)/)).toBeInTheDocument();
  });

  it('shows default value 30000ms in Browser Operations label', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
      />
    );

    fireEvent.click(screen.getByText('Timeout Settings'));

    expect(screen.getByLabelText(/Browser Operations \(default: 30000ms\)/)).toBeInTheDocument();
  });

  // ----- Accordion expand/collapse -----

  it('accordion is collapsed by default (fields not visible)', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
      />
    );

    // MUI Accordion keeps content in the DOM but hides it via CSS when collapsed
    const field = screen.queryByLabelText(/Gateway Restart/);
    if (field) {
      // If it's in the DOM, it should not be visible
      expect(field).not.toBeVisible();
    }
    // If null, the test passes trivially (component chose not to render it)
  });

  it('expands accordion on click to show fields', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
      />
    );

    fireEvent.click(screen.getByText('Timeout Settings'));

    expect(screen.getByLabelText(/Gateway Restart/)).toBeVisible();
  });

  it('collapses accordion on second click', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
      />
    );

    // MUI AccordionSummary exposes aria-expanded on the nearest ancestor with that attr
    const summaryEl = screen.getByText('Timeout Settings').closest('[aria-expanded]');
    expect(summaryEl).toHaveAttribute('aria-expanded', 'false');

    // First click expands
    fireEvent.click(screen.getByText('Timeout Settings'));
    expect(summaryEl).toHaveAttribute('aria-expanded', 'true');

    // Second click collapses (note: MUI Accordion keeps content mounted in DOM after
    // first expansion — check aria-expanded instead of DOM presence)
    fireEvent.click(screen.getByText('Timeout Settings'));
    expect(summaryEl).toHaveAttribute('aria-expanded', 'false');
  });

  // ----- Value display -----

  it('displays existing override value in the gateway_restart field', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={{ gateway_restart: 240 }}
        onChange={mockOnChange}
      />
    );

    fireEvent.click(screen.getByText('Timeout Settings'));

    const field = screen.getByLabelText(/Gateway Restart/);
    expect(field).toHaveValue(240);
  });

  it('displays empty string when no override is set', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
      />
    );

    fireEvent.click(screen.getByText('Timeout Settings'));

    const field = screen.getByLabelText(/Gateway Restart/);
    expect(field).toHaveValue(null); // empty number input has null value
  });

  // ----- onChange callbacks -----

  it('calls onChange with new value when gateway_restart field is edited', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
      />
    );

    fireEvent.click(screen.getByText('Timeout Settings'));

    const field = screen.getByLabelText(/Gateway Restart/);
    fireEvent.change(field, { target: { value: '180' } });

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({ gateway_restart: 180 })
    );
  });

  it('calls onChange with new value when module_install field is edited', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
      />
    );

    fireEvent.click(screen.getByText('Timeout Settings'));

    const field = screen.getByLabelText(/Module Installation/);
    fireEvent.change(field, { target: { value: '600' } });

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({ module_install: 600 })
    );
  });

  it('calls onChange with undefined when field is cleared', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={{ gateway_restart: 180 }}
        onChange={mockOnChange}
      />
    );

    fireEvent.click(screen.getByText('Timeout Settings'));

    const field = screen.getByLabelText(/Gateway Restart/);
    fireEvent.change(field, { target: { value: '' } });

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({ gateway_restart: undefined })
    );
  });

  it('does not call onChange for invalid non-numeric input', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
      />
    );

    fireEvent.click(screen.getByText('Timeout Settings'));

    const field = screen.getByLabelText(/Gateway Restart/);
    // NaN would be produced by parseInt('abc')
    fireEvent.change(field, { target: { value: 'abc' } });

    expect(mockOnChange).not.toHaveBeenCalled();
  });

  // ----- "customized" badge -----

  it('shows "(customized)" label when any override is set', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={{ gateway_restart: 200 }}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText('(customized)')).toBeInTheDocument();
  });

  it('does not show "(customized)" label when no overrides are set', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
      />
    );

    expect(screen.queryByText('(customized)')).not.toBeInTheDocument();
  });

  // ----- Helper text -----

  it('shows "Leave empty to use default values" hint text', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
      />
    );

    fireEvent.click(screen.getByText('Timeout Settings'));

    expect(screen.getByText(/Leave empty to use default values/)).toBeInTheDocument();
  });

  // ----- Units in adornments -----

  it('shows "seconds" unit adornment for gateway_restart field', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
        relevantTimeouts={['gateway_restart']}
      />
    );

    fireEvent.click(screen.getByText('Timeout Settings'));

    expect(screen.getByText('seconds')).toBeInTheDocument();
  });

  it('shows "ms" unit adornment for browser_operation field', () => {
    render(
      <TimeoutSettings
        timeoutOverrides={emptyOverrides}
        onChange={mockOnChange}
        relevantTimeouts={['browser_operation']}
      />
    );

    fireEvent.click(screen.getByText('Timeout Settings'));

    expect(screen.getByText('ms')).toBeInTheDocument();
  });
});
