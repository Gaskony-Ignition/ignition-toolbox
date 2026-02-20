/**
 * Main layout with hierarchical two-level tab navigation
 * Row 1: Main tabs (Playbooks, API Explorer, Stacks, UDTs, Settings)
 * Row 2: Sub-tabs (only visible when Playbooks is active)
 */

import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Tooltip,
  IconButton,
  Chip,
  SvgIcon,
} from '@mui/material';
import {
  Storage as GatewayIcon,
  DesignServices as DesignerIcon,
  Visibility as PerspectiveIcon,
  Settings as SettingsIcon,
  KeyboardArrowDown as ArrowDownIcon,
  Key as KeyIcon,
  SystemUpdateAlt as UpdateIcon,
  Api as ApiIcon,
  Layers as StackIcon,
  AccountTree as UdtIcon,
  PlayArrow as ActiveExecutionIcon,
  History as PastExecutionsIcon,
  AutoStories as PlaybooksIcon,
  Apps as ServicesIcon,
  Extension as IntegrationsIcon,
  Code as PreviewIcon,
} from '@mui/icons-material';
import { useStore, type MainTab, type PlaybookSubTab, type StackSubTab } from '../store';
import { api } from '../api/client';
import type { CredentialInfo } from '../types/api';
import { useQuery } from '@tanstack/react-query';
import packageJson from '../../package.json';
import { isElectron } from '../utils/platform';

// Custom icon: wrench + flame accent (Ignition Toolbox branding)
function IgnitionToolboxIcon(props: React.ComponentProps<typeof SvgIcon>) {
  return (
    <SvgIcon {...props} viewBox="0 0 24 24">
      <path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z" />
      <path d="M18 1c-1.5 1.8-2.5 3.5-2.5 5 0 1.6 1.1 2.5 2.5 2.5s2.5-.9 2.5-2.5c0-1.5-1-3.2-2.5-5z" />
    </SvgIcon>
  );
}

function getBadgeSx(badge: string) {
  const isOrange = badge === 'Beta';
  return {
    ml: 0.5,
    height: 18,
    fontSize: '0.65rem',
    fontWeight: 600,
    bgcolor: isOrange ? 'rgba(255, 152, 0, 0.15)' : 'rgba(147, 51, 234, 0.15)',
    color: isOrange ? '#ff9800' : '#a855f7',
    border: isOrange ? '1px solid rgba(255, 152, 0, 0.3)' : '1px solid rgba(147, 51, 234, 0.3)',
  };
}

const mainTabs: { id: MainTab; label: string; icon: React.ReactNode; iconOnly?: boolean; badge?: string }[] = [
  { id: 'playbooks', label: 'Playbooks', icon: <PlaybooksIcon fontSize="small" /> },
  { id: 'designer', label: 'Browser Designer', icon: <DesignerIcon fontSize="small" /> },
  { id: 'api', label: 'API', icon: <ApiIcon fontSize="small" /> },
  { id: 'stackbuilder', label: 'Stacks', icon: <StackIcon fontSize="small" />, badge: 'Coming Soon' },
  { id: 'udtbuilder', label: 'UDTs', icon: <UdtIcon fontSize="small" />, badge: 'Coming Soon' },
  { id: 'settings', label: 'Settings', icon: <SettingsIcon fontSize="small" />, iconOnly: true },
];

const stackSubTabs: { id: StackSubTab; label: string; icon: React.ReactNode }[] = [
  { id: 'services', label: 'Services', icon: <ServicesIcon sx={{ fontSize: '1rem' }} /> },
  { id: 'integrations', label: 'Integrations', icon: <IntegrationsIcon sx={{ fontSize: '1rem' }} /> },
  { id: 'preview', label: 'Preview', icon: <PreviewIcon sx={{ fontSize: '1rem' }} /> },
];

const playbookSubTabs: { id: PlaybookSubTab; label: string; icon: React.ReactNode; badge?: string }[] = [
  { id: 'gateway', label: 'Gateway', icon: <GatewayIcon sx={{ fontSize: '1rem' }} /> },
  { id: 'designer', label: 'Designer', icon: <DesignerIcon sx={{ fontSize: '1rem' }} /> },
  { id: 'perspective', label: 'Perspective', icon: <PerspectiveIcon sx={{ fontSize: '1rem' }} />, badge: 'Coming Soon' },
  { id: 'active-execution', label: 'Active Execution', icon: <ActiveExecutionIcon sx={{ fontSize: '1rem' }} /> },
  { id: 'past-executions', label: 'Past Executions', icon: <PastExecutionsIcon sx={{ fontSize: '1rem' }} /> },
];

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const mainTab = useStore((state) => state.mainTab);
  const setMainTab = useStore((state) => state.setMainTab);
  const playbookSubTab = useStore((state) => state.playbookSubTab);
  const setPlaybookSubTab = useStore((state) => state.setPlaybookSubTab);
  const stackSubTab = useStore((state) => state.stackSubTab);
  const setStackSubTab = useStore((state) => state.setStackSubTab);
  const globalCredential = useStore((state) => state.globalCredential);
  const setGlobalCredential = useStore((state) => state.setGlobalCredential);
  const setSelectedCredential = useStore((state) => state.setSelectedCredential);
  const updateStatus = useStore((state) => state.updateStatus);
  const setUpdateStatus = useStore((state) => state.setUpdateStatus);
  const [credentialAnchor, setCredentialAnchor] = useState<null | HTMLElement>(null);

  // Fetch credentials for dropdown
  const { data: credentials = [] } = useQuery<CredentialInfo[]>({
    queryKey: ['credentials'],
    queryFn: () => api.credentials.list(),
  });

  // Listen for update events from Electron
  useEffect(() => {
    if (isElectron() && window.electronAPI) {
      const unsubAvailable = window.electronAPI.on('update:available', (data: unknown) => {
        const updateData = data as { updateInfo?: { version: string } };
        setUpdateStatus({
          available: true,
          downloaded: false,
          version: updateData.updateInfo?.version,
        });
      });

      const unsubDownloaded = window.electronAPI.on('update:downloaded', (data: unknown) => {
        const updateData = data as { updateInfo?: { version: string } };
        setUpdateStatus({
          available: true,
          downloaded: true,
          version: updateData.updateInfo?.version,
        });
      });

      // Check current update status on mount
      window.electronAPI.getUpdateStatus().then((status) => {
        if (status.available) {
          setUpdateStatus({
            available: status.available,
            downloaded: status.downloaded,
            version: status.updateInfo?.version,
          });
        }
      }).catch(() => {});

      return () => {
        unsubAvailable();
        unsubDownloaded();
      };
    }
  }, [setUpdateStatus]);

  // Restore credential from localStorage when credentials are fetched
  useEffect(() => {
    const savedCredentialName = localStorage.getItem('selectedCredentialName');
    if (savedCredentialName && credentials.length > 0) {
      const fullCredential = credentials.find((c) => c.name === savedCredentialName);
      if (fullCredential) {
        setGlobalCredential(savedCredentialName);
        setSelectedCredential(fullCredential);
      }
    }
  }, [credentials, setGlobalCredential, setSelectedCredential]);

  const handleCredentialClick = (event: React.MouseEvent<HTMLElement>) => {
    setCredentialAnchor(event.currentTarget);
  };

  const handleCredentialClose = () => {
    setCredentialAnchor(null);
  };

  const handleCredentialSelect = (credentialName: string | null) => {
    setGlobalCredential(credentialName);
    if (credentialName) {
      const fullCredential = credentials.find((c) => c.name === credentialName);
      setSelectedCredential(fullCredential || null);
      localStorage.setItem('selectedCredentialName', credentialName);
    } else {
      setSelectedCredential(null);
      localStorage.removeItem('selectedCredentialName');
    }
    handleCredentialClose();
  };

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', bgcolor: 'background.default' }}>
      {/* Row 1: Main Header */}
      <Box
        component="header"
        sx={{
          height: 56,
          bgcolor: 'background.paper',
          borderBottom: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 2,
          flexShrink: 0,
        }}
      >
        {/* Left side: Logo and main tabs */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          {/* Logo/Title */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <IgnitionToolboxIcon sx={{ color: 'primary.main', fontSize: 24 }} />
            <Typography variant="h6" fontWeight="bold" color="text.primary">
              Ignition Toolbox
            </Typography>
          </Box>

          {/* Main Tab Navigation */}
          <Box component="nav" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            {mainTabs.map((tab) => (
              tab.iconOnly ? (
                <Tooltip key={tab.id} title={tab.label} arrow>
                  <IconButton
                    onClick={() => setMainTab(tab.id)}
                    size="small"
                    sx={{
                      p: 1,
                      borderRadius: 1,
                      color: mainTab === tab.id ? 'primary.main' : 'text.secondary',
                      bgcolor: mainTab === tab.id ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                      '&:hover': {
                        bgcolor: mainTab === tab.id ? 'rgba(59, 130, 246, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                        color: mainTab === tab.id ? 'primary.main' : 'text.primary',
                      },
                    }}
                  >
                    {tab.icon}
                  </IconButton>
                </Tooltip>
              ) : (
                <Button
                  key={tab.id}
                  onClick={() => setMainTab(tab.id)}
                  startIcon={tab.icon}
                  size="small"
                  sx={{
                    px: 1.5,
                    py: 0.75,
                    borderRadius: 1,
                    textTransform: 'none',
                    fontWeight: 500,
                    fontSize: '0.875rem',
                    color: mainTab === tab.id ? 'primary.main' : 'text.secondary',
                    bgcolor: mainTab === tab.id ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                    '&:hover': {
                      bgcolor: mainTab === tab.id ? 'rgba(59, 130, 246, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                      color: mainTab === tab.id ? 'primary.main' : 'text.primary',
                    },
                  }}
                >
                  {tab.label}
                  {tab.badge && (
                    <Chip label={tab.badge} size="small" sx={getBadgeSx(tab.badge)} />
                  )}
                </Button>
              )
            ))}
          </Box>
        </Box>

        {/* Right side: Credential selector, update, version */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {/* Global Credential Selector */}
          <Button
            onClick={handleCredentialClick}
            endIcon={<ArrowDownIcon />}
            startIcon={<KeyIcon />}
            size="small"
            variant="outlined"
            sx={{
              textTransform: 'none',
              borderColor: 'divider',
              color: globalCredential ? 'text.primary' : 'text.secondary',
              minWidth: 180,
              justifyContent: 'space-between',
            }}
          >
            {globalCredential || 'Select Credential'}
          </Button>
          <Menu
            anchorEl={credentialAnchor}
            open={Boolean(credentialAnchor)}
            onClose={handleCredentialClose}
            anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
            transformOrigin={{ vertical: 'top', horizontal: 'right' }}
          >
            <MenuItem
              onClick={() => handleCredentialSelect(null)}
              selected={!globalCredential}
            >
              <ListItemText primary="None" secondary="Manual entry required" />
            </MenuItem>
            {credentials.map((cred) => (
              <MenuItem
                key={cred.name}
                onClick={() => handleCredentialSelect(cred.name)}
                selected={globalCredential === cred.name}
              >
                <ListItemIcon>
                  <KeyIcon fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary={cred.name}
                  secondary={cred.gateway_url ? new URL(cred.gateway_url).hostname : 'No gateway'}
                />
              </MenuItem>
            ))}
            {credentials.length === 0 && (
              <MenuItem disabled>
                <ListItemText
                  primary="No credentials"
                  secondary="Add in Settings"
                />
              </MenuItem>
            )}
          </Menu>

          {/* Update Available Indicator */}
          {updateStatus.available && (
            <Button
              onClick={() => setMainTab('settings')}
              startIcon={
                <Box sx={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                  <UpdateIcon />
                  {!updateStatus.downloaded && (
                    <Box
                      sx={{
                        position: 'absolute',
                        top: -2,
                        right: -2,
                        width: 8,
                        height: 8,
                        bgcolor: '#ef4444',
                        borderRadius: '50%',
                        animation: 'pulse 2s ease-in-out infinite',
                        '@keyframes pulse': {
                          '0%, 100%': { opacity: 1, transform: 'scale(1)' },
                          '50%': { opacity: 0.6, transform: 'scale(1.2)' },
                        },
                      }}
                    />
                  )}
                </Box>
              }
              size="small"
              sx={{
                bgcolor: updateStatus.downloaded ? 'success.main' : '#f59e0b',
                color: 'white',
                textTransform: 'none',
                fontWeight: 500,
                fontSize: '0.75rem',
                px: 1.5,
                py: 0.5,
                '&:hover': {
                  bgcolor: updateStatus.downloaded ? 'success.dark' : '#d97706',
                },
              }}
            >
              {updateStatus.downloaded ? 'Install & Restart' : 'Update Available'}
            </Button>
          )}

          {/* Version */}
          <Typography variant="caption" color="text.secondary">
            v{packageJson.version}
          </Typography>
        </Box>
      </Box>

      {/* Row 2: Sub-tabs (Playbooks or Stacks) */}
      {(mainTab === 'playbooks' || mainTab === 'stackbuilder') && (
        <Box
          sx={{
            height: 40,
            bgcolor: 'background.paper',
            borderBottom: '1px solid',
            borderColor: 'divider',
            display: 'flex',
            alignItems: 'center',
            px: 2,
            justifyContent: 'flex-start',
            gap: 0.5,
            flexShrink: 0,
          }}
        >
          {mainTab === 'playbooks' && playbookSubTabs.map((tab) => (
            <Button
              key={tab.id}
              onClick={() => setPlaybookSubTab(tab.id)}
              startIcon={tab.icon}
              size="small"
              sx={{
                px: 1.5,
                py: 0.5,
                borderRadius: 1,
                textTransform: 'none',
                fontWeight: 500,
                fontSize: '0.8rem',
                minHeight: 32,
                color: playbookSubTab === tab.id ? 'primary.main' : 'text.secondary',
                bgcolor: playbookSubTab === tab.id ? 'rgba(59, 130, 246, 0.12)' : 'transparent',
                '&:hover': {
                  bgcolor: playbookSubTab === tab.id ? 'rgba(59, 130, 246, 0.18)' : 'rgba(255, 255, 255, 0.05)',
                  color: playbookSubTab === tab.id ? 'primary.main' : 'text.primary',
                },
              }}
            >
              {tab.label}
              {tab.badge && (
                <Chip label={tab.badge} size="small" sx={getBadgeSx(tab.badge)} />
              )}
            </Button>
          ))}
          {mainTab === 'stackbuilder' && stackSubTabs.map((tab) => (
            <Button
              key={tab.id}
              onClick={() => setStackSubTab(tab.id)}
              startIcon={tab.icon}
              size="small"
              sx={{
                px: 1.5,
                py: 0.5,
                borderRadius: 1,
                textTransform: 'none',
                fontWeight: 500,
                fontSize: '0.8rem',
                minHeight: 32,
                color: stackSubTab === tab.id ? 'primary.main' : 'text.secondary',
                bgcolor: stackSubTab === tab.id ? 'rgba(59, 130, 246, 0.12)' : 'transparent',
                '&:hover': {
                  bgcolor: stackSubTab === tab.id ? 'rgba(59, 130, 246, 0.18)' : 'rgba(255, 255, 255, 0.05)',
                  color: stackSubTab === tab.id ? 'primary.main' : 'text.primary',
                },
              }}
            >
              {tab.label}
            </Button>
          ))}
        </Box>
      )}

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flex: 1,
          minHeight: 0,
          p: 2,
          overflow: 'auto',
        }}
      >
        {children}
      </Box>
    </Box>
  );
}
