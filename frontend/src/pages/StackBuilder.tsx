/**
 * Stack Builder page for generating Docker Compose stacks
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
  CardActions,
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
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Tooltip,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Settings as SettingsIcon,
  Download as DownloadIcon,
  Save as SaveIcon,
  FolderOpen as LoadIcon,
  Preview as PreviewIcon,
  CheckCircle as CheckIcon,
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
    <Box role="tabpanel" hidden={value !== index} sx={{ p: 2 }}>
      {value === index && children}
    </Box>
  );
}

interface ServiceInstance {
  app_id: string;
  instance_name: string;
  config: Record<string, unknown>;
}

interface ServiceApplication {
  id: string;
  name: string;
  description: string;
  category: string;
  image: string;
  enabled: boolean;
  default_version?: string;
  default_config?: {
    ports?: string[];
    environment?: Record<string, string>;
    volumes?: string[];
  };
  config_schema?: Record<string, unknown>;
}

interface GlobalSettings {
  stack_name: string;
  timezone: string;
  restart_policy: string;
}

interface SavedStack {
  id: number;
  stack_name: string;
  description?: string;
  config_json: {
    instances: ServiceInstance[];
  };
  global_settings?: GlobalSettings;
  created_at?: string;
  updated_at?: string;
}

interface ServiceConfigDialogProps {
  open: boolean;
  onClose: () => void;
  service: ServiceApplication | null;
  instance?: ServiceInstance;
  onSave: (instance: ServiceInstance) => void;
  existingNames: string[];
}

function ServiceConfigDialog({
  open,
  onClose,
  service,
  instance,
  onSave,
  existingNames,
}: ServiceConfigDialogProps) {
  const [instanceName, setInstanceName] = useState(instance?.instance_name || '');
  const [config, setConfig] = useState<Record<string, string>>(
    (instance?.config as Record<string, string>) || {}
  );

  const { data: versions = { versions: ['latest'] } } = useQuery({
    queryKey: ['versions', service?.id],
    queryFn: () => api.stackBuilder.getVersions(service!.id),
    enabled: !!service,
  });

  const handleSave = () => {
    if (!service) return;
    onSave({
      app_id: service.id,
      instance_name: instanceName || `${service.id}-1`,
      config,
    });
    onClose();
  };

  if (!service) return null;

  const defaultEnv = service.default_config?.environment || {};

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Configure {service.name}
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          <TextField
            label="Instance Name"
            value={instanceName}
            onChange={(e) => setInstanceName(e.target.value)}
            fullWidth
            required
            placeholder={`${service.id}-1`}
            error={existingNames.includes(instanceName)}
            helperText={existingNames.includes(instanceName) ? 'Name already in use' : ''}
          />

          <FormControl fullWidth>
            <InputLabel>Version</InputLabel>
            <Select
              value={config.version || service.default_version || 'latest'}
              onChange={(e) => setConfig({ ...config, version: e.target.value })}
              label="Version"
            >
              {versions.versions.map((v: string) => (
                <MenuItem key={v} value={v}>
                  {v}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Divider sx={{ my: 1 }} />
          <Typography variant="subtitle2" color="text.secondary">
            Environment Variables
          </Typography>

          {Object.entries(defaultEnv).map(([key, defaultValue]) => (
            <TextField
              key={key}
              label={key}
              value={config[key] || ''}
              onChange={(e) => setConfig({ ...config, [key]: e.target.value })}
              placeholder={defaultValue}
              fullWidth
              size="small"
            />
          ))}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={!instanceName || existingNames.includes(instanceName)}
        >
          {instance ? 'Update' : 'Add Service'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export function StackBuilder() {
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState(0);
  const [instances, setInstances] = useState<ServiceInstance[]>([]);
  const [globalSettings, setGlobalSettings] = useState<GlobalSettings>({
    stack_name: 'iiot-stack',
    timezone: 'UTC',
    restart_policy: 'unless-stopped',
  });
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [selectedService, setSelectedService] = useState<ServiceApplication | null>(null);
  const [editingInstance, setEditingInstance] = useState<ServiceInstance | undefined>();
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [loadDialogOpen, setLoadDialogOpen] = useState(false);
  const [stackName, setStackName] = useState('');
  const [stackDescription, setStackDescription] = useState('');

  // Fetch catalog
  const { data: catalog, isLoading: catalogLoading } = useQuery({
    queryKey: ['stackbuilder-catalog'],
    queryFn: () => api.stackBuilder.getCatalog(),
  });

  // Fetch saved stacks
  const { data: savedStacks = [] } = useQuery<SavedStack[]>({
    queryKey: ['saved-stacks'],
    queryFn: () => api.stackBuilder.listStacks(),
  });

  // Detect integrations
  const { data: integrations } = useQuery({
    queryKey: ['integrations', instances],
    queryFn: () =>
      api.stackBuilder.detectIntegrations({
        instances: instances.map((i) => ({
          app_id: i.app_id,
          instance_name: i.instance_name,
          config: i.config,
        })),
      }),
    enabled: instances.length > 0,
  });

  // Generate stack mutation
  const generateMutation = useMutation({
    mutationFn: () =>
      api.stackBuilder.generate({
        instances: instances.map((i) => ({
          app_id: i.app_id,
          instance_name: i.instance_name,
          config: i.config,
        })),
        global_settings: globalSettings,
      }),
    onSuccess: (data) => {
      setPreviewContent(data.docker_compose);
      setTabValue(2);
    },
  });

  // Download stack mutation
  const downloadMutation = useMutation({
    mutationFn: async () => {
      const response = await api.stackBuilder.download({
        instances: instances.map((i) => ({
          app_id: i.app_id,
          instance_name: i.instance_name,
          config: i.config,
        })),
        global_settings: globalSettings,
      });
      return response;
    },
  });

  // Save stack mutation
  const saveStackMutation = useMutation({
    mutationFn: (data: { stack_name: string; description?: string }) =>
      api.stackBuilder.saveStack({
        stack_name: data.stack_name,
        description: data.description,
        config_json: { instances },
        global_settings: globalSettings,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-stacks'] });
      setSaveDialogOpen(false);
    },
  });

  // Delete stack mutation
  const deleteStackMutation = useMutation({
    mutationFn: (id: number) => api.stackBuilder.deleteStack(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-stacks'] });
    },
  });

  const applications = catalog?.applications?.filter((a: ServiceApplication) => a.enabled) || [];
  const categories = Array.from(new Set(applications.map((a: ServiceApplication) => a.category))) as string[];

  const handleAddService = (service: ServiceApplication) => {
    setSelectedService(service);
    setEditingInstance(undefined);
    setConfigDialogOpen(true);
  };

  const handleEditInstance = (instance: ServiceInstance) => {
    const service = applications.find((a: ServiceApplication) => a.id === instance.app_id);
    if (service) {
      setSelectedService(service);
      setEditingInstance(instance);
      setConfigDialogOpen(true);
    }
  };

  const handleSaveInstance = (instance: ServiceInstance) => {
    if (editingInstance) {
      setInstances((prev) =>
        prev.map((i) =>
          i.instance_name === editingInstance.instance_name ? instance : i
        )
      );
    } else {
      setInstances((prev) => [...prev, instance]);
    }
  };

  const handleRemoveInstance = (instanceName: string) => {
    setInstances((prev) => prev.filter((i) => i.instance_name !== instanceName));
  };

  const handleLoadStack = (stack: SavedStack) => {
    setInstances(stack.config_json.instances);
    if (stack.global_settings) {
      setGlobalSettings(stack.global_settings);
    }
    setLoadDialogOpen(false);
  };

  const existingNames = instances.map((i) => i.instance_name);

  return (
    <Box sx={{ display: 'flex', gap: 2, height: 'calc(100vh - 100px)' }}>
      {/* Left Panel: Service Catalog */}
      <Paper sx={{ width: 350, overflow: 'auto' }}>
        <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)} sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tab label="Services" />
          <Tab label="Config" />
          <Tab label="Preview" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          {catalogLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Box>
              {categories.map((category) => (
                <Box key={category} sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                    {category}
                  </Typography>
                  <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 1 }}>
                    {applications
                      .filter((a: ServiceApplication) => a.category === category)
                      .map((app: ServiceApplication) => (
                        <Card key={app.id} variant="outlined" sx={{ height: '100%' }}>
                          <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                            <Typography variant="body2" fontWeight="medium" noWrap>
                              {app.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary" sx={{
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                            }}>
                              {app.description}
                            </Typography>
                          </CardContent>
                          <CardActions sx={{ p: 1, pt: 0 }}>
                            <Button
                              size="small"
                              startIcon={<AddIcon />}
                              onClick={() => handleAddService(app)}
                            >
                              Add
                            </Button>
                          </CardActions>
                        </Card>
                      ))}
                  </Box>
                </Box>
              ))}
            </Box>
          )}
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Stack Name"
              value={globalSettings.stack_name}
              onChange={(e) => setGlobalSettings({ ...globalSettings, stack_name: e.target.value })}
              fullWidth
              size="small"
            />
            <FormControl fullWidth size="small">
              <InputLabel>Timezone</InputLabel>
              <Select
                value={globalSettings.timezone}
                onChange={(e) => setGlobalSettings({ ...globalSettings, timezone: e.target.value })}
                label="Timezone"
              >
                <MenuItem value="UTC">UTC</MenuItem>
                <MenuItem value="America/New_York">America/New_York</MenuItem>
                <MenuItem value="America/Chicago">America/Chicago</MenuItem>
                <MenuItem value="America/Denver">America/Denver</MenuItem>
                <MenuItem value="America/Los_Angeles">America/Los_Angeles</MenuItem>
                <MenuItem value="Europe/London">Europe/London</MenuItem>
                <MenuItem value="Europe/Paris">Europe/Paris</MenuItem>
                <MenuItem value="Asia/Tokyo">Asia/Tokyo</MenuItem>
                <MenuItem value="Australia/Sydney">Australia/Sydney</MenuItem>
                <MenuItem value="Australia/Adelaide">Australia/Adelaide</MenuItem>
              </Select>
            </FormControl>
            <FormControl fullWidth size="small">
              <InputLabel>Restart Policy</InputLabel>
              <Select
                value={globalSettings.restart_policy}
                onChange={(e) => setGlobalSettings({ ...globalSettings, restart_policy: e.target.value })}
                label="Restart Policy"
              >
                <MenuItem value="no">No</MenuItem>
                <MenuItem value="always">Always</MenuItem>
                <MenuItem value="on-failure">On Failure</MenuItem>
                <MenuItem value="unless-stopped">Unless Stopped</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          {previewContent ? (
            <Box
              component="pre"
              sx={{
                p: 1,
                bgcolor: 'background.default',
                borderRadius: 1,
                overflow: 'auto',
                fontSize: '0.75rem',
                fontFamily: 'monospace',
                m: 0,
              }}
            >
              {previewContent}
            </Box>
          ) : (
            <Typography color="text.secondary">
              Click "Preview" to generate docker-compose.yml
            </Typography>
          )}
        </TabPanel>
      </Paper>

      {/* Right Panel: Stack Configuration */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Actions Bar */}
        <Paper sx={{ p: 2, mb: 2 }}>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <Typography variant="h6" sx={{ flex: 1 }}>
              Stack: {globalSettings.stack_name}
            </Typography>
            <Button
              variant="outlined"
              startIcon={<LoadIcon />}
              onClick={() => setLoadDialogOpen(true)}
              size="small"
            >
              Load
            </Button>
            <Button
              variant="outlined"
              startIcon={<SaveIcon />}
              onClick={() => setSaveDialogOpen(true)}
              size="small"
              disabled={instances.length === 0}
            >
              Save
            </Button>
            <Button
              variant="outlined"
              startIcon={<PreviewIcon />}
              onClick={() => generateMutation.mutate()}
              size="small"
              disabled={instances.length === 0 || generateMutation.isPending}
            >
              Preview
            </Button>
            <Button
              variant="contained"
              startIcon={<DownloadIcon />}
              onClick={() => downloadMutation.mutate()}
              size="small"
              disabled={instances.length === 0 || downloadMutation.isPending}
            >
              Download
            </Button>
          </Box>
        </Paper>

        {/* Selected Services */}
        <Paper sx={{ flex: 1, overflow: 'auto', p: 2 }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Selected Services ({instances.length})
          </Typography>

          {instances.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography color="text.secondary">
                No services added yet. Select services from the catalog.
              </Typography>
            </Box>
          ) : (
            <List>
              {instances.map((instance) => {
                const app = applications.find((a: ServiceApplication) => a.id === instance.app_id);
                return (
                  <ListItem
                    key={instance.instance_name}
                    sx={{
                      border: 1,
                      borderColor: 'divider',
                      borderRadius: 1,
                      mb: 1,
                    }}
                  >
                    <ListItemText
                      primary={instance.instance_name}
                      secondary={
                        <Box component="span" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <span>{app?.name || instance.app_id}</span>
                          <Chip
                            label={(instance.config?.version as string) || 'latest'}
                            size="small"
                            variant="outlined"
                          />
                        </Box>
                      }
                    />
                    <ListItemSecondaryAction>
                      <Tooltip title="Configure">
                        <IconButton
                          size="small"
                          onClick={() => handleEditInstance(instance)}
                        >
                          <SettingsIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Remove">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleRemoveInstance(instance.instance_name)}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </ListItemSecondaryAction>
                  </ListItem>
                );
              })}
            </List>
          )}

          {/* Integrations */}
          {integrations && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Detected Integrations
              </Typography>

              {integrations.conflicts?.length > 0 && (
                <Alert severity="error" sx={{ mb: 1 }}>
                  {integrations.conflicts.map((c: { message: string }, i: number) => (
                    <div key={i}>{c.message}</div>
                  ))}
                </Alert>
              )}

              {integrations.warnings?.length > 0 && (
                <Alert severity="warning" sx={{ mb: 1 }}>
                  {integrations.warnings.map((w: { message: string }, i: number) => (
                    <div key={i}>{w.message}</div>
                  ))}
                </Alert>
              )}

              {Object.keys(integrations.integrations || {}).length > 0 && (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {Object.entries(integrations.integrations || {}).map(([type, _]) => (
                    <Chip
                      key={type}
                      icon={<CheckIcon />}
                      label={type.replace('_', ' ')}
                      size="small"
                      color="success"
                      variant="outlined"
                    />
                  ))}
                </Box>
              )}
            </Box>
          )}
        </Paper>
      </Box>

      {/* Service Config Dialog */}
      <ServiceConfigDialog
        open={configDialogOpen}
        onClose={() => setConfigDialogOpen(false)}
        service={selectedService}
        instance={editingInstance}
        onSave={handleSaveInstance}
        existingNames={editingInstance ? existingNames.filter((n) => n !== editingInstance.instance_name) : existingNames}
      />

      {/* Save Stack Dialog */}
      <Dialog open={saveDialogOpen} onClose={() => setSaveDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Save Stack</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <TextField
              label="Stack Name"
              value={stackName}
              onChange={(e) => setStackName(e.target.value)}
              fullWidth
              required
            />
            <TextField
              label="Description"
              value={stackDescription}
              onChange={(e) => setStackDescription(e.target.value)}
              fullWidth
              multiline
              rows={2}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSaveDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={() => saveStackMutation.mutate({ stack_name: stackName, description: stackDescription })}
            variant="contained"
            disabled={!stackName || saveStackMutation.isPending}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Load Stack Dialog */}
      <Dialog open={loadDialogOpen} onClose={() => setLoadDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Load Stack</DialogTitle>
        <DialogContent>
          {savedStacks.length === 0 ? (
            <Typography color="text.secondary">No saved stacks found.</Typography>
          ) : (
            <List>
              {savedStacks.map((stack) => (
                <ListItem
                  key={stack.id}
                  sx={{
                    border: 1,
                    borderColor: 'divider',
                    borderRadius: 1,
                    mb: 1,
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                  onClick={() => handleLoadStack(stack)}
                >
                  <ListItemText
                    primary={stack.stack_name}
                    secondary={stack.description || `${stack.config_json.instances.length} services`}
                  />
                  <ListItemSecondaryAction>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteStackMutation.mutate(stack.id);
                      }}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLoadDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
