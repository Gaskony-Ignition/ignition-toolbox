/**
 * API Client for Ignition Automation Toolkit
 *
 * Type-safe HTTP client using fetch API
 */

import type {
  PlaybookInfo,
  ExecutionRequest,
  ExecutionResponse,
  ExecutionStatusResponse,
  CredentialInfo,
  CredentialCreate,
  HealthResponse,
  DetailedHealthResponse,
  DatabaseStats,
  StorageStats,
  CleanupResult,
  LogEntry,
  LogStats,
  AuditReport,
  UdtTemplateMeta,
  UdtBuildResult,
  UdtComposition,
  UdtComposeResponse,
  UdtPreset,
} from '../types/api';
import { createLogger } from '../utils/logger';

// ============================================================
// API response types for StackBuilder, API Explorer, and others
// ============================================================

/** API Explorer - stored API key info */
export interface ApiKeyInfo {
  id?: number;
  name: string;
  gateway_url: string;
  has_api_key?: boolean;
  description?: string;
  created_at?: string;
  last_used?: string;
}

/** API Explorer - gateway info response */
export interface GatewayInfoResponse {
  platform?: string;
  version?: string;
  edition?: string;
  state?: string;
  system?: {
    version?: string;
    edition?: string;
    uptime?: string;
    [key: string]: unknown;
  };
  license?: {
    isValid?: boolean;
    expirationDate?: string;
    [key: string]: unknown;
  };
  modules?: Array<{ name: string; state: string; [key: string]: unknown }>;
  [key: string]: unknown;
}

/** API Explorer - OpenAPI spec response */
export interface OpenAPIResponse {
  openapi: string;
  info: { title: string; version: string; [key: string]: unknown };
  paths: Record<string, unknown>;
  [key: string]: unknown;
}

/** API Explorer - resource list response */
export interface ResourceListResponse {
  resources: Array<Record<string, unknown>>;
  [key: string]: unknown;
}

/** API Explorer - request execution response */
export interface ExplorerRequestResponse {
  status_code: number;
  headers: Record<string, string>;
  body: unknown;
  elapsed_ms: number;
  [key: string]: unknown;
}

/** StackBuilder - catalog response */
export interface StackBuilderCatalog {
  applications: StackBuilderApplication[];
  categories: StackBuilderCategory[];
}

/** StackBuilder - configurable option for a service */
export interface ConfigurableOption {
  type: 'text' | 'password' | 'number' | 'select' | 'multiselect' | 'checkbox' | 'textarea';
  label?: string;
  default?: unknown;
  options?: Array<{ value: string; label: string; description?: string } | string>;
  required?: boolean;
  visible?: boolean;
  description?: string;
  placeholder?: string;
  version_constraint?: string;
  [key: string]: unknown;
}

/** StackBuilder - application entry */
export interface StackBuilderApplication {
  id: string;
  name: string;
  description: string;
  category: string;
  image: string;
  enabled: boolean;
  icon?: string;
  default_version?: string;
  default_config?: {
    ports?: string[];
    environment?: Record<string, string>;
    volumes?: string[];
  };
  configurable_options?: Record<string, ConfigurableOption>;
  config_schema?: Record<string, unknown>;
  [key: string]: unknown;
}

/** StackBuilder - category entry */
export interface StackBuilderCategory {
  id: string;
  name: string;
  description: string;
  icon?: string;
}

/** StackBuilder - saved stack */
export interface SavedStack {
  id: number;
  stack_name: string;
  description?: string;
  config_json: {
    instances: Array<{
      app_id: string;
      instance_name: string;
      config: Record<string, unknown>;
    }>;
    integration_settings?: Record<string, unknown>;
  };
  global_settings?: {
    stack_name: string;
    timezone: string;
    restart_policy: string;
    [key: string]: unknown;
  };
  created_at?: string;
  updated_at?: string;
}

/** StackBuilder - integration detection result */
export interface IntegrationDetectionResult {
  integrations: Record<string, unknown>;
  suggestions: string[];
  conflicts?: Array<{ message: string; [key: string]: unknown }>;
  warnings?: Array<{ message: string; [key: string]: unknown }>;
  summary?: string[];
}

/** Playbook export data */
export interface PlaybookExportData {
  name: string;
  path: string;
  version: string;
  description: string;
  domain: string;
  yaml_content: string;
  metadata: PlaybookMetadata;
}

/** Playbook metadata (for import/export) */
export interface PlaybookMetadata {
  author?: string;
  category?: string;
  tags?: string[];
  verified?: boolean;
  [key: string]: unknown;
}

/** Playbook import/create response */
export interface PlaybookImportResponse {
  status: string;
  message: string;
  path: string;
  playbook: PlaybookInfo;
}

/** Debug context response */
export interface DebugContextResponse {
  execution_id: string;
  current_step: string;
  step_name: string;
  step_type: string;
  step_id: string;
  step_parameters: Record<string, unknown>;
  error: string;
  screenshot_base64?: string;
  page_html?: string;
  timestamp: string;
  variables: Record<string, unknown>;
  browser_state: Record<string, unknown>;
  [key: string]: unknown;
}

/** StackBuilder config for generate/deploy */
export interface StackBuilderConfig {
  instances: Array<{
    app_id: string;
    instance_name: string;
    config: Record<string, unknown>;
  }>;
  global_settings?: {
    stack_name?: string;
    timezone?: string;
    restart_policy?: string;
    [key: string]: unknown;
  };
  integration_settings?: {
    [key: string]: unknown;
  };
}

const logger = createLogger('API');

// Port fallback constants - must match electron/config.ts BACKEND_PORT_RANGE.START
const DEFAULT_BACKEND_PORT = 5000;
const DEFAULT_API_BASE_URL = `http://127.0.0.1:${DEFAULT_BACKEND_PORT}`;

// API Base URL - supports both web and Electron modes
// In Electron: get from IPC (dynamic port)
// In browser: use window.location.origin
let API_BASE_URL = import.meta.env.VITE_API_URL || DEFAULT_API_BASE_URL;
let _initialized = false;
let _initPromise: Promise<void> | null = null;

// Initialize Electron backend URL if available
export async function initializeBackendUrl(): Promise<void> {
  if (_initialized) return;

  if (window.electronAPI?.getBackendUrl) {
    try {
      API_BASE_URL = await window.electronAPI.getBackendUrl();
      logger.info('Using Electron backend URL:', API_BASE_URL);
    } catch (error) {
      logger.error('Failed to get Electron backend URL:', error);
      // Fallback to default
      API_BASE_URL = DEFAULT_API_BASE_URL;
    }
  } else if (window.location.protocol !== 'file:') {
    // Web mode - use current origin
    API_BASE_URL = window.location.origin;
  }

  _initialized = true;
}

// Get initialization promise (for awaiting before render)
export function getInitPromise(): Promise<void> {
  if (!_initPromise) {
    _initPromise = initializeBackendUrl();
  }
  return _initPromise;
}

// Initialize on module load (non-blocking, but can be awaited)
_initPromise = initializeBackendUrl();

class APIError extends Error {
  status: number;
  data?: unknown;
  recoveryHint?: string;

  constructor(message: string, status: number, data?: unknown, recoveryHint?: string) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
    this.recoveryHint = recoveryHint;
  }

  /**
   * Format error message with recovery hint for display
   */
  getDisplayMessage(): string {
    if (this.recoveryHint) {
      return `${this.message}\n\nSuggestion: ${this.recoveryHint}`;
    }
    return this.message;
  }
}

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    // Extract message and recovery hint from structured error response
    let message = `HTTP error ${response.status}`;
    let recoveryHint: string | undefined;

    if (typeof errorData.detail === 'object' && errorData.detail !== null) {
      // Structured error response: { error, message, recovery_hint, details }
      message = errorData.detail.message || message;
      recoveryHint = errorData.detail.recovery_hint;
    } else if (typeof errorData.detail === 'string') {
      // Simple string error
      message = errorData.detail;
    } else if (errorData.message) {
      // Alternative format
      message = errorData.message;
      recoveryHint = errorData.recovery_hint;
    }

    throw new APIError(message, response.status, errorData, recoveryHint);
  }

  return response.json();
}

/**
 * POST a single file as multipart/form-data and parse the JSON response.
 *
 * Deliberately not routed through fetchJSON: a multipart body must not set
 * a Content-Type header itself (the browser adds one with the boundary).
 */
async function postFileForJSON<T>(url: string, file: File): Promise<T> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}${url}`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message =
      typeof errorData.detail === 'string'
        ? errorData.detail
        : errorData.detail?.message || `HTTP error ${response.status}`;
    throw new APIError(message, response.status, errorData);
  }

  return response.json();
}

/**
 * POST a single file as multipart/form-data and trigger a browser download
 * of the response body, named from the server's Content-Disposition header.
 */
async function postFileForDownload(url: string, file: File, fallbackFilename: string): Promise<void> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}${url}`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message =
      typeof errorData.detail === 'string'
        ? errorData.detail
        : errorData.detail?.message || `HTTP error ${response.status}`;
    throw new APIError(message, response.status, errorData);
  }

  const disposition = response.headers.get('content-disposition') ?? '';
  const filenameMatch = disposition.match(/filename="?([^";]+)"?/);
  const filename = filenameMatch?.[1] ?? fallbackFilename;

  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(downloadUrl);
}

export const api = {
  /**
   * Health check
   */
  health: () => fetchJSON<HealthResponse>('/health'),

  /**
   * Health diagnostics
   */
  diagnostics: {
    /** Get detailed health status with component breakdown */
    getDetailedHealth: () =>
      fetchJSON<DetailedHealthResponse>('/health/detailed'),

    /** Get database statistics */
    getDatabaseStats: () =>
      fetchJSON<DatabaseStats>('/health/database'),

    /** Get screenshot storage statistics */
    getStorageStats: () =>
      fetchJSON<StorageStats>('/health/storage'),

    /** Cleanup old data (executions and screenshots) */
    cleanup: (olderThanDays: number = 30, dryRun: boolean = true) =>
      fetchJSON<CleanupResult>(
        `/health/cleanup?older_than_days=${olderThanDays}&dry_run=${dryRun}`,
        { method: 'POST' }
      ),
  },

  /**
   * Playbooks
   */
  playbooks: {
    list: () => fetchJSON<PlaybookInfo[]>('/api/playbooks'),
    getStepTypes: () => fetchJSON<{
      step_types: Array<{
        type: string;
        domain: string;
        description: string;
        parameters: Array<{
          name: string;
          type: string;
          required: boolean;
          default: string | number | boolean | null;
          description: string;
          options?: string[];
        }>;
      }>;
      domains: string[];
    }>('/api/playbooks/step-types'),
    get: (path: string) =>
      fetchJSON<PlaybookInfo>(`/api/playbooks/${encodeURIComponent(path)}`),
    update: (playbookPath: string, yamlContent: string) =>
      fetchJSON<{ status: string; playbook_path: string; backup_path: string; message: string }>(
        '/api/playbooks/update',
        {
          method: 'PUT',
          body: JSON.stringify({
            playbook_path: playbookPath,
            yaml_content: yamlContent,
          }),
        }
      ),
    verify: (path: string) =>
      fetchJSON<{ status: string; playbook_path: string; verified: boolean; verified_at: string; message: string }>(
        `/api/playbooks/${encodeURIComponent(path)}/verify`,
        { method: 'POST' }
      ),
    unverify: (path: string) =>
      fetchJSON<{ status: string; playbook_path: string; verified: boolean; message: string }>(
        `/api/playbooks/${encodeURIComponent(path)}/unverify`,
        { method: 'POST' }
      ),
    enable: (path: string) =>
      fetchJSON<{ status: string; playbook_path: string; enabled: boolean; message: string }>(
        `/api/playbooks/${encodeURIComponent(path)}/enable`,
        { method: 'POST' }
      ),
    disable: (path: string) =>
      fetchJSON<{ status: string; playbook_path: string; enabled: boolean; message: string }>(
        `/api/playbooks/${encodeURIComponent(path)}/disable`,
        { method: 'POST' }
      ),
    updateMetadata: (path: string, name?: string, description?: string) =>
      fetchJSON<{ status: string; playbook_path: string; name: string; description: string; revision: number; message: string }>(
        '/api/playbooks/metadata',
        {
          method: 'PATCH',
          body: JSON.stringify({ playbook_path: path, name, description }),
        }
      ),
    delete: (path: string) =>
      fetchJSON<{ status: string; playbook_path: string; message: string }>(
        `/api/playbooks/${encodeURIComponent(path)}`,
        { method: 'DELETE' }
      ),
    duplicate: (path: string, newName?: string) =>
      fetchJSON<{ status: string; message: string; original_path: string; new_path: string; new_name: string }>(
        '/api/playbooks/duplicate',
        {
          method: 'POST',
          body: JSON.stringify({
            playbook_path: path,
            new_name: newName || undefined,
          }),
        }
      ),
    export: (path: string) =>
      fetchJSON<PlaybookExportData>(
        `/api/playbooks/${encodeURIComponent(path)}/export`
      ),
    import: (name: string, domain: string, yamlContent: string, overwrite: boolean = false, metadata?: PlaybookMetadata) =>
      fetchJSON<PlaybookImportResponse>(
        '/api/playbooks/import',
        {
          method: 'POST',
          body: JSON.stringify({
            name,
            domain,
            yaml_content: yamlContent,
            overwrite,
            metadata,
          }),
        }
      ),
    create: (name: string, domain: string, yamlContent: string) =>
      fetchJSON<PlaybookImportResponse>(
        '/api/playbooks/create',
        {
          method: 'POST',
          body: JSON.stringify({
            name,
            domain,
            yaml_content: yamlContent,
            overwrite: false,
          }),
        }
      ),
    resetMetadata: () =>
      fetchJSON<{ status: string; message: string }>(
        '/api/playbooks/metadata/reset-all',
        { method: 'POST' }
      ),
  },

  /**
   * Executions
   */
  executions: {
    list: (params?: { limit?: number; status?: string }) => {
      const query = new URLSearchParams();
      if (params?.limit) query.set('limit', params.limit.toString());
      if (params?.status) query.set('status', params.status);
      const queryString = query.toString();
      return fetchJSON<ExecutionStatusResponse[]>(
        `/api/executions${queryString ? `?${queryString}` : ''}`
      );
    },

    get: (executionId: string) =>
      fetchJSON<ExecutionStatusResponse>(
        `/api/executions/${executionId}/status`
      ),

    start: (request: ExecutionRequest) =>
      fetchJSON<ExecutionResponse>('/api/executions', {
        method: 'POST',
        body: JSON.stringify(request),
      }),

    pause: (executionId: string) =>
      fetchJSON<{ status: string; execution_id: string }>(
        `/api/executions/${executionId}/pause`,
        { method: 'POST' }
      ),

    resume: (executionId: string) =>
      fetchJSON<{ status: string; execution_id: string }>(
        `/api/executions/${executionId}/resume`,
        { method: 'POST' }
      ),

    skip: (executionId: string) =>
      fetchJSON<{ status: string; execution_id: string }>(
        `/api/executions/${executionId}/skip`,
        { method: 'POST' }
      ),

    skipBack: (executionId: string) =>
      fetchJSON<{ status: string; execution_id: string }>(
        `/api/executions/${executionId}/skip_back`,
        { method: 'POST' }
      ),

    cancel: (executionId: string) =>
      fetchJSON<{ status: string; execution_id: string }>(
        `/api/executions/${executionId}/cancel`,
        { method: 'POST' }
      ),

    delete: (executionId: string) =>
      fetchJSON<{ message: string; execution_id: string; screenshots_deleted: number }>(
        `/api/executions/${executionId}`,
        { method: 'DELETE' }
      ),

    // Debug mode
    enableDebug: (executionId: string) =>
      fetchJSON<{ status: string; execution_id: string }>(
        `/api/executions/${executionId}/debug/enable`,
        { method: 'POST' }
      ),

    disableDebug: (executionId: string) =>
      fetchJSON<{ status: string; execution_id: string }>(
        `/api/executions/${executionId}/debug/disable`,
        { method: 'POST' }
      ),

    getDebugContext: (executionId: string) =>
      fetchJSON<DebugContextResponse>(`/api/executions/${executionId}/debug/context`),

    getDebugDOM: (executionId: string) =>
      fetchJSON<{ html: string }>(`/api/executions/${executionId}/debug/dom`),

    // Browser interaction
    clickAtCoordinates: (executionId: string, x: number, y: number) =>
      fetchJSON<{ status: string; message: string }>(
        `/api/executions/${executionId}/browser/click`,
        {
          method: 'POST',
          body: JSON.stringify({ x, y }),
        }
      ),

    // Claude Code integration
    getClaudeCodeSession: (executionId: string) =>
      fetchJSON<{
        command: string;
        playbook_path: string;
        execution_id: string;
        context_message: string;
      }>('/api/ai/claude-code-session', {
        method: 'POST',
        body: JSON.stringify({ execution_id: executionId }),
      }),

    // Playbook code viewer/editor
    getPlaybookCode: (executionId: string) =>
      fetchJSON<{
        code: string;
        playbook_path: string;
        playbook_name: string;
      }>(`/api/executions/${executionId}/playbook/code`),

    updatePlaybookCode: (executionId: string, code: string) =>
      fetchJSON<{
        status: string;
        message: string;
        backup_path: string;
      }>(`/api/executions/${executionId}/playbook/code`, {
        method: 'PUT',
        body: JSON.stringify({ code }),
      }),
  },

  /**
   * Credentials
   */
  credentials: {
    list: () => fetchJSON<CredentialInfo[]>('/api/credentials'),

    create: (credential: CredentialCreate) =>
      fetchJSON<{ message: string; name: string }>('/api/credentials', {
        method: 'POST',
        body: JSON.stringify(credential),
      }),

    update: (name: string, credential: CredentialCreate) =>
      fetchJSON<{ message: string; name: string }>(
        `/api/credentials/${encodeURIComponent(name)}`,
        {
          method: 'PUT',
          body: JSON.stringify(credential),
        }
      ),

    delete: (name: string) =>
      fetchJSON<{ message: string; name: string }>(
        `/api/credentials/${encodeURIComponent(name)}`,
        { method: 'DELETE' }
      ),
  },

  /**
   * API Explorer
   */
  apiExplorer: {
    listApiKeys: () => fetchJSON<ApiKeyInfo[]>('/api/explorer/api-keys'),

    createApiKey: (data: {
      name: string;
      gateway_url: string;
      api_key: string;
      description?: string;
    }) =>
      fetchJSON<ApiKeyInfo>('/api/explorer/api-keys', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    updateApiKey: (name: string, data: {
      gateway_url?: string;
      api_key?: string;
      description?: string;
    }) =>
      fetchJSON<ApiKeyInfo>(`/api/explorer/api-keys/${encodeURIComponent(name)}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),

    deleteApiKey: (name: string) =>
      fetchJSON<{ message: string; name: string }>(
        `/api/explorer/api-keys/${encodeURIComponent(name)}`,
        { method: 'DELETE' }
      ),

    getGatewayInfo: (request: {
      gateway_url: string;
      api_key_name?: string;
      api_key?: string;
    }) =>
      fetchJSON<GatewayInfoResponse>('/api/explorer/gateway-info', {
        method: 'POST',
        body: JSON.stringify(request),
      }),

    fetchOpenAPI: (request: {
      gateway_url: string;
      api_key_name?: string;
      api_key?: string;
    }) =>
      fetchJSON<OpenAPIResponse>('/api/explorer/openapi', {
        method: 'POST',
        body: JSON.stringify(request),
      }),

    listResources: (resourceType: string, request: {
      gateway_url: string;
      api_key_name?: string;
      api_key?: string;
    }) =>
      fetchJSON<ResourceListResponse>(`/api/explorer/resources/${resourceType}`, {
        method: 'POST',
        body: JSON.stringify(request),
      }),

    executeRequest: (request: {
      gateway_url: string;
      method: string;
      path: string;
      headers?: Record<string, string>;
      query_params?: Record<string, string>;
      body?: unknown;
      api_key_name?: string;
      api_key?: string;
    }) =>
      fetchJSON<ExplorerRequestResponse>('/api/explorer/request', {
        method: 'POST',
        body: JSON.stringify(request),
      }),

    scanProjects: (request: {
      gateway_url: string;
      api_key_name?: string;
      api_key?: string;
    }) =>
      fetchJSON<{ message: string }>('/api/explorer/scan/projects', {
        method: 'POST',
        body: JSON.stringify(request),
      }),

    scanConfig: (request: {
      gateway_url: string;
      api_key_name?: string;
      api_key?: string;
    }) =>
      fetchJSON<{ message: string }>('/api/explorer/scan/config', {
        method: 'POST',
        body: JSON.stringify(request),
      }),

    testConnection: (request: {
      gateway_url: string;
      api_key_name?: string;
      api_key?: string;
    }) =>
      fetchJSON<{ success: boolean; message: string; gateway_version?: string }>(
        '/api/explorer/test-connection',
        {
          method: 'POST',
          body: JSON.stringify(request),
        }
      ),
  },

  /**
   * Stack Builder
   */
  stackBuilder: {
    getCatalog: () => fetchJSON<StackBuilderCatalog>('/api/stackbuilder/catalog'),

    getApplications: () => fetchJSON<StackBuilderApplication[]>('/api/stackbuilder/catalog/applications'),

    getCategories: () => fetchJSON<StackBuilderCategory[]>('/api/stackbuilder/catalog/categories'),

    getVersions: (appId: string) =>
      fetchJSON<{ versions: string[] }>(`/api/stackbuilder/versions/${encodeURIComponent(appId)}`),

    detectIntegrations: (config: {
      instances: Array<{
        app_id: string;
        instance_name: string;
        config: Record<string, unknown>;
      }>;
      global_settings?: {
        stack_name?: string;
        timezone?: string;
        restart_policy?: string;
      };
    }) =>
      fetchJSON<IntegrationDetectionResult>('/api/stackbuilder/detect-integrations', {
        method: 'POST',
        body: JSON.stringify(config),
      }),

    generate: (config: {
      instances: Array<{
        app_id: string;
        instance_name: string;
        config: Record<string, unknown>;
      }>;
      global_settings?: {
        stack_name?: string;
        timezone?: string;
        restart_policy?: string;
      };
      integration_settings?: Record<string, unknown>;
    }) =>
      fetchJSON<{
        docker_compose: string;
        env: string;
        readme: string;
        config_files: Record<string, string>;
      }>('/api/stackbuilder/generate', {
        method: 'POST',
        body: JSON.stringify(config),
      }),

    download: async (config: {
      instances: Array<{
        app_id: string;
        instance_name: string;
        config: Record<string, unknown>;
      }>;
      global_settings?: {
        stack_name?: string;
        timezone?: string;
        restart_policy?: string;
      };
      integration_settings?: Record<string, unknown>;
    }) => {
      const response = await fetch(`${API_BASE_URL}/api/stackbuilder/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        throw new APIError('Download failed', response.status);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${config.global_settings?.stack_name || 'iiot-stack'}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    },

    offlineBundle: async (config: {
      instances: Array<{
        app_id: string;
        instance_name: string;
        config: Record<string, unknown>;
      }>;
      global_settings?: {
        stack_name?: string;
        timezone?: string;
        restart_policy?: string;
      };
      integration_settings?: Record<string, unknown>;
    }) => {
      const response = await fetch(`${API_BASE_URL}/api/stackbuilder/generate-offline-bundle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        throw new APIError('Failed to generate offline bundle', response.status);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      try {
        const a = document.createElement('a');
        a.href = url;
        a.download = `${config.global_settings?.stack_name || 'iiot-stack'}-offline.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      } finally {
        window.URL.revokeObjectURL(url);
      }
    },

    listStacks: () => fetchJSON<SavedStack[]>('/api/stackbuilder/stacks'),

    getStack: (id: number) => fetchJSON<SavedStack>(`/api/stackbuilder/stacks/${id}`),

    saveStack: (data: {
      stack_name: string;
      description?: string;
      config_json: Record<string, unknown>;
      global_settings?: Record<string, unknown>;
    }) =>
      fetchJSON<SavedStack>('/api/stackbuilder/stacks', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    updateStack: (id: number, data: {
      stack_name: string;
      description?: string;
      config_json: Record<string, unknown>;
      global_settings?: Record<string, unknown>;
    }) =>
      fetchJSON<SavedStack>(`/api/stackbuilder/stacks/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),

    deleteStack: (id: number) =>
      fetchJSON<{ message: string; id: number }>(
        `/api/stackbuilder/stacks/${id}`,
        { method: 'DELETE' }
      ),

    // Stack Deployment (Local Docker)
    getDockerStatus: () =>
      fetchJSON<{ available: boolean; message: string }>('/api/stackbuilder/docker-status'),

    deploy: (stackName: string, config: {
      instances: Array<{
        app_id: string;
        instance_name: string;
        config: Record<string, unknown>;
      }>;
      global_settings?: {
        stack_name?: string;
        timezone?: string;
        restart_policy?: string;
      };
      integration_settings?: Record<string, unknown>;
    }) =>
      fetchJSON<{ success: boolean; output?: string; error?: string }>('/api/stackbuilder/deploy', {
        method: 'POST',
        body: JSON.stringify({
          stack_name: stackName,
          stack_config: config,
        }),
      }),

    stop: (stackName: string, removeVolumes: boolean = false) =>
      fetchJSON<{ success: boolean; output?: string; error?: string }>(
        `/api/stackbuilder/stop/${encodeURIComponent(stackName)}?remove_volumes=${removeVolumes}`,
        { method: 'POST' }
      ),

    getDeploymentStatus: (stackName: string) =>
      fetchJSON<{ status: string; services: Record<string, string>; error?: string }>(
        `/api/stackbuilder/deployment-status/${encodeURIComponent(stackName)}`
      ),

    listDeployments: () =>
      fetchJSON<{ deployments: Array<{ name: string; status: string; services: Record<string, string> }> }>(
        '/api/stackbuilder/deployments'
      ),

    deleteDeployment: (stackName: string) =>
      fetchJSON<{ message: string }>(
        `/api/stackbuilder/deployment/${encodeURIComponent(stackName)}`,
        { method: 'DELETE' }
      ),
  },

  /**
   * Backend Logs - Access logs from the UI
   */
  logs: {
    /**
     * Get recent logs with optional filtering
     */
    get: (params?: {
      limit?: number;
      level?: string;
      logger_filter?: string;
      execution_id?: string;
    }) => {
      const searchParams = new URLSearchParams();
      if (params?.limit) searchParams.set('limit', params.limit.toString());
      if (params?.level) searchParams.set('level', params.level);
      if (params?.logger_filter) searchParams.set('logger_filter', params.logger_filter);
      if (params?.execution_id) searchParams.set('execution_id', params.execution_id);
      const query = searchParams.toString();
      return fetchJSON<{
        logs: LogEntry[];
        total: number;
        filtered: number;
      }>(`/api/logs${query ? `?${query}` : ''}`);
    },

    /**
     * Get logs for a specific execution
     */
    getForExecution: (executionId: string, limit?: number) =>
      fetchJSON<{
        logs: LogEntry[];
        total: number;
        filtered: number;
      }>(`/api/logs/execution/${executionId}${limit ? `?limit=${limit}` : ''}`),

    /**
     * Get log statistics
     */
    getStats: () => fetchJSON<LogStats>('/api/logs/stats'),

    /**
     * Clear all captured logs
     */
    clear: () =>
      fetchJSON<{ message: string; success: boolean }>('/api/logs', {
        method: 'DELETE',
      }),
  },

  /**
   * Perspective Project Audit
   */
  audit: {
    /** Upload a Perspective project export (zip) and get back a structured findings report. */
    runPerspectiveAudit: (file: File) =>
      postFileForJSON<AuditReport>('/api/audit/perspective', file),

    /** Same audit, downloaded as a customer-facing markdown report. */
    downloadPerspectiveAuditMarkdown: (file: File) =>
      postFileForDownload('/api/audit/perspective/markdown', file, 'audit-report.md'),
  },

  /**
   * UDT Builder / Composer — guided composition -> convention-conforming UDT
   * JSON. Download-JSON-only delivery: nothing here writes to disk or a
   * gateway.
   */
  udt: {
    /** List every available device-class template's metadata + questionnaire schema. */
    getTemplates: () => fetchJSON<UdtTemplateMeta[]>('/api/udt/templates'),

    /** Build a UDT from a template id + questionnaire answers. */
    build: (templateId: string, answers: Record<string, unknown>, namingStyle?: string) =>
      fetchJSON<UdtBuildResult>('/api/udt/build', {
        method: 'POST',
        body: JSON.stringify({
          template_id: templateId,
          answers,
          naming_style: namingStyle,
        }),
      }),

    /**
     * Compose a UDT from the wizard's composition tree — used both for the
     * final build (Review step) and for live/debounced lint-only calls as
     * the user edits. Lint findings never block; a 422 means the
     * composition itself is structurally invalid (bad type name, unknown
     * parameter ref, duplicate sibling names, invalid data type).
     */
    compose: (composition: UdtComposition) =>
      fetchJSON<UdtComposeResponse>('/api/udt/compose', {
        method: 'POST',
        body: JSON.stringify(composition),
      }),

    /** Quick-start presets (derived from the device-class templates) that prefill the composer. */
    getPresets: () => fetchJSON<UdtPreset[]>('/api/udt/presets'),
  },

  /**
   * Get the base URL for API calls
   */
  getBaseUrl: () => API_BASE_URL,

};

export { APIError };
export default api;
