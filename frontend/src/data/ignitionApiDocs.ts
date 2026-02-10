/**
 * Curated API documentation for Ignition 8.3 REST API
 *
 * This provides static documentation for common Ignition Gateway API endpoints.
 * When an OpenAPI spec is available from the gateway, it takes precedence.
 */

export interface ApiEndpointDoc {
  method: string;
  path: string;
  description: string;
  parameters?: { name: string; type: string; description: string; required?: boolean }[];
  notes?: string;
}

export interface ApiCategoryDoc {
  name: string;
  description: string;
  endpoints: ApiEndpointDoc[];
}

export const ignitionApiDocs: ApiCategoryDoc[] = [
  {
    name: 'Gateway',
    description: 'Core gateway information, status, and management endpoints.',
    endpoints: [
      {
        method: 'GET',
        path: '/data/api/v1/gateway-info',
        description: 'Get gateway system information including version, edition, and platform details.',
        notes: 'Requires API key authentication. For HTTP connections, use /system/gwinfo as a fallback.',
      },
      {
        method: 'GET',
        path: '/data/api/v1/overview',
        description: 'Get an overview of gateway status including connection counts and active problems.',
      },
      {
        method: 'POST',
        path: '/data/api/v1/gateway/backup',
        description: 'Trigger a gateway backup. Returns a downloadable backup file.',
        parameters: [
          { name: 'includeProjects', type: 'boolean', description: 'Include project resources in the backup.', required: false },
          { name: 'includeHistory', type: 'boolean', description: 'Include historical data in the backup.', required: false },
        ],
        notes: 'This operation can take significant time depending on gateway size.',
      },
      {
        method: 'GET',
        path: '/data/api/v1/licenses',
        description: 'Get license information for the gateway, including module licenses.',
      },
      {
        method: 'GET',
        path: '/data/api/v1/trial',
        description: 'Get trial status information including remaining trial time.',
      },
    ],
  },
  {
    name: 'Modules',
    description: 'Module management and health monitoring endpoints.',
    endpoints: [
      {
        method: 'GET',
        path: '/data/api/v1/modules/healthy',
        description: 'Check if all modules are healthy. Returns a boolean or detailed module list.',
        notes: 'Returns {items: [{id, name, version, onStartup, ...}]} with module details.',
      },
      {
        method: 'GET',
        path: '/data/api/v1/modules/quarantined',
        description: 'List quarantined modules that have been disabled due to errors.',
      },
      {
        method: 'GET',
        path: '/data/api/v1/modules/list',
        description: 'List all installed modules with version and status information.',
      },
      {
        method: 'POST',
        path: '/data/api/v1/modules/install',
        description: 'Install a new module from an uploaded .modl file.',
        parameters: [
          { name: 'file', type: 'file', description: 'The .modl file to install.', required: true },
          { name: 'force', type: 'boolean', description: 'Force installation even if a newer version exists.', required: false },
        ],
      },
    ],
  },
  {
    name: 'Projects',
    description: 'Project management and scanning endpoints.',
    endpoints: [
      {
        method: 'POST',
        path: '/data/api/v1/scan/projects',
        description: 'Trigger a project resource scan. Useful after modifying project files on disk.',
        notes: 'This is equivalent to clicking "Scan Projects" in the Gateway web UI.',
      },
      {
        method: 'GET',
        path: '/data/api/v1/projects/list',
        description: 'List all projects on the gateway with their metadata.',
      },
      {
        method: 'GET',
        path: '/data/api/v1/projects/names',
        description: 'Get a simple list of project names without additional metadata.',
      },
      {
        method: 'GET',
        path: '/data/api/v1/designers',
        description: 'List currently connected Designer sessions.',
      },
      {
        method: 'POST',
        path: '/data/api/v1/scan/config',
        description: 'Trigger a configuration scan to refresh gateway configuration from disk.',
      },
    ],
  },
  {
    name: 'Resources',
    description: 'Resource listing endpoints for gateway-configured resources. Uses the pattern /data/api/v1/resources/list/{moduleId}/{typeId}.',
    endpoints: [
      {
        method: 'GET',
        path: '/data/api/v1/resources/list/ignition/database-connection',
        description: 'List all configured database connections.',
        notes: 'Returns connection names, types, and status. The moduleId is "ignition" and typeId is "database-connection".',
      },
      {
        method: 'GET',
        path: '/data/api/v1/resources/list/ignition/tag-provider',
        description: 'List all tag providers configured on the gateway.',
      },
      {
        method: 'GET',
        path: '/data/api/v1/resources/list/ignition/opc-connection',
        description: 'List all OPC server connections.',
      },
      {
        method: 'GET',
        path: '/data/api/v1/resources/list/com.inductiveautomation.opcua/device',
        description: 'List all OPC UA device connections.',
        notes: 'Uses the OPC UA module ID "com.inductiveautomation.opcua" with typeId "device".',
      },
      {
        method: 'GET',
        path: '/data/api/v1/resources/list/ignition/user-source',
        description: 'List all configured user sources (authentication profiles).',
      },
    ],
  },
  {
    name: 'Diagnostics',
    description: 'Diagnostic and troubleshooting endpoints for gateway health.',
    endpoints: [
      {
        method: 'GET',
        path: '/data/api/v1/diagnostics/threads/threaddump',
        description: 'Get a full thread dump of the gateway JVM.',
        notes: 'May require elevated permissions. Returns detailed thread state information.',
      },
      {
        method: 'GET',
        path: '/data/api/v1/diagnostics/threads/deadlocks',
        description: 'Check for deadlocked threads in the gateway JVM.',
      },
      {
        method: 'GET',
        path: '/data/api/v1/logs',
        description: 'Retrieve gateway log entries with optional filtering.',
        parameters: [
          { name: 'level', type: 'string', description: 'Filter by log level (TRACE, DEBUG, INFO, WARN, ERROR).', required: false },
          { name: 'logger', type: 'string', description: 'Filter by logger name prefix.', required: false },
          { name: 'limit', type: 'integer', description: 'Maximum number of log entries to return.', required: false },
        ],
      },
      {
        method: 'GET',
        path: '/data/api/v1/diagnostics/heap',
        description: 'Get JVM heap memory usage statistics.',
      },
    ],
  },
  {
    name: 'Performance',
    description: 'Performance monitoring and metrics endpoints.',
    endpoints: [
      {
        method: 'GET',
        path: '/data/api/v1/systemPerformance/charts',
        description: 'Get system performance chart data including CPU, memory, and disk usage over time.',
      },
      {
        method: 'GET',
        path: '/data/api/v1/systemPerformance/currentGauges',
        description: 'Get current performance gauge values (CPU %, memory %, disk %).',
      },
      {
        method: 'GET',
        path: '/data/api/v1/systemPerformance/threads',
        description: 'Get thread pool performance metrics.',
      },
      {
        method: 'GET',
        path: '/data/api/v1/systemPerformance/database',
        description: 'Get database connection pool performance statistics.',
      },
    ],
  },
];
