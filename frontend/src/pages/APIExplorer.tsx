/**
 * API Explorer page for interacting with Ignition Gateway REST API
 */

import { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tab,
  Tabs,
  Card,
  CardContent,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  Alert,
  CircularProgress,
  Divider,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Collapse,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Send as SendIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandIcon,
  ChevronRight as ChevronIcon,
  Storage as DatabaseIcon,
  Info as InfoIcon,
  PlayArrow as ScanIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index }: TabPanelProps) {
  return (
    <Box role="tabpanel" hidden={value !== index} sx={{ pt: 2 }}>
      {value === index && children}
    </Box>
  );
}

interface APIKeyInfo {
  id: number;
  name: string;
  gateway_url: string;
  has_api_key: boolean;
  description?: string;
  created_at?: string;
  last_used?: string;
}

interface APIKeyDialogProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: { name: string; gateway_url: string; api_key: string; description?: string }) => void;
  isLoading?: boolean;
}

function APIKeyDialog({ open, onClose, onSave, isLoading }: APIKeyDialogProps) {
  const [name, setName] = useState('');
  const [gatewayUrl, setGatewayUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [description, setDescription] = useState('');

  const handleSave = () => {
    onSave({ name, gateway_url: gatewayUrl, api_key: apiKey, description });
    setName('');
    setGatewayUrl('');
    setApiKey('');
    setDescription('');
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add API Key</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          <TextField
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            fullWidth
            required
            placeholder="e.g., production-gateway"
          />
          <TextField
            label="Gateway URL"
            value={gatewayUrl}
            onChange={(e) => setGatewayUrl(e.target.value)}
            fullWidth
            required
            placeholder="e.g., http://localhost:8088"
          />
          <TextField
            label="API Key"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            fullWidth
            required
            type="password"
            placeholder="Enter your Ignition API token"
          />
          <TextField
            label="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            fullWidth
            multiline
            rows={2}
            placeholder="Optional description"
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={!name || !gatewayUrl || !apiKey || isLoading}
        >
          {isLoading ? <CircularProgress size={20} /> : 'Add Key'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export function APIExplorer() {
  const queryClient = useQueryClient();
  const [selectedKey, setSelectedKey] = useState<string>('');
  const [tabValue, setTabValue] = useState(0);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [expandedEndpoints, setExpandedEndpoints] = useState<string[]>(['resources']);

  // Request builder state
  const [requestMethod, setRequestMethod] = useState('GET');
  const [requestPath, setRequestPath] = useState('/data/status/sys-info');
  const [requestBody, setRequestBody] = useState('');
  const [requestResponse, setRequestResponse] = useState<Record<string, unknown> | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);

  // Fetch API keys
  const { data: apiKeys = [] } = useQuery<APIKeyInfo[]>({
    queryKey: ['api-keys'],
    queryFn: () => api.apiExplorer.listApiKeys(),
  });

  // Create API key mutation
  const createKeyMutation = useMutation({
    mutationFn: (data: { name: string; gateway_url: string; api_key: string; description?: string }) =>
      api.apiExplorer.createApiKey(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      setDialogOpen(false);
    },
  });

  // Delete API key mutation
  const deleteKeyMutation = useMutation({
    mutationFn: (name: string) => api.apiExplorer.deleteApiKey(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      if (selectedKey === deleteKeyMutation.variables) {
        setSelectedKey('');
      }
    },
  });

  // Get selected key info
  const selectedKeyInfo = apiKeys.find((k) => k.name === selectedKey);

  // Fetch gateway info when key is selected
  const { data: gatewayInfo, isLoading: gatewayLoading, refetch: refetchGateway } = useQuery({
    queryKey: ['gateway-info', selectedKey],
    queryFn: () =>
      api.apiExplorer.getGatewayInfo({
        gateway_url: selectedKeyInfo?.gateway_url || '',
        api_key_name: selectedKey,
      }),
    enabled: !!selectedKey && !!selectedKeyInfo,
  });

  // Test connection mutation
  const testConnectionMutation = useMutation({
    mutationFn: () =>
      api.apiExplorer.testConnection({
        gateway_url: selectedKeyInfo?.gateway_url || '',
        api_key_name: selectedKey,
      }),
  });

  // Execute request mutation
  const executeRequestMutation = useMutation({
    mutationFn: () =>
      api.apiExplorer.executeRequest({
        gateway_url: selectedKeyInfo?.gateway_url || '',
        api_key_name: selectedKey,
        method: requestMethod,
        path: requestPath,
        body: requestBody ? JSON.parse(requestBody) : undefined,
      }),
    onSuccess: (data) => {
      setRequestResponse(data);
      setRequestError(null);
    },
    onError: (err: Error) => {
      setRequestError(err.message);
      setRequestResponse(null);
    },
  });

  // Scan projects mutation
  const scanProjectsMutation = useMutation({
    mutationFn: () =>
      api.apiExplorer.scanProjects({
        gateway_url: selectedKeyInfo?.gateway_url || '',
        api_key_name: selectedKey,
      }),
  });

  const toggleEndpoint = (endpoint: string) => {
    setExpandedEndpoints((prev) =>
      prev.includes(endpoint)
        ? prev.filter((e) => e !== endpoint)
        : [...prev, endpoint]
    );
  };

  const endpoints = [
    {
      id: 'status',
      label: 'Status',
      icon: <InfoIcon />,
      children: [
        { path: '/data/status/sys-info', label: 'System Info' },
        { path: '/data/status/platform', label: 'Platform' },
        { path: '/data/status/modules', label: 'Modules' },
        { path: '/data/status/license', label: 'License' },
      ],
    },
    {
      id: 'resources',
      label: 'Resources',
      icon: <DatabaseIcon />,
      children: [
        { path: '/data/config/database-connections', label: 'Databases' },
        { path: '/data/config/opc-connections', label: 'OPC Connections' },
        { path: '/data/config/tag-providers', label: 'Tag Providers' },
        { path: '/data/config/projects', label: 'Projects' },
      ],
    },
  ];

  return (
    <Box sx={{ display: 'flex', gap: 2, height: 'calc(100vh - 100px)' }}>
      {/* Left Panel: Endpoint Tree */}
      <Paper sx={{ width: 280, p: 2, overflow: 'auto' }}>
        <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2 }}>
          Endpoints
        </Typography>
        <List dense>
          {endpoints.map((section) => (
            <Box key={section.id}>
              <ListItemButton onClick={() => toggleEndpoint(section.id)}>
                <ListItemIcon sx={{ minWidth: 36 }}>
                  {section.icon}
                </ListItemIcon>
                <ListItemText primary={section.label} />
                {expandedEndpoints.includes(section.id) ? <ExpandIcon /> : <ChevronIcon />}
              </ListItemButton>
              <Collapse in={expandedEndpoints.includes(section.id)}>
                <List dense sx={{ pl: 4 }}>
                  {section.children.map((child) => (
                    <ListItemButton
                      key={child.path}
                      onClick={() => {
                        setRequestPath(child.path);
                        setRequestMethod('GET');
                        setTabValue(2);
                      }}
                    >
                      <ListItemText primary={child.label} />
                    </ListItemButton>
                  ))}
                </List>
              </Collapse>
            </Box>
          ))}
        </List>
      </Paper>

      {/* Right Panel: Main Content */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Gateway Selector */}
        <Paper sx={{ p: 2, mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <FormControl size="small" sx={{ minWidth: 250 }}>
              <InputLabel>Gateway</InputLabel>
              <Select
                value={selectedKey}
                onChange={(e) => setSelectedKey(e.target.value)}
                label="Gateway"
              >
                <MenuItem value="">
                  <em>Select a gateway</em>
                </MenuItem>
                {apiKeys.map((key) => (
                  <MenuItem key={key.name} value={key.name}>
                    {key.name} - {key.gateway_url}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={() => setDialogOpen(true)}
              size="small"
            >
              Add API Key
            </Button>
            {selectedKey && (
              <>
                <Button
                  variant="outlined"
                  startIcon={<RefreshIcon />}
                  onClick={() => refetchGateway()}
                  size="small"
                  disabled={gatewayLoading}
                >
                  Refresh
                </Button>
                <IconButton
                  onClick={() => deleteKeyMutation.mutate(selectedKey)}
                  size="small"
                  color="error"
                >
                  <DeleteIcon />
                </IconButton>
              </>
            )}
          </Box>
        </Paper>

        {/* Tabs */}
        <Paper sx={{ flex: 1, overflow: 'auto' }}>
          <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)} sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tab label="Dashboard" />
            <Tab label="Resources" disabled={!selectedKey} />
            <Tab label="Request Builder" disabled={!selectedKey} />
          </Tabs>

          {/* Dashboard Tab */}
          <TabPanel value={tabValue} index={0}>
            {!selectedKey ? (
              <Box sx={{ p: 3, textAlign: 'center' }}>
                <Typography color="text.secondary">
                  Select a gateway to view information
                </Typography>
              </Box>
            ) : gatewayLoading ? (
              <Box sx={{ p: 3, textAlign: 'center' }}>
                <CircularProgress />
              </Box>
            ) : (
              <Box sx={{ p: 2 }}>
                <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 2 }}>
                  {/* System Info Card */}
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                        System Information
                      </Typography>
                      <Divider sx={{ my: 1 }} />
                      {gatewayInfo?.system ? (
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="body2" color="text.secondary">Version</Typography>
                            <Typography variant="body2">{gatewayInfo.system.version || 'N/A'}</Typography>
                          </Box>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="body2" color="text.secondary">Edition</Typography>
                            <Typography variant="body2">{gatewayInfo.system.edition || 'N/A'}</Typography>
                          </Box>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="body2" color="text.secondary">Uptime</Typography>
                            <Typography variant="body2">{gatewayInfo.system.uptime || 'N/A'}</Typography>
                          </Box>
                        </Box>
                      ) : (
                        <Typography color="text.secondary">Unable to fetch system info</Typography>
                      )}
                    </CardContent>
                  </Card>

                  {/* License Card */}
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                        License
                      </Typography>
                      <Divider sx={{ my: 1 }} />
                      {gatewayInfo?.license ? (
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                          <Chip
                            label={gatewayInfo.license.isValid ? 'Valid' : 'Invalid'}
                            color={gatewayInfo.license.isValid ? 'success' : 'error'}
                            size="small"
                          />
                          <Typography variant="body2">
                            Expires: {gatewayInfo.license.expirationDate || 'N/A'}
                          </Typography>
                        </Box>
                      ) : (
                        <Typography color="text.secondary">Unable to fetch license info</Typography>
                      )}
                    </CardContent>
                  </Card>

                  {/* Modules Card */}
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                        Modules
                      </Typography>
                      <Divider sx={{ my: 1 }} />
                      {gatewayInfo?.modules ? (
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {Array.isArray(gatewayInfo.modules) ? (
                            gatewayInfo.modules.slice(0, 10).map((mod: { name: string; state: string }, i: number) => (
                              <Chip
                                key={i}
                                label={mod.name}
                                size="small"
                                color={mod.state === 'RUNNING' ? 'success' : 'default'}
                                variant="outlined"
                              />
                            ))
                          ) : (
                            <Typography color="text.secondary">No modules found</Typography>
                          )}
                        </Box>
                      ) : (
                        <Typography color="text.secondary">Unable to fetch modules</Typography>
                      )}
                    </CardContent>
                  </Card>
                </Box>

                {/* Quick Actions */}
                <Box sx={{ mt: 3 }}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Quick Actions
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Button
                      variant="outlined"
                      startIcon={<ScanIcon />}
                      onClick={() => scanProjectsMutation.mutate()}
                      disabled={scanProjectsMutation.isPending}
                    >
                      {scanProjectsMutation.isPending ? 'Scanning...' : 'Scan Projects'}
                    </Button>
                    <Button
                      variant="outlined"
                      onClick={() => testConnectionMutation.mutate()}
                      disabled={testConnectionMutation.isPending}
                    >
                      {testConnectionMutation.isPending ? 'Testing...' : 'Test Connection'}
                    </Button>
                  </Box>
                  {scanProjectsMutation.isSuccess && (
                    <Alert severity="success" sx={{ mt: 1 }}>
                      Project scan triggered successfully
                    </Alert>
                  )}
                  {testConnectionMutation.isSuccess && (
                    <Alert
                      severity={testConnectionMutation.data?.success ? 'success' : 'error'}
                      sx={{ mt: 1 }}
                    >
                      {testConnectionMutation.data?.message}
                    </Alert>
                  )}
                </Box>
              </Box>
            )}
          </TabPanel>

          {/* Resources Tab */}
          <TabPanel value={tabValue} index={1}>
            <Box sx={{ p: 2 }}>
              <Typography color="text.secondary">
                Select a resource type from the left panel to browse gateway resources.
              </Typography>
            </Box>
          </TabPanel>

          {/* Request Builder Tab */}
          <TabPanel value={tabValue} index={2}>
            <Box sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                <FormControl size="small" sx={{ minWidth: 100 }}>
                  <Select
                    value={requestMethod}
                    onChange={(e) => setRequestMethod(e.target.value)}
                  >
                    <MenuItem value="GET">GET</MenuItem>
                    <MenuItem value="POST">POST</MenuItem>
                    <MenuItem value="PUT">PUT</MenuItem>
                    <MenuItem value="DELETE">DELETE</MenuItem>
                  </Select>
                </FormControl>
                <TextField
                  size="small"
                  fullWidth
                  value={requestPath}
                  onChange={(e) => setRequestPath(e.target.value)}
                  placeholder="/data/status/sys-info"
                />
                <Button
                  variant="contained"
                  startIcon={<SendIcon />}
                  onClick={() => executeRequestMutation.mutate()}
                  disabled={executeRequestMutation.isPending}
                >
                  Send
                </Button>
              </Box>

              {(requestMethod === 'POST' || requestMethod === 'PUT') && (
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  value={requestBody}
                  onChange={(e) => setRequestBody(e.target.value)}
                  placeholder='{"key": "value"}'
                  sx={{ mb: 2 }}
                />
              )}

              {requestError && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {requestError}
                </Alert>
              )}

              {requestResponse && (
                <Box>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Response
                  </Typography>
                  <Paper
                    variant="outlined"
                    sx={{
                      p: 2,
                      bgcolor: 'background.default',
                      maxHeight: 400,
                      overflow: 'auto',
                    }}
                  >
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                      {JSON.stringify(requestResponse, null, 2)}
                    </pre>
                  </Paper>
                </Box>
              )}
            </Box>
          </TabPanel>
        </Paper>
      </Box>

      {/* API Key Dialog */}
      <APIKeyDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSave={(data) => createKeyMutation.mutate(data)}
        isLoading={createKeyMutation.isPending}
      />
    </Box>
  );
}
