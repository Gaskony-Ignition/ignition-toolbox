/**
 * Playbook Library Dialog - Browse and install playbooks from repository
 *
 * Shows available playbooks from the central repository with:
 * - Install button for each playbook
 * - Filtering by domain (Gateway/Perspective)
 * - Search functionality
 * - Verified badges
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
  TextField,
  InputAdornment,
  Chip,
  Card,
  CardContent,
  CardActions,
  Alert,
  CircularProgress,
  Tab,
  Tabs,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Search as SearchIcon,
  Close as CloseIcon,
  Download as DownloadIcon,
  Verified as VerifiedIcon,
  Refresh as RefreshIcon,
  Description as DescriptionIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

interface AvailablePlaybook {
  playbook_path: string;
  version: string;
  domain: string;
  verified: boolean;
  verified_by?: string;
  description: string;
  author: string;
  tags: string[];
  group: string;
  size_bytes: number;
  dependencies: string[];
  release_notes?: string;
}

interface BrowseResponse {
  status: string;
  count: number;
  playbooks: AvailablePlaybook[];
  last_fetched?: string;
  message?: string;
}

interface PlaybookLibraryDialogProps {
  open: boolean;
  onClose: () => void;
}

export function PlaybookLibraryDialog({ open, onClose }: PlaybookLibraryDialogProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDomain, setSelectedDomain] = useState<string>('all');
  const [installing, setInstalling] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // Fetch available playbooks
  const { data, isLoading, error, refetch } = useQuery<BrowseResponse>({
    queryKey: ['playbook-library'],
    queryFn: async () => {
      const response = await fetch(`${api.getBaseUrl()}/api/playbooks/browse`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to fetch playbook library');
      }
      return response.json();
    },
    enabled: open, // Only fetch when dialog is open
    retry: 1, // Only retry once to avoid excessive waiting
  });

  // Install mutation
  const installMutation = useMutation({
    mutationFn: async (playbookPath: string) => {
      const response = await fetch(`${api.getBaseUrl()}/api/playbooks/install`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          playbook_path: playbookPath,
          version: 'latest',
          verify_checksum: true,
        }),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Installation failed');
      }
      return response.json();
    },
    onSuccess: () => {
      // Refresh playbook list
      queryClient.invalidateQueries({ queryKey: ['playbooks'] });
      queryClient.invalidateQueries({ queryKey: ['playbook-library'] });
      setInstalling(null);
    },
    onError: (error: Error) => {
      console.error('Installation failed:', error);
      setInstalling(null);
      alert(`Installation failed: ${error.message}`);
    },
  });

  const handleInstall = async (playbookPath: string) => {
    setInstalling(playbookPath);
    installMutation.mutate(playbookPath);
  };

  const handleRefresh = () => {
    refetch();
  };

  // Filter playbooks
  const filteredPlaybooks = data?.playbooks.filter((pb) => {
    // Domain filter
    if (selectedDomain !== 'all' && pb.domain !== selectedDomain) {
      return false;
    }

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        pb.playbook_path.toLowerCase().includes(query) ||
        pb.description.toLowerCase().includes(query) ||
        pb.author.toLowerCase().includes(query) ||
        pb.tags.some((tag) => tag.toLowerCase().includes(query))
      );
    }

    return true;
  }) || [];

  // Group playbooks by domain
  const gatewayPlaybooks = filteredPlaybooks.filter((pb) => pb.domain === 'gateway');
  const perspectivePlaybooks = filteredPlaybooks.filter((pb) => pb.domain === 'perspective');
  const designerPlaybooks = filteredPlaybooks.filter((pb) => pb.domain === 'designer');

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Playbook Library</Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Refresh library">
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
        {/* Header with search and filters */}
        <Box sx={{ mb: 3 }}>
          <TextField
            fullWidth
            placeholder="Search playbooks by name, description, author, or tags..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
            sx={{ mb: 2 }}
          />

          <Tabs
            value={selectedDomain}
            onChange={(_, newValue) => setSelectedDomain(newValue)}
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            <Tab label={`All (${filteredPlaybooks.length})`} value="all" />
            <Tab label={`Gateway (${gatewayPlaybooks.length})`} value="gateway" />
            <Tab label={`Perspective (${perspectivePlaybooks.length})`} value="perspective" />
            <Tab label={`Designer (${designerPlaybooks.length})`} value="designer" />
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
            Failed to load playbook library: {error instanceof Error ? error.message : 'Unknown error'}
          </Alert>
        )}

        {/* Empty state */}
        {!isLoading && !error && filteredPlaybooks.length === 0 && (
          <Alert severity="info">
            {data?.playbooks.length === 0
              ? (data?.message || 'The playbook library is not yet available. You can create and duplicate playbooks locally.')
              : 'No playbooks match your search criteria.'}
          </Alert>
        )}

        {/* Playbook grid */}
        {!isLoading && !error && filteredPlaybooks.length > 0 && (
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
            {filteredPlaybooks.map((playbook) => (
              <Card key={playbook.playbook_path} variant="outlined" sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                      <Typography variant="h6" component="div" sx={{ fontSize: '1rem', fontWeight: 600 }}>
                        {playbook.playbook_path.split('/')[1]}
                      </Typography>
                      {playbook.verified && (
                        <Tooltip title={`Verified by ${playbook.verified_by}`}>
                          <VerifiedIcon color="primary" fontSize="small" />
                        </Tooltip>
                      )}
                    </Box>

                    <Chip
                      label={playbook.domain}
                      size="small"
                      color={
                        playbook.domain === 'gateway'
                          ? 'primary'
                          : playbook.domain === 'perspective'
                          ? 'secondary'
                          : 'default'
                      }
                      sx={{ mb: 1 }}
                    />
                    <Chip label={`v${playbook.version}`} size="small" variant="outlined" sx={{ mb: 1, ml: 1 }} />

                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {playbook.description}
                    </Typography>

                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                      Author: {playbook.author}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                      Size: {formatBytes(playbook.size_bytes)}
                    </Typography>

                    {playbook.tags.length > 0 && (
                      <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {playbook.tags.slice(0, 3).map((tag) => (
                          <Chip key={tag} label={tag} size="small" variant="outlined" sx={{ height: 20 }} />
                        ))}
                      </Box>
                    )}

                    {playbook.release_notes && (
                      <Tooltip title={playbook.release_notes}>
                        <DescriptionIcon fontSize="small" sx={{ mt: 1, color: 'text.secondary' }} />
                      </Tooltip>
                    )}
                  </CardContent>

                  <CardActions>
                    <Button
                      size="small"
                      variant="contained"
                      startIcon={installing === playbook.playbook_path ? <CircularProgress size={16} /> : <DownloadIcon />}
                      onClick={() => handleInstall(playbook.playbook_path)}
                      disabled={installing !== null}
                      fullWidth
                    >
                      {installing === playbook.playbook_path ? 'Installing...' : 'Install'}
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
              Showing {filteredPlaybooks.length} of {data.playbooks.length} available playbooks
              {data.last_fetched && ` • Last updated: ${new Date(data.last_fetched).toLocaleString()}`}
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
