/**
 * SubmitToLibraryDialog - Submit a playbook to the GitHub library
 */

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Typography,
  Box,
  Alert,
  CircularProgress,
  Chip,
  Link,
} from '@mui/material';
import {
  Store as StoreIcon,
  CheckCircle as SuccessIcon,
} from '@mui/icons-material';
import { api } from '../api/client';
import type { PlaybookInfo } from '../types/api';

interface SubmitToLibraryDialogProps {
  open: boolean;
  onClose: () => void;
  playbook: PlaybookInfo | null;
}

export function SubmitToLibraryDialog({ open, onClose, playbook }: SubmitToLibraryDialogProps) {
  const [author, setAuthor] = useState('');
  const [tags, setTags] = useState('');
  const [group, setGroup] = useState('');
  const [releaseNotes, setReleaseNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<{ commit_url: string; message: string } | null>(null);
  const [tokenConfigured, setTokenConfigured] = useState<boolean | null>(null);

  // Check token status when dialog opens
  useEffect(() => {
    if (open) {
      setError(null);
      setSuccess(null);
      setSubmitting(false);
      setAuthor('');
      setTags('');
      setGroup(playbook?.group || '');
      setReleaseNotes('');

      fetch(`${api.getBaseUrl()}/api/playbooks/github-token`)
        .then(r => r.json())
        .then(data => setTokenConfigured(data.configured))
        .catch(() => setTokenConfigured(false));
    }
  }, [open, playbook]);

  const handleSubmit = async () => {
    if (!playbook) return;
    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch(`${api.getBaseUrl()}/api/playbooks/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          playbook_path: playbook.path,
          author: author || 'Community',
          tags: tags ? tags.split(',').map(t => t.trim()).filter(Boolean) : [],
          group: group || '',
          release_notes: releaseNotes || null,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Submission failed');
      }

      const data = await response.json();
      setSuccess({
        commit_url: data.commit_url,
        message: data.message,
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <StoreIcon />
        Submit to Library
      </DialogTitle>
      <DialogContent>
        {success ? (
          <Box sx={{ textAlign: 'center', py: 2 }}>
            <SuccessIcon color="success" sx={{ fontSize: 48, mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              {success.message}
            </Typography>
            <Link href={success.commit_url} target="_blank" rel="noopener noreferrer">
              View commit on GitHub
            </Link>
          </Box>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            {tokenConfigured === false && (
              <Alert severity="warning">
                GitHub Personal Access Token not configured. Go to Settings &gt; Integrations to set it up.
              </Alert>
            )}

            {error && (
              <Alert severity="error">{error}</Alert>
            )}

            {/* Playbook preview */}
            {playbook && (
              <Box sx={{ p: 2, bgcolor: 'action.hover', borderRadius: 1 }}>
                <Typography variant="subtitle2">{playbook.name}</Typography>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                  {playbook.path} &middot; v{playbook.version} &middot; {playbook.domain}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  {playbook.description}
                </Typography>
              </Box>
            )}

            <TextField
              label="Author"
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              placeholder="Your name or handle"
              size="small"
              fullWidth
            />

            <TextField
              label="Tags"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="gateway, backup, module (comma-separated)"
              size="small"
              fullWidth
              helperText="Comma-separated tags for discoverability"
            />

            <TextField
              label="Group"
              value={group}
              onChange={(e) => setGroup(e.target.value)}
              placeholder="e.g., Gateway (Base Playbooks)"
              size="small"
              fullWidth
            />

            <TextField
              label="Release Notes"
              value={releaseNotes}
              onChange={(e) => setReleaseNotes(e.target.value)}
              placeholder="What does this playbook do? Any special instructions?"
              size="small"
              fullWidth
              multiline
              rows={3}
            />

            {tags && (
              <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                {tags.split(',').map(t => t.trim()).filter(Boolean).map(tag => (
                  <Chip key={tag} label={tag} size="small" variant="outlined" />
                ))}
              </Box>
            )}
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>
          {success ? 'Close' : 'Cancel'}
        </Button>
        {!success && (
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={submitting || tokenConfigured === false}
            startIcon={submitting ? <CircularProgress size={16} /> : <StoreIcon />}
          >
            {submitting ? 'Submitting...' : 'Submit'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
