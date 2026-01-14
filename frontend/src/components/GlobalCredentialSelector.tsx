/**
 * GlobalCredentialSelector - Select a global credential for all playbook executions
 */

import { useState, useEffect } from 'react';
import {
  Box,
  FormControl,
  Select,
  MenuItem,
  Chip,
  Typography,
  IconButton,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import {
  Clear as ClearIcon,
  CheckCircle as ConnectedIcon,
  Error as DisconnectedIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { useStore, type SessionCredential } from '../store';
import type { CredentialInfo } from '../types/api';

export function GlobalCredentialSelector() {
  const selectedCredential = useStore((state) => state.selectedCredential);
  const setSelectedCredential = useStore((state) => state.setSelectedCredential);
  const sessionCredentials = useStore((state) => state.sessionCredentials);
  const [connectionStatus, setConnectionStatus] = useState<'unknown' | 'connected' | 'disconnected'>('unknown');

  // Fetch saved credentials
  const { data: savedCredentials = [] } = useQuery<CredentialInfo[]>({
    queryKey: ['credentials'],
    queryFn: api.credentials.list,
    refetchInterval: 10000, // Refetch every 10 seconds
  });

  // Combine saved and session credentials
  const allCredentials = [
    ...savedCredentials,
    ...sessionCredentials,
  ];

  const handleSelect = (credentialName: string) => {
    if (credentialName === '') {
      setSelectedCredential(null);
      localStorage.removeItem('selectedCredentialName');
      return;
    }

    const credential = allCredentials.find((c) => c.name === credentialName);
    if (credential) {
      setSelectedCredential(credential);
      // Save to localStorage
      localStorage.setItem('selectedCredentialName', credentialName);
    }
  };

  const handleClear = () => {
    setSelectedCredential(null);
    setConnectionStatus('unknown');
    localStorage.removeItem('selectedCredentialName');
  };

  // Restore selected credential from localStorage on mount
  useEffect(() => {
    const savedCredentialName = localStorage.getItem('selectedCredentialName');
    if (savedCredentialName && allCredentials.length > 0) {
      const credential = allCredentials.find((c) => c.name === savedCredentialName);
      if (credential) {
        setSelectedCredential(credential);
      }
    }
  }, [savedCredentials, sessionCredentials]);

  const isSessionCredential = (cred: CredentialInfo | SessionCredential): cred is SessionCredential => {
    return 'isSessionOnly' in cred && cred.isSessionOnly === true;
  };

  // Test connection when credential is selected
  useEffect(() => {
    if (!selectedCredential?.gateway_url) {
      setConnectionStatus('unknown');
      return;
    }

    const testConnection = async () => {
      setConnectionStatus('unknown');
      try {
        // Try to fetch the system/gwinfo endpoint (doesn't require auth)
        await fetch(`${selectedCredential.gateway_url}/system/gwinfo`, {
          method: 'GET',
          mode: 'no-cors', // Allow cross-origin for simple connectivity check
        });
        setConnectionStatus('connected');
      } catch (error) {
        setConnectionStatus('disconnected');
      }
    };

    testConnection();

    // Re-test every 30 seconds
    const interval = setInterval(testConnection, 30000);
    return () => clearInterval(interval);
  }, [selectedCredential]);

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, minWidth: 300 }}>
      <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: 'nowrap', fontSize: '0.75rem' }}>
        Global Credentials:
      </Typography>
      <FormControl size="small" sx={{ flex: 1, minWidth: 200 }}>
        <Select
          labelId="global-credential-label"
          id="global-credential-select"
          value={selectedCredential?.name || ''}
          onChange={(e) => handleSelect(e.target.value)}
        >
          <MenuItem value="">
            <em>None selected</em>
          </MenuItem>
          {allCredentials.map((cred) => (
            <MenuItem key={cred.name} value={cred.name}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                <Typography variant="body2">{cred.name}</Typography>
                {isSessionCredential(cred) && (
                  <Chip label="Session" size="small" color="warning" variant="outlined" />
                )}
              </Box>
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {selectedCredential && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Chip
            label={`${selectedCredential.username}@${selectedCredential.gateway_url || 'No URL'}`}
            size="small"
            color="primary"
            variant="outlined"
          />
          {selectedCredential.gateway_url && (
            <Tooltip title={connectionStatus === 'connected' ? 'Gateway reachable' : connectionStatus === 'disconnected' ? 'Gateway unreachable' : 'Testing connection...'}>
              {connectionStatus === 'unknown' ? (
                <CircularProgress size={16} />
              ) : connectionStatus === 'connected' ? (
                <ConnectedIcon fontSize="small" color="success" />
              ) : (
                <DisconnectedIcon fontSize="small" color="error" />
              )}
            </Tooltip>
          )}
          <Tooltip title="Clear selection">
            <IconButton size="small" onClick={handleClear} aria-label="Clear credential selection">
              <ClearIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      )}
    </Box>
  );
}
