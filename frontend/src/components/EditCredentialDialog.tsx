/**
 * EditCredentialDialog - Dialog for editing existing credentials
 */

import { useState, useEffect } from 'react';
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
} from '@mui/material';
import { Visibility, VisibilityOff } from '@mui/icons-material';
import type { CredentialInfo, CredentialCreate } from '../types/api';

interface EditCredentialDialogProps {
  open: boolean;
  credential: CredentialInfo | null;
  onClose: () => void;
  onSubmit: (name: string, credential: CredentialCreate) => void;
  isLoading?: boolean;
  error?: string | null;
}

export function EditCredentialDialog({
  open,
  credential,
  onClose,
  onSubmit,
  isLoading = false,
  error = null,
}: EditCredentialDialogProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [gatewayUrl, setGatewayUrl] = useState('');
  const [description, setDescription] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Populate form when credential prop changes
  useEffect(() => {
    if (credential) {
      setUsername(credential.username);
      setPassword(''); // Don't populate password for security
      setGatewayUrl(credential.gateway_url || '');
      setDescription(credential.description || '');
    }
  }, [credential]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!username.trim() || !password.trim() || !credential) {
      return;
    }

    onSubmit(credential.name, {
      name: credential.name, // Name cannot be changed
      username: username.trim(),
      password: password.trim(),
      gateway_url: gatewayUrl.trim() || undefined,
      description: description.trim() || undefined,
    });
  };

  const handleClose = () => {
    // Reset form
    setUsername('');
    setPassword('');
    setGatewayUrl('');
    setDescription('');
    setShowPassword(false);
    onClose();
  };

  const isValid = username.trim() && password.trim();

  if (!credential) return null;

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Edit Credential: {credential.name}</DialogTitle>

      <form onSubmit={handleSubmit}>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Alert severity="info" sx={{ mb: 1 }}>
              Credential name cannot be changed. Delete and recreate if you need a different name.
            </Alert>

            <TextField
              label="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              required
              fullWidth
              autoFocus
              disabled={isLoading}
            />

            <TextField
              label="Password"
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              fullWidth
              disabled={isLoading}
              helperText="Enter new password (required to update)"
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      onClick={() => setShowPassword(!showPassword)}
                      edge="end"
                    >
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <TextField
              label="Gateway URL (Optional)"
              value={gatewayUrl}
              onChange={(e) => setGatewayUrl(e.target.value)}
              placeholder="http://localhost:8088"
              fullWidth
              disabled={isLoading}
              helperText="Gateway URL for automatic configuration"
            />

            <TextField
              label="Description (Optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Gateway administrator credentials"
              fullWidth
              multiline
              rows={2}
              disabled={isLoading}
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
            {isLoading ? 'Updating...' : 'Update Credential'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
