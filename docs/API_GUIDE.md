# API Guide

This guide documents the REST API and WebSocket endpoints for the Ignition Toolbox.

## Base URL

- **Development**: `http://localhost:5000`
- **Electron**: `http://127.0.0.1:<dynamic-port>`

## Authentication

The API supports API key authentication for multi-user deployments (implemented in Phase 6).

### API Key Authentication

Include the API key in the `X-API-Key` header:

```http
GET /api/playbooks
X-API-Key: itk_your_api_key_here
```

### Key Features

- Keys are prefixed with `itk_` for identification
- Stored as SHA-256 hashes (never in plaintext)
- Support expiration dates and rate limiting
- Role-based access control (RBAC) with predefined roles: `admin`, `user`, `readonly`, `executor`

### Default Behavior

When running as a local single-user desktop app (Electron), authentication is not enforced by default. API key authentication is primarily intended for shared or headless deployments.

### WebSocket Authentication

WebSocket connections require an API key as a query parameter:

```
ws://localhost:5000/ws/executions?api_key=itk_your_api_key_here
```

## REST API Endpoints

### Playbooks

#### List Playbooks

```http
GET /api/playbooks
```

**Response:**
```json
{
  "playbooks": [
    {
      "name": "Module Upgrade",
      "path": "gateway/module_upgrade.yaml",
      "domain": "gateway",
      "description": "Upgrade modules on a gateway",
      "version": "1.0"
    }
  ]
}
```

#### Get Playbook Details

```http
GET /api/playbooks/{path}
```

**Parameters:**
- `path`: URL-encoded relative path to playbook

**Response:**
```json
{
  "name": "Module Upgrade",
  "version": "1.0",
  "description": "Upgrade modules on a gateway",
  "parameters": [
    {
      "name": "gateway_url",
      "type": "string",
      "required": true,
      "description": "Gateway base URL"
    }
  ],
  "steps": [
    {
      "id": "login",
      "name": "Login to Gateway",
      "type": "gateway.login"
    }
  ]
}
```

#### Duplicate Playbook

```http
POST /api/playbooks/duplicate
```

**Request:**
```json
{
  "source_path": "gateway/original.yaml",
  "new_name": "My Custom Playbook"
}
```

**Response:**
```json
{
  "message": "Playbook duplicated successfully",
  "new_path": "gateway/my-custom-playbook.yaml"
}
```

### Executions

#### Start Execution

```http
POST /api/executions
```

**Request:**
```json
{
  "playbook_path": "gateway/module_upgrade.yaml",
  "parameters": {
    "module_path": "/path/to/module.modl"
  },
  "gateway_url": "http://localhost:8088",
  "credential_name": "my-gateway",
  "debug_mode": false
}
```

**Response:**
```json
{
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "playbook_name": "Module Upgrade",
  "status": "started",
  "message": "Execution started with ID: 550e8400-..."
}
```

#### List Executions

```http
GET /api/executions?limit=50&status=running
```

**Parameters:**
- `limit` (optional): Maximum results (default: 50)
- `status` (optional): Filter by status (running, completed, failed, cancelled)

**Response:**
```json
[
  {
    "execution_id": "550e8400-...",
    "playbook_name": "Module Upgrade",
    "status": "running",
    "started_at": "2026-02-04T10:30:00Z",
    "current_step_index": 2,
    "total_steps": 5
  }
]
```

#### Get Execution Status

```http
GET /api/executions/{execution_id}
```

**Response:**
```json
{
  "execution_id": "550e8400-...",
  "playbook_name": "Module Upgrade",
  "status": "running",
  "started_at": "2026-02-04T10:30:00Z",
  "current_step_index": 2,
  "total_steps": 5,
  "step_results": [
    {
      "step_id": "login",
      "step_name": "Login to Gateway",
      "status": "completed",
      "started_at": "2026-02-04T10:30:01Z",
      "completed_at": "2026-02-04T10:30:03Z"
    }
  ]
}
```

#### Control Execution

```http
POST /api/executions/{execution_id}/pause
POST /api/executions/{execution_id}/resume
POST /api/executions/{execution_id}/cancel
POST /api/executions/{execution_id}/skip
```

**Response:**
```json
{
  "message": "Execution paused",
  "execution_id": "550e8400-..."
}
```

#### Delete Execution

```http
DELETE /api/executions/{execution_id}
```

**Response:**
```json
{
  "message": "Execution deleted successfully",
  "execution_id": "550e8400-...",
  "screenshots_deleted": 5
}
```

### Credentials

#### List Credentials

```http
GET /api/credentials
```

**Response:**
```json
{
  "credentials": [
    {
      "name": "my-gateway",
      "username": "admin",
      "gateway_url": "http://localhost:8088",
      "description": "Local development gateway"
    }
  ]
}
```

> **Note**: Passwords are never returned in API responses.

#### Create Credential

```http
POST /api/credentials
```

**Request:**
```json
{
  "name": "my-gateway",
  "username": "admin",
  "password": "secret",
  "gateway_url": "http://localhost:8088",
  "description": "Local development gateway"
}
```

**Response:**
```json
{
  "message": "Credential saved successfully",
  "name": "my-gateway"
}
```

#### Delete Credential

```http
DELETE /api/credentials/{name}
```

**Response:**
```json
{
  "message": "Credential deleted successfully"
}
```

### Health

#### Health Check

```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.5.4",
  "uptime_seconds": 3600
}
```

## WebSocket API

### Connection

```javascript
const ws = new WebSocket('ws://localhost:5000/ws/executions?api_key=<key>');
```

### Message Types

#### Execution Update

Sent when execution state changes:

```json
{
  "type": "execution_update",
  "data": {
    "execution_id": "550e8400-...",
    "status": "running",
    "current_step_index": 2,
    "step_result": {
      "step_id": "login",
      "status": "completed"
    }
  }
}
```

#### Screenshot Frame

Sent during browser automation (base64 encoded):

```json
{
  "type": "screenshot_frame",
  "data": {
    "execution_id": "550e8400-...",
    "frame": "data:image/png;base64,iVBORw0KGgo...",
    "timestamp": 1707000000000
  }
}
```

#### Heartbeat

Client should send ping, server responds with pong:

```json
// Client sends:
{"type": "ping", "timestamp": 1707000000000}

// Server responds:
{"type": "pong", "timestamp": 1707000000000}
```

## Error Responses

All error responses follow this format:

```json
{
  "detail": {
    "error": "playbook_not_found",
    "message": "Playbook 'test.yaml' not found",
    "details": {
      "path": "test.yaml"
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `playbook_not_found` | 404 | Playbook file not found |
| `invalid_path` | 400 | Invalid or unsafe file path |
| `execution_not_found` | 404 | Execution ID not found |
| `credential_not_found` | 404 | Credential name not found |
| `validation_error` | 400 | Request validation failed |
| `internal_error` | 500 | Unexpected server error |
| `permission_denied` | 403 | Access denied |
| `timeout_error` | 504 | Operation timed out |

## Rate Limiting

Rate limiting is available through the API key authentication system (see SECURITY.md).

## Examples

### cURL Examples

**Start an execution:**
```bash
curl -X POST http://localhost:5000/api/executions \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_path": "gateway/health_check.yaml",
    "gateway_url": "http://localhost:8088",
    "credential_name": "my-gateway"
  }'
```

**List executions:**
```bash
curl http://localhost:5000/api/executions?limit=10
```

**Cancel execution:**
```bash
curl -X POST http://localhost:5000/api/executions/550e8400-.../cancel
```

### JavaScript Examples

**Start execution:**
```javascript
const response = await fetch('http://localhost:5000/api/executions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    playbook_path: 'gateway/health_check.yaml',
    gateway_url: 'http://localhost:8088',
    credential_name: 'my-gateway'
  })
});
const { execution_id } = await response.json();
```

**WebSocket connection:**
```javascript
const ws = new WebSocket('ws://localhost:5000/ws/executions?api_key=dev-key');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === 'execution_update') {
    console.log('Status:', message.data.status);
  }
};

// Send heartbeat
setInterval(() => {
  ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
}, 15000);
```

---

**Last Updated**: 2026-02-06
**API Version**: 1.5.4
