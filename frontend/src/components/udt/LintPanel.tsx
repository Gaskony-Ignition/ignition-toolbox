/**
 * Persistent live-lint panel for the UDT composer.
 *
 * Shown on the Structure/Alarms/History/Review steps. Renders debounced
 * `/api/udt/compose` findings grouped by severity (colours matched to
 * pages/Audit.tsx), plus a set of blocking structural errors (from a 422
 * response) rendered separately and prominently — those mean the
 * composition itself won't compose yet, as opposed to lint findings which
 * never block.
 */

import { Box, Typography, Chip, Alert, Stack, CircularProgress } from '@mui/material';
import type { UdtLintFinding, UdtLintSeverity } from '../../types/api';
import { SEVERITY_COLOR } from './lintUtils';

const SEVERITY_ORDER: UdtLintSeverity[] = ['critical', 'high', 'medium', 'info'];

interface LintPanelProps {
  findings: UdtLintFinding[];
  /** Parsed '; '-joined 422 message clauses — a structurally invalid composition. */
  blockingErrors?: string[];
  isPending?: boolean;
}

export function LintPanel({ findings, blockingErrors = [], isPending = false }: LintPanelProps) {
  const grouped = SEVERITY_ORDER.map((severity) => ({
    severity,
    items: findings.filter((f) => f.severity === severity),
  })).filter((group) => group.items.length > 0);

  return (
    <Box data-testid="lint-panel" sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="subtitle2">Quality checks</Typography>
        {isPending && <CircularProgress size={14} />}
      </Box>

      {blockingErrors.length > 0 && (
        <Alert severity="error" data-testid="lint-blocking-errors">
          <Typography variant="body2" fontWeight={600} gutterBottom>
            This composition can&apos;t be built yet:
          </Typography>
          <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
            {blockingErrors.map((clause) => (
              <li key={clause}>
                <Typography variant="body2">{clause}</Typography>
              </li>
            ))}
          </Box>
        </Alert>
      )}

      {blockingErrors.length === 0 && findings.length === 0 && (
        <Typography variant="body2" color="text.secondary">
          No quality findings — looking good.
        </Typography>
      )}

      {grouped.map(({ severity, items }) => (
        <Box key={severity}>
          <Chip
            label={`${severity.charAt(0).toUpperCase() + severity.slice(1)}: ${items.length}`}
            size="small"
            color={SEVERITY_COLOR[severity]}
            variant="outlined"
            sx={{ mb: 0.75 }}
          />
          <Stack spacing={1}>
            {items.map((finding, index) => (
              <Box
                key={`${finding.rule_id}::${finding.location}::${index}`}
                sx={{ p: 1, borderRadius: 1, border: '1px solid', borderColor: 'divider' }}
              >
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'baseline', flexWrap: 'wrap' }}>
                  <Typography variant="caption" fontFamily="monospace" color="text.secondary">
                    {finding.rule_id}
                  </Typography>
                  <Typography variant="caption" fontFamily="monospace" color="text.secondary">
                    {finding.location}
                  </Typography>
                </Box>
                <Typography variant="body2">{finding.message}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {finding.recommendation}
                </Typography>
              </Box>
            ))}
          </Stack>
        </Box>
      ))}
    </Box>
  );
}
