/**
 * DebugPanel - Shows debug context when execution pauses due to failure
 *
 * Features:
 * - Screenshot view (frozen browser state at failure)
 * - DOM inspector (HTML tree viewer)
 * - Step info and error details
 * - Instructions for chatting with Claude Code
 */

import { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  Alert,
  CircularProgress,
  Button,
  Divider,
  Chip,
  TextField,
} from '@mui/material';
import {
  BugReport as BugIcon,
  Image as ImageIcon,
  Code as CodeIcon,
  Chat as ChatIcon,
  Refresh as RefreshIcon,
  BuildCircle as FixIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`debug-tabpanel-${index}`}
      aria-labelledby={`debug-tab-${index}`}
      {...other}
      style={{ height: '100%' }}
    >
      {value === index && <Box sx={{ p: 2, height: '100%' }}>{children}</Box>}
    </div>
  );
}

interface DebugPanelProps {
  executionId: string;
}

export function DebugPanel({ executionId }: DebugPanelProps) {
  const [tabValue, setTabValue] = useState(0);
  const [fixYaml, setFixYaml] = useState('');
  const [playbookPath, setPlaybookPath] = useState('');
  const [applyError, setApplyError] = useState<string | null>(null);
  const [applySuccess, setApplySuccess] = useState<string | null>(null);

  const handleApplyFix = async () => {
    if (!fixYaml.trim() || !playbookPath.trim()) {
      setApplyError('Please provide both playbook path and YAML content');
      return;
    }

    try {
      const result = await api.playbooks.update(playbookPath, fixYaml);
      setApplySuccess(`Playbook updated successfully! Backup saved to: ${result.backup_path}`);
      setApplyError(null);
      // Reset form
      setFixYaml('');
      setPlaybookPath('');
    } catch (error) {
      setApplyError((error as Error).message);
      setApplySuccess(null);
    }
  };

  // Fetch debug context
  const {
    data: debugContext,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['debugContext', executionId],
    queryFn: () => api.executions.getDebugContext(executionId),
    enabled: !!executionId,
    retry: false,
  });

  if (isLoading) {
    return (
      <Paper
        elevation={3}
        sx={{
          p: 3,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 2,
        }}
      >
        <CircularProgress size={24} />
        <Typography>Loading debug context...</Typography>
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper elevation={3} sx={{ p: 3 }}>
        <Alert severity="error">
          Failed to load debug context: {(error as Error).message}
        </Alert>
      </Paper>
    );
  }

  if (!debugContext) {
    return (
      <Paper elevation={3} sx={{ p: 3 }}>
        <Alert severity="info">
          No debug context available. Enable debug mode and run a playbook to
          see failure details.
        </Alert>
      </Paper>
    );
  }

  return (
    <Paper elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box
        sx={{
          p: 2,
          borderBottom: 1,
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          gap: 2,
        }}
      >
        <BugIcon color="error" />
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h6">Debug Mode - Step Failed</Typography>
          <Typography variant="caption" color="text.secondary">
            {debugContext.step_name} ({debugContext.step_type})
          </Typography>
        </Box>
        <Button
          startIcon={<RefreshIcon />}
          onClick={() => refetch()}
          size="small"
          variant="outlined"
        >
          Refresh
        </Button>
      </Box>

      {/* Error Alert */}
      <Box sx={{ p: 2, bgcolor: 'error.light', color: 'error.contrastText' }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
          Error:
        </Typography>
        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
          {debugContext.error}
        </Typography>
      </Box>

      {/* Tabs */}
      <Tabs
        value={tabValue}
        onChange={(_, newValue) => setTabValue(newValue)}
        sx={{ borderBottom: 1, borderColor: 'divider' }}
      >
        <Tab icon={<ImageIcon />} label="Screenshot" />
        <Tab icon={<CodeIcon />} label="DOM/HTML" />
        <Tab icon={<ChatIcon />} label="Chat with AI" />
        <Tab icon={<FixIcon />} label="Apply Fix" />
      </Tabs>

      {/* Tab Panels */}
      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
        {/* Screenshot Tab */}
        <TabPanel value={tabValue} index={0}>
          {debugContext.screenshot_base64 ? (
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                gap: 2,
                height: '100%',
              }}
            >
              <Alert severity="info">
                Browser state frozen at moment of failure
              </Alert>
              <Box
                sx={{
                  flexGrow: 1,
                  border: 1,
                  borderColor: 'divider',
                  borderRadius: 1,
                  overflow: 'auto',
                  bgcolor: 'grey.100',
                }}
              >
                <img
                  src={`data:image/png;base64,${debugContext.screenshot_base64}`}
                  alt="Frozen browser state"
                  style={{ maxWidth: '100%', display: 'block' }}
                />
              </Box>
            </Box>
          ) : (
            <Alert severity="warning">
              No screenshot available for this step type
            </Alert>
          )}
        </TabPanel>

        {/* DOM/HTML Tab */}
        <TabPanel value={tabValue} index={1}>
          {debugContext.page_html ? (
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                gap: 2,
                height: '100%',
              }}
            >
              <Alert severity="info">
                Page HTML captured at moment of failure. Use this to find
                correct selectors.
              </Alert>
              <Box
                sx={{
                  flexGrow: 1,
                  border: 1,
                  borderColor: 'divider',
                  borderRadius: 1,
                  overflow: 'auto',
                  bgcolor: 'grey.900',
                  p: 2,
                }}
              >
                <pre
                  style={{
                    margin: 0,
                    color: '#0f0',
                    fontFamily: 'monospace',
                    fontSize: '12px',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all',
                  }}
                >
                  {debugContext.page_html}
                </pre>
              </Box>
            </Box>
          ) : (
            <Alert severity="warning">
              No HTML available for this step type
            </Alert>
          )}
        </TabPanel>

        {/* Chat with AI Tab */}
        <TabPanel value={tabValue} index={2}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Alert severity="info" icon={<ChatIcon />}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Chat with Claude Code for help
              </Typography>
              <Typography variant="body2">
                This debug session is now paused. You can chat with me (Claude Code)
                directly to analyze the failure and get suggestions for fixes.
              </Typography>
            </Alert>

            <Divider />

            <Box>
              <Typography variant="h6" gutterBottom>
                Quick Actions
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Copy and paste these prompts into your Claude Code chat:
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Paper
                  variant="outlined"
                  sx={{ p: 2, cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}
                  onClick={() => {
                    navigator.clipboard.writeText(
                      `Analyze this debug context and explain why the step failed:\n\nStep: ${debugContext.step_name}\nType: ${debugContext.step_type}\nError: ${debugContext.error}\n\nParameters: ${JSON.stringify(debugContext.step_parameters, null, 2)}`
                    );
                  }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
                    📋 Analyze Failure
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Ask me to analyze why the step failed
                  </Typography>
                </Paper>

                <Paper
                  variant="outlined"
                  sx={{ p: 2, cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}
                  onClick={() => {
                    navigator.clipboard.writeText(
                      `Based on this HTML, suggest better selectors for finding elements:\n\n${debugContext.page_html?.substring(0, 2000) || 'No HTML available'}`
                    );
                  }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
                    🔍 Suggest Selectors
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Get alternative CSS selectors from the HTML
                  </Typography>
                </Paper>

                <Paper
                  variant="outlined"
                  sx={{ p: 2, cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}
                  onClick={() => {
                    navigator.clipboard.writeText(
                      `Generate a fix for this failed step and show me the corrected YAML:\n\nStep: ${debugContext.step_name}\nError: ${debugContext.error}\n\nCurrent parameters: ${JSON.stringify(debugContext.step_parameters, null, 2)}`
                    );
                  }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
                    🔧 Generate Fix
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Ask me to generate a corrected step definition
                  </Typography>
                </Paper>

                <Paper
                  variant="outlined"
                  sx={{ p: 2, cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}
                  onClick={() => {
                    navigator.clipboard.writeText(
                      `Explain what this step is trying to do and provide troubleshooting advice:\n\nStep: ${debugContext.step_name}\nType: ${debugContext.step_type}\n\nParameters: ${JSON.stringify(debugContext.step_parameters, null, 2)}`
                    );
                  }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
                    💡 Explain Step
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Understand what the step does and get troubleshooting tips
                  </Typography>
                </Paper>
              </Box>
            </Box>

            <Divider />

            <Box>
              <Typography variant="h6" gutterBottom>
                Step Details
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Step ID:
                  </Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {debugContext.step_id}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Step Type:
                  </Typography>
                  <Chip label={debugContext.step_type} size="small" />
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Parameters:
                  </Typography>
                  <Paper
                    variant="outlined"
                    sx={{ p: 1, bgcolor: 'grey.50', mt: 0.5 }}
                  >
                    <pre
                      style={{
                        margin: 0,
                        fontFamily: 'monospace',
                        fontSize: '12px',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {JSON.stringify(debugContext.step_parameters, null, 2)}
                    </pre>
                  </Paper>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Timestamp:
                  </Typography>
                  <Typography variant="body2">
                    {new Date(debugContext.timestamp).toLocaleString()}
                  </Typography>
                </Box>
              </Box>
            </Box>
          </Box>
        </TabPanel>

        {/* Apply Fix Tab */}
        <TabPanel value={tabValue} index={3}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {applySuccess && (
              <Alert severity="success" onClose={() => setApplySuccess(null)}>
                {applySuccess}
              </Alert>
            )}

            {applyError && (
              <Alert severity="error" onClose={() => setApplyError(null)}>
                {applyError}
              </Alert>
            )}

            <Alert severity="info" icon={<FixIcon />}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Apply YAML Fix from Claude Code
              </Typography>
              <Typography variant="body2">
                After chatting with Claude Code about the failure, paste the corrected
                YAML here to update your playbook. A timestamped backup will be created
                automatically.
              </Typography>
            </Alert>

            <Divider />

            <Box>
              <Typography variant="h6" gutterBottom>
                1. Specify Playbook Path
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Enter the relative path from the playbooks directory (e.g., "gateway/simple_health_check.yaml")
              </Typography>
              <TextField
                fullWidth
                placeholder="gateway/simple_health_check.yaml"
                value={playbookPath}
                onChange={(e) => setPlaybookPath(e.target.value)}
                variant="outlined"
                size="small"
              />
            </Box>

            <Box>
              <Typography variant="h6" gutterBottom>
                2. Paste Fixed YAML
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Paste the complete corrected YAML content from Claude Code
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={15}
                placeholder="Paste fixed YAML here..."
                value={fixYaml}
                onChange={(e) => setFixYaml(e.target.value)}
                variant="outlined"
                sx={{
                  fontFamily: 'monospace',
                  '& textarea': {
                    fontFamily: 'monospace',
                    fontSize: '12px',
                  },
                }}
              />
            </Box>

            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
              <Button
                variant="outlined"
                onClick={() => {
                  setFixYaml('');
                  setPlaybookPath('');
                  setApplyError(null);
                  setApplySuccess(null);
                }}
              >
                Clear
              </Button>
              <Button
                variant="contained"
                color="primary"
                startIcon={<FixIcon />}
                onClick={handleApplyFix}
                disabled={!fixYaml.trim() || !playbookPath.trim()}
              >
                Apply Fix
              </Button>
            </Box>

            <Divider />

            <Alert severity="warning">
              <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Safety Features:
              </Typography>
              <Typography variant="body2" component="div">
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  <li>Automatic backup created before applying changes</li>
                  <li>YAML syntax validation before writing</li>
                  <li>Path security check (prevents directory traversal)</li>
                </ul>
              </Typography>
            </Alert>
          </Box>
        </TabPanel>
      </Box>
    </Paper>
  );
}
