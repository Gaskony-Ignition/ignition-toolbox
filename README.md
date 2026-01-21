# Ignition Toolbox

A distributable desktop application for visual acceptance testing of Ignition SCADA systems.

## Overview

Ignition Toolbox is an Electron-based desktop application that provides:

- **Playbook-based automation** for Gateway, Perspective, and Designer testing
- **Real-time browser automation** with live screenshot streaming
- **Credential management** with encrypted storage
- **Execution history** with step-by-step results
- **Stack Builder** for generating Docker Compose deployments with automatic service integration

## Architecture

This application uses a hybrid architecture:

- **Electron** - Desktop application shell, window management, native dialogs
- **Python Backend** - FastAPI server running as subprocess, handling all automation
- **React Frontend** - Modern UI with real-time WebSocket updates

## Development

### Prerequisites

- Node.js 20+
- Python 3.10+
- npm or yarn

### Setup

```bash
# Install Node.js dependencies
npm install

# Install frontend dependencies
cd frontend && npm install && cd ..

# Install Python dependencies
cd backend && pip install -r requirements.txt && cd ..

# Install Playwright browsers (for Perspective testing)
cd backend && python -m playwright install chromium && cd ..
```

### Running in Development

```bash
# Start both frontend and Electron
npm run dev

# Or start them separately:
npm run dev:frontend   # Start Vite dev server (port 3000)
npm run dev:electron   # Start Electron with Python backend
```

### Building for Distribution

```bash
# Build for Windows
npm run dist:win

# Output will be in ./release/
```

## Project Structure

```
ignition-toolbox/
├── electron/           # Electron main process (TypeScript)
│   ├── main.ts         # App entry point
│   ├── preload.ts      # Context bridge for IPC
│   ├── ipc/            # IPC handlers
│   └── services/       # Backend manager, settings
├── backend/            # Python backend
│   ├── ignition_toolkit/  # Main package
│   ├── playbooks/      # Playbook library
│   └── run_backend.py  # Subprocess entry point
├── frontend/           # React frontend
│   ├── src/            # Source code
│   └── dist/           # Built output
└── resources/          # Build resources (icons, etc.)
```

## Stack Builder

The Stack Builder is a visual tool for generating Docker Compose deployments for IIoT/SCADA infrastructure.

### Features

- **Service Catalog**: 25+ pre-configured services including Ignition, databases, MQTT brokers, and monitoring tools
- **Automatic Integrations**: Detects and configures connections between services
- **Complete Deployment Packages**: Generates docker-compose.yml, environment files, and startup scripts

### Supported Services

| Category | Services |
|----------|----------|
| Industrial | Ignition SCADA |
| Databases | PostgreSQL, MariaDB, MSSQL |
| Messaging | EMQX, Mosquitto |
| Auth | Keycloak |
| Monitoring | Grafana, Prometheus |
| DevOps | Portainer, Node-RED, n8n |

For detailed documentation, see [backend/ignition_toolkit/stackbuilder/README.md](backend/ignition_toolkit/stackbuilder/README.md).

## License

MIT
