/**
 * Tests for DraggableStepList component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DraggableStepList } from './DraggableStepList';
import type { StepTypeInfo, CredentialInfo } from '../types/api';

// Mock @dnd-kit/core — drag-and-drop internals are not testable in jsdom
vi.mock('@dnd-kit/core', () => ({
  DndContext: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  closestCenter: vi.fn(),
  KeyboardSensor: vi.fn(),
  PointerSensor: vi.fn(),
  useSensor: vi.fn(),
  useSensors: vi.fn().mockReturnValue([]),
}));

// Mock @dnd-kit/sortable
vi.mock('@dnd-kit/sortable', () => ({
  SortableContext: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  sortableKeyboardCoordinates: vi.fn(),
  verticalListSortingStrategy: vi.fn(),
  useSortable: vi.fn().mockReturnValue({
    attributes: {},
    listeners: {},
    setNodeRef: vi.fn(),
    transform: null,
    transition: undefined,
    isDragging: false,
  }),
  arrayMove: (arr: unknown[], from: number, to: number) => {
    const result = [...arr];
    const [removed] = result.splice(from, 1);
    result.splice(to, 0, removed);
    return result;
  },
}));

// Mock @dnd-kit/utilities
vi.mock('@dnd-kit/utilities', () => ({
  CSS: {
    Transform: {
      toString: vi.fn().mockReturnValue(''),
    },
  },
}));

// Mock StepEditorPanel — we only test DraggableStepList, not the inline editor
vi.mock('./StepEditorPanel', () => ({
  StepEditorPanel: () => <div data-testid="step-editor-panel">StepEditorPanel</div>,
}));

// ---- Helpers ----

function createStep(overrides: Partial<{
  id: string;
  name: string;
  type: string;
  parameters: Record<string, unknown>;
}> = {}) {
  return {
    id: 'step-1',
    name: 'Test Step',
    type: 'gateway.check',
    parameters: {},
    ...overrides,
  };
}

const mockStepType: StepTypeInfo = {
  type: 'gateway.check',
  domain: 'gateway',
  description: 'Checks gateway connectivity',
  parameters: [],
};

const mockCredentials: CredentialInfo[] = [];

describe('DraggableStepList', () => {
  const mockOnStepsChange = vi.fn();
  const mockOnEditStep = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty state when no steps are provided', () => {
    render(
      <DraggableStepList
        steps={[]}
        stepTypes={[]}
        credentials={mockCredentials}
        onStepsChange={mockOnStepsChange}
        onEditStep={mockOnEditStep}
        editingIndex={null}
      />
    );

    expect(screen.getByText(/No steps yet/i)).toBeInTheDocument();
    expect(screen.getByText(/Add Step/i)).toBeInTheDocument();
  });

  it('renders a list of steps without crashing', () => {
    const steps = [
      createStep({ id: 'step-1', name: 'First Step', type: 'gateway.check' }),
      createStep({ id: 'step-2', name: 'Second Step', type: 'utility.sleep' }),
    ];

    render(
      <DraggableStepList
        steps={steps}
        stepTypes={[mockStepType]}
        credentials={mockCredentials}
        onStepsChange={mockOnStepsChange}
        onEditStep={mockOnEditStep}
        editingIndex={null}
      />
    );

    expect(screen.getByText('First Step')).toBeInTheDocument();
    expect(screen.getByText('Second Step')).toBeInTheDocument();
  });

  it('shows step type chips for each step', () => {
    const steps = [
      createStep({ id: 'step-1', name: 'My Step', type: 'gateway.check' }),
    ];

    render(
      <DraggableStepList
        steps={steps}
        stepTypes={[mockStepType]}
        credentials={mockCredentials}
        onStepsChange={mockOnStepsChange}
        onEditStep={mockOnEditStep}
        editingIndex={null}
      />
    );

    // The step type is shown as a Chip
    expect(screen.getByText('gateway.check')).toBeInTheDocument();
  });

  it('shows step description when a matching StepTypeInfo is provided', () => {
    const steps = [createStep({ id: 'step-1', name: 'My Step', type: 'gateway.check' })];

    render(
      <DraggableStepList
        steps={steps}
        stepTypes={[mockStepType]}
        credentials={mockCredentials}
        onStepsChange={mockOnStepsChange}
        onEditStep={mockOnEditStep}
        editingIndex={null}
      />
    );

    expect(screen.getByText('Checks gateway connectivity')).toBeInTheDocument();
  });

  it('shows step number chip starting from 1', () => {
    const steps = [
      createStep({ id: 'step-1', name: 'First Step', type: 'gateway.check' }),
    ];

    render(
      <DraggableStepList
        steps={steps}
        stepTypes={[]}
        credentials={mockCredentials}
        onStepsChange={mockOnStepsChange}
        onEditStep={mockOnEditStep}
        editingIndex={null}
      />
    );

    // Step number "1" should be shown in the chip
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('calls onEditStep when the Edit button is clicked', () => {
    const steps = [createStep({ id: 'step-1', name: 'My Step', type: 'gateway.check' })];

    render(
      <DraggableStepList
        steps={steps}
        stepTypes={[]}
        credentials={mockCredentials}
        onStepsChange={mockOnStepsChange}
        onEditStep={mockOnEditStep}
        editingIndex={null}
      />
    );

    // Click the "Edit step" tooltip button
    const editButton = screen.getByRole('button', { name: /edit step/i });
    fireEvent.click(editButton);

    expect(mockOnEditStep).toHaveBeenCalledWith(0);
  });

  it('calls onStepsChange when the Delete button is clicked', () => {
    const steps = [createStep({ id: 'step-1', name: 'My Step', type: 'gateway.check' })];

    render(
      <DraggableStepList
        steps={steps}
        stepTypes={[]}
        credentials={mockCredentials}
        onStepsChange={mockOnStepsChange}
        onEditStep={mockOnEditStep}
        editingIndex={null}
      />
    );

    const deleteButton = screen.getByRole('button', { name: /delete step/i });
    fireEvent.click(deleteButton);

    // After deletion of the only step, the new list is empty
    expect(mockOnStepsChange).toHaveBeenCalledWith([]);
  });

  it('calls onStepsChange with a duplicated step when Duplicate button is clicked', () => {
    const steps = [createStep({ id: 'step-1', name: 'My Step', type: 'gateway.check' })];

    render(
      <DraggableStepList
        steps={steps}
        stepTypes={[]}
        credentials={mockCredentials}
        onStepsChange={mockOnStepsChange}
        onEditStep={mockOnEditStep}
        editingIndex={null}
      />
    );

    const duplicateButton = screen.getByRole('button', { name: /duplicate step/i });
    fireEvent.click(duplicateButton);

    const newSteps = mockOnStepsChange.mock.calls[0][0];
    expect(newSteps).toHaveLength(2);
    expect(newSteps[1].name).toBe('My Step (Copy)');
    expect(newSteps[1].id).toBe('step-1_copy');
  });

  it('shows the StepEditorPanel when a step is being edited', () => {
    const steps = [createStep({ id: 'step-1', name: 'My Step', type: 'gateway.check' })];

    render(
      <DraggableStepList
        steps={steps}
        stepTypes={[]}
        credentials={mockCredentials}
        onStepsChange={mockOnStepsChange}
        onEditStep={mockOnEditStep}
        editingIndex={0}
      />
    );

    expect(screen.getByTestId('step-editor-panel')).toBeInTheDocument();
  });

  it('renders multiple steps with correct numbering', () => {
    const steps = [
      createStep({ id: 'a', name: 'Alpha', type: 'utility.sleep' }),
      createStep({ id: 'b', name: 'Beta', type: 'utility.sleep' }),
      createStep({ id: 'c', name: 'Gamma', type: 'utility.sleep' }),
    ];

    render(
      <DraggableStepList
        steps={steps}
        stepTypes={[]}
        credentials={mockCredentials}
        onStepsChange={mockOnStepsChange}
        onEditStep={mockOnEditStep}
        editingIndex={null}
      />
    );

    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('Alpha')).toBeInTheDocument();
    expect(screen.getByText('Beta')).toBeInTheDocument();
    expect(screen.getByText('Gamma')).toBeInTheDocument();
  });
});
