/**
 * Composer wizard — "Review" step: JSON preview of the last successful
 * compose, plus Copy JSON / Download <filename> actions. Findings are
 * shown by the persistent LintPanel the wizard renders alongside this step
 * — not duplicated here.
 */

import { Box, Typography, Button, Stack, Divider } from '@mui/material';
import { Download as DownloadIcon, ContentCopy as CopyIcon } from '@mui/icons-material';
import { JsonViewer } from '../api-explorer/JsonViewer';
import type { UdtComposeResponse } from '../../types/api';

interface ReviewStepProps {
  composeResult: UdtComposeResponse | null;
}

export function ReviewStep({ composeResult }: ReviewStepProps) {
  const handleCopy = async () => {
    if (!composeResult) return;
    await navigator.clipboard.writeText(JSON.stringify(composeResult.udt, null, 2));
  };

  const handleDownload = () => {
    if (!composeResult) return;
    const blob = new Blob([JSON.stringify(composeResult.udt, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = composeResult.filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography variant="subtitle1">Preview</Typography>
        <Stack direction="row" spacing={1}>
          <Button size="small" startIcon={<CopyIcon />} onClick={handleCopy} disabled={!composeResult}>
            Copy JSON
          </Button>
          <Button
            size="small"
            variant="outlined"
            startIcon={<DownloadIcon />}
            onClick={handleDownload}
            disabled={!composeResult}
          >
            {composeResult ? `Download ${composeResult.filename}` : 'Download'}
          </Button>
        </Stack>
      </Box>
      <Divider sx={{ mb: 1 }} />
      {composeResult ? (
        <JsonViewer data={composeResult.udt} />
      ) : (
        <Typography variant="body2" color="text.secondary">
          Waiting for a successful compose — check the quality checks panel for blocking errors.
        </Typography>
      )}
    </Box>
  );
}
