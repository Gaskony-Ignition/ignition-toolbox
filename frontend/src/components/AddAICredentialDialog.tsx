/**
 * AddAICredentialDialog - Dialog for adding new AI credentials
 */

import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Alert,
  IconButton,
  InputAdornment,
  FormControlLabel,
  Switch,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import { Visibility, VisibilityOff } from '@mui/icons-material';

export interface AICredentialCreate {
  name: string;
  provider: string;
  api_key?: string;
  api_base_url?: string;
  model_name?: string;
  enabled: boolean;
}

interface AddAICredentialDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (credential: AICredentialCreate) => void;
  isLoading?: boolean;
  error?: string | null;
}

// Helper to get default model for each provider
const getDefaultModel = (provider: string) => {
  switch (provider) {
    case 'openai': return 'gpt-4';
    case 'anthropic': return 'claude-3-5-sonnet-20241022';
    case 'gemini': return 'gemini-1.5-flash';
    case 'local': return 'custom-model';
    default: return 'gpt-4';
  }
};

// Get valid models for a provider
const getValidModels = (provider: string): string[] => {
  switch (provider) {
    case 'openai':
      return ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo', 'gpt-4o', 'gpt-4o-mini'];
    case 'anthropic':
      return ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307'];
    case 'gemini':
      return ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.0-pro'];
    case 'local':
      return ['custom-model'];
    default:
      return ['gpt-4'];
  }
};

export function AddAICredentialDialog({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  error = null,
}: AddAICredentialDialogProps) {
  const [name, setName] = useState('');
  const [provider, setProvider] = useState('openai');
  const [apiKey, setApiKey] = useState('');
  const [apiBaseUrl, setApiBaseUrl] = useState('');
  const [modelName, setModelName] = useState('gpt-4');
  const [enabled, setEnabled] = useState(true);
  const [showApiKey, setShowApiKey] = useState(false);

  const handleProviderChange = (newProvider: string) => {
    setProvider(newProvider);
    setModelName(getDefaultModel(newProvider));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim() || !apiKey.trim()) {
      return;
    }

    onSubmit({
      name: name.trim(),
      provider,
      api_key: apiKey.trim(),
      api_base_url: apiBaseUrl.trim() || undefined,
      model_name: modelName,
      enabled,
    });
  };

  const handleClose = () => {
    // Reset form
    setName('');
    setProvider('openai');
    setApiKey('');
    setApiBaseUrl('');
    setModelName('gpt-4');
    setEnabled(true);
    setShowApiKey(false);
    onClose();
  };

  const isValid = name.trim() && apiKey.trim();

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add AI Credential</DialogTitle>

      <form onSubmit={handleSubmit}>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="my_openai_key"
              required
              fullWidth
              autoFocus
              helperText="Unique identifier for this AI credential"
              disabled={isLoading}
            />

            <FormControl fullWidth disabled={isLoading}>
              <InputLabel>Provider</InputLabel>
              <Select
                value={provider}
                label="Provider"
                onChange={(e) => handleProviderChange(e.target.value)}
              >
                <MenuItem value="openai">OpenAI</MenuItem>
                <MenuItem value="anthropic">Anthropic (Claude)</MenuItem>
                <MenuItem value="gemini">Google Gemini</MenuItem>
                <MenuItem value="local">Local LLM</MenuItem>
              </Select>
            </FormControl>

            <TextField
              label="API Key"
              type={showApiKey ? 'text' : 'password'}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              required
              fullWidth
              disabled={isLoading}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label={showApiKey ? 'Hide API key' : 'Show API key'}
                      onClick={() => setShowApiKey(!showApiKey)}
                      edge="end"
                    >
                      {showApiKey ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            {provider === 'local' && (
              <TextField
                label="Base URL"
                value={apiBaseUrl}
                onChange={(e) => setApiBaseUrl(e.target.value)}
                placeholder="http://localhost:1234/v1"
                fullWidth
                disabled={isLoading}
                helperText="For local LLMs like LM Studio or Ollama"
              />
            )}

            <FormControl fullWidth disabled={isLoading}>
              <InputLabel>Model Name</InputLabel>
              <Select
                value={modelName}
                label="Model Name"
                onChange={(e) => setModelName(e.target.value)}
              >
                {getValidModels(provider).map((model) => (
                  <MenuItem key={model} value={model}>
                    {model}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControlLabel
              control={
                <Switch
                  checked={enabled}
                  onChange={(e) => setEnabled(e.target.checked)}
                  disabled={isLoading}
                />
              }
              label="Enable AI Assistant"
            />

            {error && (
              <Alert severity="error" sx={{ mt: 1 }}>
                {error}
              </Alert>
            )}
          </Box>
        </DialogContent>

        <DialogActions>
          <Button onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={!isValid || isLoading}
          >
            {isLoading ? 'Adding...' : 'Add Credential'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
