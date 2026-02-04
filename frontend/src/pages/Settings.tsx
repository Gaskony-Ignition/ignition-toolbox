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
  Switch,
  FormControlLabel,
  RadioGroup,
  Radio,
  FormControl,
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
  Palette as AppearanceIcon,
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
  ViewCompact as CompactIcon,
  ViewComfy as ComfortableIcon,
  ViewModule as SpaciousIcon,
  GridView as GridIcon,
  SmartToy as ChatIcon,
  BugReport as DiagnosticsIcon,
} from '@mui/icons-material';
import { Credentials } from './Credentials';
import { Executions } from './Executions';
import { ChatPanel } from '../components/chat/ChatPanel';
import { DiagnosticsPanel } from '../components/DiagnosticsPanel';
import { api } from '../api/client';
import { useStore } from '../store';
import type { HealthResponse } from '../types/api';
import packageJson from '../../package.json';

type SettingsTab = 'credentials' | 'executions' | 'diagnostics' | 'updates' | 'appearance' | 'chat' | 'about';

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
  { id: 'diagnostics', label: 'Diagnostics & Logs', icon: <DiagnosticsIcon /> },
  { id: 'updates', label: 'Updates', icon: <DownloadIcon /> },
  { id: 'appearance', label: 'Appearance', icon: <AppearanceIcon /> },
  { id: 'chat', label: 'Assistant', icon: <ChatIcon /> },
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
  const theme = useStore((state) => state.theme);
  const setTheme = useStore((state) => state.setTheme);
  const density = useStore((state) => state.density);
  const setDensity = useStore((state) => state.setDensity);
  const playbookGridColumns = useStore((state) => state.playbookGridColumns);
  const setPlaybookGridColumns = useStore((state) => state.setPlaybookGridColumns);

  // Get app version and health on mount
  useEffect(() => {
    if (isElectron() && window.electronAPI) {
      window.electronAPI.getVersion().then(setAppVersion).catch(() => {});
    }
    api.health().then(setHealth).catch(() => {});
  }, []);

  // Listen for update events from Electron
  useEffect(() => {
    if (!isElectron() || !window.electronAPI) return;

    const unsubscribeProgress = window.electronAPI.on('update:progress', (data) => {
      const status = data as UpdateStatus;
      setUpdateStatus((prev) => ({
        ...prev,
        downloading: true,
        progress: status.progress,
      }));
    });

    const unsubscribeDownloaded = window.electronAPI.on('update:downloaded', (data) => {
      const status = data as UpdateStatus;
      setUpdateStatus((prev) => ({
        ...prev,
        downloading: false,
        downloaded: true,
        progress: 100,
        updateInfo: status.updateInfo || prev.updateInfo,
      }));
    });

    const unsubscribeError = window.electronAPI.on('update:error', (data) => {
      const status = data as UpdateStatus;
      setUpdateStatus((prev) => ({
        ...prev,
        checking: false,
        downloading: false,
        error: status.error,
      }));
    });

    const unsubscribeAvailable = window.electronAPI.on('update:available', (data) => {
      const status = data as UpdateStatus;
      setUpdateStatus((prev) => ({
        ...prev,
        checking: false,
        available: true,
        updateInfo: status.updateInfo,
      }));
    });

    const unsubscribeNotAvailable = window.electronAPI.on('update:not-available', () => {
      setUpdateStatus((prev) => ({
        ...prev,
        checking: false,
        available: false,
      }));
    });

    return () => {
      unsubscribeProgress();
      unsubscribeDownloaded();
      unsubscribeError();
      unsubscribeAvailable();
      unsubscribeNotAvailable();
    };
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
    <Box sx={{ width: '100%', maxWidth: '100%' }}>
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
                <Typography variant="h5" fontWeight="bold">
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

            {/* Update Settings */}
            <Divider />
            <Box>
              <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2, textTransform: 'uppercase', letterSpacing: 1 }}>
                Update Settings
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Updates are manual only. Check for updates when you want, download when ready, and install when convenient.
              </Typography>
            </Box>
          </Stack>
        </Paper>
      )}
    </Box>
  );

  const renderAboutContent = () => (
    <Box sx={{ width: '100%', maxWidth: '100%' }}>
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

  const renderAppearanceContent = () => (
    <Box sx={{ width: '100%', maxWidth: '100%' }}>
      <Typography variant="h6" sx={{ mb: 3 }}>
        Appearance
      </Typography>

      <Stack spacing={3}>
        {/* Theme Section */}
        <Paper
          sx={{
            p: 3,
            bgcolor: 'background.paper',
            border: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2, textTransform: 'uppercase', letterSpacing: 1 }}>
            Theme
          </Typography>
          <Divider sx={{ mb: 3 }} />

          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              {theme === 'dark' ? (
                <DarkModeIcon sx={{ color: 'primary.main' }} />
              ) : (
                <LightModeIcon sx={{ color: 'warning.main' }} />
              )}
              <Box>
                <Typography variant="body1" fontWeight="medium">
                  {theme === 'dark' ? 'Dark Mode' : 'Light Mode'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {theme === 'dark'
                    ? 'Using dark theme with navy blue background'
                    : 'Using light theme with white background'}
                </Typography>
              </Box>
            </Box>
            <FormControlLabel
              control={
                <Switch
                  checked={theme === 'dark'}
                  onChange={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                  color="primary"
                />
              }
              label=""
            />
          </Box>
        </Paper>

        {/* Density Section */}
        <Paper
          sx={{
            p: 3,
            bgcolor: 'background.paper',
            border: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2, textTransform: 'uppercase', letterSpacing: 1 }}>
            Display Density
          </Typography>
          <Divider sx={{ mb: 3 }} />

          <FormControl component="fieldset">
            <RadioGroup
              value={density}
              onChange={(e) => setDensity(e.target.value as 'compact' | 'comfortable' | 'spacious')}
            >
              <FormControlLabel
                value="compact"
                control={<Radio size="small" />}
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <CompactIcon sx={{ color: density === 'compact' ? 'primary.main' : 'text.secondary' }} />
                    <Box>
                      <Typography variant="body2" fontWeight={density === 'compact' ? 'medium' : 'normal'}>
                        Compact
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Less spacing, more content visible
                      </Typography>
                    </Box>
                  </Box>
                }
                sx={{ mb: 1.5 }}
              />
              <FormControlLabel
                value="comfortable"
                control={<Radio size="small" />}
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <ComfortableIcon sx={{ color: density === 'comfortable' ? 'primary.main' : 'text.secondary' }} />
                    <Box>
                      <Typography variant="body2" fontWeight={density === 'comfortable' ? 'medium' : 'normal'}>
                        Comfortable
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Balanced spacing (default)
                      </Typography>
                    </Box>
                  </Box>
                }
                sx={{ mb: 1.5 }}
              />
              <FormControlLabel
                value="spacious"
                control={<Radio size="small" />}
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <SpaciousIcon sx={{ color: density === 'spacious' ? 'primary.main' : 'text.secondary' }} />
                    <Box>
                      <Typography variant="body2" fontWeight={density === 'spacious' ? 'medium' : 'normal'}>
                        Spacious
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        More breathing room between elements
                      </Typography>
                    </Box>
                  </Box>
                }
              />
            </RadioGroup>
          </FormControl>
        </Paper>

        {/* Playbook Grid Columns Section */}
        <Paper
          sx={{
            p: 3,
            bgcolor: 'background.paper',
            border: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2, textTransform: 'uppercase', letterSpacing: 1 }}>
            Playbook Grid
          </Typography>
          <Divider sx={{ mb: 3 }} />

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <GridIcon sx={{ color: 'primary.main' }} />
            <Box>
              <Typography variant="body1" fontWeight="medium">
                Maximum Columns
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Maximum number of playbook cards per row on large screens
              </Typography>
            </Box>
          </Box>

          <FormControl component="fieldset">
            <RadioGroup
              row
              value={playbookGridColumns}
              onChange={(e) => setPlaybookGridColumns(parseInt(e.target.value, 10) as 3 | 4 | 5 | 6)}
            >
              {[3, 4, 5, 6].map((cols) => (
                <FormControlLabel
                  key={cols}
                  value={cols}
                  control={<Radio size="small" />}
                  label={
                    <Typography
                      variant="body2"
                      fontWeight={playbookGridColumns === cols ? 'medium' : 'normal'}
                    >
                      {cols}
                    </Typography>
                  }
                  sx={{ mr: 3 }}
                />
              ))}
            </RadioGroup>
          </FormControl>
        </Paper>
      </Stack>
    </Box>
  );

  const renderChatContent = () => (
    <Box sx={{ width: '100%', height: 'calc(100vh - 200px)' }}>
      <Typography variant="h6" sx={{ mb: 3 }}>
        Toolbox Assistant
      </Typography>
      <Paper
        elevation={0}
        sx={{
          height: 'calc(100% - 60px)',
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 2,
          overflow: 'hidden',
        }}
      >
        <ChatPanel height="100%" showClearButton />
      </Paper>
    </Box>
  );

  return (
    <Box sx={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
    }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3, flexShrink: 0 }}>
        <SettingsIcon sx={{ color: 'primary.main' }} />
        <Typography variant="h5" fontWeight="bold">
          Settings
        </Typography>
      </Box>

      <Box sx={{ display: 'flex', gap: 3, flex: 1 }}>
        {/* Sidebar */}
        <Paper
          elevation={0}
          sx={{
            width: 240,
            flexShrink: 0,
            bgcolor: 'background.paper',
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 2,
            alignSelf: 'flex-start',
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
                    bgcolor: 'rgba(59, 130, 246, 0.15)',
                    color: 'primary.main',
                    '&:hover': {
                      bgcolor: 'rgba(59, 130, 246, 0.25)',
                    },
                    '& .MuiListItemIcon-root': {
                      color: 'primary.main',
                    },
                  },
                  '&:hover': {
                    bgcolor: 'action.hover',
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 36, color: activeTab === tab.id ? 'primary.main' : 'text.secondary' }}>
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

        {/* Content - fills remaining width */}
        <Box
          sx={{
            flex: 1,
            minWidth: 0,
            overflow: 'auto',
          }}
        >
          {activeTab === 'credentials' && <Credentials />}
          {activeTab === 'executions' && <Executions />}
          {activeTab === 'diagnostics' && <DiagnosticsPanel />}
          {activeTab === 'updates' && renderUpdatesContent()}
          {activeTab === 'appearance' && renderAppearanceContent()}
          {activeTab === 'chat' && renderChatContent()}
          {activeTab === 'about' && renderAboutContent()}
        </Box>
      </Box>
    </Box>
  );
}
