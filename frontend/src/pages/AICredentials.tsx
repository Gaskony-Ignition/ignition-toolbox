/**
 * AI Credentials page - Manage AI provider credentials
 */

import { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  Chip,
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon } from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AddAICredentialDialog, type AICredentialCreate } from '../components/AddAICredentialDialog';

interface AICredentialInfo {
  id: number;
  name: string;
  provider: string;
  api_base_url: string | null;
  model_name: string | null;
  enabled: string;
  has_api_key: boolean;
}

export function AICredentials() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarOpen, setSnackbarOpen] = useState(false);

  // Fetch AI credentials
  const { data: credentials = [], isLoading, error } = useQuery<AICredentialInfo[]>({
    queryKey: ['ai-credentials'],
    queryFn: () => fetch('/api/ai-credentials').then((r) => r.json()),
  });

  // Add credential mutation
  const addMutation = useMutation({
    mutationFn: (credential: AICredentialCreate) =>
      fetch('/api/ai-credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credential),
      }).then((r) => r.json()),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['ai-credentials'] });
      setDialogOpen(false);
      setSnackbarMessage(`AI Credential "${data.name}" added successfully`);
      setSnackbarOpen(true);
    },
  });

  // Delete credential mutation
  const deleteMutation = useMutation({
    mutationFn: (name: string) =>
      fetch(`/api/ai-credentials/${name}`, {
        method: 'DELETE',
      }).then((r) => r.json()),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['ai-credentials'] });
      setSnackbarMessage(`AI Credential "${data.name}" deleted successfully`);
      setSnackbarOpen(true);
    },
    onError: (error) => {
      setSnackbarMessage(`Failed to delete: ${(error as Error).message}`);
      setSnackbarOpen(true);
    },
  });

  const handleAddCredential = (credential: AICredentialCreate) => {
    addMutation.mutate(credential);
  };

  const handleDeleteCredential = (name: string) => {
    deleteMutation.mutate(name);
  };

  return (
    <Box sx={{ width: '100%', maxWidth: '100%' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" gutterBottom>
            AI Credentials
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Manage AI provider credentials for the debug assistant
          </Typography>
        </Box>

        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setDialogOpen(true)}
          aria-label="Add new AI credential"
        >
          Add AI Credential
        </Button>
      </Box>

      {/* Loading state */}
      {isLoading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <CircularProgress size={20} aria-label="Loading AI credentials" />
          <Typography variant="body2" color="text.secondary">
            Loading AI credentials...
          </Typography>
        </Box>
      )}

      {/* Error state */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load AI credentials: {(error as Error).message}
        </Alert>
      )}

      {/* Empty state */}
      {!isLoading && !error && credentials.length === 0 && (
        <Alert severity="info">
          No AI credentials yet. Add your first AI provider credential to enable the debug assistant.
        </Alert>
      )}

      {/* Credentials Table */}
      {!isLoading && !error && credentials.length > 0 && (
        <TableContainer component={Paper} sx={{ width: '100%', maxWidth: '100%' }}>
          <Table size="medium" sx={{ tableLayout: 'fixed', width: '100%' }}>
            <TableHead>
              <TableRow>
                <TableCell width="20%">Name</TableCell>
                <TableCell width="15%">Provider</TableCell>
                <TableCell width="25%">Model</TableCell>
                <TableCell width="20%">Base URL</TableCell>
                <TableCell width="10%">Status</TableCell>
                <TableCell width="10%" align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {credentials.map((credential) => (
                <TableRow
                  key={credential.name}
                  sx={{ '&:hover': { backgroundColor: 'action.hover' } }}
                >
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {credential.name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={credential.provider}
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {credential.model_name || 'Not set'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {credential.api_base_url ? (
                      <Typography variant="body2" color="text.secondary">
                        {credential.api_base_url}
                      </Typography>
                    ) : (
                      <Typography variant="body2" color="text.disabled">
                        Default
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={credential.enabled === 'true' ? 'Enabled' : 'Disabled'}
                      size="small"
                      color={credential.enabled === 'true' ? 'success' : 'default'}
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="Delete credential">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDeleteCredential(credential.name)}
                        aria-label={`Delete ${credential.name}`}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Add Credential Dialog */}
      <AddAICredentialDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSubmit={handleAddCredential}
        isLoading={addMutation.isPending}
        error={addMutation.error ? (addMutation.error as Error).message : null}
      />

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={4000}
        onClose={() => setSnackbarOpen(false)}
        message={snackbarMessage}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      />
    </Box>
  );
}
