/**
 * Settings page with sub-tabs for Credentials, Executions, Updates, and About
 * Styled to match cw-dashboard-dist
 */

import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  Button,
  CircularProgress,
  Alert,
  Chip,
  Link,
  Divider,
  Stack,
} from '@mui/material';
import {
  Key as CredentialsIcon,
  History as ExecutionsIcon,
  Info as AboutIcon,
  Settings as SettingsIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  RestartAlt as RestartIcon,
} from '@mui/icons-material';
import { Credentials } from './Credentials';
import { Executions } from './Executions';
import { api } from '../api/client';
import type { HealthResponse } from '../types/api';
import packageJson from '../../package.json';

type SettingsTab = 'credentials' | 'executions' | 'updates' | 'about';

interface UpdateStatus {
  checking: boolean;
  available: boolean;
  downloading: boolean;
  downloaded: boolean;
  progress?: number;
  error?: string;
  updateInfo?: {
    version: string;
    releaseDate: string;
    releaseNotes?: string;
  };
}

const settingsTabs: { id: SettingsTab; label: string; icon: React.ReactNode }[] = [
  { id: 'credentials', label: 'Gateway Credentials', icon: <CredentialsIcon /> },
  { id: 'executions', label: 'Execution History', icon: <ExecutionsIcon /> },
  { id: 'updates', label: 'Updates', icon: <DownloadIcon /> },
  { id: 'about', label: 'About', icon: <AboutIcon /> },
];

// Check if running in Electron
const isElectron = (): boolean => {
  return typeof window !== 'undefined' && !!window.electronAPI;
};

export function Settings() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('credentials');
  const [appVersion, setAppVersion] = useState<string>(packageJson.version);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [updateStatus, setUpdateStatus] = useState<UpdateStatus>({
    checking: false,
    available: false,
    downloading: false,
    downloaded: false,
  });

  // Get app version and health on mount
  useEffect(() => {
    if (isElectron() && window.electronAPI) {
      window.electronAPI.getVersion().then(setAppVersion).catch(() => {});
    }
    api.health().then(setHealth).catch(() => {});
  }, []);

  const handleCheckUpdate = async () => {
    if (!isElectron() || !window.electronAPI) return;
    setUpdateStatus((prev) => ({ ...prev, checking: true, error: undefined }));
    try {
      const result = await window.electronAPI.checkForUpdates();
      setUpdateStatus(result);
    } catch (err) {
      setUpdateStatus((prev) => ({
        ...prev,
        checking: false,
        error: err instanceof Error ? err.message : 'Failed to check for updates',
      }));
    }
  };

  const handleDownloadUpdate = async () => {
    if (!isElectron() || !window.electronAPI) return;
    setUpdateStatus((prev) => ({ ...prev, downloading: true, error: undefined }));
    try {
      await window.electronAPI.downloadUpdate();
      // The status will be updated via events, but set downloading for UI feedback
    } catch (err) {
      setUpdateStatus((prev) => ({
        ...prev,
        downloading: false,
        error: err instanceof Error ? err.message : 'Failed to download update',
      }));
    }
  };

  const handleInstallUpdate = async () => {
    if (!isElectron() || !window.electronAPI) return;
    try {
      await window.electronAPI.installUpdate();
    } catch (err) {
      setUpdateStatus((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Failed to install update',
      }));
    }
  };

  const renderUpdatesContent = () => (
    <Box sx={{ height: '100%' }}>
      <Typography variant="h6" sx={{ mb: 3 }}>
        Software Updates
      </Typography>

      {!isElectron() ? (
        <Paper
          sx={{
            p: 4,
            textAlign: 'center',
            bgcolor: 'background.paper',
            border: '1px solid',
            borderColor: 'divider',
          }}
        >
          <ErrorIcon sx={{ fontSize: 48, color: 'warning.main', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Desktop Only Feature
          </Typography>
          <Typography color="text.secondary">
            Auto-updates are only available in the desktop application.
          </Typography>
        </Paper>
      ) : (
        <Paper
          sx={{
            p: 3,
            bgcolor: 'background.paper',
            border: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Stack spacing={3}>
            {/* Current Version */}
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Current Version
                </Typography>
                <Typography variant="h5" sx={{ fontFamily: 'monospace' }}>
                  v{appVersion}
                </Typography>
              </Box>
              <Button
                variant="outlined"
                startIcon={updateStatus.checking ? <CircularProgress size={16} /> : <RefreshIcon />}
                onClick={handleCheckUpdate}
                disabled={updateStatus.checking || updateStatus.downloading}
              >
                {updateStatus.checking ? 'Checking...' : 'Check for Updates'}
              </Button>
            </Box>

            {/* Update Available */}
            {updateStatus.available && !updateStatus.downloaded && (
              <Paper
                sx={{
                  p: 2,
                  bgcolor: 'primary.main',
                  color: 'primary.contrastText',
                  backgroundImage: 'linear-gradient(rgba(255,255,255,0.1), rgba(255,255,255,0))',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography variant="subtitle1" fontWeight="medium" gutterBottom>
                      Update Available: v{updateStatus.updateInfo?.version}
                    </Typography>
                    {updateStatus.updateInfo?.releaseNotes && (
                      <Typography variant="body2" sx={{ opacity: 0.9, whiteSpace: 'pre-line' }}>
                        {updateStatus.updateInfo.releaseNotes.replace(/<[^>]+>/g, '')}
                      </Typography>
                    )}
                  </Box>
                  <Button
                    variant="contained"
                    color="inherit"
                    startIcon={updateStatus.downloading ? <CircularProgress size={16} /> : <DownloadIcon />}
                    onClick={handleDownloadUpdate}
                    disabled={updateStatus.downloading}
                    sx={{ bgcolor: 'white', color: 'primary.main', '&:hover': { bgcolor: 'grey.100' } }}
                  >
                    {updateStatus.downloading ? 'Downloading...' : 'Download'}
                  </Button>
                </Box>
                {updateStatus.downloading && updateStatus.progress !== undefined && (
                  <Box sx={{ mt: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="caption">Downloading...</Typography>
                      <Typography variant="caption">{Math.round(updateStatus.progress)}%</Typography>
                    </Box>
                    <Box
                      sx={{
                        height: 4,
                        bgcolor: 'rgba(255,255,255,0.3)',
                        borderRadius: 2,
                        overflow: 'hidden',
                      }}
                    >
                      <Box
                        sx={{
                          height: '100%',
                          width: `${updateStatus.progress}%`,
                          bgcolor: 'white',
                          borderRadius: 2,
                          transition: 'width 0.3s',
                        }}
                      />
                    </Box>
                  </Box>
                )}
              </Paper>
            )}

            {/* Update Downloaded */}
            {updateStatus.downloaded && (
              <Paper
                sx={{
                  p: 2,
                  bgcolor: 'success.main',
                  color: 'success.contrastText',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <CheckCircleIcon />
                    <Box>
                      <Typography variant="subtitle1" fontWeight="medium">
                        Update Ready to Install
                      </Typography>
                      <Typography variant="body2" sx={{ opacity: 0.9 }}>
                        Restart the application to install v{updateStatus.updateInfo?.version}
                      </Typography>
                    </Box>
                  </Box>
                  <Button
                    variant="contained"
                    color="inherit"
                    startIcon={<RestartIcon />}
                    onClick={handleInstallUpdate}
                    sx={{ bgcolor: 'white', color: 'success.main', '&:hover': { bgcolor: 'grey.100' } }}
                  >
                    Restart & Install
                  </Button>
                </Box>
              </Paper>
            )}

            {/* No Update Available Message */}
            {!updateStatus.available && !updateStatus.checking && !updateStatus.error && (
              <Alert severity="success" icon={<CheckCircleIcon />}>
                You are running the latest version.
              </Alert>
            )}

            {/* Error */}
            {updateStatus.error && (
              <Alert severity="error">
                {updateStatus.error}
              </Alert>
            )}
          </Stack>
        </Paper>
      )}
    </Box>
  );

  const renderAboutContent = () => (
    <Box sx={{ height: '100%' }}>
      <Typography variant="h6" sx={{ mb: 3 }}>
        About Ignition Toolbox
      </Typography>

      <Stack spacing={3}>
        {/* App Info Card */}
        <Paper
          sx={{
            p: 4,
            textAlign: 'center',
            bgcolor: 'background.paper',
            border: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Box
            sx={{
              width: 64,
              height: 64,
              bgcolor: 'primary.main',
              borderRadius: 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              mx: 'auto',
              mb: 2,
            }}
          >
            <SettingsIcon sx={{ fontSize: 32, color: 'white' }} />
          </Box>
          <Typography variant="h5" fontWeight="bold" gutterBottom>
            Ignition Toolbox
          </Typography>
          <Typography color="text.secondary" gutterBottom>
            Version {appVersion}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 400, mx: 'auto', mt: 2 }}>
            Visual acceptance testing platform for Ignition SCADA systems.
            Automate Gateway, Designer, and Perspective operations with playbook-driven workflows.
          </Typography>
        </Paper>

        {/* System Information */}
        <Paper
          sx={{
            p: 3,
            bgcolor: 'background.paper',
            border: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2, textTransform: 'uppercase', letterSpacing: 1 }}>
            System Information
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Stack spacing={2}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">Platform</Typography>
              <Typography variant="body2">
                {isElectron() ? 'Desktop (Electron)' : 'Web Browser'}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">Frontend Version</Typography>
              <Typography variant="body2">{packageJson.version}</Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">Backend Version</Typography>
              <Typography variant="body2">{health?.version || 'Loading...'}</Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">Backend Status</Typography>
              <Chip
                label={health?.status === 'healthy' ? 'Healthy' : 'Unhealthy'}
                color={health?.status === 'healthy' ? 'success' : 'error'}
                size="small"
                icon={health?.status === 'healthy' ? <CheckCircleIcon /> : <ErrorIcon />}
              />
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">License</Typography>
              <Typography variant="body2">MIT License</Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">Repository</Typography>
              <Link
                href="https://github.com/nigelgwork/ignition-toolbox"
                target="_blank"
                rel="noopener noreferrer"
                sx={{ fontSize: '0.875rem' }}
              >
                github.com/nigelgwork/ignition-toolbox
              </Link>
            </Box>
          </Stack>
        </Paper>
      </Stack>
    </Box>
  );

  return (
    <Box sx={{ height: 'calc(100vh - 88px)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3, flexShrink: 0 }}>
        <SettingsIcon sx={{ color: 'text.secondary' }} />
        <Typography variant="h5" fontWeight="bold">
          Settings
        </Typography>
      </Box>

      <Box sx={{ display: 'flex', gap: 3, flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {/* Sidebar */}
        <Paper
          elevation={0}
          sx={{
            width: 220,
            flexShrink: 0,
            bgcolor: 'background.paper',
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 2,
            overflow: 'hidden',
          }}
        >
          <List sx={{ p: 1 }}>
            {settingsTabs.map((tab) => (
              <ListItemButton
                key={tab.id}
                selected={activeTab === tab.id}
                onClick={() => setActiveTab(tab.id)}
                sx={{
                  borderRadius: 1,
                  mb: 0.5,
                  '&.Mui-selected': {
                    bgcolor: 'primary.main',
                    color: 'primary.contrastText',
                    '&:hover': {
                      bgcolor: 'primary.dark',
                    },
                    '& .MuiListItemIcon-root': {
                      color: 'primary.contrastText',
                    },
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 36, color: activeTab === tab.id ? 'inherit' : 'text.secondary' }}>
                  {tab.icon}
                </ListItemIcon>
                <ListItemText
                  primary={tab.label}
                  primaryTypographyProps={{
                    fontSize: '0.875rem',
                    fontWeight: activeTab === tab.id ? 600 : 400,
                  }}
                />
              </ListItemButton>
            ))}
          </List>
        </Paper>

        {/* Content */}
        <Box sx={{ flex: 1, overflow: 'auto', minWidth: 0 }}>
          {activeTab === 'credentials' && <Credentials />}
          {activeTab === 'executions' && <Executions />}
          {activeTab === 'updates' && renderUpdatesContent()}
          {activeTab === 'about' && renderAboutContent()}
        </Box>
      </Box>
    </Box>
  );
}
