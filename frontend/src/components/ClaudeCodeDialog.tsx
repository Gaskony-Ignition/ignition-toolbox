/**
 * ClaudeCodeDialog - Shows Claude Code integration command
 *
 * Displays a dialog with a pre-generated Claude Code command that includes
 * full execution context and playbook file path. User can copy and run manually.
 */

import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Alert,
  TextField,
  IconButton,
  Tooltip,
  CircularProgress,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import {
  ContentCopy as CopyIcon,
  Terminal as TerminalIcon,
  CheckCircle as CheckIcon,
  Code as CodeIcon,
  Computer as ComputerIcon,
} from '@mui/icons-material';
import { useMutation } from '@tanstack/react-query';
import api from '../api/client';
import { EmbeddedTerminal } from './EmbeddedTerminal';
import { createLogger } from '../utils/logger';

const logger = createLogger('ClaudeCodeDialog');

interface ClaudeCodeDialogProps {
  open: boolean;
  onClose: () => void;
  executionId: string;
}

type ClaudeCodeMode = 'embedded' | 'manual';

export function ClaudeCodeDialog({
  open,
  onClose,
  executionId,
}: ClaudeCodeDialogProps) {
  const [copied, setCopied] = useState(false);
  const [mode, setMode] = useState<ClaudeCodeMode>('embedded');
  const [terminalError, setTerminalError] = useState<string | null>(null);

  // Fetch Claude Code session command
  const sessionMutation = useMutation({
    mutationFn: () =>
      api.executions.getClaudeCodeSession(executionId),
    onSuccess: () => {
      setCopied(false);
    },
  });

  // Load session when dialog opens
  const handleOpen = () => {
    if (open && !sessionMutation.data && !sessionMutation.isPending) {
      sessionMutation.mutate();
    }
  };

  // Handle copy to clipboard
  const handleCopy = async () => {
    if (sessionMutation.data?.command) {
      try {
        await navigator.clipboard.writeText(sessionMutation.data.command);
        setCopied(true);
        setTimeout(() => setCopied(false), 3000);
      } catch (err) {
        logger.error('Failed to copy:', err);
      }
    }
  };

  // Auto-load on open
  if (open && !sessionMutation.data && !sessionMutation.isPending && !sessionMutation.isError) {
    handleOpen();
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth={mode === 'embedded' ? 'lg' : 'md'}
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: 'background.paper',
          backgroundImage: 'none',
          height: mode === 'embedded' ? '80vh' : 'auto',
        },
      }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <TerminalIcon />
          Claude Code Integration
        </Box>

        <ToggleButtonGroup
          value={mode}
          exclusive
          onChange={(_, newMode) => {
            if (newMode !== null) {
              setMode(newMode);
            }
          }}
          size="small"
          sx={{ ml: 'auto' }}
        >
          <ToggleButton value="embedded">
            <ComputerIcon fontSize="small" sx={{ mr: 0.5 }} />
            Embedded
          </ToggleButton>
          <ToggleButton value="manual">
            <CodeIcon fontSize="small" sx={{ mr: 0.5 }} />
            Manual
          </ToggleButton>
        </ToggleButtonGroup>
      </DialogTitle>

      <DialogContent sx={{ display: 'flex', flexDirection: 'column', height: mode === 'embedded' ? '100%' : 'auto' }}>
        {sessionMutation.isPending && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {sessionMutation.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Failed to generate Claude Code session.{' '}
            {sessionMutation.error instanceof Error
              ? sessionMutation.error.message
              : 'Unknown error'}
          </Alert>
        )}

        {mode === 'embedded' && (
          <>
            {terminalError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {terminalError}
              </Alert>
            )}

            <Alert severity="info" icon={<TerminalIcon />} sx={{ mb: 2 }}>
              <Typography variant="body2" fontWeight="bold">
                Embedded Claude Code Terminal
              </Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                Claude Code is running in the terminal below. You can type commands and interact
                with it directly. The playbook file is already loaded with execution context.
              </Typography>
            </Alert>

            <Box sx={{ flexGrow: 1, minHeight: 400, mb: 2 }}>
              <EmbeddedTerminal
                executionId={executionId}
                onClose={onClose}
                onError={setTerminalError}
              />
            </Box>
          </>
        )}

        {mode === 'manual' && sessionMutation.data && (
          <>
            <Alert severity="info" icon={<TerminalIcon />} sx={{ mb: 2 }}>
              <Typography variant="body2" fontWeight="bold">
                Claude Code Integration (Manual)
              </Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                Copy the command below and run it in your terminal. This will open Claude Code
                with full access to your playbook file and execution context.
              </Typography>
            </Alert>

            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
                Playbook File:
              </Typography>
              <Typography variant="body2" fontFamily="monospace">
                {sessionMutation.data.playbook_path}
              </Typography>
            </Box>

            <Box sx={{ mb: 2 }}>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  mb: 0.5,
                }}
              >
                <Typography variant="caption" color="text.secondary">
                  Command:
                </Typography>
                <Tooltip title={copied ? 'Copied!' : 'Copy to clipboard'}>
                  <IconButton
                    size="small"
                    onClick={handleCopy}
                    color={copied ? 'success' : 'default'}
                  >
                    {copied ? <CheckIcon fontSize="small" /> : <CopyIcon fontSize="small" />}
                  </IconButton>
                </Tooltip>
              </Box>
              <TextField
                fullWidth
                multiline
                rows={6}
                value={sessionMutation.data.command}
                variant="outlined"
                InputProps={{
                  readOnly: true,
                  sx: {
                    fontFamily: 'monospace',
                    fontSize: '0.75rem',
                    bgcolor: 'background.default',
                  },
                }}
              />
            </Box>

            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
                Execution Context:
              </Typography>
              <Box
                sx={{
                  p: 1.5,
                  bgcolor: 'background.default',
                  borderRadius: 1,
                  border: '1px solid',
                  borderColor: 'divider',
                  maxHeight: 200,
                  overflow: 'auto',
                }}
              >
                <Typography
                  variant="body2"
                  fontFamily="monospace"
                  fontSize="0.75rem"
                  sx={{ whiteSpace: 'pre-wrap' }}
                >
                  {sessionMutation.data.context_message}
                </Typography>
              </Box>
            </Box>

            <Alert severity="warning" sx={{ mb: 1 }}>
              <Typography variant="caption">
                <strong>Note:</strong> Claude Code must be installed and accessible via the{' '}
                <code>claude-code</code> command. Claude Code will be able to read and edit the
                playbook file with your approval.
              </Typography>
            </Alert>
          </>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} variant="outlined">
          Close
        </Button>
        {mode === 'manual' && sessionMutation.data && (
          <Button
            onClick={handleCopy}
            variant="contained"
            startIcon={copied ? <CheckIcon /> : <CopyIcon />}
            color={copied ? 'success' : 'primary'}
          >
            {copied ? 'Copied!' : 'Copy Command'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
