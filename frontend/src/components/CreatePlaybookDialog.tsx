/**
 * CreatePlaybookDialog - Dialog to create a new playbook from template
 *
 * Extracted from Playbooks.tsx to reduce file size and improve maintainability.
 */

import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Box,
  Alert,
} from '@mui/material';
import type { QueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

export type PlaybookDomain = 'gateway' | 'perspective';

interface CreatePlaybookDialogProps {
  open: boolean;
  onClose: () => void;
  defaultDomain: PlaybookDomain;
  queryClient: QueryClient;
  showNotification: (message: string, severity: 'success' | 'error' | 'warning' | 'info') => void;
}

export function CreatePlaybookDialog({
  open,
  onClose,
  defaultDomain,
  queryClient,
  showNotification,
}: CreatePlaybookDialogProps) {
  const [newPlaybookName, setNewPlaybookName] = useState('');
  const [newPlaybookDescription, setNewPlaybookDescription] = useState('');
  const [newPlaybookDomain, setNewPlaybookDomain] = useState<PlaybookDomain>(defaultDomain);

  const handleCreatePlaybook = async () => {
    if (!newPlaybookName.trim()) {
      showNotification('Please enter a playbook name', 'warning');
      return;
    }

    // Create basic playbook template
    const yamlTemplate = `name: "${newPlaybookName}"
version: "1.0"
description: "${newPlaybookDescription || 'New playbook'}"
domain: ${newPlaybookDomain}

parameters:
  - name: gateway_url
    type: string
    required: true
    description: "Gateway URL (e.g., http://localhost:8088)"

  - name: username
    type: string
    required: true
    description: "Gateway admin username"

  - name: password
    type: string
    required: true
    description: "Gateway admin password"

steps:
  # Add your steps here
  - id: step1
    name: "Example Step"
    type: utility.sleep
    parameters:
      seconds: 1
    timeout: 10
    on_failure: abort

metadata:
  author: "User"
  category: "${newPlaybookDomain}"
  tags: ["custom"]
`;

    try {
      const result = await api.playbooks.create(
        newPlaybookName,
        newPlaybookDomain,
        yamlTemplate
      );

      showNotification(`Playbook created at: ${result.path}`, 'success');

      // Reset form
      setNewPlaybookName('');
      setNewPlaybookDescription('');
      setNewPlaybookDomain(defaultDomain);
      onClose();

      // Refresh playbook list via React Query
      queryClient.invalidateQueries({ queryKey: ['playbooks'] });
    } catch (error) {
      showNotification(`Failed to create playbook: ${(error as Error).message}`, 'error');
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>Create New Playbook</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Playbook Name"
            value={newPlaybookName}
            onChange={(e) => setNewPlaybookName(e.target.value)}
            fullWidth
            required
            variant="outlined"
            helperText="Give your playbook a descriptive name"
          />
          <TextField
            label="Description"
            value={newPlaybookDescription}
            onChange={(e) => setNewPlaybookDescription(e.target.value)}
            fullWidth
            multiline
            rows={2}
            variant="outlined"
            helperText="Describe what this playbook does"
          />
          <FormControl fullWidth>
            <InputLabel>Domain</InputLabel>
            <Select
              value={newPlaybookDomain}
              onChange={(e) => setNewPlaybookDomain(e.target.value as PlaybookDomain)}
              label="Domain"
            >
              <MenuItem value="gateway">Gateway</MenuItem>
              <MenuItem value="perspective">Perspective</MenuItem>
            </Select>
          </FormControl>
          <Alert severity="info">
            A basic playbook template will be created with standard parameters and a sample step.
            You can edit the YAML file after creation to add your own steps.
          </Alert>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>
          Cancel
        </Button>
        <Button
          onClick={handleCreatePlaybook}
          variant="contained"
          disabled={!newPlaybookName.trim()}
        >
          Create Playbook
        </Button>
      </DialogActions>
    </Dialog>
  );
}
