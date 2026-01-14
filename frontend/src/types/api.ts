/**
 * TypeScript types generated from FastAPI backend
 *
 * These types match the Pydantic models in ignition_toolkit/api/app.py
 */

export interface ParameterInfo {
  name: string;
  type: string;
  required: boolean;
  default: string | null;
  description: string;
}

export interface StepInfo {
  id: string;
  name: string;
  type: string;
  timeout: number;
  retry_count: number;
}

export interface PlaybookInfo {
  name: string;
  path: string;
  version: string;
  description: string;
  parameter_count: number;
  step_count: number;
  parameters: ParameterInfo[];
  steps: StepInfo[];
  // Metadata fields
  domain: string | null;  // Playbook domain (gateway, designer, perspective)
  group: string | null;  // Playbook group for UI organization (e.g., "Gateway (Base Playbooks)")
  revision: number;
  verified: boolean;
  enabled: boolean;
  last_modified: string | null;
  verified_at: string | null;
  // PORTABILITY v4: Origin tracking
  origin: string;  // built-in, user-created, duplicated, unknown
  duplicated_from: string | null;  // Source playbook path if duplicated
  created_at: string | null;  // When playbook was created/added
}

export interface TimeoutOverrides {
  gateway_restart?: number;   // seconds (default: 120)
  module_install?: number;    // seconds (default: 300)
  browser_operation?: number; // milliseconds (default: 30000)
}

export interface ExecutionRequest {
  playbook_path: string;
  parameters: Record<string, string>;
  gateway_url?: string;
  credential_name?: string;
  debug_mode?: boolean;
  timeout_overrides?: TimeoutOverrides;
}

export interface ExecutionResponse {
  execution_id: string;
  status: string;
  message: string;
}

export interface ExecutionStatusResponse {
  execution_id: string;
  playbook_name: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  current_step_index: number;
  total_steps: number;
  error: string | null;
  debug_mode?: boolean;
  step_results?: StepResult[];
  domain?: string | null;  // Playbook domain (gateway, designer, perspective)
}

export interface CredentialInfo {
  name: string;
  username: string;
  gateway_url?: string;
  description?: string;
}

export interface CredentialCreate {
  name: string;
  username: string;
  password: string;
  gateway_url?: string;
  description?: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
}

// WebSocket message types
export interface StepResult {
  step_id: string;
  step_name: string;
  status: string;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  output?: {
    _output?: string;
    [key: string]: any;
  };
}

export interface ExecutionUpdate {
  execution_id: string;
  playbook_name: string;
  status: string;
  current_step_index: number;
  total_steps: number;
  error: string | null;
  debug_mode?: boolean;
  started_at: string | null;
  completed_at: string | null;
  step_results: StepResult[];
  domain?: string | null;  // Playbook domain (gateway, designer, perspective)
}

export interface ScreenshotFrame {
  executionId: string;
  screenshot: string; // base64 encoded JPEG
  timestamp: string;
}

export interface WebSocketMessage {
  type: 'execution_update' | 'screenshot_frame' | 'pong' | 'error';
  data?: ExecutionUpdate | ScreenshotFrame;
  error?: string;
}

// Enums
export type ExecutionStatus =
  | 'pending'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type StepStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'skipped';

export type ParameterType =
  | 'string'
  | 'integer'
  | 'float'
  | 'boolean'
  | 'file'
  | 'credential'
  | 'list'
  | 'dict';
