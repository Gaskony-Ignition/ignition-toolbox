/**
 * Perspective Project Audit page
 *
 * Upload a Perspective project export (zip) and get back a customer-facing
 * findings report: executive summary, findings aggregated by rule + view
 * (a real project can produce hundreds of raw findings from a single rule
 * in one view — the API already collapses these into one row with example
 * locations), and a markdown report download.
 */

import { useCallback, useRef, useState, Fragment } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Collapse,
  Stack,
} from '@mui/material';
import {
  UploadFile as UploadFileIcon,
  Download as DownloadIcon,
  KeyboardArrowDown as RowExpandIcon,
  KeyboardArrowUp as RowCollapseIcon,
  Refresh as ResetIcon,
} from '@mui/icons-material';
import { api, APIError } from '../api/client';
import type { AuditAggregatedFinding, AuditReport, AuditSeverity } from '../types/api';

const SEVERITY_ORDER: AuditSeverity[] = ['critical', 'high', 'medium', 'info'];

const SEVERITY_COLOR: Record<AuditSeverity, 'error' | 'warning' | 'info' | 'default'> = {
  critical: 'error',
  high: 'warning',
  medium: 'info',
  info: 'default',
};

// ============================================================================
// Drop zone
// ============================================================================

interface DropZoneProps {
  onFileSelected: (file: File) => void;
  disabled: boolean;
}

function DropZone({ onFileSelected, disabled }: DropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragOver(false);
      if (disabled) return;
      const file = e.dataTransfer.files?.[0];
      if (file) onFileSelected(file);
    },
    [disabled, onFileSelected]
  );

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onFileSelected(file);
    // Reset so selecting the same file again still fires onChange
    e.target.value = '';
  };

  return (
    <Box
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      sx={{
        p: 5,
        textAlign: 'center',
        border: '2px dashed',
        borderColor: isDragOver ? 'primary.main' : 'divider',
        borderRadius: 2,
        bgcolor: isDragOver ? 'action.hover' : 'background.paper',
        cursor: disabled ? 'default' : 'pointer',
        opacity: disabled ? 0.6 : 1,
        transition: 'border-color 0.15s, background-color 0.15s',
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".zip"
        hidden
        onChange={handleInputChange}
        disabled={disabled}
        data-testid="audit-file-input"
      />
      <UploadFileIcon sx={{ fontSize: 40, color: 'text.secondary', mb: 1 }} />
      <Typography variant="body1" gutterBottom>
        Drop a Perspective project export (.zip) here, or click to browse
      </Typography>
      <Typography variant="caption" color="text.secondary">
        Designer export (Project → Export) or a gateway backup. Max 50 MB.
      </Typography>
    </Box>
  );
}

// ============================================================================
// Executive summary
// ============================================================================

function ExecutiveSummary({ report }: { report: AuditReport }) {
  return (
    <Box
      sx={{
        p: 2,
        mb: 3,
        bgcolor: 'background.paper',
        borderRadius: 1,
        border: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Typography variant="h6" gutterBottom>
        {report.project_name}
      </Typography>
      <Stack direction="row" spacing={3} sx={{ mb: 2, flexWrap: 'wrap' }}>
        <Typography variant="body2" color="text.secondary">
          {report.inventory.view_count} views
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {report.inventory.component_count} components
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {report.inventory.binding_count} bindings
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {report.summary.total_findings} findings ({report.aggregated_findings.length} rule/view groups)
        </Typography>
      </Stack>
      <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
        {SEVERITY_ORDER.map((severity) => (
          <Chip
            key={severity}
            label={`${severity.charAt(0).toUpperCase() + severity.slice(1)}: ${report.summary.by_severity[severity] ?? 0}`}
            size="small"
            color={SEVERITY_COLOR[severity]}
            variant="outlined"
          />
        ))}
      </Stack>
    </Box>
  );
}

// ============================================================================
// Aggregated findings table
// ============================================================================

function AggregatedFindingsTable({ rows }: { rows: AuditAggregatedFinding[] }) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const toggleExpanded = (index: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  if (rows.length === 0) {
    return (
      <Box sx={{ p: 4, textAlign: 'center', opacity: 0.6 }}>
        <Typography variant="body2">No findings — nothing to report.</Typography>
      </Box>
    );
  }

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell sx={{ width: 40 }} />
            <TableCell>Rule</TableCell>
            <TableCell>Severity</TableCell>
            <TableCell>View</TableCell>
            <TableCell align="right">Count</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, index) => {
            const isOpen = expanded.has(index);
            return (
              <Fragment key={`${row.rule_id}::${row.view}`}>
                <TableRow hover>
                  <TableCell>
                    <IconButton
                      size="small"
                      onClick={() => toggleExpanded(index)}
                      aria-label={isOpen ? 'Collapse details' : 'Expand details'}
                    >
                      {isOpen ? <RowCollapseIcon fontSize="small" /> : <RowExpandIcon fontSize="small" />}
                    </IconButton>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontFamily="monospace">
                      {row.rule_id}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={row.severity}
                      size="small"
                      color={SEVERITY_COLOR[row.severity]}
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>{row.view}</TableCell>
                  <TableCell align="right">{row.count}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell sx={{ py: 0, borderBottom: isOpen ? undefined : 'none' }} colSpan={5}>
                    <Collapse in={isOpen} timeout="auto" unmountOnExit>
                      <Box sx={{ py: 2, px: 2, maxWidth: 900 }}>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          {row.message}
                        </Typography>
                        <Typography variant="subtitle2" gutterBottom>
                          Example locations
                        </Typography>
                        <Box component="ul" sx={{ mt: 0, mb: 1.5, pl: 3 }}>
                          {row.example_locations.map((location) => (
                            <li key={location}>
                              <Typography variant="caption" fontFamily="monospace">
                                {location}
                              </Typography>
                            </li>
                          ))}
                        </Box>
                        <Typography variant="subtitle2" gutterBottom>
                          Recommendation
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {row.recommendation}
                        </Typography>
                      </Box>
                    </Collapse>
                  </TableCell>
                </TableRow>
              </Fragment>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

// ============================================================================
// Main Audit page
// ============================================================================

export function Audit() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const auditMutation = useMutation({
    mutationFn: (file: File) => api.audit.runPerspectiveAudit(file),
  });

  const downloadMutation = useMutation({
    mutationFn: (file: File) => api.audit.downloadPerspectiveAuditMarkdown(file),
  });

  const handleFileSelected = (file: File) => {
    setSelectedFile(file);
    auditMutation.mutate(file);
  };

  const handleReset = () => {
    setSelectedFile(null);
    auditMutation.reset();
  };

  const handleDownload = () => {
    if (selectedFile) downloadMutation.mutate(selectedFile);
  };

  const errorMessage = (error: unknown): string =>
    error instanceof APIError ? error.getDisplayMessage() : 'An unexpected error occurred.';

  return (
    <Box>
      {/* Page header */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="h5" fontWeight={700} gutterBottom>
          Perspective Project Audit
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Upload a Perspective project export to check naming, layout, bindings, scripts,
          consistency, and hygiene against best-practice rules — no gateway required.
        </Typography>
      </Box>

      {!auditMutation.isSuccess && (
        <DropZone onFileSelected={handleFileSelected} disabled={auditMutation.isPending} />
      )}

      {auditMutation.isPending && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mt: 3 }}>
          <CircularProgress size={20} />
          <Typography variant="body2" color="text.secondary">
            Analysing {selectedFile?.name}…
          </Typography>
        </Box>
      )}

      {auditMutation.isError && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {errorMessage(auditMutation.error)}
        </Alert>
      )}

      {auditMutation.isSuccess && (
        <Box sx={{ mt: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mb: 2 }}>
            <Button
              size="small"
              variant="outlined"
              startIcon={<DownloadIcon />}
              onClick={handleDownload}
              disabled={downloadMutation.isPending}
            >
              {downloadMutation.isPending ? 'Preparing…' : 'Download report (.md)'}
            </Button>
            <Button size="small" startIcon={<ResetIcon />} onClick={handleReset}>
              Audit another project
            </Button>
          </Box>

          {downloadMutation.isError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {errorMessage(downloadMutation.error)}
            </Alert>
          )}

          <ExecutiveSummary report={auditMutation.data} />

          <Typography variant="subtitle1" gutterBottom>
            Findings by rule &amp; view
          </Typography>
          <AggregatedFindingsTable rows={auditMutation.data.aggregated_findings} />
        </Box>
      )}
    </Box>
  );
}
