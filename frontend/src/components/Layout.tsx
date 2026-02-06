/**
 * Main layout with horizontal top navigation
 * Design inspired by CW Dashboard
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
} from '@mui/material';
import {
  Storage as GatewayIcon,
  DesignServices as DesignerIcon,
  Visibility as PerspectiveIcon,
  Settings as SettingsIcon,
  KeyboardArrowDown as ArrowDownIcon,
  Key as KeyIcon,
  SystemUpdateAlt as UpdateIcon,
  Handyman as ToolboxIcon,
  Api as ApiIcon,
  Layers as StackIcon,
  PlaylistPlay as ExecutionsIcon,
} from '@mui/icons-material';
import { useStore } from '../store';
import { api } from '../api/client';
import type { CredentialInfo } from '../types/api';
import { useQuery } from '@tanstack/react-query';
import packageJson from '../../package.json';

// Check if running in Electron
const isElectron = (): boolean => {
  return typeof window !== 'undefined' && !!window.electronAPI;
};

// Domain tabs for playbook filtering
export type DomainTab = 'gateway' | 'designer' | 'perspective' | 'executions' | 'api' | 'stackbuilder' | 'settings';

const domainTabs: { id: DomainTab; label: string; icon: React.ReactNode; iconOnly?: boolean }[] = [
  { id: 'gateway', label: 'Gateway', icon: <GatewayIcon fontSize="small" /> },
  { id: 'designer', label: 'Designer', icon: <DesignerIcon fontSize="small" /> },
  { id: 'perspective', label: 'Perspective', icon: <PerspectiveIcon fontSize="small" /> },
  { id: 'executions', label: 'Executions', icon: <ExecutionsIcon fontSize="small" /> },
  { id: 'api', label: 'API', icon: <ApiIcon fontSize="small" /> },
  { id: 'stackbuilder', label: 'Stacks', icon: <StackIcon fontSize="small" /> },
  { id: 'settings', label: 'Settings', icon: <SettingsIcon fontSize="small" />, iconOnly: true },
];

interface LayoutProps {
  activeTab: DomainTab;
  onTabChange: (tab: DomainTab) => void;
  children: React.ReactNode;
}

export function Layout({ activeTab, onTabChange, children }: LayoutProps) {
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
    // Also set the full credential object for PlaybookCard/execution
    if (credentialName) {
      const fullCredential = credentials.find((c) => c.name === credentialName);
      setSelectedCredential(fullCredential || null);
      // Persist to localStorage
      localStorage.setItem('selectedCredentialName', credentialName);
    } else {
      setSelectedCredential(null);
      localStorage.removeItem('selectedCredentialName');
    }
    handleCredentialClose();
  };

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', bgcolor: 'background.default' }}>
      {/* Header */}
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
        }}
      >
        {/* Left side: Logo and tabs */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          {/* Logo/Title */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <ToolboxIcon sx={{ color: 'primary.main', fontSize: 24 }} />
            <Typography variant="h6" fontWeight="bold" color="text.primary">
              Ignition Toolbox
            </Typography>
          </Box>

          {/* Tab Navigation */}
          <Box component="nav" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            {domainTabs.map((tab) => (
              tab.iconOnly ? (
                <Tooltip key={tab.id} title={tab.label} arrow>
                  <IconButton
                    onClick={() => onTabChange(tab.id)}
                    size="small"
                    sx={{
                      p: 1,
                      borderRadius: 1,
                      color: activeTab === tab.id ? 'primary.main' : 'text.secondary',
                      bgcolor: activeTab === tab.id ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                      '&:hover': {
                        bgcolor: activeTab === tab.id ? 'rgba(59, 130, 246, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                        color: activeTab === tab.id ? 'primary.main' : 'text.primary',
                      },
                    }}
                  >
                    {tab.icon}
                  </IconButton>
                </Tooltip>
              ) : (
                <Button
                  key={tab.id}
                  onClick={() => onTabChange(tab.id)}
                  startIcon={tab.icon}
                  size="small"
                  sx={{
                    px: 1.5,
                    py: 0.75,
                    borderRadius: 1,
                    textTransform: 'none',
                    fontWeight: 500,
                    fontSize: '0.875rem',
                    color: activeTab === tab.id ? 'primary.main' : 'text.secondary',
                    bgcolor: activeTab === tab.id ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                    '&:hover': {
                      bgcolor: activeTab === tab.id ? 'rgba(59, 130, 246, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                      color: activeTab === tab.id ? 'primary.main' : 'text.primary',
                    },
                  }}
                >
                  {tab.label}
                </Button>
              )
            ))}
          </Box>
        </Box>

        {/* Right side: Credential selector, health, version, theme toggle */}
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
              onClick={() => onTabChange('settings')}
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
