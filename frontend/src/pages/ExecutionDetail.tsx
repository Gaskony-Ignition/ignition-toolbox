/**
 * ExecutionDetail - Detailed view of a running/completed playbook execution
 *
 * Features:
 * - Split-pane layout: Step progress (left) + Live browser view (right)
 * - Execution controls (pause/resume/skip/stop)
 * - Real-time updates via WebSocket
 */

import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  Chip,
  List,
  ListItem,
  ListItemText,
  LinearProgress,
  Button,
  Divider,
  CircularProgress,
  Alert,
  Switch,
  FormControlLabel,
  Tooltip,
} from '@mui/material';
import {
  CheckCircle as CompletedIcon,
  Error as ErrorIcon,
  PlayArrow as RunningIcon,
  Pending as PendingIcon,
  Cancel as SkippedIcon,
  BugReport as DebugIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { LiveBrowserView } from '../components/LiveBrowserView';
import { ExecutionControls } from '../components/ExecutionControls';
import { DebugPanel } from '../components/DebugPanel';
import { PlaybookCodeViewer } from '../components/PlaybookCodeViewer';
import { useStore } from '../store';
import type { ExecutionStatusResponse } from '../types/api';

export function ExecutionDetail() {
  const { executionId } = useParams<{ executionId: string }>();
  const executionUpdates = useStore((state) => state.executionUpdates);
  const [debugMode, setDebugMode] = useState(false);
  const [debugModeUserOverride, setDebugModeUserOverride] = useState(false);
  const [debugModeToggling, setDebugModeToggling] = useState(false);
  const [showDebugPanel, setShowDebugPanel] = useState(false);
  const [showCodeViewer, setShowCodeViewer] = useState(false);
  const [runtime, setRuntime] = useState<string>('0s');

  // Fetch execution from API
  const { data: executionFromAPI, isLoading, error } = useQuery<ExecutionStatusResponse>({
    queryKey: ['execution', executionId],
    queryFn: () => api.executions.get(executionId!),
    enabled: !!executionId,
    refetchInterval: 2000, // Refetch every 2 seconds as fallback
  });

  if (!executionId) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography color="error">Invalid execution ID</Typography>
      </Box>
    );
  }

  // Use WebSocket update if available, otherwise use API data
  const wsUpdate = executionUpdates.get(executionId);
  const execution = wsUpdate || executionFromAPI;

  // Deduplicate step results by step_id (keep the most recent - completed over pending)
  const deduplicatedStepResults = execution?.step_results
    ? Array.from(
        execution.step_results.reduce((map, step) => {
          const existing = map.get(step.step_id);
          // Keep the step with higher priority: completed > running > failed > skipped > pending
          const priorityOrder = { completed: 5, running: 4, failed: 3, skipped: 2, pending: 1 };
          const existingPriority = existing ? priorityOrder[existing.status as keyof typeof priorityOrder] || 0 : 0;
          const newPriority = priorityOrder[step.status as keyof typeof priorityOrder] || 0;

          if (!existing || newPriority > existingPriority || (newPriority === existingPriority && step.completed_at)) {
            map.set(step.step_id, step);
          }
          return map;
        }, new Map()).values()
      )
    : [];

  // Sync debug mode from execution data (only if user hasn't manually overridden it)
  useEffect(() => {
    if (execution?.debug_mode !== undefined && !debugModeUserOverride) {
      setDebugMode(execution.debug_mode);
    }
  }, [execution?.debug_mode, debugModeUserOverride]);

  // Calculate and update runtime every second
  useEffect(() => {
    if (!execution?.started_at) {
      setRuntime('0s');
      return;
    }

    const calculateRuntime = () => {
      if (!execution.started_at) return '0s';
      const startTime = new Date(execution.started_at).getTime();
      const endTime = execution.completed_at
        ? new Date(execution.completed_at).getTime()
        : Date.now();
      const diffMs = endTime - startTime;

      const seconds = Math.floor(diffMs / 1000);
      const minutes = Math.floor(seconds / 60);
      const hours = Math.floor(minutes / 60);

      if (hours > 0) {
        return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
      } else if (minutes > 0) {
        return `${minutes}m ${seconds % 60}s`;
      } else {
        return `${seconds}s`;
      }
    };

    setRuntime(calculateRuntime());

    // Update timer every second if not completed
    if (execution.status !== 'completed' && execution.status !== 'failed' && execution.status !== 'cancelled') {
      const interval = setInterval(() => {
        setRuntime(calculateRuntime());
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [execution?.started_at, execution?.completed_at, execution?.status]);

  // Auto-show debug panel when execution is paused and debug mode is on
  // Look for a failed step in the results
  if (
    execution &&
    debugMode &&
    execution.status === 'running' &&
    deduplicatedStepResults.length > 0 &&
    deduplicatedStepResults.some((s) => s.status === 'failed')
  ) {
    if (!showDebugPanel) {
      setShowDebugPanel(true);
    }
  }

  if (isLoading) {
    return (
      <Box sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <CircularProgress size={20} />
        <Typography>Loading execution details...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          Failed to load execution: {(error as Error).message}
        </Alert>
      </Box>
    );
  }

  if (!execution) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">
          Execution not found
        </Alert>
      </Box>
    );
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CompletedIcon color="success" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      case 'running':
        return <RunningIcon color="primary" />;
      case 'cancelled':
        return <SkippedIcon color="disabled" />;
      case 'skipped':
        return <SkippedIcon color="warning" />;
      default:
        return <PendingIcon color="disabled" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'running':
        return 'primary';
      case 'cancelled':
        return 'default';
      case 'skipped':
        return 'warning';
      default:
        return 'default';
    }
  };

  const progress = deduplicatedStepResults.length > 0
    ? (deduplicatedStepResults.filter((s) => s.status === 'completed').length /
        deduplicatedStepResults.length) *
      100
    : 0;

  return (
    <Box sx={{
      position: 'fixed',
      left: 240, // Drawer width
      right: 0,
      top: 64, // AppBar height
      bottom: 0,
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      bgcolor: 'background.default',
    }}>
      {/* Header */}
      <Paper
        elevation={1}
        sx={{
          p: 1,
          borderRadius: 0,
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          flexShrink: 0,
        }}
      >
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="subtitle1" sx={{ fontSize: '0.95rem', fontWeight: 600, lineHeight: 1.3 }}>
            {execution.playbook_name}
            <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 1.5, fontSize: '0.7rem', fontFamily: 'monospace' }}>
              ID: {executionId}
            </Typography>
          </Typography>
        </Box>

        <Chip
          label={execution.status}
          color={getStatusColor(execution.status) as any}
          size="small"
          sx={{ height: '24px', fontSize: '0.7rem' }}
        />

        <Tooltip title={debugModeToggling ? "Updating debug mode..." : "Auto-pause after each step for debugging"}>
          <FormControlLabel
            control={
              <Switch
                checked={debugMode}
                disabled={debugModeToggling}
                onChange={async (e) => {
                  const enabled = e.target.checked;
                  setDebugMode(enabled);
                  setDebugModeUserOverride(true);
                  setDebugModeToggling(true);
                  try {
                    if (enabled) {
                      await api.executions.enableDebug(executionId);
                    } else {
                      await api.executions.disableDebug(executionId);
                      // If currently paused, resume execution when debug mode is turned off
                      if (execution.status === 'paused') {
                        await api.executions.resume(executionId);
                      }
                    }
                    // Clear override after 10 seconds to allow WebSocket sync (increased from 3s)
                    setTimeout(() => {
                      setDebugModeUserOverride(false);
                      setDebugModeToggling(false);
                    }, 10000);
                  } catch (error) {
                    console.error('Failed to toggle debug mode:', error);
                    alert(`Failed to toggle debug mode: ${error instanceof Error ? error.message : String(error)}`);
                    // Revert on error
                    setDebugMode(!enabled);
                    setDebugModeUserOverride(false);
                    setDebugModeToggling(false);
                  }
                }}
                size="small"
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <DebugIcon fontSize="small" />
                <Typography variant="body2">
                  Debug {debugModeToggling && '(updating...)'}
                </Typography>
              </Box>
            }
          />
        </Tooltip>

        {/* View Code Button - Only show when debug mode or paused */}
        {(debugMode || execution.status === 'paused') && (
          <Tooltip title={showCodeViewer ? "Hide playbook code" : "View playbook code"}>
            <Button
              variant="outlined"
              size="small"
              startIcon={showCodeViewer ? <VisibilityOffIcon /> : <VisibilityIcon />}
              onClick={() => setShowCodeViewer(!showCodeViewer)}
              sx={{ ml: 1 }}
            >
              Code
            </Button>
          </Tooltip>
        )}

        <ExecutionControls
          executionId={executionId}
          status={execution.status}
          debugMode={debugMode}
        />
      </Paper>

      {/* Progress Bar */}
      {execution.status === 'running' && (
        <Box sx={{ px: 2, py: 1, flexShrink: 0 }}>
          <LinearProgress variant="determinate" value={progress} />
          <Typography variant="caption" color="text.secondary">
            Progress: {Math.round(progress)}%
          </Typography>
        </Box>
      )}

      {/* Split Pane */}
      <Box
        sx={{
          flexGrow: 1,
          display: 'grid',
          gridTemplateColumns: '1fr 2fr',
          gap: 2,
          p: 2,
          overflow: 'hidden',
          minHeight: 0, // Important for proper flex sizing
        }}
      >
        {/* Left: Step Progress */}
        <Paper elevation={2} sx={{ overflow: 'auto' }}>
          <Box
            sx={{
              p: 2,
              borderBottom: 1,
              borderColor: 'divider',
              position: 'sticky',
              top: 0,
              bgcolor: 'background.paper',
              zIndex: 1,
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">Step Progress</Typography>
              <Chip
                label={`Runtime: ${runtime}`}
                size="small"
                color={execution.status === 'running' ? 'primary' : 'default'}
                sx={{ fontWeight: 'bold', fontFamily: 'monospace' }}
              />
            </Box>
            <Typography variant="caption" color="text.secondary">
              {execution.current_step_index !== undefined
                ? `Current step: ${execution.current_step_index + 1} of ${execution.total_steps}`
                : 'Initializing...'}
            </Typography>
          </Box>

          <List sx={{ py: 0 }}>
            {deduplicatedStepResults.length > 0 ? (
              deduplicatedStepResults.map((step, index) => (
                <Box key={step.step_id || index}>
                  <ListItem
                    sx={{
                      py: 0.5,
                      px: 1,
                      minHeight: '36px',
                      bgcolor:
                        index === execution.current_step_index
                          ? 'action.selected'
                          : 'transparent',
                    }}
                  >
                    <Box sx={{ mr: 1, display: 'flex', alignItems: 'center', fontSize: '1rem' }}>{getStatusIcon(step.status)}</Box>
                    <ListItemText
                      primary={step.step_name || `Step ${index + 1}`}
                      secondary={
                        <>
                          {step.error ? (
                            <Typography variant="caption" color="error" sx={{ fontSize: '0.65rem' }}>
                              Error: {step.error}
                            </Typography>
                          ) : step.completed_at ? (
                            `Completed at ${new Date(
                              step.completed_at
                            ).toLocaleTimeString()}`
                          ) : (
                            step.status
                          )}
                          {/* Display python script output if available */}
                          {step.output && step.output._output && (
                            <Typography
                              variant="caption"
                              component="pre"
                              sx={{
                                fontSize: '0.7rem',
                                fontFamily: 'monospace',
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word',
                                mt: 1,
                                p: 1,
                                bgcolor: 'rgba(0, 255, 0, 0.05)',
                                borderRadius: 1,
                                border: '1px solid rgba(0, 255, 0, 0.2)',
                                color: '#00ff00',
                                maxHeight: '400px',
                                overflow: 'auto',
                                display: 'block',
                              }}
                            >
                              {step.output._output}
                            </Typography>
                          )}
                        </>
                      }
                      primaryTypographyProps={{ variant: 'body2', fontSize: '0.8rem' }}
                      secondaryTypographyProps={{ variant: 'caption', fontSize: '0.7rem' }}
                    />
                    <Chip
                      label={step.status}
                      size="small"
                      color={getStatusColor(step.status) as any}
                      sx={{ height: '20px', fontSize: '0.65rem', '& .MuiChip-label': { px: 1, py: 0 } }}
                    />
                  </ListItem>
                  {index < deduplicatedStepResults.length - 1 && <Divider />}
                </Box>
              ))
            ) : (
              <ListItem sx={{ py: 1 }}>
                <ListItemText primary="No steps executed yet" primaryTypographyProps={{ variant: 'body2', fontSize: '0.8rem' }} />
              </ListItem>
            )}
          </List>
        </Paper>

        {/* Middle: Live Browser View OR Debug Panel OR Placeholder */}
        {showDebugPanel ? (
          <DebugPanel executionId={executionId} />
        ) : execution?.domain === 'perspective' || execution?.domain === 'gateway' || execution?.domain === null ? (
          <LiveBrowserView executionId={executionId} />
        ) : (
          <Paper
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              bgcolor: '#2a2a2a',
              borderRadius: 1,
              minHeight: '400px',
            }}
          >
            <VisibilityOffIcon sx={{ fontSize: 48, color: '#666', mb: 2 }} />
            <Typography variant="h6" sx={{ color: '#999' }}>
              No browser view available for this playbook
            </Typography>
            <Typography variant="body2" sx={{ color: '#666', mt: 1 }}>
              Domain: {execution?.domain || 'unknown'}
            </Typography>
          </Paper>
        )}
      </Box>

      {/* Playbook Code Viewer Dialog */}
      <PlaybookCodeViewer
        open={showCodeViewer}
        executionId={executionId}
        playbookName={execution.playbook_name}
        isDebugMode={debugMode}
        isPaused={execution.status === 'paused'}
        onClose={() => setShowCodeViewer(false)}
      />
    </Box>
  );
}
