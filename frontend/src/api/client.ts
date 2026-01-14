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
} from '../types/api';

// API Base URL - supports both web and Electron modes
// In Electron: get from IPC (dynamic port)
// In browser: use window.location.origin
let API_BASE_URL = import.meta.env.VITE_API_URL || window.location.origin;

// Initialize Electron backend URL if available
async function initializeBackendUrl(): Promise<void> {
  if (window.electronAPI?.getBackendUrl) {
    try {
      API_BASE_URL = await window.electronAPI.getBackendUrl();
      console.log('Using Electron backend URL:', API_BASE_URL);
    } catch (error) {
      console.error('Failed to get Electron backend URL:', error);
    }
  }
}

// Initialize on module load (non-blocking)
initializeBackendUrl();

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
      fetchJSON<{ status: string; message: string; source_path: string; new_path: string; playbook: any }>(
        `/api/playbooks/${encodeURIComponent(path)}/duplicate${newName ? `?new_name=${encodeURIComponent(newName)}` : ''}`,
        { method: 'POST' }
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
   * Get the base URL for API calls
   */
  getBaseUrl: () => API_BASE_URL,
};

export { APIError };
export default api;
