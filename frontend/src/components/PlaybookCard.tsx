/**
 * PlaybookCard - Display playbook information with action button
 */

import { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  Box,
  Divider,
  List,
  ListItem,
  ListItemText,
  Tooltip,
  IconButton,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
  Switch,
  FormControlLabel,
  TextField,
} from '@mui/material';
import {
  Settings as ConfigureIcon,
  PlayArrow as PlayIcon,
  Warning as WarningIcon,
  Download as DownloadIcon,
  MoreVert as MoreVertIcon,
  List as ViewStepsIcon,
  Verified as VerifiedIcon,
  ToggleOn as EnableIcon,
  ToggleOff as DisableIcon,
  Info as InfoIcon,
  Close as ClearIcon,
  BugReport as DebugIcon,
  Edit as EditIcon,
  Check as SaveIcon,
  Cancel as CancelIcon,
  Delete as DeleteIcon,
  Schedule as ScheduleIcon,
  ContentCopy as DuplicateIcon,
  CheckCircle as ConfiguredIcon,
  RadioButtonUnchecked as NotConfiguredIcon,
} from '@mui/icons-material';
import type { PlaybookInfo } from '../types/api';
import { useStore } from '../store';
import { api } from '../api/client';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import ScheduleDialog from './ScheduleDialog';

interface PlaybookCardProps {
  playbook: PlaybookInfo;
  onConfigure: (playbook: PlaybookInfo) => void;
  onExecute?: (playbook: PlaybookInfo) => void;
  onExport?: (playbook: PlaybookInfo) => void;
  onViewSteps?: (playbook: PlaybookInfo) => void;
}

// Get saved config for preview
interface SavedConfig {
  parameters: Record<string, string>;
  savedAt: string;
}

function getSavedConfigPreview(playbookPath: string): SavedConfig | null {
  const stored = localStorage.getItem(`playbook_config_${playbookPath}`);
  return stored ? JSON.parse(stored) : null;
}

// Verification status is now based on playbook.verified property

export function PlaybookCard({ playbook, onConfigure, onExecute, onExport, onViewSteps }: PlaybookCardProps) {
  const queryClient = useQueryClient();
  const [savedConfig, setSavedConfig] = useState<SavedConfig | null>(getSavedConfigPreview(playbook.path));
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [debugMode, setDebugMode] = useState(() => {
    const stored = localStorage.getItem(`playbook_debug_${playbook.path}`);
    return stored === 'true';
  });
  const [scheduleMode, setScheduleMode] = useState(() => {
    const stored = localStorage.getItem(`playbook_schedule_mode_${playbook.path}`);
    return stored === 'true';
  });
  const [scheduleDialogOpen, setScheduleDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editedName, setEditedName] = useState(playbook.name);
  const [editedDescription, setEditedDescription] = useState(playbook.description);
  const [duplicateDialogOpen, setDuplicateDialogOpen] = useState(false);
  const [duplicateName, setDuplicateName] = useState('');
  const selectedCredential = useStore((state) => state.selectedCredential);

  const isDisabled = !playbook.enabled;

  // Check if required parameters are configured
  const areParamsConfigured = (): boolean => {
    // If there are no parameters, consider it configured
    if (!playbook.parameters || playbook.parameters.length === 0) {
      return true;
    }

    // Check if a global credential is selected (covers gateway_url, username, password)
    const hasGlobalCredential = !!selectedCredential;

    // Parameters that are covered by the global credential selection
    const credentialCoveredParams = ['gateway_url', 'username', 'password', 'user', 'pass', 'credential_name'];

    // Get required parameters that need user input (exclude credential-related ones)
    const requiredUserParams = playbook.parameters.filter(
      p => p.required &&
           p.default === null &&
           !credentialCoveredParams.some(cp => p.name.toLowerCase().includes(cp.toLowerCase()))
    );

    // If we have a global credential, the credential params are covered
    // Now check if other required params are configured
    if (hasGlobalCredential) {
      // No other required params? We're good!
      if (requiredUserParams.length === 0) {
        return true;
      }

      // Check saved config for remaining required params
      if (savedConfig) {
        const configuredParams = Object.keys(savedConfig.parameters);
        const allRequiredConfigured = requiredUserParams.every(
          p => configuredParams.includes(p.name) && savedConfig.parameters[p.name] !== ''
        );
        if (allRequiredConfigured) {
          return true;
        }
      }
    }

    // No global credential - need to check if everything is in saved config
    // But since credentials are stripped from saved config, without global credential
    // we can't be fully configured
    return false;
  };

  const paramsConfigured = areParamsConfigured();

  // Check for saved config updates periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setSavedConfig(getSavedConfigPreview(playbook.path));
    }, 1000);
    return () => clearInterval(interval);
  }, [playbook.path]);

  // Mutation for verifying playbook
  const verifyMutation = useMutation({
    mutationFn: () => api.playbooks.verify(playbook.path),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['playbooks'] });
      setSnackbarMessage('Playbook marked as verified');
      setSnackbarOpen(true);
      setMenuAnchor(null);
    },
    onError: (error) => {
      setSnackbarMessage(`Failed to verify: ${(error as Error).message}`);
      setSnackbarOpen(true);
    },
  });

  // Mutation for unverifying playbook
  const unverifyMutation = useMutation({
    mutationFn: () => api.playbooks.unverify(playbook.path),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['playbooks'] });
      setSnackbarMessage('Playbook verification removed');
      setSnackbarOpen(true);
      setMenuAnchor(null);
    },
    onError: (error) => {
      setSnackbarMessage(`Failed to unverify: ${(error as Error).message}`);
      setSnackbarOpen(true);
    },
  });

  // Mutation for enabling playbook
  const enableMutation = useMutation({
    mutationFn: () => api.playbooks.enable(playbook.path),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['playbooks'] });
      setSnackbarMessage('Playbook enabled');
      setSnackbarOpen(true);
      setMenuAnchor(null);
    },
    onError: (error) => {
      setSnackbarMessage(`Failed to enable: ${(error as Error).message}`);
      setSnackbarOpen(true);
    },
  });

  // Mutation for disabling playbook
  const disableMutation = useMutation({
    mutationFn: () => api.playbooks.disable(playbook.path),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['playbooks'] });
      setSnackbarMessage('Playbook disabled');
      setSnackbarOpen(true);
      setMenuAnchor(null);
    },
    onError: (error) => {
      setSnackbarMessage(`Failed to disable: ${(error as Error).message}`);
      setSnackbarOpen(true);
    },
  });

  // Mutation for updating playbook metadata
  const updateMetadataMutation = useMutation({
    mutationFn: ({ name, description }: { name?: string; description?: string }) =>
      api.playbooks.updateMetadata(playbook.path, name, description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['playbooks'] });
      setSnackbarMessage('Playbook updated successfully');
      setSnackbarOpen(true);
      setEditDialogOpen(false);
    },
    onError: (error) => {
      setSnackbarMessage(`Failed to update: ${(error as Error).message}`);
      setSnackbarOpen(true);
    },
  });

  // Mutation for deleting playbook
  const deleteMutation = useMutation({
    mutationFn: () => api.playbooks.delete(playbook.path),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['playbooks'] });
      setSnackbarMessage('Playbook deleted successfully');
      setSnackbarOpen(true);
      setMenuAnchor(null);
    },
    onError: (error) => {
      setSnackbarMessage(`Failed to delete: ${(error as Error).message}`);
      setSnackbarOpen(true);
    },
  });

  // Mutation for duplicating playbook
  const duplicateMutation = useMutation({
    mutationFn: (newName?: string) => api.playbooks.duplicate(playbook.path, newName),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['playbooks'] });
      setSnackbarMessage(`Playbook duplicated: ${data.new_path}`);
      setSnackbarOpen(true);
      setMenuAnchor(null);
      setDuplicateDialogOpen(false);
      setDuplicateName('');
    },
    onError: (error) => {
      setSnackbarMessage(`Failed to duplicate: ${(error as Error).message}`);
      setSnackbarOpen(true);
    },
  });

  const handleOpenDuplicateDialog = () => {
    setDuplicateName('');
    setDuplicateDialogOpen(true);
    setMenuAnchor(null);
  };

  const handleDuplicate = () => {
    duplicateMutation.mutate(duplicateName || undefined);
  };

  const handleOpenEditDialog = () => {
    setEditedName(playbook.name);
    setEditedDescription(playbook.description);
    setEditDialogOpen(true);
    setMenuAnchor(null);
  };

  const handleSaveEdit = () => {
    updateMetadataMutation.mutate({
      name: editedName !== playbook.name ? editedName : undefined,
      description: editedDescription !== playbook.description ? editedDescription : undefined,
    });
  };

  const handleDebugModeToggle = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newDebugMode = event.target.checked;
    setDebugMode(newDebugMode);
    localStorage.setItem(`playbook_debug_${playbook.path}`, newDebugMode.toString());
  };

  const handleScheduleModeToggle = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newScheduleMode = event.target.checked;
    setScheduleMode(newScheduleMode);
    localStorage.setItem(`playbook_schedule_mode_${playbook.path}`, newScheduleMode.toString());
  };

  const handleExecuteClick = () => {
    if (onExecute) {
      onExecute(playbook);
    } else {
      // Fallback to configure if no execute handler
      onConfigure(playbook);
    }
  };

  return (
    <Card
      elevation={3}
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        opacity: isDisabled ? 0.7 : 1,
        border: '2px solid',
        borderColor: isDisabled ? 'warning.main' : 'divider',
        borderRadius: 2,
        backgroundColor: 'background.paper',
        transition: 'all 0.3s ease-in-out',
        '&:hover': {
          transform: 'translateY(-6px)',
          boxShadow: (theme) => theme.shadows[12],
          borderColor: isDisabled ? 'warning.main' : 'primary.main',
          borderWidth: isDisabled ? '2px' : '3px',
          backgroundColor: 'action.hover',
        },
        cursor: 'grab',
      }}
    >
      <CardContent sx={{ flexGrow: 1, pb: 0 }}>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <Typography variant="h6" gutterBottom sx={{ flexGrow: 1 }}>
            {playbook.name}
          </Typography>

          {/* Menu Button */}
          {onExport && (
            <IconButton
              size="small"
              onClick={(e) => setMenuAnchor(e.currentTarget)}
              sx={{ ml: 1 }}
            >
              <MoreVertIcon fontSize="small" />
            </IconButton>
          )}

          {/* Verification Status Icon */}
          {!playbook.verified && (
            <Tooltip title="Unverified - use with caution">
              <WarningIcon color="warning" fontSize="small" />
            </Tooltip>
          )}
        </Box>

        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            mb: 2,
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            lineHeight: 1.5,
          }}
        >
          {playbook.description}
        </Typography>

        <Box sx={{ display: 'flex', gap: 1, mb: 1, flexWrap: 'wrap' }}>
          <Chip
            label={`v${playbook.version}.r${playbook.revision}`}
            size="small"
            color="primary"
            variant="outlined"
          />
          <Chip
            label={`${playbook.step_count} steps`}
            size="small"
            variant="outlined"
          />
          {playbook.parameter_count > 0 && (
            <Tooltip title={paramsConfigured ? 'Parameters configured' : 'Parameters need configuration'}>
              <Chip
                icon={paramsConfigured ? <ConfiguredIcon /> : <NotConfiguredIcon />}
                label="params"
                size="small"
                color={paramsConfigured ? 'success' : 'default'}
                variant="outlined"
              />
            </Tooltip>
          )}
          {playbook.verified && (
            <Chip
              icon={<VerifiedIcon />}
              label="Verified"
              size="small"
              color="success"
              variant="outlined"
            />
          )}
          {!playbook.enabled && (
            <Chip
              label="Disabled"
              size="small"
              color="warning"
              variant="outlined"
            />
          )}
        </Box>

        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
          {playbook.path.split('/').slice(-2).join('/')}
        </Typography>

        {/* Mode Toggles - Debug and Schedule */}
        <Box sx={{ mt: 1, mb: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2 }}>
          {/* Debug Mode Toggle - Left */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <DebugIcon fontSize="small" color={debugMode ? 'primary' : 'disabled'} />
            <FormControlLabel
              control={
                <Switch
                  checked={debugMode}
                  onChange={handleDebugModeToggle}
                  size="small"
                  color="primary"
                />
              }
              label={
                <Typography variant="caption" color={debugMode ? 'primary' : 'text.secondary'} fontWeight={debugMode ? 'bold' : 'normal'}>
                  Debug
                </Typography>
              }
            />
          </Box>

          {/* Schedule Mode Toggle - Right */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <ScheduleIcon fontSize="small" color={scheduleMode ? 'secondary' : 'disabled'} />
            <FormControlLabel
              control={
                <Switch
                  checked={scheduleMode}
                  onChange={handleScheduleModeToggle}
                  size="small"
                  color="secondary"
                />
              }
              label={
                <Typography variant="caption" color={scheduleMode ? 'secondary' : 'text.secondary'} fontWeight={scheduleMode ? 'bold' : 'normal'}>
                  Schedule
                </Typography>
              }
            />
          </Box>
        </Box>

      </CardContent>

      <CardActions sx={{ pt: 0, gap: 1, flexWrap: 'wrap' }}>
        {/* Configure Button */}
        <Tooltip title="Configure parameters for this playbook">
          <span style={{ flex: 1, minWidth: scheduleMode ? '100px' : 'auto' }}>
            <Button
              size="small"
              variant="outlined"
              startIcon={<ConfigureIcon />}
              onClick={() => onConfigure(playbook)}
              fullWidth
              disabled={isDisabled}
              aria-label={`Configure ${playbook.name} playbook`}
            >
              Configure
            </Button>
          </span>
        </Tooltip>

        {/* Schedule Button - Only visible when Schedule Mode is enabled */}
        {scheduleMode && (
          <Tooltip title="Set up a schedule for this playbook">
            <span style={{ flex: 1, minWidth: '100px' }}>
              <Button
                size="small"
                variant="outlined"
                color="secondary"
                startIcon={<ScheduleIcon />}
                onClick={() => setScheduleDialogOpen(true)}
                fullWidth
                disabled={isDisabled}
                aria-label={`Schedule ${playbook.name} playbook`}
              >
                Schedule
              </Button>
            </span>
          </Tooltip>
        )}

        {/* Execute Button */}
        <Tooltip title={
          isDisabled ? 'Enable this playbook first' :
          selectedCredential ? `Execute with global credential: ${selectedCredential.name}` :
          savedConfig ? 'Execute with saved configuration' :
          'Select a global credential or configure this playbook first'
        }>
          <span style={{ flex: 1 }}>
            <Button
              size="small"
              variant="contained"
              startIcon={<PlayIcon />}
              onClick={handleExecuteClick}
              fullWidth
              disabled={isDisabled || (!savedConfig && !selectedCredential)}
              aria-label={`Execute ${playbook.name} playbook`}
            >
              Execute
            </Button>
          </span>
        </Tooltip>
      </CardActions>

      {/* Menu for all options */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={() => setMenuAnchor(null)}
      >
        {/* Show Details */}
        <MenuItem
          onClick={() => {
            setMenuAnchor(null);
            setDetailsDialogOpen(true);
          }}
        >
          <InfoIcon fontSize="small" sx={{ mr: 1 }} />
          Show Details
        </MenuItem>

        {/* Clear Saved Config */}
        {savedConfig && Object.keys(savedConfig.parameters).length > 0 && (
          <MenuItem
            onClick={() => {
              localStorage.removeItem(`playbook_config_${playbook.path}`);
              setSavedConfig(null);
              setMenuAnchor(null);
              setSnackbarMessage('Saved configuration cleared');
              setSnackbarOpen(true);
            }}
          >
            <ClearIcon fontSize="small" sx={{ mr: 1 }} />
            Clear Saved Config
          </MenuItem>
        )}

        <Divider />

        {/* Edit Playbook */}
        <MenuItem onClick={handleOpenEditDialog}>
          <EditIcon fontSize="small" sx={{ mr: 1 }} />
          Edit Playbook
        </MenuItem>

        {/* Duplicate Playbook */}
        <MenuItem
          onClick={handleOpenDuplicateDialog}
          disabled={duplicateMutation.isPending}
        >
          <DuplicateIcon fontSize="small" sx={{ mr: 1 }} />
          Duplicate Playbook
        </MenuItem>

        <Divider />

        {/* Verify/Unverify */}
        {playbook.verified ? (
          <MenuItem
            onClick={() => unverifyMutation.mutate()}
            disabled={unverifyMutation.isPending}
          >
            <VerifiedIcon fontSize="small" sx={{ mr: 1 }} />
            Remove Verification
          </MenuItem>
        ) : (
          <MenuItem
            onClick={() => verifyMutation.mutate()}
            disabled={verifyMutation.isPending}
          >
            <VerifiedIcon fontSize="small" sx={{ mr: 1 }} />
            Mark as Verified
          </MenuItem>
        )}

        {/* Enable/Disable */}
        {playbook.enabled ? (
          <MenuItem
            onClick={() => disableMutation.mutate()}
            disabled={disableMutation.isPending}
          >
            <DisableIcon fontSize="small" sx={{ mr: 1 }} />
            Disable Playbook
          </MenuItem>
        ) : (
          <MenuItem
            onClick={() => enableMutation.mutate()}
            disabled={enableMutation.isPending}
          >
            <EnableIcon fontSize="small" sx={{ mr: 1 }} />
            Enable Playbook
          </MenuItem>
        )}

        <Divider />

        {/* View All Steps */}
        {onViewSteps && (
          <MenuItem
            onClick={() => {
              setMenuAnchor(null);
              onViewSteps(playbook);
            }}
          >
            <ViewStepsIcon fontSize="small" sx={{ mr: 1 }} />
            View All Steps
          </MenuItem>
        )}

        {/* Export */}
        <MenuItem
          onClick={() => {
            setMenuAnchor(null);
            onExport?.(playbook);
          }}
        >
          <DownloadIcon fontSize="small" sx={{ mr: 1 }} />
          Export Playbook
        </MenuItem>

        <Divider />

        {/* Delete Playbook */}
        <MenuItem
          onClick={() => {
            if (window.confirm(`Are you sure you want to delete "${playbook.name}"? This cannot be undone.`)) {
              deleteMutation.mutate();
            }
          }}
          disabled={deleteMutation.isPending}
          sx={{ color: 'error.main' }}
        >
          <DeleteIcon fontSize="small" sx={{ mr: 1 }} />
          Delete Playbook
        </MenuItem>
      </Menu>

      {/* Edit Dialog */}
      <Dialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Edit Playbook</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Playbook Name"
              value={editedName}
              onChange={(e) => setEditedName(e.target.value)}
              fullWidth
              variant="outlined"
              size="small"
            />
            <TextField
              label="Description"
              value={editedDescription}
              onChange={(e) => setEditedDescription(e.target.value)}
              fullWidth
              multiline
              rows={3}
              variant="outlined"
              size="small"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)} startIcon={<CancelIcon />}>
            Cancel
          </Button>
          <Button
            onClick={handleSaveEdit}
            variant="contained"
            startIcon={<SaveIcon />}
            disabled={updateMetadataMutation.isPending || (editedName === playbook.name && editedDescription === playbook.description)}
          >
            {updateMetadataMutation.isPending ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Duplicate Dialog */}
      <Dialog
        open={duplicateDialogOpen}
        onClose={() => setDuplicateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Duplicate Playbook</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Creating a copy of: <strong>{playbook.name}</strong>
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Location: {playbook.path.split('/')[0]}/
            </Typography>
            <TextField
              label="New Playbook Name"
              value={duplicateName}
              onChange={(e) => setDuplicateName(e.target.value)}
              fullWidth
              variant="outlined"
              size="small"
              placeholder="Leave empty for auto-generated name"
              helperText="Enter a new name or leave empty to use auto-generated name"
              autoFocus
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDuplicateDialogOpen(false)} startIcon={<CancelIcon />}>
            Cancel
          </Button>
          <Button
            onClick={handleDuplicate}
            variant="contained"
            startIcon={<DuplicateIcon />}
            disabled={duplicateMutation.isPending}
          >
            {duplicateMutation.isPending ? 'Duplicating...' : 'Duplicate'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Details Dialog */}
      <Dialog
        open={detailsDialogOpen}
        onClose={() => setDetailsDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>{playbook.name} - Details</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 1 }}>
            <Typography variant="caption" color="text.secondary" fontWeight="bold">
              Steps ({playbook.step_count}):
            </Typography>
            <List dense sx={{ py: 0 }}>
              {playbook.steps && playbook.steps.length > 0 ? (
                playbook.steps.map((step, index) => (
                  <ListItem key={step.id} sx={{ py: 0.5 }}>
                    <ListItemText
                      primary={
                        <Typography variant="caption" color="text.secondary">
                          {index + 1}. {step.name}
                        </Typography>
                      }
                      secondary={
                        <Typography variant="caption" color="text.secondary">
                          Type: {step.type} | Timeout: {step.timeout}s
                        </Typography>
                      }
                    />
                  </ListItem>
                ))
              ) : (
                <ListItem sx={{ py: 0.5 }}>
                  <ListItemText
                    primary={
                      <Typography variant="caption" color="text.secondary">
                        • {playbook.step_count} step(s)
                      </Typography>
                    }
                  />
                </ListItem>
              )}
            </List>

            {playbook.parameter_count > 0 && (
              <>
                <Typography variant="caption" color="text.secondary" fontWeight="bold" sx={{ mt: 2 }}>
                  Required Parameters:
                </Typography>
                <List dense sx={{ py: 0 }}>
                  <ListItem sx={{ py: 0.5 }}>
                    <ListItemText
                      primary={
                        <Typography variant="caption" color="text.secondary">
                          • Gateway URL
                        </Typography>
                      }
                    />
                  </ListItem>
                  <ListItem sx={{ py: 0.5 }}>
                    <ListItemText
                      primary={
                        <Typography variant="caption" color="text.secondary">
                          • Gateway Credentials
                        </Typography>
                      }
                    />
                  </ListItem>
                </List>
              </>
            )}

            {playbook.verified && playbook.verified_at && (
              <Box sx={{ mt: 2, p: 1, bgcolor: 'success.dark', borderRadius: 1 }}>
                <Typography variant="caption" color="success.light" fontWeight="bold">
                  Verified
                </Typography>
                <Typography variant="caption" color="success.light" sx={{ display: 'block' }}>
                  At: {new Date(playbook.verified_at).toLocaleString()}
                </Typography>
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Schedule Dialog */}
      <ScheduleDialog
        open={scheduleDialogOpen}
        onClose={() => setScheduleDialogOpen(false)}
        playbook={playbook}
        savedConfig={savedConfig}
      />

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={4000}
        onClose={() => setSnackbarOpen(false)}
        message={snackbarMessage}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      />
    </Card>
  );
}
