import * as http from 'http';

/**
 * Playbook summary from context API
 */
interface PlaybookSummary {
  name: string;
  description: string | null;
  domain: string | null;
  step_count: number;
  path: string;
}

/**
 * Step result summary from context API
 */
interface StepResultSummary {
  step_name: string;
  status: string;
  error: string | null;
  duration_seconds: number | null;
}

/**
 * Execution summary from context API
 */
interface ExecutionSummary {
  execution_id: string;
  playbook_name: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  step_results: StepResultSummary[];
  parameters: Record<string, unknown> | null;
}

/**
 * Credential summary from context API
 */
interface CredentialSummary {
  name: string;
  has_gateway_url: boolean;
  gateway_url: string | null;
}

/**
 * CloudDesigner summary from context API
 */
interface CloudDesignerSummary {
  status: string;
  port: number | null;
}

/**
 * Log entry from context API
 */
interface LogEntry {
  timestamp: string;
  level: string;
  logger: string;
  message: string;
  execution_id: string | null;
}

/**
 * System summary from context API
 */
interface SystemSummary {
  browser_available: boolean;
  active_executions: number;
  log_stats: Record<string, unknown> | null;
}

/**
 * Complete context summary from API (simple endpoint)
 */
export interface ContextSummary {
  playbooks: PlaybookSummary[];
  recent_executions: ExecutionSummary[];
  credentials: CredentialSummary[];
  clouddesigner: CloudDesignerSummary;
  system: SystemSummary;
  recent_logs: LogEntry[];
}

/**
 * Full context from API (detailed endpoint)
 */
export interface FullContext {
  playbooks: PlaybookSummary[];
  executions: ExecutionSummary[];
  credentials: CredentialSummary[];
  clouddesigner: CloudDesignerSummary;
  system: SystemSummary;
  logs: LogEntry[];
  error_logs: LogEntry[];
}

/**
 * Context builder for AI chat
 *
 * Fetches project context from the Python backend and builds
 * a system prompt for the AI assistant.
 */
export class ContextBuilder {
  private backendPort: number;

  constructor(backendPort: number) {
    this.backendPort = backendPort;
  }

  /**
   * Update the backend port (if it changes after restart)
   */
  setBackendPort(port: number): void {
    this.backendPort = port;
  }

  /**
   * Fetch context summary from Python backend
   */
  async fetchContext(): Promise<ContextSummary | null> {
    return this.fetchFromEndpoint<ContextSummary>('/api/context/summary');
  }

  /**
   * Fetch full context with logs and detailed execution data
   */
  async fetchFullContext(): Promise<FullContext | null> {
    return this.fetchFromEndpoint<FullContext>('/api/context/full?execution_limit=20&log_limit=100');
  }

  /**
   * Generic fetch helper
   */
  private async fetchFromEndpoint<T>(path: string): Promise<T | null> {
    return new Promise((resolve) => {
      const req = http.request(
        {
          hostname: '127.0.0.1',
          port: this.backendPort,
          path,
          method: 'GET',
          timeout: 10000,
        },
        (res) => {
          let data = '';

          res.on('data', (chunk) => {
            data += chunk;
          });

          res.on('end', () => {
            try {
              const context = JSON.parse(data) as T;
              resolve(context);
            } catch {
              console.error('[ContextBuilder] Failed to parse context response');
              resolve(null);
            }
          });
        }
      );

      req.on('error', (error) => {
        console.error('[ContextBuilder] Failed to fetch context:', error.message);
        resolve(null);
      });

      req.on('timeout', () => {
        req.destroy();
        console.error('[ContextBuilder] Context fetch timed out');
        resolve(null);
      });

      req.end();
    });
  }

  /**
   * Build a system prompt with full project context for the AI
   */
  async buildSystemPrompt(): Promise<string> {
    // Use full context for comprehensive information
    const context = await this.fetchFullContext();

    let prompt = `You are Clawdbot, an AI assistant for Ignition Toolbox - a desktop application for visual acceptance testing of Ignition SCADA systems.

You have FULL ACCESS to the project including:
- All playbooks and their configurations
- Execution history with step-by-step results
- Backend logs and error messages
- System status and configuration

You help users with:
- Understanding playbook steps and execution results
- Debugging failed executions using logs and error messages
- Suggesting playbook improvements
- Explaining Ignition SCADA concepts
- Troubleshooting browser automation issues

Always be concise and actionable. When debugging, reference specific log entries or step errors.
`;

    if (!context) {
      prompt += '\n(Project context unavailable - backend may not be running)';
      return prompt;
    }

    prompt += '\n## Current Project Context\n';

    // Playbooks
    if (context.playbooks.length > 0) {
      prompt += '\n### Playbooks\n';
      for (const playbook of context.playbooks.slice(0, 30)) {
        const desc = playbook.description ? ` - ${playbook.description}` : '';
        const domain = playbook.domain ? ` [${playbook.domain}]` : '';
        prompt += `- **${playbook.name}**${domain}: ${playbook.step_count} steps${desc}\n`;
      }
      if (context.playbooks.length > 30) {
        prompt += `- ... and ${context.playbooks.length - 30} more playbooks\n`;
      }
    } else {
      prompt += '\n### Playbooks\nNo playbooks installed yet.\n';
    }

    // Executions with step details
    if (context.executions.length > 0) {
      prompt += '\n### Recent Executions\n';
      for (const exec of context.executions.slice(0, 10)) {
        const status = exec.status.toUpperCase();
        prompt += `\n#### ${exec.playbook_name} (${status})\n`;
        prompt += `- ID: ${exec.execution_id}\n`;
        if (exec.started_at) {
          prompt += `- Started: ${exec.started_at}\n`;
        }
        if (exec.error) {
          prompt += `- **Error**: ${exec.error}\n`;
        }

        // Include step results for failed/recent executions
        if (exec.step_results && exec.step_results.length > 0) {
          const failedSteps = exec.step_results.filter(s => s.status === 'failed');
          if (failedSteps.length > 0) {
            prompt += `- Failed steps:\n`;
            for (const step of failedSteps) {
              prompt += `  - ${step.step_name}: ${step.error || 'No error message'}\n`;
            }
          }
        }
      }
    } else {
      prompt += '\n### Recent Executions\nNo recent executions.\n';
    }

    // Credentials
    if (context.credentials.length > 0) {
      prompt += '\n### Available Credentials\n';
      for (const cred of context.credentials) {
        const gateway = cred.gateway_url ? ` -> ${cred.gateway_url}` : '';
        prompt += `- ${cred.name}${gateway}\n`;
      }
    }

    // System Status
    prompt += '\n### System Status\n';
    prompt += `- CloudDesigner: ${context.clouddesigner.status}`;
    if (context.clouddesigner.port) {
      prompt += ` (port ${context.clouddesigner.port})`;
    }
    prompt += '\n';
    prompt += `- Active Executions: ${context.system.active_executions}\n`;
    prompt += `- Browser Automation: ${context.system.browser_available ? 'Available' : 'Not Available'}\n`;

    // Error Logs (important for debugging)
    if (context.error_logs && context.error_logs.length > 0) {
      prompt += '\n### Recent Error Logs\n';
      prompt += '```\n';
      for (const log of context.error_logs.slice(0, 20)) {
        const execId = log.execution_id ? ` [${log.execution_id.slice(0, 8)}]` : '';
        prompt += `[${log.timestamp}] ${log.level}${execId}: ${log.message}\n`;
      }
      prompt += '```\n';
    }

    // Recent Logs (for context)
    if (context.logs && context.logs.length > 0) {
      prompt += '\n### Recent Backend Logs\n';
      prompt += '```\n';
      for (const log of context.logs.slice(0, 30)) {
        const execId = log.execution_id ? ` [${log.execution_id.slice(0, 8)}]` : '';
        prompt += `[${log.timestamp}] ${log.level}${execId}: ${log.message}\n`;
      }
      prompt += '```\n';
    }

    return prompt;
  }

  /**
   * Get a simple context summary for display in the UI
   */
  async getDisplayContext(): Promise<{
    playbookCount: number;
    recentExecutions: { name: string; status: string }[];
    cloudDesignerStatus: string;
  }> {
    const context = await this.fetchContext();

    if (!context) {
      return {
        playbookCount: 0,
        recentExecutions: [],
        cloudDesignerStatus: 'unknown',
      };
    }

    return {
      playbookCount: context.playbooks.length,
      recentExecutions: context.recent_executions.slice(0, 5).map((e) => ({
        name: e.playbook_name,
        status: e.status,
      })),
      cloudDesignerStatus: context.clouddesigner.status,
    };
  }
}

// Singleton instance
let contextBuilderInstance: ContextBuilder | null = null;

/**
 * Get or create the singleton context builder instance
 */
export function getContextBuilder(backendPort?: number): ContextBuilder {
  if (!contextBuilderInstance && backendPort) {
    contextBuilderInstance = new ContextBuilder(backendPort);
  } else if (contextBuilderInstance && backendPort) {
    contextBuilderInstance.setBackendPort(backendPort);
  }

  if (!contextBuilderInstance) {
    throw new Error('ContextBuilder not initialized - backend port required');
  }

  return contextBuilderInstance;
}
