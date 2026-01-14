/**
 * Main layout with navigation
 */

import { useState, useEffect } from 'react';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  Drawer,
  List,
  ListItemButton,
  ListItemText,
  IconButton,
  Divider,
  Chip,
  Paper,
  Stack,
} from '@mui/material';
import {
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
} from '@mui/icons-material';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { useStore } from '../store';
import { api } from '../api/client';
import type { HealthResponse } from '../types/api';
import { GlobalCredentialSelector } from './GlobalCredentialSelector';
import packageJson from '../../package.json';

const DRAWER_WIDTH = 240;

const navItems = [
  { path: '/', label: 'Playbooks' },
  { path: '/executions', label: 'Executions' },
  { path: '/credentials', label: 'Gateway Credentials' },
  { path: '/about', label: 'About' },
];

export function Layout() {
  const location = useLocation();
  const isWSConnected = useStore((state) => state.isWSConnected);
  const wsConnectionStatus = useStore((state) => state.wsConnectionStatus);
  const theme = useStore((state) => state.theme);
  const setTheme = useStore((state) => state.setTheme);
  const [health, setHealth] = useState<'healthy' | 'unhealthy'>('healthy');

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

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar sx={{ minHeight: '51px !important', height: '51px' }}>
          <Typography variant="h6" noWrap component="div">
            ⚡ Ignition Playground <Box component="span" sx={{ color: 'primary.light', fontWeight: 300 }}>(Portable)</Box>
          </Typography>

          {/* Global Credential Selector */}
          <Box sx={{ flexGrow: 1, display: 'flex', justifyContent: 'center', px: 2 }}>
            <GlobalCredentialSelector />
          </Box>

          {/* Health Badge */}
          <Chip
            label={health === 'healthy' ? 'Healthy' : 'Unhealthy'}
            size="small"
            color={health === 'healthy' ? 'success' : 'error'}
            sx={{ mr: 2 }}
          />

          {/* Frontend Version */}
          <Chip
            label={`UI v${packageJson.version}`}
            size="small"
            variant="outlined"
            sx={{ mr: 2 }}
          />

          {/* WebSocket Status */}
          <Box
            sx={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              bgcolor: wsConnectionStatus === 'connected'
                ? 'success.main'
                : wsConnectionStatus === 'connecting' || wsConnectionStatus === 'reconnecting'
                ? 'warning.main'
                : 'error.main',
              mr: 1,
              animation: wsConnectionStatus === 'connecting' || wsConnectionStatus === 'reconnecting'
                ? 'pulse 1.5s ease-in-out infinite'
                : 'none',
              '@keyframes pulse': {
                '0%, 100%': { opacity: 1 },
                '50%': { opacity: 0.4 },
              },
            }}
            role="status"
            aria-label={`WebSocket ${wsConnectionStatus}`}
          />
          <Typography variant="body2" color="inherit" sx={{ mr: 2, textTransform: 'capitalize' }}>
            {wsConnectionStatus}
          </Typography>

          {/* Theme Toggle */}
          <IconButton
            onClick={toggleTheme}
            color="inherit"
            aria-label="Toggle theme"
            size="small"
          >
            {theme === 'dark' ? <LightModeIcon /> : <DarkModeIcon />}
          </IconButton>
        </Toolbar>
      </AppBar>

      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
            display: 'flex',
            flexDirection: 'column',
          },
        }}
      >
        <Toolbar />

        {/* Navigation */}
        <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
          <List aria-label="Main navigation">
            {navItems.map((item) => (
              <ListItemButton
                key={item.path}
                component={Link}
                to={item.path}
                selected={location.pathname === item.path}
              >
                <ListItemText primary={item.label} />
              </ListItemButton>
            ))}
          </List>

          <Divider sx={{ my: 2 }} />

          {/* Stats Panel */}
          <Box sx={{ px: 2 }}>
            <Paper
              elevation={0}
              sx={{
                p: 2,
                backgroundColor: 'background.default',
                border: '1px solid',
                borderColor: 'divider',
              }}
            >
              <Typography variant="caption" color="text.secondary" gutterBottom>
                System Stats
              </Typography>
              <Stack spacing={1} mt={1}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2">Status:</Typography>
                  <Typography variant="body2" color={health === 'healthy' ? 'success.main' : 'error.main'}>
                    {health === 'healthy' ? '✓' : '✗'}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2">WebSocket:</Typography>
                  <Typography variant="body2" color={isWSConnected ? 'success.main' : 'error.main'}>
                    {isWSConnected ? '✓' : '✗'}
                  </Typography>
                </Box>
              </Stack>
            </Paper>
          </Box>
        </Box>

        {/* Footer with Version */}
        <Box
          sx={{
            p: 2,
            borderTop: '1px solid',
            borderColor: 'divider',
            textAlign: 'center',
          }}
        >
          <Typography variant="caption" color="text.secondary">
            UI v{packageJson.version}
          </Typography>
          <Typography variant="caption" display="block" color="text.secondary">
            Ignition Playground
          </Typography>
        </Box>
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, p: 3, pt: 1.5, minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Toolbar sx={{ minHeight: '51px !important', height: '51px' }} />
        <Box sx={{ flexGrow: 1 }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
