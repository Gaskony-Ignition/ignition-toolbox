/**
 * API Explorer page for interacting with Ignition Gateway REST API
 */

import { useState, useMemo } from 'react';
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
  InputAdornment,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Send as SendIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandIcon,
  ChevronRight as ChevronIcon,
  Info as InfoIcon,
  PlayArrow as ScanIcon,
  Extension as ModulesIcon,
  FolderOpen as ProjectsIcon,
  Speed as PerfIcon,
  SettingsInputComponent as ResourcesIcon,
  Visibility as PerspectiveIcon,
  BugReport as DiagnosticsIcon,
  Search as SearchIcon,
  MenuBook as DocsIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type ApiKeyInfo } from '../api/client';
import { ignitionApiDocs, type ApiEndpointDoc, type ApiCategoryDoc } from '../data/ignitionApiDocs';

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

/** Helper to determine HTTP method color */
function getMethodColor(method: string): string {
  switch (method.toUpperCase()) {
    case 'GET': return '#4caf50';
    case 'POST': return '#2196f3';
    case 'PUT': return '#ff9800';
    case 'DELETE': return '#f44336';
    case 'PATCH': return '#9c27b0';
    default: return '#757575';
  }
}

/** Documentation tab content with search and OpenAPI support */
function DocumentationTab({
  selectedKeyInfo,
  selectedKey,
}: {
  selectedKeyInfo: ApiKeyInfo | undefined;
  selectedKey: string;
}) {
  const [searchQuery, setSearchQuery] = useState('');

  // Try to fetch OpenAPI spec if a gateway is selected
  const { data: openApiSpec, isLoading: openApiLoading } = useQuery({
    queryKey: ['openapi-spec', selectedKey],
    queryFn: () =>
      api.apiExplorer.fetchOpenAPI({
        gateway_url: selectedKeyInfo?.gateway_url || '',
        api_key_name: selectedKey,
      }),
    enabled: !!selectedKey && !!selectedKeyInfo,
    retry: false,
  });

  // Parse OpenAPI spec into categories if available
  const openApiCategories = useMemo(() => {
    if (!openApiSpec?.paths) return null;

    const tagMap = new Map<string, ApiEndpointDoc[]>();

    for (const [path, methods] of Object.entries(openApiSpec.paths)) {
      if (typeof methods !== 'object' || methods === null) continue;
      for (const [method, details] of Object.entries(methods as Record<string, unknown>)) {
        if (!['get', 'post', 'put', 'delete', 'patch'].includes(method)) continue;
        const detail = details as {
          tags?: string[];
          summary?: string;
          description?: string;
          parameters?: Array<{
            name: string;
            in: string;
            description?: string;
            required?: boolean;
            schema?: { type?: string };
          }>;
        };
        const tags = detail.tags || ['Other'];
        const endpoint: ApiEndpointDoc = {
          method: method.toUpperCase(),
          path,
          description: detail.summary || detail.description || '',
          parameters: detail.parameters?.map((p) => ({
            name: p.name,
            type: p.schema?.type || p.in,
            description: p.description || '',
            required: p.required,
          })),
        };
        for (const tag of tags) {
          if (!tagMap.has(tag)) tagMap.set(tag, []);
          tagMap.get(tag)!.push(endpoint);
        }
      }
    }

    const categories: ApiCategoryDoc[] = [];
    for (const [name, endpoints] of tagMap.entries()) {
      categories.push({
        name,
        description: `Endpoints tagged "${name}" from gateway OpenAPI specification.`,
        endpoints,
      });
    }
    return categories.sort((a, b) => a.name.localeCompare(b.name));
  }, [openApiSpec]);

  // Use OpenAPI categories if available, otherwise static docs
  const docsSource = openApiCategories || ignitionApiDocs;
  const isFromOpenApi = !!openApiCategories;

  // Filter categories and endpoints by search query
  const filteredDocs = useMemo(() => {
    if (!searchQuery.trim()) return docsSource;

    const query = searchQuery.toLowerCase();
    return docsSource
      .map((category) => ({
        ...category,
        endpoints: category.endpoints.filter(
          (ep) =>
            ep.path.toLowerCase().includes(query) ||
            ep.description.toLowerCase().includes(query) ||
            ep.method.toLowerCase().includes(query)
        ),
      }))
      .filter((category) => category.endpoints.length > 0);
  }, [docsSource, searchQuery]);

  return (
    <Box sx={{ p: 2 }}>
      {/* Source indicator */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <DocsIcon color="action" />
        <Typography variant="subtitle2" color="text.secondary">
          {isFromOpenApi
            ? 'Documentation loaded from gateway OpenAPI specification'
            : 'Curated Ignition 8.3 API documentation'}
        </Typography>
        {openApiLoading && selectedKey && (
          <CircularProgress size={16} sx={{ ml: 1 }} />
        )}
      </Box>

      {/* Search bar */}
      <TextField
        size="small"
        fullWidth
        placeholder="Search endpoints by path, description, or method..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        sx={{ mb: 2 }}
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          },
        }}
      />

      {/* Categories */}
      {filteredDocs.length === 0 ? (
        <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
          No endpoints match your search.
        </Typography>
      ) : (
        filteredDocs.map((category) => (
          <Accordion key={category.name} defaultExpanded={filteredDocs.length <= 3 || !!searchQuery}>
            <AccordionSummary expandIcon={<ExpandIcon />}>
              <Box>
                <Typography variant="subtitle1" fontWeight="bold">
                  {category.name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {category.description} ({category.endpoints.length} endpoint{category.endpoints.length !== 1 ? 's' : ''})
                </Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails sx={{ p: 0 }}>
              {category.endpoints.map((endpoint, idx) => (
                <Box
                  key={`${endpoint.method}-${endpoint.path}-${idx}`}
                  sx={{
                    px: 2,
                    py: 1.5,
                    borderTop: idx > 0 ? 1 : 0,
                    borderColor: 'divider',
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                    <Chip
                      label={endpoint.method}
                      size="small"
                      sx={{
                        fontWeight: 'bold',
                        fontFamily: 'monospace',
                        bgcolor: getMethodColor(endpoint.method),
                        color: '#fff',
                        minWidth: 60,
                      }}
                    />
                    <Typography
                      variant="body2"
                      fontFamily="monospace"
                      sx={{ wordBreak: 'break-all' }}
                    >
                      {endpoint.path}
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ ml: 0.5 }}>
                    {endpoint.description}
                  </Typography>
                  {endpoint.parameters && endpoint.parameters.length > 0 && (
                    <Box sx={{ mt: 1, ml: 1 }}>
                      <Typography variant="caption" color="text.secondary" fontWeight="bold">
                        Parameters:
                      </Typography>
                      {endpoint.parameters.map((param) => (
                        <Box key={param.name} sx={{ display: 'flex', gap: 1, ml: 1, mt: 0.25 }}>
                          <Typography variant="caption" fontFamily="monospace" color="primary.main">
                            {param.name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            ({param.type}){param.required ? ' *required' : ''}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            - {param.description}
                          </Typography>
                        </Box>
                      ))}
                    </Box>
                  )}
                  {endpoint.notes && (
                    <Alert severity="info" variant="outlined" sx={{ mt: 1, py: 0 }}>
                      <Typography variant="caption">{endpoint.notes}</Typography>
                    </Alert>
                  )}
                </Box>
              ))}
            </AccordionDetails>
          </Accordion>
        ))
      )}
    </Box>
  );
}

export function APIExplorer() {
  const queryClient = useQueryClient();
  const [selectedKey, setSelectedKey] = useState<string>('');
  const [tabValue, setTabValue] = useState(0);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [expandedEndpoints, setExpandedEndpoints] = useState<string[]>(['gateway']);

  // Request builder state
  const [requestMethod, setRequestMethod] = useState('GET');
  const [requestPath, setRequestPath] = useState('/data/api/v1/gateway-info');
  const [requestBody, setRequestBody] = useState('');
  const [requestResponse, setRequestResponse] = useState<Record<string, unknown> | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);

  // Fetch API keys
  const { data: apiKeys = [] } = useQuery<ApiKeyInfo[]>({
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

  // Determine if the selected gateway uses HTTP
  const isHttpConnection = useMemo(() => {
    if (!selectedKeyInfo?.gateway_url) return false;
    const url = selectedKeyInfo.gateway_url.toLowerCase();
    return url.startsWith('http://') || (!url.startsWith('https://') && !url.startsWith('http'));
  }, [selectedKeyInfo]);

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
      id: 'gateway',
      label: 'Gateway',
      icon: <InfoIcon />,
      children: [
        { path: '/data/api/v1/gateway-info', label: 'Gateway Info' },
        { path: '/data/api/v1/overview', label: 'Overview' },
        { path: '/data/api/v1/licenses', label: 'Licenses' },
        { path: '/data/api/v1/trial', label: 'Trial Status' },
        { path: '/data/api/v1/designers', label: 'Connected Designers' },
      ],
    },
    {
      id: 'modules',
      label: 'Modules',
      icon: <ModulesIcon />,
      children: [
        { path: '/data/api/v1/modules/healthy', label: 'Module Health' },
        { path: '/data/api/v1/modules/quarantined', label: 'Quarantined' },
      ],
    },
    {
      id: 'projects',
      label: 'Projects',
      icon: <ProjectsIcon />,
      children: [
        { path: '/data/api/v1/projects/list', label: 'List Projects' },
        { path: '/data/api/v1/projects/names', label: 'Project Names' },
      ],
    },
    {
      id: 'resources',
      label: 'Resources',
      icon: <ResourcesIcon />,
      children: [
        { path: '/data/api/v1/resources/list/ignition/database-connection', label: 'Database Connections' },
        { path: '/data/api/v1/resources/list/ignition/tag-provider', label: 'Tag Providers' },
        { path: '/data/api/v1/resources/list/ignition/opc-connection', label: 'OPC Connections' },
        { path: '/data/api/v1/resources/list/com.inductiveautomation.opcua/device', label: 'OPC UA Devices' },
        { path: '/data/api/v1/resources/list/ignition/user-source', label: 'User Sources' },
        { path: '/data/api/v1/resources/list/ignition/schedule', label: 'Schedules' },
        { path: '/data/api/v1/resources/list/ignition/alarm-journal', label: 'Alarm Journals' },
        { path: '/data/api/v1/resources/list/ignition/email-profile', label: 'Email Profiles' },
        { path: '/data/api/v1/resources/list/ignition/identity-provider', label: 'Identity Providers' },
        { path: '/data/api/v1/resources/list/ignition/api-token', label: 'API Tokens' },
      ],
    },
    {
      id: 'perspective',
      label: 'Perspective',
      icon: <PerspectiveIcon />,
      children: [
        { path: '/data/perspective/api/v1/sessions/', label: 'Sessions' },
        { path: '/data/api/v1/resources/list/com.inductiveautomation.perspective/themes', label: 'Themes' },
        { path: '/data/api/v1/resources/list/com.inductiveautomation.perspective/icons', label: 'Icons' },
      ],
    },
    {
      id: 'diagnostics',
      label: 'Diagnostics',
      icon: <DiagnosticsIcon />,
      children: [
        { path: '/data/api/v1/diagnostics/threads/threaddump', label: 'Thread Dump' },
        { path: '/data/api/v1/diagnostics/threads/deadlocks', label: 'Deadlocks' },
        { path: '/data/api/v1/logs', label: 'Logs' },
      ],
    },
    {
      id: 'performance',
      label: 'Performance',
      icon: <PerfIcon />,
      children: [
        { path: '/data/api/v1/systemPerformance/charts', label: 'Charts' },
        { path: '/data/api/v1/systemPerformance/currentGauges', label: 'Current Gauges' },
        { path: '/data/api/v1/systemPerformance/threads', label: 'Threads' },
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
        <Paper
          sx={{
            p: 2,
            mb: 2,
            borderLeft: selectedKey
              ? `4px solid ${isHttpConnection ? '#ff9800' : '#4caf50'}`
              : undefined,
          }}
        >
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
          {selectedKey && isHttpConnection && (
            <Alert severity="warning" sx={{ mt: 1.5 }} variant="outlined">
              HTTP connection detected. Some API features require HTTPS. API key authentication works best over HTTPS.
            </Alert>
          )}
        </Paper>

        {/* Tabs */}
        <Paper sx={{ flex: 1, overflow: 'auto' }}>
          <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)} sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tab label="Dashboard" />
            <Tab label="Resources" disabled={!selectedKey} />
            <Tab label="Request Builder" disabled={!selectedKey} />
            <Tab label="Documentation" />
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
                          {Object.entries(gatewayInfo.system as Record<string, unknown>).slice(0, 8).map(([key, value]) => (
                            <Box key={key} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                              <Typography variant="body2" color="text.secondary">{key}</Typography>
                              <Typography variant="body2">{String(value ?? 'N/A')}</Typography>
                            </Box>
                          ))}
                        </Box>
                      ) : (
                        <Typography color="text.secondary">Unable to fetch system info</Typography>
                      )}
                    </CardContent>
                  </Card>

                  {/* License / Trial Card */}
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                        License
                      </Typography>
                      <Divider sx={{ my: 1 }} />
                      {gatewayInfo?.license ? (
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                          {typeof gatewayInfo.license === 'object' && !Array.isArray(gatewayInfo.license) ? (
                            Object.entries(gatewayInfo.license as Record<string, unknown>).slice(0, 6).map(([key, value]) => (
                              <Box key={key} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                                <Typography variant="body2" color="text.secondary">{key}</Typography>
                                <Typography variant="body2">{String(value ?? 'N/A')}</Typography>
                              </Box>
                            ))
                          ) : (
                            <Typography variant="body2">
                              {JSON.stringify(gatewayInfo.license, null, 2)}
                            </Typography>
                          )}
                        </Box>
                      ) : gatewayInfo?.trial ? (
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                          <Chip label="Trial Mode" color="warning" size="small" />
                          {Object.entries(gatewayInfo.trial as Record<string, unknown>).map(([key, value]) => (
                            <Box key={key} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                              <Typography variant="body2" color="text.secondary">{key}</Typography>
                              <Typography variant="body2">{String(value ?? 'N/A')}</Typography>
                            </Box>
                          ))}
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
                          {typeof gatewayInfo.modules === 'boolean' ? (
                            <Chip
                              label={gatewayInfo.modules ? 'All Healthy' : 'Issues Detected'}
                              color={gatewayInfo.modules ? 'success' : 'error'}
                              size="small"
                            />
                          ) : Array.isArray(gatewayInfo.modules) ? (
                            gatewayInfo.modules.slice(0, 15).map((mod: { name?: string; state?: string } | string, i: number) => (
                              <Chip
                                key={i}
                                label={typeof mod === 'string' ? mod : (mod.name || 'Unknown')}
                                size="small"
                                color={typeof mod === 'object' && mod.state === 'RUNNING' ? 'success' : 'default'}
                                variant="outlined"
                              />
                            ))
                          ) : (
                            <Typography variant="body2">
                              {JSON.stringify(gatewayInfo.modules)}
                            </Typography>
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
                  placeholder="/data/api/v1/gateway-info"
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

          {/* Documentation Tab */}
          <TabPanel value={tabValue} index={3}>
            <DocumentationTab
              selectedKeyInfo={selectedKeyInfo}
              selectedKey={selectedKey}
            />
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
