/**
 * executionStatus - Centralized execution status constants and helpers
 *
 * Single source of truth for status colors and icons used across:
 * - ExecutionCard
 * - Executions page
 * - ExecutionDetail page
 * - ExecutionTimeline
 */

import React from 'react';
import {
  CheckCircle as CompletedIcon,
  Error as ErrorIcon,
  PlayArrow as RunningIcon,
  Pending as PendingIcon,
  Cancel as CancelledIcon,
  Pause as PausedIcon,
} from '@mui/icons-material';

export type ExecutionStatus =
  | 'pending'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'skipped';

type MuiChipColor =
  | 'default'
  | 'primary'
  | 'secondary'
  | 'error'
  | 'warning'
  | 'info'
  | 'success';

/** MUI Chip/Badge color prop values per status */
export const STATUS_CHIP_COLOR: Record<ExecutionStatus, MuiChipColor> = {
  pending: 'default',
  running: 'primary',
  paused: 'warning',
  completed: 'success',
  failed: 'error',
  cancelled: 'default',
  skipped: 'warning',
};

/** CSS hex colors per status (used for inline styles, borders, SVG fills) */
export const STATUS_HEX_COLOR: Record<ExecutionStatus, string> = {
  pending: '#666',
  running: '#2196f3',
  paused: '#ff9800',
  completed: '#4caf50',
  failed: '#f44336',
  cancelled: '#666',
  skipped: '#ff9800',
};

/** Returns the MUI Chip color string for a given status */
export function getStatusChipColor(status: string): MuiChipColor {
  return STATUS_CHIP_COLOR[status as ExecutionStatus] ?? 'default';
}

/** Returns a hex color string for a given status (for CSS / inline styles) */
export function getStatusTimelineColor(status: string): string {
  return STATUS_HEX_COLOR[status as ExecutionStatus] ?? '#666';
}

/**
 * Returns a React element icon for a given status.
 *
 * @param status - The execution/step status string
 * @param options.size - Icon size: 'small' (1rem) or 'medium' (1.25rem). Defaults to 'small'.
 * @param options.color - Override the icon color (CSS color string). Defaults to the status color.
 */
export function getStatusIcon(
  status: string,
  options?: { size?: 'small' | 'medium'; color?: string }
): React.ReactElement {
  const fontSize = options?.size === 'medium' ? '1.25rem' : '1rem';
  const color = options?.color ?? getStatusTimelineColor(status);

  switch (status) {
    case 'completed':
      return React.createElement(CompletedIcon, { sx: { fontSize, color } });
    case 'failed':
      return React.createElement(ErrorIcon, { sx: { fontSize, color } });
    case 'running':
      return React.createElement(RunningIcon, { sx: { fontSize, color } });
    case 'paused':
      return React.createElement(PausedIcon, { sx: { fontSize, color } });
    case 'cancelled':
      return React.createElement(CancelledIcon, { sx: { fontSize, color } });
    case 'skipped':
      // Re-use Cancel icon tinted warning (same as ExecutionDetail/ExecutionTimeline)
      return React.createElement(CancelledIcon, { sx: { fontSize, color } });
    default:
      return React.createElement(PendingIcon, { sx: { fontSize, color } });
  }
}
