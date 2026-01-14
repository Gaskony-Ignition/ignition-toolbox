import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Box,
  CircularProgress,
  Alert,
} from '@mui/material';
import FolderIcon from '@mui/icons-material/Folder';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';

interface DirectoryEntry {
  name: string;
  path: string;
  is_directory: boolean;
  is_accessible: boolean;
}

interface DirectoryContents {
  current_path: string;
  parent_path: string | null;
  entries: DirectoryEntry[];
}

interface FolderBrowserDialogProps {
  open: boolean;
  onClose: () => void;
  onSelect: (path: string) => void;
  initialPath?: string;
}

export default function FolderBrowserDialog({
  open,
  onClose,
  onSelect,
  initialPath = './data/downloads',
}: FolderBrowserDialogProps) {
  const [currentPath, setCurrentPath] = useState<string>(initialPath);
  const [contents, setContents] = useState<DirectoryContents | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDirectory = async (path: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/filesystem/browse?path=${encodeURIComponent(path)}`
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to browse directory');
      }

      const data: DirectoryContents = await response.json();
      setContents(data);
      setCurrentPath(data.current_path);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setContents(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchDirectory(currentPath);
    }
  }, [open]);

  const handleNavigate = (path: string) => {
    fetchDirectory(path);
  };

  const handleSelect = () => {
    onSelect(currentPath);
    onClose();
  };

  const handleQuickNavigate = (path: string) => {
    fetchDirectory(path);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Select Download Folder</DialogTitle>
      <DialogContent>
        {/* Quick Access Buttons for Windows Drives and Common Folders */}
        <Box sx={{ mb: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button
            size="small"
            variant="outlined"
            onClick={() => handleQuickNavigate('/Ubuntu/modules')}
          >
            Ubuntu Modules
          </Button>
          <Button
            size="small"
            variant="outlined"
            onClick={() => handleQuickNavigate('/mnt/c/Users')}
          >
            C:\Users
          </Button>
          <Button
            size="small"
            variant="outlined"
            onClick={() => handleQuickNavigate('/mnt/c/temp')}
          >
            C:\temp
          </Button>
          <Button
            size="small"
            variant="outlined"
            onClick={() => handleQuickNavigate('/mnt/c/')}
          >
            C:\
          </Button>
          <Button
            size="small"
            variant="outlined"
            onClick={() => handleQuickNavigate('/mnt/d/')}
          >
            D:\
          </Button>
          <Button
            size="small"
            variant="outlined"
            onClick={() => handleQuickNavigate('./data/downloads')}
          >
            Default (./data/downloads)
          </Button>
        </Box>

        <Box sx={{ mb: 2 }}>
          <Typography
            variant="body2"
            sx={{
              fontFamily: 'monospace',
              p: 1,
              bgcolor: 'rgba(0, 255, 0, 0.05)',
              border: '1px solid rgba(0, 255, 0, 0.3)',
              borderRadius: 1,
            }}
          >
            {currentPath}
          </Typography>
        </Box>

        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress size={40} />
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {contents && !loading && (
          <List sx={{ maxHeight: '400px', overflow: 'auto' }}>
            {contents.parent_path && (
              <ListItem disablePadding>
                <ListItemButton onClick={() => handleNavigate(contents.parent_path!)}>
                  <ListItemIcon>
                    <ArrowUpwardIcon sx={{ color: '#00ff00' }} />
                  </ListItemIcon>
                  <ListItemText
                    primary=".."
                    secondary="Parent directory"
                    primaryTypographyProps={{
                      sx: { fontFamily: 'monospace', color: '#00ff00' },
                    }}
                    secondaryTypographyProps={{
                      sx: { color: 'rgba(0, 255, 0, 0.6)' },
                    }}
                  />
                </ListItemButton>
              </ListItem>
            )}

            {contents.entries.length === 0 && (
              <ListItem>
                <ListItemText
                  primary="No subdirectories"
                  primaryTypographyProps={{
                    sx: { color: 'rgba(0, 255, 0, 0.6)', fontStyle: 'italic' },
                  }}
                />
              </ListItem>
            )}

            {contents.entries.map((entry) => (
              <ListItem key={entry.path} disablePadding>
                <ListItemButton
                  onClick={() => handleNavigate(entry.path)}
                  disabled={!entry.is_accessible}
                >
                  <ListItemIcon>
                    {entry.is_accessible ? (
                      <FolderIcon sx={{ color: '#00ff00' }} />
                    ) : (
                      <FolderIcon sx={{ color: 'rgba(255, 0, 0, 0.5)' }} />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary={entry.name}
                    secondary={entry.is_accessible ? '' : 'Access denied'}
                    primaryTypographyProps={{
                      sx: {
                        fontFamily: 'monospace',
                        color: entry.is_accessible
                          ? '#00ff00'
                          : 'rgba(255, 0, 0, 0.5)',
                      },
                    }}
                    secondaryTypographyProps={{
                      sx: { color: 'rgba(255, 0, 0, 0.6)' },
                    }}
                  />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} sx={{ color: '#00ff00' }}>
          Cancel
        </Button>
        <Button
          onClick={handleSelect}
          variant="contained"
          disabled={!contents}
          sx={{
            bgcolor: '#00ff00',
            color: '#000',
            '&:hover': { bgcolor: '#00cc00' },
            '&:disabled': { bgcolor: 'rgba(0, 255, 0, 0.3)' },
          }}
        >
          Select This Folder
        </Button>
      </DialogActions>
    </Dialog>
  );
}
