/**
 * Main layout with horizontal top navigation
 * Design inspired by CW Dashboard
 */

import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  IconButton,
  Chip,
  Button,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
  Storage as GatewayIcon,
  DesignServices as DesignerIcon,
  Visibility as PerspectiveIcon,
  Settings as SettingsIcon,
  KeyboardArrowDown as ArrowDownIcon,
  Key as KeyIcon,
} from '@mui/icons-material';
import { useStore } from '../store';
import { api } from '../api/client';
import type { HealthResponse, CredentialInfo } from '../types/api';
import { useQuery } from '@tanstack/react-query';
import packageJson from '../../package.json';

// Domain tabs for playbook filtering
export type DomainTab = 'gateway' | 'designer' | 'perspective' | 'settings';

const domainTabs: { id: DomainTab; label: string; icon: React.ReactNode }[] = [
  { id: 'gateway', label: 'Gateway', icon: <GatewayIcon fontSize="small" /> },
  { id: 'designer', label: 'Designer', icon: <DesignerIcon fontSize="small" /> },
  { id: 'perspective', label: 'Perspective', icon: <PerspectiveIcon fontSize="small" /> },
  { id: 'settings', label: 'Settings', icon: <SettingsIcon fontSize="small" /> },
];

interface LayoutProps {
  activeTab: DomainTab;
  onTabChange: (tab: DomainTab) => void;
  children: React.ReactNode;
}

export function Layout({ activeTab, onTabChange, children }: LayoutProps) {
  const theme = useStore((state) => state.theme);
  const setTheme = useStore((state) => state.setTheme);
  const globalCredential = useStore((state) => state.globalCredential);
  const setGlobalCredential = useStore((state) => state.setGlobalCredential);
  const [health, setHealth] = useState<'healthy' | 'unhealthy'>('healthy');
  const [credentialAnchor, setCredentialAnchor] = useState<null | HTMLElement>(null);

  // Fetch credentials for dropdown
  const { data: credentials = [] } = useQuery<CredentialInfo[]>({
    queryKey: ['credentials'],
    queryFn: () => api.credentials.list(),
  });

  // Fetch health on mount
  useEffect(() => {
    api.health()
      .then((data: HealthResponse) => {
        setHealth(data.status === 'healthy' ? 'healthy' : 'unhealthy');
      })
      .catch(() => {
        setHealth('unhealthy');
      });
  }, []);

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  };

  const handleCredentialClick = (event: React.MouseEvent<HTMLElement>) => {
    setCredentialAnchor(event.currentTarget);
  };

  const handleCredentialClose = () => {
    setCredentialAnchor(null);
  };

  const handleCredentialSelect = (credentialName: string | null) => {
    setGlobalCredential(credentialName);
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
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Typography variant="h6" fontWeight="bold" color="text.primary">
              Ignition Toolbox
            </Typography>
          </Box>

          {/* Tab Navigation */}
          <Box component="nav" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            {domainTabs.map((tab) => (
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

          {/* Health indicator */}
          <Chip
            label={health === 'healthy' ? 'Healthy' : 'Unhealthy'}
            size="small"
            color={health === 'healthy' ? 'success' : 'error'}
            variant="outlined"
          />

          {/* Version */}
          <Typography variant="caption" color="text.secondary">
            v{packageJson.version}
          </Typography>

          {/* Theme Toggle */}
          <IconButton
            onClick={toggleTheme}
            size="small"
            sx={{ color: 'text.secondary' }}
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? <LightModeIcon fontSize="small" /> : <DarkModeIcon fontSize="small" />}
          </IconButton>
        </Box>
      </Box>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 2,
          overflow: 'auto',
        }}
      >
        {children}
      </Box>
    </Box>
  );
}
