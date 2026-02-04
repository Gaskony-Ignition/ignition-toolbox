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
  DockerStatus,
  CloudDesignerStatus,
  CloudDesignerStartResponse,
  CloudDesignerStopResponse,
  CloudDesignerConfig,
  DetailedHealthResponse,
  DatabaseStats,
  StorageStats,
  CleanupResult,
  LogEntry,
  LogStats,
} from '../types/api';
import { createLogger } from '../utils/logger';

const logger = createLogger('API');

// API Base URL - supports both web and Electron modes
// In Electron: get from IPC (dynamic port)
// In browser: use window.location.origin
let API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000';
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
      API_BASE_URL = 'http://127.0.0.1:5000';
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

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
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
    throw new APIError(
      errorData.detail || `HTTP error ${response.status}`,
      response.status,
      errorData
    );
  }

  return response.json();
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
      fetchJSON<{ name: string; path: string; version: string; description: string; domain: string; yaml_content: string; metadata: any }>(
        `/api/playbooks/${encodeURIComponent(path)}/export`
      ),
    import: (name: string, domain: string, yamlContent: string, overwrite: boolean = false, metadata?: any) =>
      fetchJSON<{ status: string; message: string; path: string; playbook: any }>(
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
      fetchJSON<{ status: string; message: string; path: string; playbook: any }>(
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
      fetchJSON<any>(`/api/executions/${executionId}/debug/context`),

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
    listApiKeys: () => fetchJSON<any[]>('/api/explorer/api-keys'),

    createApiKey: (data: {
      name: string;
      gateway_url: string;
      api_key: string;
      description?: string;
    }) =>
      fetchJSON<any>('/api/explorer/api-keys', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    updateApiKey: (name: string, data: {
      gateway_url?: string;
      api_key?: string;
      description?: string;
    }) =>
      fetchJSON<any>(`/api/explorer/api-keys/${encodeURIComponent(name)}`, {
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
      fetchJSON<any>('/api/explorer/gateway-info', {
        method: 'POST',
        body: JSON.stringify(request),
      }),

    fetchOpenAPI: (request: {
      gateway_url: string;
      api_key_name?: string;
      api_key?: string;
    }) =>
      fetchJSON<any>('/api/explorer/openapi', {
        method: 'POST',
        body: JSON.stringify(request),
      }),

    listResources: (resourceType: string, request: {
      gateway_url: string;
      api_key_name?: string;
      api_key?: string;
    }) =>
      fetchJSON<any>(`/api/explorer/resources/${resourceType}`, {
        method: 'POST',
        body: JSON.stringify(request),
      }),

    executeRequest: (request: {
      gateway_url: string;
      method: string;
      path: string;
      headers?: Record<string, string>;
      query_params?: Record<string, string>;
      body?: any;
      api_key_name?: string;
      api_key?: string;
    }) =>
      fetchJSON<any>('/api/explorer/request', {
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
    getCatalog: () => fetchJSON<any>('/api/stackbuilder/catalog'),

    getApplications: () => fetchJSON<any[]>('/api/stackbuilder/catalog/applications'),

    getCategories: () => fetchJSON<any[]>('/api/stackbuilder/catalog/categories'),

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
      fetchJSON<any>('/api/stackbuilder/detect-integrations', {
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
      integration_settings?: Record<string, any>;
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
      integration_settings?: Record<string, any>;
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

    listStacks: () => fetchJSON<any[]>('/api/stackbuilder/stacks'),

    getStack: (id: number) => fetchJSON<any>(`/api/stackbuilder/stacks/${id}`),

    saveStack: (data: {
      stack_name: string;
      description?: string;
      config_json: Record<string, any>;
      global_settings?: Record<string, any>;
    }) =>
      fetchJSON<any>('/api/stackbuilder/stacks', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    updateStack: (id: number, data: {
      stack_name: string;
      description?: string;
      config_json: Record<string, any>;
      global_settings?: Record<string, any>;
    }) =>
      fetchJSON<any>(`/api/stackbuilder/stacks/${id}`, {
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
      integration_settings?: Record<string, any>;
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
   * CloudDesigner - Browser-based Ignition Designer
   */
  cloudDesigner: {
    getDockerStatus: () =>
      fetchJSON<DockerStatus>('/api/clouddesigner/docker-status'),

    getStatus: () =>
      fetchJSON<CloudDesignerStatus>('/api/clouddesigner/status'),

    start: (gatewayUrl: string, credentialName?: string) =>
      fetchJSON<CloudDesignerStartResponse>('/api/clouddesigner/start', {
        method: 'POST',
        body: JSON.stringify({
          gateway_url: gatewayUrl,
          credential_name: credentialName,
        }),
      }),

    stop: () =>
      fetchJSON<CloudDesignerStopResponse>('/api/clouddesigner/stop', {
        method: 'POST',
      }),

    cleanup: () =>
      fetchJSON<CloudDesignerStopResponse>('/api/clouddesigner/cleanup', {
        method: 'POST',
      }),

    getConfig: () =>
      fetchJSON<CloudDesignerConfig>('/api/clouddesigner/config'),
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
   * Get the base URL for API calls
   */
  getBaseUrl: () => API_BASE_URL,
};

export { APIError };
export default api;
