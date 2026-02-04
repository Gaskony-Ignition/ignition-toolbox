/**
 * Welcome dialog for first-time users
 *
 * Shows a brief introduction to the Ignition Toolbox on first launch.
 * Uses localStorage to track if user has dismissed the dialog.
 */

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  VpnKey as KeyIcon,
  Code as CodeIcon,
  BugReport as DebugIcon,
} from '@mui/icons-material';

const STORAGE_KEY = 'ignition-toolbox-welcome-dismissed';

export function WelcomeDialog() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    // Check if user has already dismissed the welcome dialog
    const dismissed = localStorage.getItem(STORAGE_KEY);
    if (!dismissed) {
      setOpen(true);
    }
  }, []);

  const handleClose = () => {
    localStorage.setItem(STORAGE_KEY, 'true');
    setOpen(false);
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 2,
        },
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Typography variant="h5" component="span" fontWeight="bold">
          Welcome to Ignition Toolbox
        </Typography>
      </DialogTitle>

      <DialogContent>
        <Typography variant="body1" color="text.secondary" paragraph>
          Visual acceptance testing for Ignition SCADA systems. Run automated
          playbooks to test Gateway operations, Designer features, and
          Perspective views.
        </Typography>

        <Divider sx={{ my: 2 }} />

        <Typography variant="subtitle1" fontWeight="medium" gutterBottom>
          Quick Start
        </Typography>

        <List dense>
          <ListItem>
            <ListItemIcon>
              <KeyIcon color="primary" />
            </ListItemIcon>
            <ListItemText
              primary="Add Credentials"
              secondary="Go to Settings and add your Gateway credentials first"
            />
          </ListItem>

          <ListItem>
            <ListItemIcon>
              <PlayIcon color="success" />
            </ListItemIcon>
            <ListItemText
              primary="Run a Playbook"
              secondary="Select a playbook from Gateway/Perspective tabs and click Run"
            />
          </ListItem>

          <ListItem>
            <ListItemIcon>
              <DebugIcon color="warning" />
            </ListItemIcon>
            <ListItemText
              primary="Debug Mode"
              secondary="Enable debug mode to pause on failures and inspect state"
            />
          </ListItem>

          <ListItem>
            <ListItemIcon>
              <CodeIcon color="info" />
            </ListItemIcon>
            <ListItemText
              primary="Customize Playbooks"
              secondary="Duplicate existing playbooks and modify them for your needs"
            />
          </ListItem>
        </List>

        <Box
          sx={{
            mt: 2,
            p: 2,
            bgcolor: 'action.hover',
            borderRadius: 1,
          }}
        >
          <Typography variant="body2" color="text.secondary">
            Need help? Check the documentation or use the chat assistant in the
            bottom-right corner.
          </Typography>
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} variant="contained" color="primary">
          Get Started
        </Button>
      </DialogActions>
    </Dialog>
  );
}

/**
 * Reset the welcome dialog (for testing)
 */
export function resetWelcomeDialog() {
  localStorage.removeItem(STORAGE_KEY);
}
