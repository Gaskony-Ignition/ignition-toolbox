# Security Guide

This document describes the security architecture and best practices for the Ignition Toolbox.

## Credential Storage

### Encryption

All credentials are encrypted using **Fernet symmetric encryption** (AES-128-CBC with HMAC-SHA256):

- **Encryption Key**: Stored in `~/.ignition-toolkit/encryption.key`
- **Credentials File**: Stored in `~/.ignition-toolkit/credentials.json` (encrypted)
- **File Permissions**: Both files are set to `0600` (owner read/write only)

### Key Generation

The encryption key is automatically generated on first use:

```python
# Uses cryptography library's Fernet.generate_key()
# Produces a URL-safe base64-encoded 32-byte key
```

### Storage Location

Credentials are stored in the user's data directory:

| Platform | Location |
|----------|----------|
| Windows  | `%APPDATA%\ignition-toolkit\` |
| Linux    | `~/.ignition-toolkit/` |
| macOS    | `~/.ignition-toolkit/` |

### What's Encrypted

- **Password field**: Encrypted before storage
- **Entire credentials file**: Double-encrypted (file-level + field-level)

### Key Rotation

To rotate the encryption key:

1. Export credentials to a secure backup
2. Delete `~/.ignition-toolkit/encryption.key`
3. Delete `~/.ignition-toolkit/credentials.json`
4. Restart the application (new key is generated)
5. Re-enter all credentials

> **Warning**: Deleting the encryption key without backing up credentials will result in permanent credential loss.

## WebSocket Security

### API Key Authentication

WebSocket connections require an API key:

```
ws://localhost:5000/ws/executions?api_key=<key>
```

- **Development**: Uses default key `dev-key-change-in-production`
- **Production**: Set `WEBSOCKET_API_KEY` environment variable

### Connection Security

- WebSocket connections are authenticated on connect
- Invalid API keys are rejected immediately
- Heartbeat mechanism (15-second ping/pong) maintains connection health

## API Security

### CORS Configuration

- Default: Allows `http://localhost:*` origins
- Electron mode: Allows `file://` and `app://` origins
- Configurable via `ALLOWED_ORIGINS` environment variable

### Path Traversal Prevention

All file path operations validate against directory traversal:

```python
# Prevented patterns:
# - ../  (parent directory)
# - Absolute paths
# - Symlinks outside allowed directories
```

## Electron Security

### Context Isolation

- Renderer process is isolated from Node.js APIs
- Communication only through approved IPC channels
- `contextIsolation: true` in webPreferences

### Content Security Policy

```
default-src 'self';
script-src 'self';
style-src 'self' 'unsafe-inline';
img-src 'self' data:;
connect-src 'self' ws://127.0.0.1:* http://127.0.0.1:*;
```

### Auto-Updater

- Updates are fetched from GitHub Releases
- Signed executables (Windows)
- Verification before installation

## Network Security

### Gateway Connections

- Credentials are never logged
- HTTPS recommended for production gateways
- Credentials are stored locally, not transmitted to external services

### Browser Automation

- Playwright runs in isolated browser contexts
- No persistent cookies between executions
- Screenshots are stored locally only

## Best Practices

### For Users

1. **Use strong passwords** for Gateway credentials
2. **Set `WEBSOCKET_API_KEY`** in production deployments
3. **Backup encryption key** before system migration
4. **Don't share** the `.ignition-toolkit` directory
5. **Use HTTPS** for Gateway connections when possible

### For Developers

1. **Never log credentials** or encryption keys
2. **Validate all file paths** against traversal attacks
3. **Use parameterized queries** for database operations
4. **Sanitize user input** in playbook parameters
5. **Keep dependencies updated** for security patches

## Vulnerability Reporting

If you discover a security vulnerability:

1. **Do not** create a public GitHub issue
2. Email details to the maintainer
3. Include steps to reproduce
4. Allow time for a fix before public disclosure

## Audit Log

Audit logging was implemented in Phase 6 (v1.5.0) as part of Multi-User Support. API key authentication, RBAC, and audit trails are available for production deployments.

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `WEBSOCKET_API_KEY` | WebSocket authentication | Auto-generated secure key |
| `ALLOWED_ORIGINS` | CORS allowed origins | `http://localhost:*` |
| `DEBUG` | Enable debug logging | `false` |

## File Permissions Summary

| File | Permissions | Purpose |
|------|-------------|---------|
| `encryption.key` | `0600` | Fernet encryption key |
| `credentials.json` | `0600` | Encrypted credentials |
| `playbooks/*.yaml` | `0644` | Playbook definitions |
| `database.sqlite` | `0600` | Execution history |

---

**Last Updated**: 2026-02-04
**Security Review**: Pending
