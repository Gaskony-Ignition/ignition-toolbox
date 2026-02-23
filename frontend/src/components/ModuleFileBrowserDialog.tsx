import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  CircularProgress,
  Alert,
  RadioGroup,
  FormControlLabel,
  Radio,
  Chip,
  Divider,
} from '@mui/material';
import FolderIcon from '@mui/icons-material/Folder';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

interface ModuleFile {
  filename: string;
  filepath: string;
  is_unsigned: boolean;
  module_name: string | null;
  module_version: string | null;
  module_id: string | null;
}

interface ModuleFilesResponse {
  path: string;
  files: ModuleFile[];
}

interface ModuleFileBrowserDialogProps {
  open: boolean;
  onClose: () => void;
  onSelect: (filePath: string, metadata: { name: string; version: string }) => void;
  initialPath?: string;
}

export default function ModuleFileBrowserDialog({
  open,
  onClose,
  onSelect,
  initialPath = '/Ubuntu/modules',
}: ModuleFileBrowserDialogProps) {
  const [currentPath, setCurrentPath] = useState<string>(initialPath);
  const [moduleFiles, setModuleFiles] = useState<ModuleFile[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  const fetchModuleFiles = async (path: string) => {
    setLoading(true);
    setError(null);
    setSelectedFile(null);

    try {
      const response = await fetch(
        `/api/filesystem/list-modules?path=${encodeURIComponent(path)}`
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to list module files');
      }

      const data: ModuleFilesResponse = await response.json();
      setModuleFiles(data.files);
      setCurrentPath(data.path);

      // Auto-select first file if only one exists
      if (data.files.length === 1) {
        setSelectedFile(data.files[0].filepath);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setModuleFiles([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchModuleFiles(currentPath);
    }
    // Only fetch when dialog opens, not on every path change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const handleSelect = () => {
    const selected = moduleFiles.find((f) => f.filepath === selectedFile);
    if (selected && selected.module_name && selected.module_version) {
      onSelect(selected.filepath, {
        name: selected.module_name,
        version: selected.module_version,
      });
      onClose();
    }
  };

  const handlePathChange = (newPath: string) => {
    setCurrentPath(newPath);
    fetchModuleFiles(newPath);
  };

  const getModuleGroups = () => {
    // Group signed and unsigned versions of the same module
    const groups: { [key: string]: ModuleFile[] } = {};

    moduleFiles.forEach((file) => {
      const key = file.module_name || file.filename;
      if (!groups[key]) {
        groups[key] = [];
      }
      groups[key].push(file);
    });

    return Object.entries(groups);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Select Module File</DialogTitle>
      <DialogContent>
        {/* Quick Access Buttons */}
        <Box sx={{ mb: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button
            size="small"
            variant={currentPath === '/Ubuntu/modules' ? 'contained' : 'outlined'}
            startIcon={<FolderIcon />}
            onClick={() => handlePathChange('/Ubuntu/modules')}
          >
            Ubuntu Modules
          </Button>
        </Box>

        {/* Current Path */}
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

        {!loading && !error && moduleFiles.length === 0 && (
          <Alert severity="info">
            No module files (.modl or .unsigned.modl) found in this directory.
          </Alert>
        )}

        {!loading && !error && moduleFiles.length > 0 && (
          <Box>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Found {moduleFiles.length} module file{moduleFiles.length !== 1 ? 's' : ''}:
            </Typography>

            <RadioGroup value={selectedFile} onChange={(e) => setSelectedFile(e.target.value)}>
              {getModuleGroups().map(([moduleName, files], index) => (
                <Box key={moduleName} sx={{ mb: 2 }}>
                  {index > 0 && <Divider sx={{ my: 2 }} />}

                  <Typography variant="subtitle1" color="primary" gutterBottom>
                    {moduleName}
                  </Typography>

                  {files.map((file) => (
                    <Box
                      key={file.filepath}
                      sx={{
                        p: 2,
                        mb: 1,
                        border: '1px solid',
                        borderColor:
                          selectedFile === file.filepath
                            ? 'primary.main'
                            : 'rgba(0, 255, 0, 0.3)',
                        borderRadius: 1,
                        bgcolor:
                          selectedFile === file.filepath
                            ? 'rgba(0, 255, 0, 0.1)'
                            : 'transparent',
                        cursor: 'pointer',
                        '&:hover': {
                          bgcolor: 'rgba(0, 255, 0, 0.05)',
                        },
                      }}
                      onClick={() => setSelectedFile(file.filepath)}
                    >
                      <FormControlLabel
                        value={file.filepath}
                        control={<Radio color="primary" />}
                        label={
                          <Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                              <Typography variant="body1" fontFamily="monospace">
                                {file.filename}
                              </Typography>
                              {file.is_unsigned ? (
                                <Chip
                                  label="Unsigned"
                                  size="small"
                                  color="warning"
                                  sx={{ height: 20 }}
                                />
                              ) : (
                                <Chip
                                  label="Signed"
                                  size="small"
                                  color="success"
                                  icon={<CheckCircleIcon />}
                                  sx={{ height: 20 }}
                                />
                              )}
                            </Box>
                            {file.module_version && (
                              <Typography variant="caption" color="text.secondary">
                                Version: {file.module_version}
                              </Typography>
                            )}
                            {file.module_id && (
                              <Typography
                                variant="caption"
                                color="text.secondary"
                                display="block"
                              >
                                ID: {file.module_id}
                              </Typography>
                            )}
                          </Box>
                        }
                      />
                    </Box>
                  ))}
                </Box>
              ))}
            </RadioGroup>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} sx={{ color: '#00ff00' }}>
          Cancel
        </Button>
        <Button
          onClick={handleSelect}
          variant="contained"
          disabled={!selectedFile}
          sx={{
            bgcolor: '#00ff00',
            color: '#000',
            '&:hover': { bgcolor: '#00cc00' },
            '&:disabled': { bgcolor: 'rgba(0, 255, 0, 0.3)' },
          }}
        >
          Select Module
        </Button>
      </DialogActions>
    </Dialog>
  );
}
