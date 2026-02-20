/**
 * PlaybookExecutionDialog - Dialog for configuring and executing playbooks
 */

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Alert,
  Chip,
} from '@mui/material';
import { Save as SaveIcon, Warning as WarningIcon } from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { ParameterInput } from './ParameterInput';
import { TimeoutSettings } from './TimeoutSettings';
import type { PlaybookInfo, CredentialInfo, TimeoutOverrides } from '../types/api';
import { useStore, type SessionCredential } from '../store';

interface PlaybookExecutionDialogProps {
  open: boolean;
  playbook: PlaybookInfo | null;
  onClose: () => void;
}

interface SavedConfig {
  parameters: Record<string, string>;
  timeoutOverrides?: TimeoutOverrides;
  savedAt: string;
}

// Get saved config for a playbook
function getSavedConfig(playbookPath: string): SavedConfig | null {
  const stored = localStorage.getItem(`playbook_config_${playbookPath}`);
  return stored ? JSON.parse(stored) : null;
}

// Save config for a playbook (only parameters, NOT gateway_url/username/password)
function saveConfig(playbookPath: string, config: SavedConfig) {
  localStorage.setItem(`playbook_config_${playbookPath}`, JSON.stringify(config));
}

export function PlaybookExecutionDialog({
  open,
  playbook,
  onClose,
}: PlaybookExecutionDialogProps) {
  const [parameters, setParameters] = useState<Record<string, string>>({});
  const [timeoutOverrides, setTimeoutOverrides] = useState<TimeoutOverrides>({});
  const [configSaved, setConfigSaved] = useState(false);

  // Get global selected credential
  const selectedCredential = useStore((state) => state.selectedCredential);
  const sessionCredentials = useStore((state) => state.sessionCredentials);

  // Fetch available credentials
  const { data: credentials = [] } = useQuery<CredentialInfo[]>({
    queryKey: ['credentials'],
    queryFn: api.credentials.list,
    enabled: open,
  });

  // Combine saved and session credentials for display
  const allCredentials = [
    ...credentials,
    ...sessionCredentials,
  ];

  // Load saved config or defaults when playbook changes
  useEffect(() => {
    if (playbook) {
      const savedConfig = getSavedConfig(playbook.path);

      if (savedConfig) {
        // Load saved configuration (only parameters, not gateway_url)
        setParameters(savedConfig.parameters);
        setTimeoutOverrides(savedConfig.timeoutOverrides || {});
        setConfigSaved(true);
      } else {
        // Reset timeout overrides when loading defaults
        setTimeoutOverrides({});
        // Load defaults
        const defaultParams: Record<string, string> = {};
        playbook.parameters.forEach((param) => {
          // Check for non-null/undefined defaults (including false, 0, empty string)
          if (param.default !== null && param.default !== undefined) {
            defaultParams[param.name] = String(param.default);
          }
        });

        // Auto-fill from global credential if available
        if (selectedCredential) {
          // Auto-fill credential parameter if playbook has one
          const credentialParam = playbook.parameters.find(p => p.type === 'credential');
          if (credentialParam) {
            defaultParams[credentialParam.name] = selectedCredential.name;
          }

          // Auto-fill any username/password parameters if they exist
          const usernameParam = playbook.parameters.find(p => p.name.toLowerCase().includes('username') || p.name.toLowerCase().includes('user'));
          const passwordParam = playbook.parameters.find(p => p.name.toLowerCase().includes('password') || p.name.toLowerCase().includes('pass'));

          if (usernameParam) {
            defaultParams[usernameParam.name] = selectedCredential.username;
          }

          // For session credentials, we have the password available
          const isSessionCredential = 'isSessionOnly' in selectedCredential && selectedCredential.isSessionOnly;
          if (passwordParam && isSessionCredential) {
            defaultParams[passwordParam.name] = (selectedCredential as SessionCredential).password;
          }
        }

        setParameters(defaultParams);
        setConfigSaved(false);
      }
    }
  }, [playbook, selectedCredential]);

  if (!playbook) return null;

  const handleParameterChange = (name: string, value: string) => {
    setParameters((prev) => ({ ...prev, [name]: value }));
    setConfigSaved(false); // Mark as unsaved when changes are made
  };

  const handleTimeoutChange = (overrides: TimeoutOverrides) => {
    setTimeoutOverrides(overrides);
    setConfigSaved(false); // Mark as unsaved when changes are made
  };

  const handleSaveConfig = () => {
    if (!playbook) return;

    // Filter out sensitive parameters (gateway_url, username, password, etc.)
    const sensitiveParams = ['gateway_url', 'username', 'password', 'user', 'pass', 'gateway_username', 'gateway_password'];
    const filteredParameters = Object.fromEntries(
      Object.entries(parameters).filter(([key]) =>
        !sensitiveParams.includes(key.toLowerCase())
      )
    );

    // Only include timeout overrides if any are set
    const hasTimeoutOverrides = Object.values(timeoutOverrides).some(v => v !== undefined);

    saveConfig(playbook.path, {
      parameters: filteredParameters,
      ...(hasTimeoutOverrides && { timeoutOverrides }),
      savedAt: new Date().toISOString(),
    });
    setConfigSaved(true);
  };

  const savedConfig = playbook ? getSavedConfig(playbook.path) : null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span>Configure Playbook: {playbook.name}</span>
          {savedConfig && (
            <Chip
              label={configSaved ? 'Configuration Saved' : 'Unsaved Changes'}
              size="small"
              color={configSaved ? 'success' : 'warning'}
              variant="outlined"
            />
          )}
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary">
            {playbook.description}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            Version {playbook.version} • {playbook.step_count} steps
          </Typography>
          {savedConfig && (
            <Typography variant="caption" color="success.main" sx={{ display: 'block', mt: 0.5 }}>
              Last saved: {new Date(savedConfig.savedAt).toLocaleString()}
            </Typography>
          )}
        </Box>

        {/* Unverified playbook warning */}
        {!playbook.verified && (
          <Alert severity="warning" icon={<WarningIcon />} sx={{ mb: 2 }}>
            This playbook has not been verified. Review the steps before executing.
          </Alert>
        )}

        {/* Show selected credential info if available */}
        {selectedCredential && !savedConfig && (
          <Alert severity="info" sx={{ mb: 2 }}>
            Auto-filled from global credential: <strong>{selectedCredential.name}</strong>
            {selectedCredential.gateway_url && ` (${selectedCredential.gateway_url})`}
          </Alert>
        )}


        {/* Parameter inputs - filter out gateway_url since it's shown above */}
        {playbook.parameters.filter(p => p.name !== 'gateway_url').length > 0 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant="subtitle2" color="text.secondary">
              Parameters
            </Typography>

            {playbook.parameters
              .filter(param =>
                param.name !== 'gateway_url' &&
                !['username', 'password', 'user', 'pass', 'gateway_username', 'gateway_password'].includes(param.name.toLowerCase())
              )
              .map((param) => (
                <ParameterInput
                  key={param.name}
                  parameter={param}
                  value={parameters[param.name] || ''}
                  credentials={allCredentials}
                  onChange={handleParameterChange}
                />
              ))}
          </Box>
        )}

        {/* Timeout Settings */}
        <Box sx={{ mt: 2 }}>
          <TimeoutSettings
            timeoutOverrides={timeoutOverrides}
            onChange={handleTimeoutChange}
            relevantTimeouts={playbook.relevant_timeouts}
          />
        </Box>
      </DialogContent>

      <DialogActions sx={{ gap: 1, flexWrap: 'wrap' }}>
        <Button onClick={onClose}>
          Close
        </Button>

        <Box sx={{ flexGrow: 1 }} />

        <Button
          onClick={handleSaveConfig}
          variant="contained"
          disabled={configSaved}
          startIcon={<SaveIcon />}
        >
          Save Config
        </Button>
      </DialogActions>
    </Dialog>
  );
}
