/**
 * CredentialCard - Display credential information with delete action
 */

import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Box,
  Chip,
} from '@mui/material';
import { Delete as DeleteIcon, Key as KeyIcon } from '@mui/icons-material';
import type { CredentialInfo } from '../types/api';

interface CredentialCardProps {
  credential: CredentialInfo;
  onDelete: (name: string) => void;
}

export function CredentialCard({ credential, onDelete }: CredentialCardProps) {
  const handleDelete = () => {
    if (window.confirm(`Are you sure you want to delete credential "${credential.name}"?`)) {
      onDelete(credential.name);
    }
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <KeyIcon color="primary" />
          <Typography variant="h6">{credential.name}</Typography>
        </Box>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Username:
            </Typography>
            <Chip label={credential.username} size="small" />
          </Box>

          {credential.gateway_url && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Gateway URL:
              </Typography>
              <Chip label={credential.gateway_url} size="small" color="primary" variant="outlined" />
            </Box>
          )}

          {credential.description && (
            <Typography variant="body2" color="text.secondary">
              {credential.description}
            </Typography>
          )}

          <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
            Password: ••••••••
          </Typography>
        </Box>
      </CardContent>

      <CardActions sx={{ justifyContent: 'flex-end' }}>
        <Button
          size="small"
          color="error"
          startIcon={<DeleteIcon />}
          onClick={handleDelete}
          aria-label={`Delete ${credential.name} credential`}
        >
          Delete
        </Button>
      </CardActions>
    </Card>
  );
}
