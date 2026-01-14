/**
 * Credentials page - Manage Gateway credentials
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
import { Add as AddIcon, Delete as DeleteIcon, Edit as EditIcon } from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { AddCredentialDialog } from '../components/AddCredentialDialog';
import { EditCredentialDialog } from '../components/EditCredentialDialog';
import type { CredentialInfo, CredentialCreate } from '../types/api';

export function Credentials() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingCredential, setEditingCredential] = useState<CredentialInfo | null>(null);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarOpen, setSnackbarOpen] = useState(false);

  // Fetch credentials
  const { data: credentials = [], isLoading, error } = useQuery<CredentialInfo[]>({
    queryKey: ['credentials'],
    queryFn: api.credentials.list,
  });

  // Add credential mutation
  const addMutation = useMutation({
    mutationFn: (credential: CredentialCreate) => api.credentials.create(credential),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] });
      setDialogOpen(false);
      setSnackbarMessage(`Credential "${data.name}" added successfully`);
      setSnackbarOpen(true);
    },
  });

  // Update credential mutation
  const updateMutation = useMutation({
    mutationFn: ({ name, credential }: { name: string; credential: CredentialCreate }) =>
      api.credentials.update(name, credential),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] });
      setEditDialogOpen(false);
      setEditingCredential(null);
      setSnackbarMessage(`Credential "${data.name}" updated successfully`);
      setSnackbarOpen(true);
    },
    onError: (error) => {
      setSnackbarMessage(`Failed to update: ${(error as Error).message}`);
      setSnackbarOpen(true);
    },
  });

  // Delete credential mutation
  const deleteMutation = useMutation({
    mutationFn: (name: string) => api.credentials.delete(name),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] });
      setSnackbarMessage(`Credential "${data.name}" deleted successfully`);
      setSnackbarOpen(true);
    },
    onError: (error) => {
      setSnackbarMessage(`Failed to delete: ${(error as Error).message}`);
      setSnackbarOpen(true);
    },
  });

  const handleAddCredential = (credential: CredentialCreate) => {
    addMutation.mutate(credential);
  };

  const handleEditCredential = (credential: CredentialInfo) => {
    setEditingCredential(credential);
    setEditDialogOpen(true);
  };

  const handleUpdateCredential = (name: string, credential: CredentialCreate) => {
    updateMutation.mutate({ name, credential });
  };

  const handleDeleteCredential = (name: string) => {
    if (!name) {
      console.error('[Credentials] handleDeleteCredential called with empty name');
      setSnackbarMessage('Error: Credential name is empty');
      setSnackbarOpen(true);
      return;
    }

    if (window.confirm(`Are you sure you want to delete credential "${name}"?`)) {
      deleteMutation.mutate(name);
    }
  };

  return (
    <Box sx={{ width: '100%', maxWidth: '100%' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" gutterBottom>
            Gateway Credentials
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Manage Gateway login credentials (stored encrypted locally)
          </Typography>
        </Box>

        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setDialogOpen(true)}
          aria-label="Add new credential"
        >
          Add Credential
        </Button>
      </Box>

      {/* Loading state */}
      {isLoading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <CircularProgress size={20} aria-label="Loading credentials" />
          <Typography variant="body2" color="text.secondary">
            Loading credentials...
          </Typography>
        </Box>
      )}

      {/* Error state */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load credentials: {(error as Error).message}
        </Alert>
      )}

      {/* Empty state */}
      {!isLoading && !error && credentials.length === 0 && (
        <Alert severity="info">
          No credentials yet. Add your first Gateway credential to get started.
        </Alert>
      )}

      {/* Credentials Table */}
      {!isLoading && !error && credentials.length > 0 && (
        <TableContainer component={Paper} sx={{ width: '100%', maxWidth: '100%' }}>
          <Table size="medium" sx={{ tableLayout: 'fixed', width: '100%' }}>
            <TableHead>
              <TableRow>
                <TableCell width="25%">Name</TableCell>
                <TableCell width="25%">Username</TableCell>
                <TableCell width="40%">Gateway URL</TableCell>
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
                    <Typography variant="body2" color="text.secondary">
                      {credential.username}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {credential.gateway_url ? (
                      <Chip
                        label={credential.gateway_url}
                        size="small"
                        variant="outlined"
                        color="primary"
                      />
                    ) : (
                      <Typography variant="body2" color="text.disabled">
                        Not set
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="Edit credential">
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={() => handleEditCredential(credential)}
                        aria-label={`Edit ${credential.name}`}
                        sx={{ mr: 1 }}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
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
      <AddCredentialDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSubmit={handleAddCredential}
        isLoading={addMutation.isPending}
        error={addMutation.error ? (addMutation.error as Error).message : null}
      />

      {/* Edit Credential Dialog */}
      <EditCredentialDialog
        open={editDialogOpen}
        credential={editingCredential}
        onClose={() => {
          setEditDialogOpen(false);
          setEditingCredential(null);
        }}
        onSubmit={handleUpdateCredential}
        isLoading={updateMutation.isPending}
        error={updateMutation.error ? (updateMutation.error as Error).message : null}
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
