/**
 * Diagnostics sections - System health, data management, and logs viewer
 * Split into 3 separate components for use in Settings sidebar tabs
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Typography,
  Paper,
  Stack,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  TextField,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  Download as DownloadIcon,
  CheckCircle as HealthyIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Storage as StorageIcon,
  Memory as MemoryIcon,
  Schedule as ScheduleIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Clear as ClearIcon,
} from '@mui/icons-material';
import { api } from '../api/client';
import { TIMING } from '../config/timing';
import type {
  LogEntry,
  LogStats,
  DetailedHealthResponse,
  DatabaseStats,
  StorageStats,
  CleanupResult,
  HealthStatus,
} from '../types/api';

// Log level colors
const levelColors: Record<string, 'error' | 'warning' | 'info' | 'success' | 'default'> = {
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info',
  DEBUG: 'default',
};

// Health status colors and icons
const healthStatusConfig: Record<HealthStatus, { color: 'success' | 'warning' | 'error' | 'default'; icon: React.ReactElement }> = {
  healthy: { color: 'success', icon: <HealthyIcon /> },
  degraded: { color: 'warning', icon: <WarningIcon /> },
  unhealthy: { color: 'error', icon: <ErrorIcon /> },
  unknown: { color: 'default', icon: <WarningIcon /> },
};

// Safe accessor for health status config
const getHealthConfig = (status: string | undefined | null) => {
  const validStatus = status && status in healthStatusConfig ? status as HealthStatus : 'unknown';
  return healthStatusConfig[validStatus];
};

/**
 * DiagnosticsSection - System Health only
 */
export function DiagnosticsSection() {
  const [health, setHealth] = useState<DetailedHealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);

  const fetchHealth = useCallback(async () => {
    setHealthLoading(true);
    try {
      const response = await api.diagnostics.getDetailedHealth();
      setHealth(response);
    } catch {
      // Non-critical
    } finally {
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  return (
    <Box sx={{ width: '100%', maxWidth: '100%' }}>
      <Typography variant="h6" sx={{ mb: 3 }}>
        Diagnostics
      </Typography>

      <Paper
        sx={{
          p: 3,
          bgcolor: 'background.paper',
          border: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>
            System Health
          </Typography>
          <IconButton size="small" onClick={fetchHealth} disabled={healthLoading}>
            {healthLoading ? <CircularProgress size={16} /> : <RefreshIcon fontSize="small" />}
          </IconButton>
        </Box>
        <Divider sx={{ mb: 2 }} />

        {health ? (
          <Stack spacing={2}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Chip
                icon={getHealthConfig(health.status).icon}
                label={(health.status || 'unknown').charAt(0).toUpperCase() + (health.status || 'unknown').slice(1)}
                color={getHealthConfig(health.status).color}
                size="small"
              />
              <Typography variant="body2" color="text.secondary">
                Uptime: {Math.floor(health.uptime_seconds / 3600)}h {Math.floor((health.uptime_seconds % 3600) / 60)}m
              </Typography>
            </Box>

            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 1.5 }}>
              {Object.entries(health.components || {}).map(([name, component]) => (
                <Paper
                  key={name}
                  variant="outlined"
                  sx={{
                    p: 1.5,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    borderColor: component?.status === 'healthy' ? 'success.main' :
                                 component?.status === 'degraded' ? 'warning.main' : 'error.main',
                  }}
                >
                  {getHealthConfig(component?.status).icon}
                  <Box>
                    <Typography variant="body2" fontWeight="medium" sx={{ textTransform: 'capitalize' }}>
                      {name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {component.message}
                    </Typography>
                  </Box>
                </Paper>
              ))}
            </Box>

            {health.errors.length > 0 && (
              <Alert severity="error" sx={{ mt: 1 }}>
                {health.errors.join(', ')}
              </Alert>
            )}
            {health.warnings.length > 0 && (
              <Alert severity="warning" sx={{ mt: 1 }}>
                {health.warnings.join(', ')}
              </Alert>
            )}
          </Stack>
        ) : (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
            <CircularProgress size={24} />
          </Box>
        )}
      </Paper>
    </Box>
  );
}

/**
 * DataManagementSection - Database stats, Screenshots stats, Data Cleanup
 */
export function DataManagementSection() {
  const [dbStats, setDbStats] = useState<DatabaseStats | null>(null);
  const [dbLoading, setDbLoading] = useState(false);
  const [storageStats, setStorageStats] = useState<StorageStats | null>(null);
  const [storageLoading, setStorageLoading] = useState(false);
  const [cleanupDialog, setCleanupDialog] = useState(false);
  const [cleanupDays, setCleanupDays] = useState(30);
  const [cleanupResult, setCleanupResult] = useState<CleanupResult | null>(null);
  const [cleanupLoading, setCleanupLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDbStats = useCallback(async () => {
    setDbLoading(true);
    try {
      const response = await api.diagnostics.getDatabaseStats();
      setDbStats(response);
    } catch {
      // Non-critical
    } finally {
      setDbLoading(false);
    }
  }, []);

  const fetchStorageStats = useCallback(async () => {
    setStorageLoading(true);
    try {
      const response = await api.diagnostics.getStorageStats();
      setStorageStats(response);
    } catch {
      // Non-critical
    } finally {
      setStorageLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDbStats();
    fetchStorageStats();
  }, [fetchDbStats, fetchStorageStats]);

  const handleCleanupPreview = async () => {
    setCleanupLoading(true);
    try {
      const result = await api.diagnostics.cleanup(cleanupDays, true);
      setCleanupResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to preview cleanup');
    } finally {
      setCleanupLoading(false);
    }
  };

  const handleCleanupExecute = async () => {
    setCleanupLoading(true);
    try {
      const result = await api.diagnostics.cleanup(cleanupDays, false);
      setCleanupResult(result);
      await Promise.all([fetchDbStats(), fetchStorageStats()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute cleanup');
    } finally {
      setCleanupLoading(false);
    }
  };

  return (
    <Box sx={{ width: '100%', maxWidth: '100%' }}>
      <Typography variant="h6" sx={{ mb: 3 }}>
        Data Management
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Stack spacing={3}>
        {/* Storage & Database Stats */}
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
          <Paper
            sx={{
              p: 3,
              bgcolor: 'background.paper',
              border: '1px solid',
              borderColor: 'divider',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <MemoryIcon color="primary" />
              <Typography variant="subtitle2" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>
                Database
              </Typography>
              {dbLoading && <CircularProgress size={14} />}
            </Box>
            <Divider sx={{ mb: 2 }} />

            {dbStats ? (
              <Stack spacing={1.5}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">Size</Typography>
                  <Typography variant="body2" fontWeight="medium">{dbStats.db_size_readable}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">Executions</Typography>
                  <Typography variant="body2" fontWeight="medium">{dbStats.execution_count}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">Step Results</Typography>
                  <Typography variant="body2" fontWeight="medium">{dbStats.step_result_count}</Typography>
                </Box>
                {dbStats.newest_execution && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Latest</Typography>
                    <Typography variant="body2">{new Date(dbStats.newest_execution).toLocaleDateString()}</Typography>
                  </Box>
                )}
              </Stack>
            ) : (
              <Typography variant="body2" color="text.secondary">Loading...</Typography>
            )}
          </Paper>

          <Paper
            sx={{
              p: 3,
              bgcolor: 'background.paper',
              border: '1px solid',
              borderColor: 'divider',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <StorageIcon color="primary" />
              <Typography variant="subtitle2" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>
                Screenshots
              </Typography>
              {storageLoading && <CircularProgress size={14} />}
            </Box>
            <Divider sx={{ mb: 2 }} />

            {storageStats ? (
              <Stack spacing={1.5}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">Size</Typography>
                  <Typography variant="body2" fontWeight="medium">{storageStats.total_size_readable}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">Files</Typography>
                  <Typography variant="body2" fontWeight="medium">{storageStats.file_count}</Typography>
                </Box>
                {storageStats.newest_screenshot && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Latest</Typography>
                    <Typography variant="body2">{new Date(storageStats.newest_screenshot).toLocaleDateString()}</Typography>
                  </Box>
                )}
              </Stack>
            ) : (
              <Typography variant="body2" color="text.secondary">Loading...</Typography>
            )}
          </Paper>
        </Box>

        {/* Cleanup Section */}
        <Paper
          sx={{
            p: 3,
            bgcolor: 'background.paper',
            border: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2, textTransform: 'uppercase', letterSpacing: 1 }}>
            Data Cleanup
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <TextField
              type="number"
              label="Delete data older than (days)"
              value={cleanupDays}
              onChange={(e) => setCleanupDays(parseInt(e.target.value, 10) || 30)}
              size="small"
              sx={{ width: 200 }}
              slotProps={{
                htmlInput: { min: 1, max: 365 }
              }}
            />
            <Button
              variant="outlined"
              startIcon={<ScheduleIcon />}
              onClick={() => {
                setCleanupResult(null);
                setCleanupDialog(true);
                handleCleanupPreview();
              }}
            >
              Preview Cleanup
            </Button>
          </Box>
        </Paper>
      </Stack>

      {/* Cleanup Dialog */}
      <Dialog open={cleanupDialog} onClose={() => setCleanupDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Data Cleanup</DialogTitle>
        <DialogContent>
          {cleanupLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : cleanupResult ? (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <Alert severity={cleanupResult.dry_run ? 'info' : 'success'}>
                {cleanupResult.dry_run
                  ? 'Preview: The following will be deleted'
                  : 'Cleanup completed successfully'}
              </Alert>

              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2" color="text.secondary">Executions to delete</Typography>
                <Typography variant="body2" fontWeight="medium">{cleanupResult.executions_deleted}</Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2" color="text.secondary">Screenshots to delete</Typography>
                <Typography variant="body2" fontWeight="medium">{cleanupResult.screenshots_deleted}</Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2" color="text.secondary">Space to free</Typography>
                <Typography variant="body2" fontWeight="medium">{cleanupResult.space_freed_readable}</Typography>
              </Box>
            </Stack>
          ) : (
            <Typography color="text.secondary">Loading preview...</Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCleanupDialog(false)}>Cancel</Button>
          {cleanupResult?.dry_run && (
            <Button
              variant="contained"
              color="error"
              startIcon={<DeleteIcon />}
              onClick={handleCleanupExecute}
              disabled={cleanupLoading || (cleanupResult.executions_deleted === 0 && cleanupResult.screenshots_deleted === 0)}
            >
              Delete Now
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
}

/**
 * LogsSection - Backend Logs viewer with filters
 */
export function LogsSection() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [logStats, setLogStats] = useState<LogStats | null>(null);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logLevel, setLogLevel] = useState<string>('');
  const [loggerFilter, setLoggerFilter] = useState<string>('');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const logsContainerRef = useRef<HTMLDivElement>(null);
  const autoRefreshRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchLogs = useCallback(async () => {
    setLogsLoading(true);
    try {
      const [logsResponse, statsResponse] = await Promise.all([
        api.logs.get({
          limit: 500,
          level: logLevel || undefined,
          logger_filter: loggerFilter || undefined,
        }),
        api.logs.getStats(),
      ]);
      setLogs(logsResponse.logs);
      setLogStats(statsResponse);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch logs');
    } finally {
      setLogsLoading(false);
    }
  }, [logLevel, loggerFilter]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  useEffect(() => {
    if (autoRefresh) {
      autoRefreshRef.current = setInterval(() => {
        fetchLogs();
      }, TIMING.UI.NOTIFICATION);
    } else {
      if (autoRefreshRef.current) {
        clearInterval(autoRefreshRef.current);
        autoRefreshRef.current = null;
      }
    }
    return () => {
      if (autoRefreshRef.current) {
        clearInterval(autoRefreshRef.current);
      }
    };
  }, [autoRefresh, fetchLogs]);

  const handleClearLogs = async () => {
    try {
      await api.logs.clear();
      await fetchLogs();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear logs');
    }
  };

  const handleExportLogs = () => {
    const logText = logs
      .map((log) => `[${log.timestamp}] [${log.level}] [${log.logger}] ${log.message}`)
      .join('\n');
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ignition-toolbox-logs-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Box sx={{ width: '100%', maxWidth: '100%' }}>
      <Typography variant="h6" sx={{ mb: 3 }}>
        Backend Logs
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Paper
        sx={{
          p: 3,
          bgcolor: 'background.paper',
          border: '1px solid',
          borderColor: 'divider',
        }}
      >
        {/* Log Controls */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Level</InputLabel>
            <Select
              value={logLevel}
              label="Level"
              onChange={(e) => setLogLevel(e.target.value)}
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="DEBUG">DEBUG</MenuItem>
              <MenuItem value="INFO">INFO</MenuItem>
              <MenuItem value="WARNING">WARNING</MenuItem>
              <MenuItem value="ERROR">ERROR</MenuItem>
            </Select>
          </FormControl>

          <TextField
            size="small"
            label="Logger Filter"
            value={loggerFilter}
            onChange={(e) => setLoggerFilter(e.target.value)}
            placeholder="e.g., playbook"
            sx={{ width: 180 }}
          />

          <Box sx={{ flex: 1 }} />

          {logStats && (
            <Chip label={`${logStats.total_captured} / ${logStats.max_entries}`} size="small" variant="outlined" />
          )}

          <Tooltip title={autoRefresh ? 'Stop auto-refresh' : 'Start auto-refresh (3s)'}>
            <IconButton
              size="small"
              onClick={() => setAutoRefresh(!autoRefresh)}
              color={autoRefresh ? 'primary' : 'default'}
            >
              {autoRefresh ? <PauseIcon /> : <PlayIcon />}
            </IconButton>
          </Tooltip>

          <Tooltip title="Refresh logs">
            <IconButton size="small" onClick={fetchLogs} disabled={logsLoading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title="Export logs">
            <IconButton size="small" onClick={handleExportLogs} disabled={logs.length === 0}>
              <DownloadIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title="Clear logs">
            <IconButton size="small" onClick={handleClearLogs} color="error">
              <ClearIcon />
            </IconButton>
          </Tooltip>
        </Box>

        <Divider sx={{ mb: 2 }} />

        {/* Log Level Stats */}
        {logStats && (
          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            {Object.entries(logStats.level_counts).map(([level, count]) => (
              <Chip
                key={level}
                label={`${level}: ${count}`}
                size="small"
                color={levelColors[level] || 'default'}
                variant={logLevel === level ? 'filled' : 'outlined'}
                onClick={() => setLogLevel(logLevel === level ? '' : level)}
                sx={{ cursor: 'pointer' }}
              />
            ))}
          </Box>
        )}

        {/* Logs Table */}
        <TableContainer
          ref={logsContainerRef}
          sx={{
            maxHeight: 500,
            bgcolor: 'background.default',
            borderRadius: 1,
          }}
        >
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell sx={{ width: 180 }}>Timestamp</TableCell>
                <TableCell sx={{ width: 80 }}>Level</TableCell>
                <TableCell sx={{ width: 200 }}>Logger</TableCell>
                <TableCell>Message</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {logs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} align="center" sx={{ py: 4 }}>
                    <Typography variant="body2" color="text.secondary">
                      No logs captured
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                logs.map((log, index) => (
                  <TableRow key={index} hover>
                    <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                      {new Date(log.timestamp).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={log.level}
                        size="small"
                        color={levelColors[log.level] || 'default'}
                        sx={{ fontWeight: 'bold', fontSize: '0.7rem' }}
                      />
                    </TableCell>
                    <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'text.secondary' }}>
                      {log.logger.split('.').pop()}
                    </TableCell>
                    <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem', wordBreak: 'break-word' }}>
                      {log.message}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Box>
  );
}

/**
 * Legacy export - renders all three sections together
 */
export function DiagnosticsPanel() {
  return (
    <Stack spacing={4}>
      <DiagnosticsSection />
      <DataManagementSection />
      <LogsSection />
    </Stack>
  );
}
