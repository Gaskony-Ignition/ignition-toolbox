/**
 * PlaybookCodeViewer - View and edit playbook YAML code
 *
 * Floating dialog that shows the playbook source code in a syntax-highlighted editor.
 * Allows editing when in debug/paused mode.
 * Can be popped out into a separate window for easier operation.
 */

import { useState, useEffect } from 'react';
import {
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  Button,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Code as CodeIcon,
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Close as CloseIcon,
  OpenInNew as PopOutIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

interface PlaybookCodeViewerProps {
  open: boolean;
  executionId: string;
  playbookName: string;
  isDebugMode: boolean;
  isPaused: boolean;
  onClose: () => void;
}

interface PlaybookCodeResponse {
  code: string;
  playbook_path: string;
  playbook_name: string;
}

export function PlaybookCodeViewer({
  open,
  executionId,
  playbookName,
  isDebugMode,
  isPaused,
  onClose,
}: PlaybookCodeViewerProps) {
  const [code, setCode] = useState('');
  const [hasChanges, setHasChanges] = useState(false);
  const queryClient = useQueryClient();

  // Fetch playbook code
  const { data: playbookData, isLoading, error, refetch } = useQuery<PlaybookCodeResponse>({
    queryKey: ['playbook-code', executionId],
    queryFn: async () => {
      const response = await api.executions.getPlaybookCode(executionId);
      return response;
    },
    enabled: open,  // Only fetch when dialog is open
  });

  // Set initial code when data loads
  useEffect(() => {
    if (playbookData?.code) {
      setCode(playbookData.code);
      setHasChanges(false);
    }
  }, [playbookData]);

  // Save playbook code mutation
  const saveMutation = useMutation({
    mutationFn: async (updatedCode: string) => {
      return await api.executions.updatePlaybookCode(executionId, updatedCode);
    },
    onSuccess: () => {
      setHasChanges(false);
      queryClient.invalidateQueries({ queryKey: ['playbook-code', executionId] });
    },
  });

  const handleCodeChange = (newCode: string) => {
    setCode(newCode);
    setHasChanges(newCode !== (playbookData?.code || ''));
  };

  const handleSave = () => {
    saveMutation.mutate(code);
  };

  const handleRefresh = () => {
    refetch();
  };

  // Open in new window
  const handlePopOut = () => {
    const width = 1200;
    const height = 800;
    const left = (window.screen.width - width) / 2;
    const top = (window.screen.height - height) / 2;

    const newWindow = window.open(
      '',
      'PlaybookCodeViewer',
      `width=${width},height=${height},left=${left},top=${top},menubar=no,toolbar=no,location=no,status=no`
    );

    if (newWindow) {
      newWindow.document.write(`
        <!DOCTYPE html>
        <html>
          <head>
            <title>Playbook Code - ${playbookName}</title>
            <style>
              body {
                margin: 0;
                padding: 20px;
                background: #1e1e1e;
                color: #d4d4d4;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
              }
              h1 {
                font-size: 1.2rem;
                margin: 0 0 10px 0;
                color: #fff;
              }
              .controls {
                margin-bottom: 10px;
                display: flex;
                gap: 10px;
              }
              button {
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                background: #1976d2;
                color: white;
                cursor: pointer;
                font-size: 0.875rem;
              }
              button:hover {
                background: #1565c0;
              }
              button:disabled {
                background: #666;
                cursor: not-allowed;
              }
              #editor-container {
                width: 100%;
                height: calc(100vh - 100px);
                border: 1px solid #444;
                border-radius: 4px;
              }
            </style>
          </head>
          <body>
            <h1>Playbook Code - ${playbookName}</h1>
            <div class="controls">
              ${canEdit ? '<button id="saveBtn" disabled>Save</button>' : ''}
              ${canEdit ? '<button id="revertBtn" disabled>Revert</button>' : ''}
              <button id="closeBtn">Close Window</button>
            </div>
            <div id="editor-container"></div>

            <script src="https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs/loader.js"></script>
            <script>
              const originalCode = \`${code.replace(/`/g, '\\`').replace(/\$/g, '\\$')}\`;
              const saveBtn = document.getElementById('saveBtn');
              const revertBtn = document.getElementById('revertBtn');
              let editor;

              // Load Monaco Editor
              require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' } });

              require(['vs/editor/editor.main'], function () {
                editor = monaco.editor.create(document.getElementById('editor-container'), {
                  value: originalCode,
                  language: 'yaml',
                  theme: 'vs-dark',
                  readOnly: ${!canEdit},
                  automaticLayout: true,
                  minimap: { enabled: true },
                  fontSize: 14,
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                  wordWrap: 'on',
                  folding: true,
                  tabSize: 2,
                });

                ${canEdit ? `
                // Track changes to enable/disable buttons
                editor.onDidChangeModelContent(() => {
                  const currentCode = editor.getValue();
                  const hasChanges = currentCode !== originalCode;
                  saveBtn.disabled = !hasChanges;
                  revertBtn.disabled = !hasChanges;
                });

                // Save button handler
                saveBtn.addEventListener('click', async () => {
                  saveBtn.disabled = true;
                  saveBtn.textContent = 'Saving...';

                  try {
                    const response = await fetch('${api.getBaseUrl()}/api/playbooks/${encodeURIComponent(playbookName)}', {
                      method: 'PUT',
                      headers: {
                        'Content-Type': 'application/json',
                      },
                      body: JSON.stringify({ code: editor.getValue() }),
                    });

                    if (response.ok) {
                      saveBtn.textContent = 'Saved!';
                      setTimeout(() => {
                        saveBtn.textContent = 'Save';
                        saveBtn.disabled = true;
                        revertBtn.disabled = true;
                      }, 2000);
                    } else {
                      const errorData = await response.json();
                      alert('Failed to save: ' + (errorData.detail || 'Unknown error'));
                      saveBtn.textContent = 'Save';
                      saveBtn.disabled = false;
                    }
                  } catch (error) {
                    alert('Failed to save: ' + error.message);
                    saveBtn.textContent = 'Save';
                    saveBtn.disabled = false;
                  }
                });

                // Revert button handler
                revertBtn.addEventListener('click', () => {
                  if (confirm('Revert all changes to the original code?')) {
                    editor.setValue(originalCode);
                    saveBtn.disabled = true;
                    revertBtn.disabled = true;
                  }
                });
                ` : ''}

                // Close button handler
                document.getElementById('closeBtn').addEventListener('click', () => window.close());
              });
            </script>
          </body>
        </html>
      `);
      newWindow.document.close();

      // Close the dialog since we're opening in new window
      onClose();
    }
  };

  const canEdit = isDebugMode || isPaused;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: {
          height: '85vh',
          maxHeight: '85vh',
        },
      }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, pb: 1 }}>
        <CodeIcon />
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h6" component="span">
            Playbook Code
          </Typography>
          <Typography variant="body2" color="text.secondary" component="span" sx={{ ml: 2 }}>
            {playbookName}
          </Typography>
        </Box>

        <Tooltip title="Open in New Window">
          <IconButton size="small" onClick={handlePopOut}>
            <PopOutIcon />
          </IconButton>
        </Tooltip>

        <Tooltip title="Close">
          <IconButton size="small" onClick={onClose}>
            <CloseIcon />
          </IconButton>
        </Tooltip>
      </DialogTitle>

      <DialogContent sx={{ p: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {isLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ m: 2 }}>
            Failed to load playbook code: {error instanceof Error ? error.message : 'Unknown error'}
          </Alert>
        )}

        {saveMutation.isError && (
          <Alert severity="error" sx={{ m: 2 }}>
            Failed to save changes: {saveMutation.error instanceof Error ? saveMutation.error.message : 'Unknown error'}
          </Alert>
        )}

        {saveMutation.isSuccess && (
          <Alert severity="success" sx={{ m: 2 }}>
            Changes saved successfully!
          </Alert>
        )}

        {!canEdit && (
          <Alert severity="info" sx={{ m: 2 }}>
            Enable debug mode or pause execution to edit the playbook code.
          </Alert>
        )}

        {!isLoading && !error && (
          <Box
            component="textarea"
            value={code}
            onChange={(e) => handleCodeChange(e.target.value)}
            readOnly={!canEdit}
            sx={{
              flexGrow: 1,
              width: '100%',
              fontFamily: '"Fira Code", "Monaco", "Courier New", monospace',
              fontSize: '0.875rem',
              lineHeight: 1.6,
              p: 2,
              m: 2,
              border: 1,
              borderColor: 'divider',
              borderRadius: 1,
              bgcolor: canEdit ? 'background.default' : 'action.disabledBackground',
              color: 'text.primary',
              resize: 'none',
              '&:focus': {
                outline: 'none',
                borderColor: 'primary.main',
              },
            }}
          />
        )}

        {/* Footer with unsaved changes warning */}
        {hasChanges && (
          <Box
            sx={{
              p: 1,
              mx: 2,
              mb: 2,
              borderRadius: 1,
              bgcolor: 'warning.dark',
            }}
          >
            <Typography variant="caption" color="warning.contrastText">
              ⚠️ You have unsaved changes
            </Typography>
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        {canEdit && (
          <>
            <Tooltip title="Refresh code from file">
              <IconButton size="small" onClick={handleRefresh} disabled={isLoading}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={handleSave}
              disabled={!hasChanges || saveMutation.isPending}
            >
              {saveMutation.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </>
        )}
        <Button onClick={handlePopOut} variant="outlined" startIcon={<PopOutIcon />}>
          Pop Out
        </Button>
        <Button onClick={onClose} variant="outlined">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}
