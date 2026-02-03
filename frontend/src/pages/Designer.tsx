/**
 * Designer page - CloudDesigner integration + Designer playbooks
 *
 * Provides browser-based Ignition Designer access via Docker/Guacamole
 * along with Designer-specific playbooks.
 */

import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Alert,
  CircularProgress,
  Stack,
  Chip,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from '@mui/material';
import {
  PlayArrow as StartIcon,
  Stop as StopIcon,
  OpenInNew as OpenIcon,
  CheckCircle as RunningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  ExpandMore as ExpandMoreIcon,
  Refresh as RefreshIcon,
  DeleteForever as CleanupIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { useStore } from '../store';
import { Playbooks } from './Playbooks';
import type { DockerStatus, CloudDesignerStatus } from '../types/api';

export function Designer() {
  const queryClient = useQueryClient();
  const selectedCredential = useStore((state) => state.selectedCredential);
  const [startError, setStartError] = useState<string | null>(null);
  const [showDebug, setShowDebug] = useState(false);
  const [showCleanupConfirm, setShowCleanupConfirm] = useState(false);

  // Query Docker status
  const {
    data: dockerStatus,
    isLoading: dockerLoading,
    error: dockerError,
    refetch: refetchDocker,
  } = useQuery<DockerStatus>({
    queryKey: ['clouddesigner-docker'],
    queryFn: api.cloudDesigner.getDockerStatus,
    refetchInterval: 30000, // Check every 30s
  });

  // Query container status
  const {
    data: containerStatus,
    isLoading: containerLoading,
  } = useQuery<CloudDesignerStatus>({
    queryKey: ['clouddesigner-status'],
    queryFn: api.cloudDesigner.getStatus,
    refetchInterval: 5000, // Poll every 5s when running
    enabled: dockerStatus?.running === true,
  });

  // Start mutation - pass both gateway URL and credential name for auto-login
  const startMutation = useMutation({
    mutationFn: ({ gatewayUrl, credentialName }: { gatewayUrl: string; credentialName?: string }) =>
      api.cloudDesigner.start(gatewayUrl, credentialName),
    onSuccess: (data) => {
      if (!data.success) {
        setStartError(data.error || 'Failed to start CloudDesigner');
      } else {
        setStartError(null);
      }
      // Refresh status
      queryClient.invalidateQueries({ queryKey: ['clouddesigner-status'] });
    },
    onError: (error: Error) => {
      setStartError(error.message);
    },
  });

  // Query recent logs for debugging - also poll while starting (must be after startMutation)
  const { data: logsData, refetch: refetchLogs } = useQuery({
    queryKey: ['docker-detection-logs'],
    queryFn: () => api.logs.get({ limit: 500 }),
    enabled: showDebug || startMutation.isPending,
    refetchInterval: startMutation.isPending ? 1500 : false, // Poll every 1.5s while starting
  });

  // Stop mutation
  const stopMutation = useMutation({
    mutationFn: () => api.cloudDesigner.stop(),
    onSuccess: () => {
      setStartError(null);
      // Refresh status
      queryClient.invalidateQueries({ queryKey: ['clouddesigner-status'] });
    },
    onError: (error: Error) => {
      setStartError(error.message);
    },
  });

  // Cleanup mutation - forcefully removes all containers, volumes, and images
  const cleanupMutation = useMutation({
    mutationFn: () => api.cloudDesigner.cleanup(),
    onSuccess: (data) => {
      if (data.success) {
        setStartError(null);
      } else {
        setStartError(data.error || 'Cleanup failed');
      }
      // Refresh status
      queryClient.invalidateQueries({ queryKey: ['clouddesigner-status'] });
    },
    onError: (error: Error) => {
      setStartError(error.message);
    },
  });

  // Handle start button click
  const handleStart = () => {
    if (selectedCredential?.gateway_url) {
      setStartError(null);
      startMutation.mutate({
        gatewayUrl: selectedCredential.gateway_url,
        credentialName: selectedCredential.name,
      });
    }
  };

  // Handle open designer in browser
  const handleOpenDesigner = async () => {
    // Use /connect endpoint for auto-login to Guacamole
    const url = 'http://localhost:8080/connect';

    // In Electron, use the IPC API which handles WSL2 properly
    if (window.electronAPI?.openExternal) {
      try {
        await window.electronAPI.openExternal(url);
      } catch (error) {
        console.error('Failed to open URL:', error);
        // Fallback: copy to clipboard
        navigator.clipboard.writeText(url).catch(() => {});
        setStartError(`Could not open browser. Please navigate to: ${url}`);
      }
    } else {
      // Non-Electron: use window.open
      window.open(url, '_blank');
    }
  };

  // Determine if container is running
  const isRunning = containerStatus?.status === 'running';
  const isStarting = startMutation.isPending;
  const isStopping = stopMutation.isPending;
  const isCleaning = cleanupMutation.isPending;

  // Auto-expand debug panel when starting to show progress
  useEffect(() => {
    if (isStarting) {
      setShowDebug(true);
    }
  }, [isStarting]);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* CloudDesigner Section */}
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box>
            <Typography variant="h6" sx={{ mb: 0.5 }}>
              Browser-Based Designer
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Launch Ignition Designer in a Docker container accessible via your browser
            </Typography>
          </Box>

          {/* Status indicator */}
          {dockerStatus?.running && (
            <Chip
              icon={isRunning ? <RunningIcon /> : <InfoIcon />}
              label={isRunning ? 'Running' : containerStatus?.status || 'Stopped'}
              color={isRunning ? 'success' : 'default'}
              size="small"
            />
          )}
        </Box>

        {/* Loading state */}
        {(dockerLoading || containerLoading) && !dockerStatus && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <CircularProgress size={20} />
            <Typography variant="body2" color="text.secondary">
              Checking Docker status...
            </Typography>
          </Box>
        )}

        {/* Docker error */}
        {dockerError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Failed to check Docker status: {(dockerError as Error).message}
          </Alert>
        )}

        {/* Docker not installed */}
        {dockerStatus && !dockerStatus.installed && (
          <Box>
            <Alert severity="warning" icon={<ErrorIcon />} sx={{ mb: 2 }}>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                Docker is not installed or not detected
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Install Docker Desktop to use the browser-based Designer.
                Visit <a href="https://www.docker.com/products/docker-desktop" target="_blank" rel="noopener noreferrer">docker.com</a> to download.
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                If Docker is installed in WSL, make sure WSL is running and Docker daemon is started inside WSL.
                {dockerStatus.docker_path && ` (Detected: ${dockerStatus.docker_path})`}
              </Typography>
            </Alert>

            {/* Debug section */}
            <Accordion
              expanded={showDebug}
              onChange={() => {
                setShowDebug(!showDebug);
                if (!showDebug) refetchLogs();
              }}
              sx={{ bgcolor: 'background.paper' }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="body2" color="text.secondary">
                  Troubleshooting & Debug Info
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Stack spacing={2}>
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>Detection Status</Typography>
                    <Typography variant="body2" component="pre" sx={{
                      fontFamily: 'monospace',
                      fontSize: '0.75rem',
                      bgcolor: 'action.hover',
                      p: 1,
                      borderRadius: 1,
                      overflow: 'auto'
                    }}>
{`Installed: ${dockerStatus.installed}
Running: ${dockerStatus.running}
Version: ${dockerStatus.version || 'Not detected'}
Path: ${dockerStatus.docker_path || 'Not found'}`}
                    </Typography>
                  </Box>

                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="subtitle2">Recent Backend Logs</Typography>
                      <Stack direction="row" spacing={1}>
                        <Tooltip title="Refresh logs">
                          <IconButton size="small" onClick={() => refetchLogs()}>
                            <RefreshIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Re-check Docker">
                          <IconButton size="small" onClick={() => refetchDocker()}>
                            <RefreshIcon fontSize="small" color="primary" />
                          </IconButton>
                        </Tooltip>
                      </Stack>
                    </Box>
                    <Box sx={{
                      fontFamily: 'monospace',
                      fontSize: '0.7rem',
                      bgcolor: 'grey.900',
                      color: 'grey.300',
                      p: 1,
                      borderRadius: 1,
                      maxHeight: 300,
                      overflow: 'auto'
                    }}>
                      {logsData?.logs?.slice(0, 100).map((log: { timestamp: string; level: string; message: string }, i: number) => {
                        const isRelevant = log.message.toLowerCase().includes('docker') ||
                          log.message.toLowerCase().includes('wsl') ||
                          log.message.toLowerCase().includes('clouddesigner') ||
                          log.message.toLowerCase().includes('compose');
                        return (
                          <Box key={i} sx={{ mb: 0.5, opacity: isRelevant ? 1 : 0.5 }}>
                            <Typography component="span" sx={{ color: 'grey.500', fontSize: 'inherit' }}>
                              {new Date(log.timestamp).toLocaleTimeString()}
                            </Typography>
                            {' '}
                            <Typography component="span" sx={{ color: log.level === 'ERROR' ? 'error.main' : log.level === 'WARNING' ? 'warning.main' : 'info.main', fontSize: 'inherit' }}>
                              [{log.level}]
                            </Typography>
                            {' '}{log.message}
                          </Box>
                        );
                      }) || <Typography variant="body2" color="text.secondary">No logs found. Click refresh to re-check.</Typography>}
                    </Box>
                  </Box>

                  <Alert severity="info" sx={{ fontSize: '0.75rem' }}>
                    <Typography variant="body2" sx={{ fontSize: 'inherit' }}>
                      <strong>WSL Users:</strong> Open a WSL terminal and run these commands:
                    </Typography>
                    <Typography component="pre" sx={{ fontFamily: 'monospace', fontSize: 'inherit', mt: 1 }}>
{`# Check if Docker is installed in WSL
docker --version

# Start Docker daemon if not running
sudo service docker start

# Verify Docker is working
docker info`}
                    </Typography>
                  </Alert>
                </Stack>
              </AccordionDetails>
            </Accordion>
          </Box>
        )}

        {/* Docker not running */}
        {dockerStatus && dockerStatus.installed && !dockerStatus.running && (
          <Alert severity="warning" icon={<ErrorIcon />}>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              Docker is not running
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Start Docker Desktop to use the browser-based Designer.
            </Typography>
          </Alert>
        )}

        {/* Docker running - show controls */}
        {dockerStatus?.running && (
          <Box>
            {/* Start error */}
            {startError && (
              <Alert severity="error" sx={{ mb: 2 }} onClose={() => setStartError(null)}>
                {startError}
              </Alert>
            )}

            {/* No credential selected */}
            {!selectedCredential?.gateway_url && !isRunning && (
              <Alert severity="info" sx={{ mb: 2 }}>
                Select a credential with a gateway URL from the header dropdown to start the Designer container.
              </Alert>
            )}

            {/* Starting progress indicator */}
            {isStarting && (
              <Alert severity="info" sx={{ mb: 2 }}>
                <Typography variant="body2" sx={{ fontWeight: 500, mb: 1 }}>
                  Starting CloudDesigner...
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  This may take several minutes on first run while Docker images are built.
                  The process includes: cleanup → build → start containers.
                </Typography>
              </Alert>
            )}

            {/* Control buttons */}
            <Stack direction="row" spacing={2} alignItems="center">
              {isRunning ? (
                <>
                  <Button
                    variant="contained"
                    color="primary"
                    startIcon={<OpenIcon />}
                    onClick={handleOpenDesigner}
                    size="large"
                  >
                    Open Designer
                  </Button>
                  <Button
                    variant="outlined"
                    color="error"
                    startIcon={isStopping ? <CircularProgress size={16} /> : <StopIcon />}
                    onClick={() => stopMutation.mutate()}
                    disabled={isStopping}
                    size="large"
                  >
                    {isStopping ? 'Stopping...' : 'Stop Container'}
                  </Button>
                  <Typography variant="body2" color="text.secondary">
                    Or open directly:{' '}
                    <a
                      href="http://localhost:8080/connect"
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: 'inherit' }}
                    >
                      http://localhost:8080/connect
                    </a>
                  </Typography>
                </>
              ) : (
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={isStarting ? <CircularProgress size={16} color="inherit" /> : <StartIcon />}
                  onClick={handleStart}
                  disabled={!selectedCredential?.gateway_url || isStarting}
                  size="large"
                >
                  {isStarting ? 'Starting Container...' : 'Start Designer Container'}
                </Button>
              )}
            </Stack>

            {/* Docker version info */}
            {dockerStatus.version && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
                {dockerStatus.version}
                {dockerStatus.docker_path && ` (${dockerStatus.docker_path})`}
              </Typography>
            )}

            {/* Debug section - also available when Docker is running for troubleshooting */}
            <Accordion
              expanded={showDebug}
              onChange={() => {
                setShowDebug(!showDebug);
                if (!showDebug) refetchLogs();
              }}
              sx={{ mt: 2, bgcolor: 'background.paper' }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="body2" color="text.secondary">
                  Troubleshooting & Logs
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Stack spacing={2}>
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>Docker Status</Typography>
                    <Typography variant="body2" component="pre" sx={{
                      fontFamily: 'monospace',
                      fontSize: '0.75rem',
                      bgcolor: 'action.hover',
                      p: 1,
                      borderRadius: 1,
                      overflow: 'auto'
                    }}>
{`Installed: ${dockerStatus.installed}
Running: ${dockerStatus.running}
Version: ${dockerStatus.version || 'Not detected'}
Path: ${dockerStatus.docker_path || 'Not found'}
Container: ${containerStatus?.status || 'not_created'}`}
                    </Typography>
                  </Box>

                  {/* Cleanup Button */}
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>Container Cleanup</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      If containers are in a bad state or causing conflicts, use this to forcefully clean up everything.
                    </Typography>
                    <Button
                      variant="outlined"
                      color="warning"
                      size="small"
                      startIcon={isCleaning ? <CircularProgress size={14} /> : <CleanupIcon />}
                      onClick={() => setShowCleanupConfirm(true)}
                      disabled={isCleaning || isStarting}
                    >
                      {isCleaning ? 'Cleaning up...' : 'Clean Up Containers'}
                    </Button>
                  </Box>

                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="subtitle2">Recent CloudDesigner Logs</Typography>
                      <Tooltip title="Refresh logs">
                        <IconButton size="small" onClick={() => refetchLogs()}>
                          <RefreshIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                    <Box sx={{
                      fontFamily: 'monospace',
                      fontSize: '0.7rem',
                      bgcolor: 'grey.900',
                      color: 'grey.300',
                      p: 1,
                      borderRadius: 1,
                      maxHeight: 300,
                      overflow: 'auto'
                    }}>
                      {logsData?.logs?.slice(0, 100).map((log: { timestamp: string; level: string; message: string }, i: number) => {
                        const isRelevant = log.message.toLowerCase().includes('docker') ||
                          log.message.toLowerCase().includes('wsl') ||
                          log.message.toLowerCase().includes('clouddesigner') ||
                          log.message.toLowerCase().includes('compose');
                        return (
                          <Box key={i} sx={{ mb: 0.5, opacity: isRelevant ? 1 : 0.5 }}>
                            <Typography component="span" sx={{ color: 'grey.500', fontSize: 'inherit' }}>
                              {new Date(log.timestamp).toLocaleTimeString()}
                            </Typography>
                            {' '}
                            <Typography component="span" sx={{ color: log.level === 'ERROR' ? 'error.main' : log.level === 'WARNING' ? 'warning.main' : 'info.main', fontSize: 'inherit' }}>
                              [{log.level}]
                            </Typography>
                            {' '}{log.message}
                          </Box>
                        );
                      }) || <Typography variant="body2" color="text.secondary">No logs found. Click refresh to update.</Typography>}
                    </Box>
                  </Box>
                </Stack>
              </AccordionDetails>
            </Accordion>
          </Box>
        )}
      </Paper>

      <Divider />

      {/* Designer Playbooks Section */}
      <Playbooks domainFilter="designer" />

      {/* Cleanup Confirmation Dialog */}
      <Dialog
        open={showCleanupConfirm}
        onClose={() => setShowCleanupConfirm(false)}
      >
        <DialogTitle>Clean Up CloudDesigner?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This will forcefully remove all CloudDesigner containers, volumes, networks, and cached images.
            Any unsaved work in the Designer will be lost and images will need to be rebuilt on next start.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCleanupConfirm(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              setShowCleanupConfirm(false);
              cleanupMutation.mutate();
            }}
            color="warning"
            variant="contained"
            autoFocus
          >
            Clean Up
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
