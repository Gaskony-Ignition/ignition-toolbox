/**
 * TerminalOpener - Opens terminal in playbooks directory with Claude Code instructions
 *
 * Simple component that opens a new terminal window/tab pointing to the playbooks
 * directory where CLAUDE_CODE_INSTRUCTIONS.md provides context for Claude Code.
 */

import { useEffect, useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  Terminal as TerminalIcon,
  Article as ArticleIcon,
  Folder as FolderIcon,
  Code as CodeIcon,
  CheckCircle as CheckIcon,
} from '@mui/icons-material';

interface TerminalOpenerProps {
  open: boolean;
  onClose: () => void;
  executionId: string;
}

export function TerminalOpener({
  open,
  onClose,
}: TerminalOpenerProps) {
  const [playbooksPath, setPlaybooksPath] = useState<string>('./playbooks'); // Default

  // PORTABILITY: Fetch playbooks path from config API on mount
  useEffect(() => {
    fetch('/api/config')
      .then(res => res.json())
      .then(config => {
        if (config.paths?.playbooks_dir) {
          setPlaybooksPath(config.paths.playbooks_dir);
        }
      })
      .catch(err => {
        console.warn('Failed to fetch config, using default playbooks path:', err);
        // Keep default './playbooks'
      });
  }, []);

  const handleOpenTerminal = () => {
    // For now, just provide instructions since direct terminal opening requires system integration
    alert(`Terminal Opening Instructions:\n\n1. Open your terminal application\n2. Run: cd ${playbooksPath}\n3. Run: claude-code\n4. Refer to CLAUDE_CODE_INSTRUCTIONS.md for context`);
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: 'background.paper',
          backgroundImage: 'none',
        },
      }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <TerminalIcon />
        Open Claude Code in Terminal
      </DialogTitle>

      <DialogContent>
        <Alert severity="info" icon={<TerminalIcon />} sx={{ mb: 3 }}>
          <Typography variant="body2" fontWeight="bold">
            Claude Code Terminal Integration
          </Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            This will help you open Claude Code in your terminal with full playbook context.
          </Typography>
        </Alert>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <FolderIcon />
            Manual Setup (Recommended)
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Follow these steps to use Claude Code with your playbooks:
          </Typography>

          <List dense>
            <ListItem>
              <ListItemIcon>
                <CheckIcon color="primary" />
              </ListItemIcon>
              <ListItemText
                primary="Open your terminal application"
                secondary="Use your preferred terminal (gnome-terminal, xterm, iTerm2, etc.)"
              />
            </ListItem>

            <ListItem>
              <ListItemIcon>
                <CheckIcon color="primary" />
              </ListItemIcon>
              <ListItemText
                primary={`Navigate to playbooks directory: cd ${playbooksPath}`}
                secondary="This is where all playbook YAML files are located"
                secondaryTypographyProps={{
                  sx: { fontFamily: 'monospace', fontSize: '0.85rem' }
                }}
              />
            </ListItem>

            <ListItem>
              <ListItemIcon>
                <CheckIcon color="primary" />
              </ListItemIcon>
              <ListItemText
                primary="Start Claude Code: claude-code"
                secondary="Or use 'claude-work' depending on your installation"
                secondaryTypographyProps={{
                  sx: { fontFamily: 'monospace', fontSize: '0.85rem' }
                }}
              />
            </ListItem>

            <ListItem>
              <ListItemIcon>
                <ArticleIcon color="primary" />
              </ListItemIcon>
              <ListItemText
                primary="Reference the instruction manual"
                secondary={`Read CLAUDE_CODE_INSTRUCTIONS.md in the playbooks folder for full context`}
                secondaryTypographyProps={{
                  sx: { fontFamily: 'monospace', fontSize: '0.85rem' }
                }}
              />
            </ListItem>
          </List>
        </Box>

        <Alert severity="success" icon={<CodeIcon />} sx={{ mb: 2 }}>
          <Typography variant="body2">
            <strong>What Claude Code Will Have:</strong>
          </Typography>
          <Typography variant="body2" component="div" sx={{ mt: 1 }}>
            <ul style={{ margin: 0, paddingLeft: '1.2rem' }}>
              <li>Full access to all playbook YAML files</li>
              <li>CLAUDE_CODE_INSTRUCTIONS.md with syntax reference</li>
              <li>Project documentation and best practices</li>
              <li>Ability to read, edit, and create playbooks</li>
            </ul>
          </Typography>
        </Alert>

        <Box
          sx={{
            p: 2,
            bgcolor: 'background.default',
            borderRadius: 1,
            border: '1px solid',
            borderColor: 'divider',
            fontFamily: 'monospace',
            fontSize: '0.85rem',
          }}
        >
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
            Copy these commands:
          </Typography>
          <Typography component="pre" sx={{ m: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
{`# Navigate to playbooks
cd ${playbooksPath}

# Start Claude Code
claude-code

# Or if using claude-work:
claude-work`}
          </Typography>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} variant="outlined">
          Close
        </Button>
        <Button
          onClick={handleOpenTerminal}
          variant="contained"
          startIcon={<TerminalIcon />}
        >
          Show Instructions
        </Button>
      </DialogActions>
    </Dialog>
  );
}
