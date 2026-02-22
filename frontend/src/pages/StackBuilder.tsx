/**
 * Stack Builder page for generating Docker Compose stacks
 */

import { useState, useEffect } from 'react';
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
  Switch,
  FormControlLabel,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Checkbox,
  FormGroup,
  FormHelperText,
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
  ExpandMore as ExpandMoreIcon,
  CloudDownload as CloudDownloadIcon,
  FlightTakeoff as OfflineIcon,
  PlayArrow as DeployIcon,
  Stop as StopIcon,
  Circle as StatusIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type StackBuilderApplication } from '../api/client';
import { TIMING } from '../config/timing';
import { useStore } from '../store';

interface ServiceInstance {
  app_id: string;
  instance_name: string;
  config: Record<string, unknown>;
}

/** Local alias for StackBuilderApplication */
type ServiceApplication = StackBuilderApplication;

interface GlobalSettings {
  stack_name: string;
  timezone: string;
  restart_policy: string;
  [key: string]: unknown;
}

interface IntegrationSettings {
  reverse_proxy: {
    base_domain: string;
    enable_https: boolean;
    letsencrypt_email: string;
  };
  mqtt: {
    enable_tls: boolean;
    username: string;
    password: string;
    tls_port: number;
  };
  oauth: {
    realm_name: string;
    auto_configure_services: boolean;
  };
  database: {
    auto_register: boolean;
  };
  email: {
    from_address: string;
    auto_configure_services: boolean;
  };
  [key: string]: unknown;
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
  const [config, setConfig] = useState<Record<string, string | string[] | boolean>>(
    (instance?.config as Record<string, string | string[] | boolean>) || {}
  );

  const { data: versions = { versions: ['latest'] } } = useQuery({
    queryKey: ['versions', service?.id],
    queryFn: () => api.stackBuilder.getVersions(service!.id),
    enabled: !!service,
  });

  // Reset state when dialog opens with new service or instance
  useEffect(() => {
    if (instance) {
      setInstanceName(instance.instance_name);
      setConfig((instance.config as Record<string, string | string[] | boolean>) || {});
    } else if (service) {
      setInstanceName(`${service.id}-1`);
      setConfig({});
    }
  }, [instance, service]);

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
  const configurableOptions = service.configurable_options || {};

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

          {/* Configurable Options from Catalog */}
          {Object.keys(configurableOptions).length > 0 && (
            <>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle2" color="text.secondary">
                Configuration Options
              </Typography>

              {Object.entries(configurableOptions).map(([key, option]) => {
                if (option.visible === false) return null;
                // Skip 'name' field as it's handled by Instance Name above
                if (key === 'name') return null;
                // Skip version field as it's handled separately
                if (key === 'version') return null;

                // Check version constraint for module options
                if (option.version_constraint) {
                  const rawVersion = config.version;
                  const selectedVersion = (typeof rawVersion === 'string' ? rawVersion : null) || service.default_version || 'latest';
                  const constraint = option.version_constraint;
                  // Show 8.1 modules for 8.1.x versions, 8.3 modules for 8.3+ or latest
                  if (constraint === '8.1' && !selectedVersion.startsWith('8.1')) return null;
                  if (constraint === '8.3' && selectedVersion !== 'latest' && !selectedVersion.startsWith('8.3') && !selectedVersion.startsWith('8.4')) return null;
                }

                // Multiselect - for module selection
                if (option.type === 'multiselect' && option.options) {
                  const selectedValues = Array.isArray(config[key])
                    ? config[key] as Array<{ value: string } | string>
                    : [];
                  const selectedSet = new Set(
                    selectedValues.map(v => typeof v === 'object' ? v.value : v)
                  );

                  const handleMultiSelectChange = (optValue: string, checked: boolean) => {
                    const currentValues = [...selectedSet];
                    if (checked) {
                      setConfig({ ...config, [key]: [...currentValues, optValue] });
                    } else {
                      setConfig({ ...config, [key]: currentValues.filter(v => v !== optValue) });
                    }
                  };

                  return (
                    <FormControl key={key} component="fieldset" fullWidth size="small">
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                        {option.label || key}
                      </Typography>
                      {option.description && (
                        <FormHelperText sx={{ mt: 0, mb: 1 }}>{option.description}</FormHelperText>
                      )}
                      <FormGroup sx={{ maxHeight: 200, overflow: 'auto', pl: 1 }}>
                        {option.options.map((opt) => {
                          const optValue = typeof opt === 'string' ? opt : opt.value;
                          const optLabel = typeof opt === 'string' ? opt : opt.label;
                          const optDesc = typeof opt === 'object' ? opt.description : undefined;
                          return (
                            <Tooltip key={optValue} title={optDesc || ''} placement="right">
                              <FormControlLabel
                                control={
                                  <Checkbox
                                    size="small"
                                    checked={selectedSet.has(optValue)}
                                    onChange={(e) => handleMultiSelectChange(optValue, e.target.checked)}
                                  />
                                }
                                label={<Typography variant="body2">{optLabel}</Typography>}
                              />
                            </Tooltip>
                          );
                        })}
                      </FormGroup>
                    </FormControl>
                  );
                }

                // Select - dropdown for single selection
                if (option.type === 'select' && option.options) {
                  return (
                    <FormControl key={key} fullWidth size="small">
                      <InputLabel>{option.label || key}</InputLabel>
                      <Select
                        value={config[key] || option.default || ''}
                        onChange={(e) => setConfig({ ...config, [key]: String(e.target.value) })}
                        label={option.label || key}
                      >
                        {option.options.map((opt) => {
                          const optValue = typeof opt === 'string' ? opt : opt.value;
                          const optLabel = typeof opt === 'string' ? opt : opt.label;
                          return (
                            <MenuItem key={optValue} value={optValue}>
                              {optLabel}
                            </MenuItem>
                          );
                        })}
                      </Select>
                      {option.description && (
                        <FormHelperText>{option.description}</FormHelperText>
                      )}
                    </FormControl>
                  );
                }

                // Checkbox - for boolean options
                if (option.type === 'checkbox') {
                  const isChecked = config[key] !== undefined
                    ? Boolean(config[key])
                    : Boolean(option.default);
                  return (
                    <FormControl key={key} fullWidth size="small">
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={isChecked}
                            onChange={(e) => setConfig({ ...config, [key]: e.target.checked })}
                            size="small"
                          />
                        }
                        label={option.label || key}
                      />
                      {option.description && (
                        <FormHelperText sx={{ mt: -1, ml: 4 }}>{option.description}</FormHelperText>
                      )}
                    </FormControl>
                  );
                }

                // Textarea - for multi-line text input
                if (option.type === 'textarea') {
                  return (
                    <TextField
                      key={key}
                      label={option.label || key}
                      value={config[key] || ''}
                      onChange={(e) => setConfig({ ...config, [key]: e.target.value })}
                      placeholder={option.placeholder || String(option.default || '')}
                      helperText={option.description}
                      fullWidth
                      size="small"
                      multiline
                      minRows={3}
                      maxRows={6}
                    />
                  );
                }

                // Password - for sensitive fields
                if (option.type === 'password') {
                  return (
                    <TextField
                      key={key}
                      label={option.label || key}
                      type="password"
                      value={config[key] || ''}
                      onChange={(e) => setConfig({ ...config, [key]: e.target.value })}
                      placeholder={String(option.default || '')}
                      helperText={option.description}
                      fullWidth
                      size="small"
                    />
                  );
                }

                // Number - for numeric fields
                if (option.type === 'number') {
                  return (
                    <TextField
                      key={key}
                      label={option.label || key}
                      type="number"
                      value={config[key] || ''}
                      onChange={(e) => setConfig({ ...config, [key]: e.target.value })}
                      placeholder={String(option.default || '')}
                      helperText={option.description}
                      fullWidth
                      size="small"
                    />
                  );
                }

                // Text - default text input
                return (
                  <TextField
                    key={key}
                    label={option.label || key}
                    value={config[key] || ''}
                    onChange={(e) => setConfig({ ...config, [key]: e.target.value })}
                    placeholder={String(option.default || '')}
                    helperText={option.description}
                    fullWidth
                    size="small"
                  />
                );
              })}
            </>
          )}

          {/* Environment Variables fallback */}
          {Object.keys(configurableOptions).length === 0 && Object.keys(defaultEnv).length > 0 && (
            <>
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
            </>
          )}
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
  const stackSubTab = useStore((state) => state.stackSubTab);
  const [instances, setInstances] = useState<ServiceInstance[]>([]);
  const [globalSettings, setGlobalSettings] = useState<GlobalSettings>({
    stack_name: 'iiot-stack',
    timezone: 'UTC',
    restart_policy: 'unless-stopped',
  });
  const [integrationSettings, setIntegrationSettings] = useState<IntegrationSettings>({
    reverse_proxy: {
      base_domain: 'localhost',
      enable_https: false,
      letsencrypt_email: '',
    },
    mqtt: {
      enable_tls: false,
      username: '',
      password: '',
      tls_port: 8883,
    },
    oauth: {
      realm_name: 'iiot',
      auto_configure_services: true,
    },
    database: {
      auto_register: true,
    },
    email: {
      from_address: 'noreply@iiot.local',
      auto_configure_services: true,
    },
  });
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [selectedService, setSelectedService] = useState<ServiceApplication | null>(null);
  const [editingInstance, setEditingInstance] = useState<ServiceInstance | undefined>();
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [loadDialogOpen, setLoadDialogOpen] = useState(false);
  const [stackName, setStackName] = useState('');
  const [stackDescription, setStackDescription] = useState('');

  // Deployment state
  const [deploymentStatus, setDeploymentStatus] = useState<{
    status: string;
    services: Record<string, string>;
  } | null>(null);

  // Fetch catalog
  const { data: catalog, isLoading: catalogLoading, error: catalogError } = useQuery({
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
        integration_settings: integrationSettings,
      }),
    onSuccess: (data) => {
      setPreviewContent(data.docker_compose);
      useStore.getState().setStackSubTab('preview');
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
        integration_settings: integrationSettings,
      });
      return response;
    },
  });

  // Download offline bundle mutation
  const offlineBundleMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch(`${api.getBaseUrl()}/api/stackbuilder/generate-offline-bundle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          instances: instances.map((i) => ({
            app_id: i.app_id,
            instance_name: i.instance_name,
            config: i.config,
          })),
          global_settings: globalSettings,
          integration_settings: integrationSettings,
        }),
      });
      if (!response.ok) throw new Error('Failed to generate offline bundle');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${globalSettings.stack_name}-offline.zip`;
      a.click();
      URL.revokeObjectURL(url);
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

  // Docker status check
  const { data: dockerStatus } = useQuery({
    queryKey: ['docker-status'],
    queryFn: () => api.stackBuilder.getDockerStatus(),
    refetchInterval: TIMING.POLLING.STACKBUILDER_SLOW, // Check every 30 seconds
  });

  // Deployment status check
  const { refetch: refetchDeploymentStatus } = useQuery({
    queryKey: ['deployment-status', globalSettings.stack_name],
    queryFn: async () => {
      const status = await api.stackBuilder.getDeploymentStatus(globalSettings.stack_name);
      setDeploymentStatus(status);
      return status;
    },
    enabled: !!globalSettings.stack_name,
    refetchInterval: TIMING.POLLING.STACKBUILDER_FAST, // Check every 5 seconds when deployed
  });

  // Deploy stack mutation
  const deployMutation = useMutation({
    mutationFn: () =>
      api.stackBuilder.deploy(globalSettings.stack_name, {
        instances: instances.map((i) => ({
          app_id: i.app_id,
          instance_name: i.instance_name,
          config: i.config,
        })),
        global_settings: globalSettings,
        integration_settings: integrationSettings,
      }),
    onSuccess: () => {
      refetchDeploymentStatus();
    },
  });

  // Stop stack mutation
  const stopMutation = useMutation({
    mutationFn: () => api.stackBuilder.stop(globalSettings.stack_name, false),
    onSuccess: () => {
      refetchDeploymentStatus();
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

  // Check which integrations are relevant
  const hasTraefik = instances.some((i) => i.app_id === 'traefik');
  const hasMqtt = instances.some((i) => ['mosquitto', 'emqx'].includes(i.app_id));
  const hasOAuth = instances.some((i) => ['keycloak', 'authentik'].includes(i.app_id));
  const hasDatabase = instances.some((i) => ['postgres', 'mariadb', 'mssql'].includes(i.app_id));
  const hasEmail = instances.some((i) => i.app_id === 'mailhog');

  return (
    <Box sx={{ display: 'flex', gap: 2, height: 'calc(100vh - 140px)' }}>
      {/* Left Panel: Service Catalog & Config */}
      <Paper sx={{ width: 380, overflow: 'auto' }}>
        {/* Services Tab */}
        {stackSubTab === 'services' && (
        <Box sx={{ p: 2 }}>
          {catalogLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress />
            </Box>
          ) : catalogError ? (
            <Alert severity="error" sx={{ m: 1 }}>
              Failed to load service catalog. Make sure the backend is running.
            </Alert>
          ) : applications.length === 0 ? (
            <Alert severity="info" sx={{ m: 1 }}>
              No services available in the catalog.
            </Alert>
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
        </Box>
        )}

        {/* Integrations Tab */}
        {stackSubTab === 'integrations' && (
        <Box sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {/* Info message when no integrations are active */}
            {!hasTraefik && !hasMqtt && !hasOAuth && !hasDatabase && !hasEmail && (
              <Alert severity="info" sx={{ mb: 1 }}>
                Add services like Traefik, Mosquitto, or Keycloak to enable integrations.
              </Alert>
            )}

            {/* Reverse Proxy Settings */}
            <Accordion disabled={!hasTraefik}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="body2">
                  {hasTraefik
                    ? <>Reverse Proxy <Chip label="Active" size="small" color="success" sx={{ ml: 1 }} /></>
                    : 'Reverse Proxy (add Traefik to enable)'}
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  <TextField
                    label="Base Domain"
                    value={integrationSettings.reverse_proxy.base_domain}
                    onChange={(e) => setIntegrationSettings({
                      ...integrationSettings,
                      reverse_proxy: { ...integrationSettings.reverse_proxy, base_domain: e.target.value }
                    })}
                    size="small"
                    fullWidth
                  />
                  <FormControlLabel
                    control={
                      <Switch
                        checked={integrationSettings.reverse_proxy.enable_https}
                        onChange={(e) => setIntegrationSettings({
                          ...integrationSettings,
                          reverse_proxy: { ...integrationSettings.reverse_proxy, enable_https: e.target.checked }
                        })}
                      />
                    }
                    label="Enable HTTPS"
                  />
                  {integrationSettings.reverse_proxy.enable_https && (
                    <TextField
                      label="Let's Encrypt Email"
                      value={integrationSettings.reverse_proxy.letsencrypt_email}
                      onChange={(e) => setIntegrationSettings({
                        ...integrationSettings,
                        reverse_proxy: { ...integrationSettings.reverse_proxy, letsencrypt_email: e.target.value }
                      })}
                      size="small"
                      fullWidth
                    />
                  )}
                </Box>
              </AccordionDetails>
            </Accordion>

            {/* MQTT Settings */}
            <Accordion disabled={!hasMqtt}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="body2">
                  {hasMqtt
                    ? <>MQTT Broker <Chip label="Active" size="small" color="success" sx={{ ml: 1 }} /></>
                    : 'MQTT Broker (add Mosquitto or EMQX to enable)'}
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  <TextField
                    label="Username"
                    value={integrationSettings.mqtt.username}
                    onChange={(e) => setIntegrationSettings({
                      ...integrationSettings,
                      mqtt: { ...integrationSettings.mqtt, username: e.target.value }
                    })}
                    size="small"
                    fullWidth
                  />
                  <TextField
                    label="Password"
                    type="password"
                    value={integrationSettings.mqtt.password}
                    onChange={(e) => setIntegrationSettings({
                      ...integrationSettings,
                      mqtt: { ...integrationSettings.mqtt, password: e.target.value }
                    })}
                    size="small"
                    fullWidth
                  />
                  <FormControlLabel
                    control={
                      <Switch
                        checked={integrationSettings.mqtt.enable_tls}
                        onChange={(e) => setIntegrationSettings({
                          ...integrationSettings,
                          mqtt: { ...integrationSettings.mqtt, enable_tls: e.target.checked }
                        })}
                      />
                    }
                    label="Enable TLS"
                  />
                </Box>
              </AccordionDetails>
            </Accordion>

            {/* OAuth Settings */}
            <Accordion disabled={!hasOAuth}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="body2">
                  {hasOAuth
                    ? <>OAuth/SSO <Chip label="Active" size="small" color="success" sx={{ ml: 1 }} /></>
                    : 'OAuth/SSO (add Keycloak or Authentik to enable)'}
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  <TextField
                    label="Realm Name"
                    value={integrationSettings.oauth.realm_name}
                    onChange={(e) => setIntegrationSettings({
                      ...integrationSettings,
                      oauth: { ...integrationSettings.oauth, realm_name: e.target.value }
                    })}
                    size="small"
                    fullWidth
                  />
                  <FormControlLabel
                    control={
                      <Switch
                        checked={integrationSettings.oauth.auto_configure_services}
                        onChange={(e) => setIntegrationSettings({
                          ...integrationSettings,
                          oauth: { ...integrationSettings.oauth, auto_configure_services: e.target.checked }
                        })}
                      />
                    }
                    label="Auto-configure OAuth clients"
                  />
                </Box>
              </AccordionDetails>
            </Accordion>

            {/* Database Settings */}
            <Accordion disabled={!hasDatabase}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="body2">
                  {hasDatabase
                    ? <>Database <Chip label="Active" size="small" color="success" sx={{ ml: 1 }} /></>
                    : 'Database (add PostgreSQL, MariaDB, or MSSQL to enable)'}
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <FormControlLabel
                  control={
                    <Switch
                      checked={integrationSettings.database.auto_register}
                      onChange={(e) => setIntegrationSettings({
                        ...integrationSettings,
                        database: { auto_register: e.target.checked }
                      })}
                    />
                  }
                  label="Auto-register in Ignition"
                />
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                  Generates scripts to automatically configure database connections in Ignition Gateway
                </Typography>
              </AccordionDetails>
            </Accordion>

            {/* Email Settings */}
            <Accordion disabled={!hasEmail}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="body2">
                  {hasEmail
                    ? <>Email <Chip label="Active" size="small" color="success" sx={{ ml: 1 }} /></>
                    : 'Email (add MailHog to enable)'}
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  <TextField
                    label="From Address"
                    value={integrationSettings.email.from_address}
                    onChange={(e) => setIntegrationSettings({
                      ...integrationSettings,
                      email: { ...integrationSettings.email, from_address: e.target.value }
                    })}
                    size="small"
                    fullWidth
                  />
                  <FormControlLabel
                    control={
                      <Switch
                        checked={integrationSettings.email.auto_configure_services}
                        onChange={(e) => setIntegrationSettings({
                          ...integrationSettings,
                          email: { ...integrationSettings.email, auto_configure_services: e.target.checked }
                        })}
                      />
                    }
                    label="Auto-configure email services"
                  />
                </Box>
              </AccordionDetails>
            </Accordion>
          </Box>
        </Box>
        )}

        {/* Preview Tab */}
        {stackSubTab === 'preview' && (
        <Box sx={{ p: 2 }}>
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
        </Box>
        )}
      </Paper>

      {/* Right Panel: Stack Configuration */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Actions Bar */}
        <Paper sx={{ p: 2, mb: 2 }}>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
            <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="h6">
                Stack: {globalSettings.stack_name}
              </Typography>
              {deploymentStatus && deploymentStatus.status !== 'not_deployed' && (
                <Chip
                  icon={<StatusIcon sx={{ fontSize: '0.75rem !important' }} />}
                  label={deploymentStatus.status}
                  size="small"
                  color={
                    deploymentStatus.status === 'running'
                      ? 'success'
                      : deploymentStatus.status === 'partial'
                      ? 'warning'
                      : 'default'
                  }
                  sx={{
                    '& .MuiChip-icon': {
                      color:
                        deploymentStatus.status === 'running'
                          ? 'success.main'
                          : deploymentStatus.status === 'partial'
                          ? 'warning.main'
                          : 'text.secondary',
                    },
                  }}
                />
              )}
            </Box>
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
              variant="outlined"
              startIcon={<OfflineIcon />}
              onClick={() => offlineBundleMutation.mutate()}
              size="small"
              disabled={instances.length === 0 || offlineBundleMutation.isPending}
            >
              Offline
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
            {/* Deploy/Stop buttons */}
            {deploymentStatus?.status === 'running' || deploymentStatus?.status === 'partial' ? (
              <Button
                variant="contained"
                color="error"
                startIcon={stopMutation.isPending ? <CircularProgress size={16} color="inherit" /> : <StopIcon />}
                onClick={() => stopMutation.mutate()}
                size="small"
                disabled={stopMutation.isPending}
              >
                Stop
              </Button>
            ) : (
              <Tooltip
                title={
                  !dockerStatus?.available
                    ? 'Docker is not available. Please start Docker first.'
                    : instances.length === 0
                    ? 'Add services to deploy'
                    : 'Deploy stack to local Docker'
                }
              >
                <span>
                  <Button
                    variant="contained"
                    color="success"
                    startIcon={deployMutation.isPending ? <CircularProgress size={16} color="inherit" /> : <DeployIcon />}
                    onClick={() => deployMutation.mutate()}
                    size="small"
                    disabled={instances.length === 0 || !dockerStatus?.available || deployMutation.isPending}
                  >
                    Deploy
                  </Button>
                </span>
              </Tooltip>
            )}
            {/* Settings icon button */}
            <Tooltip title="Stack Settings">
              <IconButton
                onClick={() => setSettingsDialogOpen(true)}
                size="small"
                sx={{
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  p: 0.75,
                }}
              >
                <SettingsIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
          {/* Deployment error/success messages */}
          {deployMutation.isError && (
            <Alert severity="error" sx={{ mt: 1 }}>
              Deploy failed: {(deployMutation.error as Error)?.message || 'Unknown error'}
            </Alert>
          )}
          {stopMutation.isError && (
            <Alert severity="error" sx={{ mt: 1 }}>
              Stop failed: {(stopMutation.error as Error)?.message || 'Unknown error'}
            </Alert>
          )}
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

              {integrations.conflicts && integrations.conflicts.length > 0 && (
                <Alert severity="error" sx={{ mb: 1 }}>
                  {integrations.conflicts.map((c: { message: string }, i: number) => (
                    <div key={i}>{c.message}</div>
                  ))}
                </Alert>
              )}

              {integrations.warnings && integrations.warnings.length > 0 && (
                <Alert severity="warning" sx={{ mb: 1 }}>
                  {integrations.warnings.map((w: { message: string }, i: number) => (
                    <div key={i}>{w.message}</div>
                  ))}
                </Alert>
              )}

              {integrations.summary && (
                <Box sx={{ mb: 2 }}>
                  {integrations.summary.map((s: string, i: number) => (
                    <Typography key={i} variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <CheckIcon fontSize="small" color="success" /> {s}
                    </Typography>
                  ))}
                </Box>
              )}

              {Object.keys(integrations.integrations || {}).length > 0 && (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {Object.entries(integrations.integrations || {}).map(([type]) => (
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

      {/* Settings Dialog */}
      <Dialog open={settingsDialogOpen} onClose={() => setSettingsDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Stack Settings</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <Typography variant="subtitle2" color="text.secondary">
              Global Stack Settings
            </Typography>
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

            <Divider sx={{ my: 1 }} />

            <Typography variant="subtitle2" color="text.secondary">
              Docker Installation
            </Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                size="small"
                variant="outlined"
                startIcon={<CloudDownloadIcon />}
                href={`${api.getBaseUrl()}/api/stackbuilder/download/docker-installer/linux`}
                download="install-docker-linux.sh"
              >
                Linux Script
              </Button>
              <Button
                size="small"
                variant="outlined"
                startIcon={<CloudDownloadIcon />}
                href={`${api.getBaseUrl()}/api/stackbuilder/download/docker-installer/windows`}
                download="install-docker-windows.ps1"
              >
                Windows Script
              </Button>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSettingsDialogOpen(false)} variant="contained">Done</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
