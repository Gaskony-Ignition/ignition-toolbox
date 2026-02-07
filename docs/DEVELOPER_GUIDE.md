# Developer Guide

Guide for setting up, running, and contributing to Ignition Toolbox.

## Prerequisites

- **Node.js 20+** (Electron + frontend build)
- **Python 3.10+** (backend)
- **npm** (package management)
- **Docker** (optional, for CloudDesigner and Stack Builder features)

## Setup

```bash
cd /git/ignition-toolbox

# Install Node.js dependencies (Electron)
npm install

# Install frontend dependencies
cd frontend && npm install && cd ..

# Create Python virtual environment and install backend deps
cd backend
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cd ..

# Install Playwright browsers (required for Perspective testing)
cd backend && python -m playwright install chromium && cd ..
```

## Development Mode

### Full Electron App

```bash
npm run dev
```

This starts the Vite dev server (port 3000) and Electron simultaneously. Electron spawns the Python backend as a subprocess. Requires a display (X11/Wayland/Windows).

### Backend + Frontend Separately

Useful for headless development or when you only need one component:

```bash
# Terminal 1 - Python backend (FastAPI on :5000)
cd backend && source .venv/bin/activate
python run_backend.py

# Terminal 2 - React frontend (Vite on :3000)
cd frontend && npm run dev
```

Open `http://localhost:3000` in a browser. The frontend proxies API requests to the backend on port 5000.

### Backend Only

For backend development or CI environments without a display:

```bash
cd backend && source .venv/bin/activate
python run_backend.py
```

The API is available at `http://localhost:5000`. Swagger docs at `http://localhost:5000/docs`.

## Project Structure

```
ignition-toolbox/
├── electron/                # Electron main process (TypeScript)
├── backend/                 # Python backend
│   ├── ignition_toolkit/    # Main package
│   │   ├── api/             # FastAPI app + routers
│   │   ├── playbook/        # Playbook engine + step handlers
│   │   ├── browser/         # Playwright automation
│   │   ├── gateway/         # Ignition Gateway REST client
│   │   ├── credentials/     # Fernet-encrypted vault
│   │   ├── storage/         # SQLite (SQLAlchemy)
│   │   ├── clouddesigner/   # Docker-based Designer launcher
│   │   ├── stackbuilder/    # Docker Compose generator
│   │   ├── auth/            # API key auth + RBAC
│   │   ├── execution/       # Parallel execution queue
│   │   └── reporting/       # Analytics + report exports
│   ├── playbooks/           # YAML playbook library
│   └── run_backend.py       # Entry point
├── frontend/                # React 19 + TypeScript + MUI v7
│   └── src/
│       ├── pages/           # 11 pages
│       ├── components/      # Reusable UI components
│       ├── hooks/           # Custom hooks (WebSocket, etc.)
│       ├── store/           # Zustand global state
│       └── api/             # HTTP API client
└── docs/                    # Documentation
```

## Running Tests

### Python Backend

```bash
cd backend && source .venv/bin/activate
pytest tests/ -v
```

### Frontend

```bash
cd frontend
npx vitest run
```

## Docker Deployment

The project includes a `docker-compose.yml` for containerized deployment:

```bash
docker compose up
```

This runs the backend and frontend in containers. Note that this is separate from the CloudDesigner and Stack Builder features, which use Docker to manage Ignition infrastructure.

## Key Patterns

### Step Handler Development

When adding new playbook step handlers, all operations that can block for more than 1 second **must** use cancellable utilities. See [CANCELLATION_PATTERN.md](CANCELLATION_PATTERN.md) for the mandatory pattern.

### API Routers

The FastAPI backend uses modular routers in `backend/ignition_toolkit/api/routers/`. Each router handles a single domain. Add new routers by creating a file in that directory and registering it in `app.py`.

### Frontend Pages

Pages live in `frontend/src/pages/`. Each page maps to a route in `App.tsx`. The frontend communicates with the backend via HTTP REST and WebSocket for real-time updates.

## Release Process

See [VERSIONING_GUIDE.md](VERSIONING_GUIDE.md) for the full release workflow. In brief:

1. Update version in `package.json` and `frontend/package.json`
2. Commit changes
3. Tag and push: `git tag v1.5.3 && git push origin v1.5.3`
4. GitHub Actions builds and publishes the Windows installer automatically

---

**Last Updated**: 2026-02-06
