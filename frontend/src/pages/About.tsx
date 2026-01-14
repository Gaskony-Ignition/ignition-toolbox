/**
 * About page with system information and update checker
 */

import { useState, useEffect } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  Stack,
  Divider,
  Alert,
  CircularProgress,
  Chip,
  Link,
} from '@mui/material';
import {
  Info as InfoIcon,
  Refresh as RefreshIcon,
  SystemUpdate as UpdateIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { api } from '../api/client';
import type { HealthResponse } from '../types/api';
import packageJson from '../../package.json';

interface UpdateInfo {
  current_version: string;
  latest_version: string;
  release_url: string;
  release_notes: string;
  download_url: string;
  published_at: string;
  is_newer: boolean;
  size_mb?: number;
}

export function About() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [updateInfo, setUpdateInfo] = useState<UpdateInfo | null>(null);
  const [checking, setChecking] = useState(false);
  const [installing, setInstalling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Fetch health info on mount
  useEffect(() => {
    fetchHealth();
  }, []);

  const fetchHealth = async () => {
    try {
      const data = await api.health();
      setHealth(data);
    } catch (err) {
      console.error('Failed to fetch health:', err);
    }
  };

  const checkForUpdates = async () => {
    setChecking(true);
    setError(null);
    setSuccess(null);
    setUpdateInfo(null);

    try {
      const response = await fetch('/api/updates/check');
      const data = await response.json();

      if (response.ok) {
        if (data.update_available) {
          setUpdateInfo(data.update);
          setSuccess('Update available!');
        } else {
          setSuccess('You are running the latest version!');
        }
      } else {
        setError(data.detail || 'Failed to check for updates');
      }
    } catch (err) {
      setError('Failed to check for updates. Please try again.');
      console.error('Update check error:', err);
    } finally {
      setChecking(false);
    }
  };

  const installUpdate = async () => {
    if (!updateInfo) return;

    setInstalling(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch('/api/updates/install', {
        method: 'POST',
      });
      const data = await response.json();

      if (response.ok) {
        setSuccess('Update installation started! The server will restart shortly.');
        // Poll status endpoint
        pollInstallStatus();
      } else {
        setError(data.detail || 'Failed to start update installation');
      }
    } catch (err) {
      setError('Failed to install update. Please try again.');
      console.error('Update install error:', err);
    } finally {
      setInstalling(false);
    }
  };

  const pollInstallStatus = async () => {
    // Poll every 2 seconds for update status
    const interval = setInterval(async () => {
      try {
        const response = await fetch('/api/updates/status');
        const data = await response.json();

        if (data.status === 'completed') {
          clearInterval(interval);
          setSuccess('Update installed successfully! Please restart the server.');
        } else if (data.status === 'failed') {
          clearInterval(interval);
          setError(`Update failed: ${data.error}`);
        }
      } catch (err) {
        // Server might be restarting
        console.error('Status poll error:', err);
      }
    }, 2000);

    // Stop polling after 2 minutes
    setTimeout(() => clearInterval(interval), 120000);
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 2 }}>
      <Stack spacing={3}>
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <InfoIcon fontSize="large" color="primary" />
          <Typography variant="h4" component="h1">
            About
          </Typography>
        </Box>

        {/* System Information */}
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            System Information
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Stack spacing={2}>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Application Name
              </Typography>
              <Typography variant="body1" fontWeight="medium">
                Ignition Automation Toolkit
              </Typography>
            </Box>

            <Box>
              <Typography variant="body2" color="text.secondary">
                Backend Version
              </Typography>
              <Typography variant="body1" fontWeight="medium">
                {health?.version || 'Loading...'}
              </Typography>
            </Box>

            <Box>
              <Typography variant="body2" color="text.secondary">
                Frontend Version
              </Typography>
              <Typography variant="body1" fontWeight="medium">
                {packageJson.version}
              </Typography>
            </Box>

            <Box>
              <Typography variant="body2" color="text.secondary">
                Backend Status
              </Typography>
              <Chip
                label={health?.status === 'healthy' ? 'Healthy' : 'Unhealthy'}
                color={health?.status === 'healthy' ? 'success' : 'error'}
                size="small"
                icon={health?.status === 'healthy' ? <CheckCircleIcon /> : <ErrorIcon />}
              />
            </Box>

            <Box>
              <Typography variant="body2" color="text.secondary">
                Description
              </Typography>
              <Typography variant="body1">
                Lightweight, transferable automation platform for Ignition SCADA Gateway operations.
              </Typography>
            </Box>

            <Box>
              <Typography variant="body2" color="text.secondary">
                License
              </Typography>
              <Typography variant="body1">
                MIT License
              </Typography>
            </Box>

            <Box>
              <Typography variant="body2" color="text.secondary">
                Repository
              </Typography>
              <Link
                href="https://github.com/nigelgwork/ignition-playground"
                target="_blank"
                rel="noopener noreferrer"
              >
                github.com/nigelgwork/ignition-playground
              </Link>
            </Box>
          </Stack>
        </Paper>

        {/* Update Checker */}
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Software Updates
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Stack spacing={2}>
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Check for updates from GitHub Releases
              </Typography>
              <Button
                variant="contained"
                startIcon={checking ? <CircularProgress size={20} /> : <RefreshIcon />}
                onClick={checkForUpdates}
                disabled={checking || installing}
              >
                {checking ? 'Checking...' : 'Check for Updates'}
              </Button>
            </Box>

            {/* Success Message */}
            {success && (
              <Alert severity="success" onClose={() => setSuccess(null)}>
                {success}
              </Alert>
            )}

            {/* Error Message */}
            {error && (
              <Alert severity="error" onClose={() => setError(null)}>
                {error}
              </Alert>
            )}

            {/* Update Available */}
            {updateInfo && (
              <Paper sx={{ p: 2, backgroundColor: 'action.hover' }}>
                <Stack spacing={2}>
                  <Box>
                    <Typography variant="subtitle1" fontWeight="medium" gutterBottom>
                      Update Available: v{updateInfo.latest_version}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Current: v{updateInfo.current_version} → Latest: v{updateInfo.latest_version}
                    </Typography>
                  </Box>

                  {updateInfo.size_mb && (
                    <Typography variant="body2" color="text.secondary">
                      Download size: ~{updateInfo.size_mb} MB
                    </Typography>
                  )}

                  {updateInfo.release_notes && (
                    <Box>
                      <Typography variant="body2" fontWeight="medium" gutterBottom>
                        Release Notes:
                      </Typography>
                      <Box
                        sx={{
                          maxHeight: 200,
                          overflow: 'auto',
                          p: 2,
                          backgroundColor: 'background.paper',
                          borderRadius: 1,
                          border: '1px solid',
                          borderColor: 'divider',
                        }}
                      >
                        <Typography
                          variant="body2"
                          component="pre"
                          sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.85rem' }}
                        >
                          {updateInfo.release_notes}
                        </Typography>
                      </Box>
                    </Box>
                  )}

                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Button
                      variant="contained"
                      color="primary"
                      startIcon={installing ? <CircularProgress size={20} /> : <UpdateIcon />}
                      onClick={installUpdate}
                      disabled={installing}
                    >
                      {installing ? 'Installing...' : 'Install Update'}
                    </Button>
                    <Button
                      variant="outlined"
                      href={updateInfo.release_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      View on GitHub
                    </Button>
                  </Box>

                  <Alert severity="info">
                    <Typography variant="body2">
                      <strong>Note:</strong> The server will automatically restart after installation.
                      Your credentials and data will be backed up before the update.
                    </Typography>
                  </Alert>
                </Stack>
              </Paper>
            )}
          </Stack>
        </Paper>
      </Stack>
    </Container>
  );
}
