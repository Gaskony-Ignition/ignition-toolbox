/**
 * Playbook Updates Dialog - View and apply available playbook updates
 *
 * Shows playbooks with updates available with:
 * - Current vs latest version comparison
 * - Release notes
 * - Update button for each playbook
 * - Filtering by domain
 * - Badge indicators for major/minor updates
 */

import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Card,
  CardContent,
  CardActions,
  Alert,
  CircularProgress,
  Tab,
  Tabs,
  IconButton,
  Tooltip,
  Chip,
} from '@mui/material';
import {
  Close as CloseIcon,
  SystemUpdate as UpdateIcon,
  Refresh as RefreshIcon,
  ArrowForward as ArrowForwardIcon,
  Verified as VerifiedIcon,
  NewReleases as NewReleasesIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { createLogger } from '../utils/logger';

const logger = createLogger('PlaybookUpdatesDialog');

interface PlaybookUpdate {
  playbook_path: string;
  current_version: string;
  latest_version: string;
  description: string;
  release_notes: string | null;
  domain: string;
  verified: boolean;
  verified_by: string | null;
  size_bytes: number;
  author: string;
  tags: string[];
  is_major_update: boolean;
  version_diff: number;
  download_url: string;
  checksum: string;
}

interface UpdatesResponse {
  status: string;
  checked_at: string;
  total_playbooks: number;
  updates_available: number;
  has_updates: boolean;
  last_fetched: string | null;
  updates: PlaybookUpdate[];
  major_updates: number;
  minor_updates: number;
}

interface PlaybookUpdatesDialogProps {
  open: boolean;
  onClose: () => void;
}

export function PlaybookUpdatesDialog({ open, onClose }: PlaybookUpdatesDialogProps) {
  const [selectedDomain, setSelectedDomain] = useState<string>('all');
  const [updating, setUpdating] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // Fetch available updates
  const { data, isLoading, error, refetch } = useQuery<UpdatesResponse>({
    queryKey: ['playbook-updates'],
    queryFn: async () => {
      const response = await fetch(`${api.getBaseUrl()}/api/playbooks/updates`);
      if (!response.ok) {
        throw new Error('Failed to fetch playbook updates');
      }
      return response.json();
    },
    enabled: open, // Only fetch when dialog is open
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: async (playbookPath: string) => {
      const response = await fetch(`${api.getBaseUrl()}/api/playbooks/${playbookPath}/update`, {
        method: 'POST',
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Update failed');
      }
      return response.json();
    },
    onSuccess: () => {
      // Refresh playbook list and updates
      queryClient.invalidateQueries({ queryKey: ['playbooks'] });
      queryClient.invalidateQueries({ queryKey: ['playbook-updates'] });
      setUpdating(null);
    },
    onError: (error: Error) => {
      logger.error('Update failed:', error);
      setUpdating(null);
      alert(`Update failed: ${error.message}`);
    },
  });

  const handleUpdate = async (playbookPath: string) => {
    setUpdating(playbookPath);
    updateMutation.mutate(playbookPath);
  };

  const handleRefresh = () => {
    refetch();
  };

  // Filter updates by domain
  const filteredUpdates = data?.updates.filter((update) => {
    if (selectedDomain !== 'all' && update.domain !== selectedDomain) {
      return false;
    }
    return true;
  }) || [];

  // Group by domain
  const gatewayUpdates = filteredUpdates.filter((u) => u.domain === 'gateway');
  const perspectiveUpdates = filteredUpdates.filter((u) => u.domain === 'perspective');
  const designerUpdates = filteredUpdates.filter((u) => u.domain === 'designer');

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <UpdateIcon />
            <Typography variant="h6">Playbook Updates</Typography>
            {data?.has_updates && (
              <Chip
                label={`${data.updates_available} available`}
                color="primary"
                size="small"
              />
            )}
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Refresh updates">
              <IconButton onClick={handleRefresh} size="small">
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            <IconButton onClick={onClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent>
        {/* Header with tabs */}
        <Box sx={{ mb: 3 }}>
          <Tabs
            value={selectedDomain}
            onChange={(_, newValue) => setSelectedDomain(newValue)}
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            <Tab label={`All (${filteredUpdates.length})`} value="all" />
            <Tab label={`Gateway (${gatewayUpdates.length})`} value="gateway" />
            <Tab label={`Perspective (${perspectiveUpdates.length})`} value="perspective" />
            <Tab label={`Designer (${designerUpdates.length})`} value="designer" />
          </Tabs>
        </Box>

        {/* Loading state */}
        {isLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {/* Error state */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Failed to load updates: {error instanceof Error ? error.message : 'Unknown error'}
          </Alert>
        )}

        {/* Empty state */}
        {!isLoading && !error && filteredUpdates.length === 0 && (
          <Alert severity="success">
            {data?.updates.length === 0
              ? 'All your playbooks are up to date! 🎉'
              : 'No updates available for this domain.'}
          </Alert>
        )}

        {/* Updates grid */}
        {!isLoading && !error && filteredUpdates.length > 0 && (
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: '1fr',
                sm: 'repeat(2, 1fr)',
                md: 'repeat(3, 1fr)',
              },
              gap: 2,
            }}
          >
            {filteredUpdates.map((update) => (
              <Card
                key={update.playbook_path}
                variant="outlined"
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  borderColor: update.is_major_update ? 'warning.main' : undefined,
                  borderWidth: update.is_major_update ? 2 : 1,
                }}
              >
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                      <Typography variant="h6" component="div" sx={{ fontSize: '1rem', fontWeight: 600 }}>
                        {update.playbook_path.split('/')[1]}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        {update.verified && (
                          <Tooltip title={`Verified by ${update.verified_by}`}>
                            <VerifiedIcon color="primary" fontSize="small" />
                          </Tooltip>
                        )}
                        {update.is_major_update && (
                          <Tooltip title="Major update">
                            <NewReleasesIcon color="warning" fontSize="small" />
                          </Tooltip>
                        )}
                      </Box>
                    </Box>

                    {/* Version comparison */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <Chip
                        label={`v${update.current_version}`}
                        size="small"
                        variant="outlined"
                        color="default"
                      />
                      <ArrowForwardIcon fontSize="small" color="action" />
                      <Chip
                        label={`v${update.latest_version}`}
                        size="small"
                        variant="filled"
                        color="success"
                      />
                    </Box>

                    <Chip
                      label={update.domain}
                      size="small"
                      color={
                        update.domain === 'gateway'
                          ? 'primary'
                          : update.domain === 'perspective'
                          ? 'secondary'
                          : 'default'
                      }
                      sx={{ mb: 1 }}
                    />

                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {update.description}
                    </Typography>

                    {update.release_notes && (
                      <Alert severity="info" sx={{ mt: 1, py: 0.5 }}>
                        <Typography variant="caption" sx={{ whiteSpace: 'pre-wrap' }}>
                          {update.release_notes}
                        </Typography>
                      </Alert>
                    )}

                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                      Author: {update.author}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                      Size: {formatBytes(update.size_bytes)}
                    </Typography>
                  </CardContent>

                  <CardActions>
                    <Button
                      size="small"
                      variant="contained"
                      color={update.is_major_update ? 'warning' : 'primary'}
                      startIcon={updating === update.playbook_path ? <CircularProgress size={16} /> : <UpdateIcon />}
                      onClick={() => handleUpdate(update.playbook_path)}
                      disabled={updating !== null}
                      fullWidth
                    >
                      {updating === update.playbook_path ? 'Updating...' : 'Update'}
                    </Button>
                  </CardActions>
                </Card>
            ))}
          </Box>
        )}

        {/* Footer info */}
        {data && (
          <Box sx={{ mt: 3, pt: 2, borderTop: 1, borderColor: 'divider' }}>
            <Typography variant="caption" color="text.secondary">
              {data.updates_available} update{data.updates_available !== 1 ? 's' : ''} available
              ({data.major_updates} major, {data.minor_updates} minor)
              {data.last_fetched && ` • Last checked: ${new Date(data.checked_at).toLocaleString()}`}
            </Typography>
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
