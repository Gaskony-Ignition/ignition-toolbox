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
  Download as DownloadIcon,
  Build as BuildIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { useStore } from '../store';
import { Playbooks } from './Playbooks';
import type { DockerStatus, CloudDesignerStatus } from '../types/api';
import { createLogger } from '../utils/logger';

const logger = createLogger('Designer');

export function Designer() {
  const queryClient = useQueryClient();
  const selectedCredential = useStore((state) => state.selectedCredential);
  const [startError, setStartError] = useState<string | null>(null);
  const [showDebug, setShowDebug] = useState(false);
  const [showCleanupConfirm, setShowCleanupConfirm] = useState(false);

  // Debug logging for credential state
  useEffect(() => {
    logger.debug('[Designer] Component mounted/updated');
    logger.debug('[Designer] selectedCredential:', selectedCredential);
    logger.debug('[Designer] gateway_url:', selectedCredential?.gateway_url);
  }, [selectedCredential]);

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
    mutationFn: async ({ gatewayUrl, credentialName, forceRebuild }: { gatewayUrl: string; credentialName?: string; forceRebuild?: boolean }) => {
      logger.debug('[CloudDesigner] Calling API start with:', { gatewayUrl, credentialName, forceRebuild });
      const result = await api.cloudDesigner.start(gatewayUrl, credentialName, forceRebuild);
      logger.debug('[CloudDesigner] API start result:', result);
      return result;
    },
    onSuccess: (data) => {
      logger.debug('[CloudDesigner] onSuccess:', data);
      if (!data.success) {
        setStartError(data.error || 'Failed to start CloudDesigner');
      } else {
        setStartError(null);
      }
      // Refresh status
      queryClient.invalidateQueries({ queryKey: ['clouddesigner-status'] });
    },
    onError: (error: Error) => {
      logger.error('[CloudDesigner] onError:', error);
      setStartError(error.message);
    },
  });

  // Query image status - check which Docker images are available
  const {
    data: imageStatus,
    isLoading: imageStatusLoading,
    refetch: refetchImageStatus,
  } = useQuery<{
    images: Record<string, { exists: boolean; source: string }>;
    all_ready: boolean;
  }>({
    queryKey: ['clouddesigner-images'],
    queryFn: api.cloudDesigner.getImageStatus,
    refetchInterval: false, // Only refresh on demand
    enabled: dockerStatus?.running === true,
  });

  // Prepare mutation - pull base images and build designer-desktop
  const prepareMutation = useMutation({
    mutationFn: async (forceRebuild: boolean = false) => {
      logger.debug('[CloudDesigner] Preparing images, forceRebuild:', forceRebuild);
      return api.cloudDesigner.prepare(forceRebuild);
    },
    onSuccess: (data) => {
      if (!data.success) {
        setStartError(data.error || 'Failed to prepare images');
      } else {
        setStartError(null);
      }
      // Refresh image status after prepare
      queryClient.invalidateQueries({ queryKey: ['clouddesigner-images'] });
    },
    onError: (error: Error) => {
      setStartError(error.message);
      // Refresh image status even on error (partial progress may have been made)
      queryClient.invalidateQueries({ queryKey: ['clouddesigner-images'] });
    },
  });

  // Query all container statuses - for debug panel
  const { data: allStatuses, refetch: refetchAllStatuses } = useQuery<{ statuses: Record<string, string> }>({
    queryKey: ['clouddesigner-all-statuses'],
    queryFn: api.cloudDesigner.getAllStatuses,
    enabled: showDebug && dockerStatus?.running === true,
    refetchInterval: showDebug ? 5000 : false,
  });

  // Query recent logs for debugging - also poll while starting or preparing (must be after mutations)
  const { data: logsData, refetch: refetchLogs } = useQuery({
    queryKey: ['docker-detection-logs'],
    queryFn: () => api.logs.get({ limit: 500 }),
    enabled: showDebug || startMutation.isPending || prepareMutation.isPending,
    refetchInterval: (startMutation.isPending || prepareMutation.isPending) ? 1500 : false,
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
      // Refresh status and image status
      queryClient.invalidateQueries({ queryKey: ['clouddesigner-status'] });
      queryClient.invalidateQueries({ queryKey: ['clouddesigner-images'] });
    },
    onError: (error: Error) => {
      setStartError(error.message);
    },
  });

  // Handle start button click
  const handleStart = (forceRebuild: boolean = false) => {
    logger.debug('[CloudDesigner] handleStart called', { forceRebuild });
    logger.debug('[CloudDesigner] selectedCredential:', selectedCredential);
    if (selectedCredential?.gateway_url) {
      logger.debug('[CloudDesigner] Starting with gateway:', selectedCredential.gateway_url);
      setStartError(null);
      startMutation.mutate({
        gatewayUrl: selectedCredential.gateway_url,
        credentialName: selectedCredential.name,
        forceRebuild,
      });
    } else {
      logger.debug('[CloudDesigner] No gateway URL - cannot start');
      setStartError('No gateway URL configured in selected credential');
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
        logger.error('Failed to open URL:', error);
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
  const isPreparing = prepareMutation.isPending;
  const imagesReady = imageStatus?.all_ready === true;

  // Auto-expand debug panel when starting or preparing to show progress
  useEffect(() => {
    if (isStarting || isPreparing) {
      setShowDebug(true);
    }
  }, [isStarting, isPreparing]);

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

          {/* Status indicator + credential info */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {selectedCredential && (
              <Chip
                label={`${selectedCredential.name}${selectedCredential.gateway_url ? ` (${new URL(selectedCredential.gateway_url).hostname})` : ''}`}
                size="small"
                variant="outlined"
                color="primary"
              />
            )}
            {dockerStatus?.running && (
              <Chip
                icon={isRunning ? <RunningIcon /> : <InfoIcon />}
                label={isRunning ? 'Running' : containerStatus?.status || 'Stopped'}
                color={isRunning ? 'success' : 'default'}
                size="small"
              />
            )}
          </Box>
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
                      <Typography variant="subtitle2">Docker Detection Logs</Typography>
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
                      maxHeight: 400,
                      overflow: 'auto'
                    }}>
                      {(() => {
                        // Filter to Docker-related logs for troubleshooting
                        const relevantLogs = logsData?.logs?.filter((log: { message: string }) => {
                          const msg = log.message.toLowerCase();
                          return msg.includes('docker') ||
                            msg.includes('wsl') ||
                            msg.includes('clouddesigner') ||
                            msg.includes('compose');
                        }) || [];

                        if (relevantLogs.length === 0) {
                          return <Typography variant="body2" color="text.secondary">No Docker-related logs found. Click Re-check Docker above.</Typography>;
                        }

                        return relevantLogs.slice(0, 200).map((log: { timestamp: string; level: string; message: string }, i: number) => (
                          <Box key={i} sx={{ mb: 0.5 }}>
                            <Typography component="span" sx={{ color: 'grey.500', fontSize: 'inherit' }}>
                              {new Date(log.timestamp).toLocaleTimeString()}
                            </Typography>
                            {' '}
                            <Typography component="span" sx={{ color: log.level === 'ERROR' ? 'error.main' : log.level === 'WARNING' ? 'warning.main' : 'info.main', fontSize: 'inherit' }}>
                              [{log.level}]
                            </Typography>
                            {' '}{log.message}
                          </Box>
                        ));
                      })()}
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

        {/* Docker running - show multi-stage controls */}
        {dockerStatus?.running && (
          <Box>
            {/* Start error */}
            {startError && (
              <Alert severity="error" sx={{ mb: 2 }} onClose={() => setStartError(null)}>
                {startError}
              </Alert>
            )}

            {/* Container status error (from polling) */}
            {!startError && containerStatus?.error && !isRunning && (
              <Alert
                severity="warning"
                sx={{ mb: 2 }}
                action={
                  (containerStatus.status === 'restarting' || containerStatus.status === 'exited' || containerStatus.status === 'created') ? (
                    <Stack direction="row" spacing={1}>
                      <Button
                        color="inherit"
                        size="small"
                        onClick={() => stopMutation.mutate()}
                        disabled={isStopping}
                        startIcon={<StopIcon />}
                      >
                        {isStopping ? 'Stopping...' : 'Stop'}
                      </Button>
                      <Button
                        color="inherit"
                        size="small"
                        onClick={() => setShowCleanupConfirm(true)}
                        startIcon={<CleanupIcon />}
                      >
                        Cleanup
                      </Button>
                    </Stack>
                  ) : undefined
                }
              >
                {containerStatus.status === 'restarting'
                  ? 'Container is crash-looping. Stop or cleanup the containers to resolve.'
                  : containerStatus.error}
              </Alert>
            )}

            {/* ===== STAGE 1: Image Readiness ===== */}
            {!isRunning && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Step 1: Docker Images
                </Typography>

                {imageStatusLoading && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <CircularProgress size={16} />
                    <Typography variant="body2" color="text.secondary">
                      Checking image status...
                    </Typography>
                  </Box>
                )}

                {imageStatus && (
                  <Box sx={{ mb: 2 }}>
                    {/* Per-image status chips */}
                    <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mb: 1.5 }}>
                      {Object.entries(imageStatus.images).map(([name, info]) => (
                        <Chip
                          key={name}
                          icon={info.exists ? <RunningIcon /> : <ErrorIcon />}
                          label={`${name.split('/').pop()?.split(':')[0] || name} ${info.exists ? '(ready)' : info.source === 'build' ? '(needs build)' : '(needs download)'}`}
                          color={info.exists ? 'success' : 'default'}
                          variant={info.exists ? 'filled' : 'outlined'}
                          size="small"
                        />
                      ))}
                      <Tooltip title="Re-check image status">
                        <IconButton size="small" onClick={() => refetchImageStatus()}>
                          <RefreshIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Stack>

                    {/* Summary and action */}
                    {imagesReady ? (
                      <Box>
                        <Alert severity="success" sx={{ py: 0.5, mb: 1 }}>
                          All Docker images are ready. You can start the Designer.
                        </Alert>
                        <Button
                          variant="outlined"
                          color="primary"
                          startIcon={isPreparing ? <CircularProgress size={14} /> : <BuildIcon />}
                          onClick={() => prepareMutation.mutate(true)}
                          disabled={isPreparing}
                          size="small"
                        >
                          {isPreparing ? 'Rebuilding...' : 'Force Rebuild Image'}
                        </Button>
                      </Box>
                    ) : (
                      <Box>
                        <Alert severity="info" sx={{ py: 0.5, mb: 1.5 }}>
                          Some images need to be downloaded or built before starting.
                        </Alert>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <Button
                            variant="contained"
                            color="primary"
                            startIcon={isPreparing ? <CircularProgress size={16} color="inherit" /> : <DownloadIcon />}
                            onClick={() => prepareMutation.mutate(false)}
                            disabled={isPreparing}
                          >
                            {isPreparing ? 'Preparing Images...' : 'Download & Build Images'}
                          </Button>
                          <Button
                            variant="outlined"
                            color="primary"
                            startIcon={isPreparing ? <CircularProgress size={14} /> : <BuildIcon />}
                            onClick={() => prepareMutation.mutate(true)}
                            disabled={isPreparing}
                            size="small"
                          >
                            Force Rebuild
                          </Button>
                        </Stack>
                      </Box>
                    )}

                    {/* Preparing progress */}
                    {isPreparing && (
                      <Alert severity="info" sx={{ mt: 1.5 }}>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          Downloading and building Docker images...
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          This may take a few minutes on the first run. Check the logs below for progress.
                        </Typography>
                      </Alert>
                    )}
                  </Box>
                )}
              </Box>
            )}

            {/* ===== STAGE 2: Start / Running Controls ===== */}
            {!isRunning && imagesReady && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Step 2: Launch Designer
                </Typography>

                {/* No credential selected */}
                {!selectedCredential && (
                  <Alert severity="warning" sx={{ mb: 1.5 }}>
                    <strong>No credential selected.</strong> Select a credential from the header dropdown to start the Designer container.
                  </Alert>
                )}

                {/* Credential selected but no gateway URL */}
                {selectedCredential && !selectedCredential.gateway_url && (
                  <Alert severity="warning" sx={{ mb: 1.5 }}>
                    <strong>Credential &quot;{selectedCredential.name}&quot; has no gateway URL.</strong> Edit the credential in Settings to add a gateway URL.
                  </Alert>
                )}

                {/* Starting progress indicator */}
                {isStarting && (
                  <Alert severity="info" sx={{ mb: 1.5 }}>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      Starting CloudDesigner containers...
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Launching 4 containers (nginx, guacd, guacamole, designer-desktop). Check logs below for progress.
                    </Typography>
                  </Alert>
                )}

                <Button
                  variant="contained"
                  color="primary"
                  startIcon={isStarting ? <CircularProgress size={16} color="inherit" /> : <StartIcon />}
                  onClick={() => handleStart(false)}
                  disabled={!selectedCredential?.gateway_url || isStarting || isPreparing}
                  size="large"
                >
                  {isStarting ? 'Starting Container...' : 'Start Designer Container'}
                </Button>
              </Box>
            )}

            {/* ===== Running State Controls ===== */}
            {isRunning && (
              <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
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
                <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                  URL: http://localhost:8080/connect
                </Typography>
              </Stack>
            )}

            {/* Docker version info */}
            {dockerStatus.version && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                {dockerStatus.version}
                {dockerStatus.docker_path && ` (${dockerStatus.docker_path})`}
              </Typography>
            )}

            {/* Debug section - also available when Docker is running for troubleshooting */}
            <Accordion
              expanded={showDebug}
              onChange={() => {
                setShowDebug(!showDebug);
                if (!showDebug) {
                  refetchLogs();
                  refetchAllStatuses();
                }
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
Primary Container: ${containerStatus?.status || 'not_created'}
Images Ready: ${imagesReady ? 'Yes' : 'No'}${allStatuses?.statuses ? '\n\nAll Containers:\n' + Object.entries(allStatuses.statuses).map(([name, status]) => `  ${name.replace('clouddesigner-', '')}: ${status}`).join('\n') : ''}`}
                    </Typography>
                  </Box>

                  {/* Maintenance Actions */}
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>Maintenance</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      Clean up removes all CloudDesigner containers, volumes, networks, and cached images.
                    </Typography>
                    <Stack direction="row" spacing={1}>
                      <Button
                        variant="outlined"
                        color="warning"
                        size="small"
                        startIcon={isCleaning ? <CircularProgress size={14} /> : <CleanupIcon />}
                        onClick={() => setShowCleanupConfirm(true)}
                        disabled={isCleaning || isStarting || isPreparing}
                      >
                        {isCleaning ? 'Cleaning up...' : 'Clean Up Everything'}
                      </Button>
                    </Stack>
                  </Box>

                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="subtitle2">CloudDesigner Logs (filtered)</Typography>
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
                      maxHeight: 400,
                      overflow: 'auto'
                    }}>
                      {(() => {
                        // Filter to only CloudDesigner-related logs
                        const relevantLogs = logsData?.logs?.filter((log: { message: string }) => {
                          const msg = log.message.toLowerCase();
                          return msg.includes('clouddesigner') ||
                            msg.includes('compose') ||
                            msg.includes('[clouddesigner') ||
                            msg.includes('pulling') ||
                            msg.includes('building') ||
                            msg.includes('step ') ||
                            (msg.includes('build') && (msg.includes('docker') || msg.includes('container') || msg.includes('image')));
                        }) || [];

                        if (relevantLogs.length === 0) {
                          return <Typography variant="body2" color="text.secondary">No CloudDesigner logs found yet.</Typography>;
                        }

                        return relevantLogs.slice(0, 200).map((log: { timestamp: string; level: string; message: string }, i: number) => (
                          <Box key={i} sx={{ mb: 0.5 }}>
                            <Typography component="span" sx={{ color: 'grey.500', fontSize: 'inherit' }}>
                              {new Date(log.timestamp).toLocaleTimeString()}
                            </Typography>
                            {' '}
                            <Typography component="span" sx={{ color: log.level === 'ERROR' ? 'error.main' : log.level === 'WARNING' ? 'warning.main' : 'info.main', fontSize: 'inherit' }}>
                              [{log.level}]
                            </Typography>
                            {' '}{log.message}
                          </Box>
                        ));
                      })()}
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
