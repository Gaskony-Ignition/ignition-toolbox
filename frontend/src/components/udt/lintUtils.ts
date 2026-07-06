/** Non-component helpers shared by LintPanel and its consumers (kept out of
 * LintPanel.tsx so fast-refresh doesn't complain about mixed exports). */

import type { UdtLintSeverity } from '../../types/api';

export const SEVERITY_COLOR: Record<UdtLintSeverity, 'error' | 'warning' | 'info' | 'default'> = {
  critical: 'error',
  high: 'warning',
  medium: 'info',
  info: 'default',
};

/** Best-effort split of the backend's joined 422 message into individual clauses. */
export function splitBlockingErrors(message: string): string[] {
  return message
    .replace(/^Invalid composition:\s*/i, '')
    .split(';')
    .map((clause) => clause.trim())
    .filter(Boolean);
}
