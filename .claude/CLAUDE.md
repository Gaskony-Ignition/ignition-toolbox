# CLAUDE.md - Development Guide for Claude Code

This file provides guidance to Claude Code when working with the Ignition Toolbox.

> **Note:** This is the distributable Electron version of the Ignition Automation Toolkit.

## Project Overview

**Ignition Toolbox** is a distributable desktop application for visual acceptance testing of Ignition SCADA systems. It packages the Ignition Automation Toolkit as a standalone Electron app with an embedded Python backend.

**Current Version:** 3.0.15
**Architecture:** Electron + Python subprocess
**Target Platform:** Windows, macOS, Linux
**Key Technologies:** Electron, TypeScript, React 19, FastAPI, Playwright, SQLite

## Architecture

### Hybrid Electron + Python Subprocess

```
┌─────────────────────────────────────────────────────────┐
│                    Electron App                         │
├─────────────────────────────────────────────────────────┤
│  Main Process (TypeScript)                              │
│  ├── Window management                                  │
│  ├── Python subprocess lifecycle                        │
│  ├── IPC handlers                                       │
│  ├── Native dialogs                                     │
│  ├── Auto-updater (GitHub releases)                     │
│  └── App settings (electron-store)                      │
├─────────────────────────────────────────────────────────┤
│  Python Subprocess (FastAPI)                            │
│  ├── Playbook engine (44 step types)                    │
│  ├── Playwright browser automation                      │
│  ├── Gateway REST client                                │
│  ├── Credential vault (Fernet encryption)               │
│  └── SQLite database (execution history)                │
├─────────────────────────────────────────────────────────┤
│  Renderer Process (React)                               │
│  ├── Material-UI v7 with Warp Terminal theme            │
│  ├── HTTP/WebSocket to Python backend                   │
│  └── Real-time execution updates                        │
└─────────────────────────────────────────────────────────┘
```

## Project Structure

```
ignition-toolbox/
├── electron/                      # Electron main process (TypeScript)
│   ├── main.ts                    # App entry, window creation
│   ├── preload.ts                 # Context bridge for IPC
│   ├── ipc/handlers.ts            # IPC handler registration
│   └── services/
│       ├── python-backend.ts      # Python subprocess manager
│       ├── auto-updater.ts        # GitHub auto-updates
│       └── settings.ts            # App settings
│
├── backend/                       # Python backend
│   ├── ignition_toolkit/          # Main package
│   ├── playbooks/                 # Playbook library
│   ├── requirements.txt           # Python dependencies
│   └── run_backend.py             # Subprocess entry point
│
├── frontend/                      # React frontend
│   ├── src/
│   │   ├── pages/                 # Playbooks, Executions, Credentials
│   │   ├── components/            # UI components
│   │   ├── hooks/                 # WebSocket, API hooks
│   │   ├── store/                 # Zustand state
│   │   └── api/                   # API client
│   └── dist/                      # Built output
│
├── docs/                          # Documentation
├── .claude/                       # Claude Code configuration
├── package.json                   # Electron + build config
└── electron-builder.yml           # Distribution config
```

## Development Workflow

### Prerequisites
- Node.js 22+
- Python 3.13+
- npm

### Setup
```bash
cd /git/ignition-toolbox

# Install Node.js dependencies
npm install

# Install frontend dependencies
cd frontend && npm install && cd ..

# Create Python virtual environment and install deps
cd backend
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cd ..
```

### Running in Development
```bash
# Start both frontend and Electron (requires display)
npm run dev

# Or run components separately:
npm run dev:frontend      # Vite dev server (port 3000)
npm run dev:electron      # Electron with Python backend

# Test Python backend only (headless)
cd backend && source .venv/bin/activate
python run_backend.py
```

### Building for Distribution

**IMPORTANT: Production builds are done via GitHub Actions, NOT locally.**

```bash
# To release a new version:
# 1. Update version in package.json and frontend/package.json
# 2. Commit changes
# 3. Create and push a version tag:
git tag v3.0.15
git push origin v3.0.15

# This triggers GitHub Actions workflow (build.yml) which:
# - Builds on 4 runners (Windows, Linux, macOS x64, macOS arm64)
# - Creates platform-specific installers with PyInstaller + electron-builder
# - Publishes to GitHub Releases with all installers
# - Users receive auto-update notification

# You can also manually trigger from GitHub Actions UI using workflow_dispatch
```

**DO NOT use `npm run dist:*` for production releases** - these only work on local machines and are not the standard release process.

## Key Components

### Electron Main Process (`electron/`)

| File | Purpose |
|------|---------|
| `main.ts` | App entry, window creation, lifecycle |
| `preload.ts` | Context bridge exposing IPC to renderer |
| `services/python-backend.ts` | Spawns/monitors Python subprocess |
| `services/auto-updater.ts` | GitHub-based auto-updates |
| `services/settings.ts` | Persistent app settings |
| `ipc/handlers.ts` | IPC handler registration |

### Python Backend (`backend/`)

The Python backend is the full Ignition Automation Toolkit:

| Module | Purpose |
|--------|---------|
| `ignition_toolkit/api/` | FastAPI REST API and WebSocket |
| `ignition_toolkit/playbook/` | Playbook engine with 44 step types |
| `ignition_toolkit/browser/` | Playwright browser automation |
| `ignition_toolkit/gateway/` | Ignition Gateway REST client |
| `ignition_toolkit/credentials/` | Fernet-encrypted credential vault |
| `ignition_toolkit/storage/` | SQLite database |
| `ignition_toolkit/clouddesigner/` | Docker-based Designer launcher |
| `ignition_toolkit/stackbuilder/` | Docker Compose generator (25+ services) |
| `ignition_toolkit/auth/` | API key authentication + RBAC |
| `ignition_toolkit/execution/` | Parallel execution queue |
| `ignition_toolkit/reporting/` | Analytics and report exports |
| `ignition_toolkit/mcp_server.py` | MCP server (12 tools, 2 resources) |
| `ignition_toolkit/startup/` | Startup validation and Playwright installer |
| `ignition_toolkit/scheduler/` | Playbook scheduling |
| `ignition_toolkit/update/` | Version update checking |
| `ignition_toolkit/designer/` | Designer integration |
| `ignition_toolkit/modules/` | Ignition module management |
| `ignition_toolkit/exchange/` | Ignition Exchange scraper (Playwright + BeautifulSoup) |

### Frontend (`frontend/`)

React 19 + TypeScript + Material-UI v7 frontend:

| Directory | Purpose |
|-----------|---------|
| `src/pages/` | 10 pages: Playbooks, Executions, ExecutionDetail, Credentials, Designer, StackBuilder, APIExplorer, Exchange, Settings |
| `src/components/` | Reusable UI components |
| `src/components/api-explorer/` | API Explorer sub-components (ResponseViewer, JsonViewer, TableView, EndpointDocPanel, DocumentationCard) |
| `src/data/` | Static data (ignitionApiDocs.ts) |
| `src/hooks/` | WebSocket hook, playbook order hook |
| `src/store/` | Zustand global state |
| `src/api/` | HTTP API client |

> **Docker features vs Docker deployment:** CloudDesigner and StackBuilder are *features* that manage Docker containers for Ignition infrastructure. The `docker-compose.yml` at project root is for *deploying* the Toolbox itself in containers. These are independent concerns.

## Core Principles

1. **Domain Separation** - Playbooks are Gateway-only OR Perspective-only OR Designer-only
2. **Visual Feedback** - Users see what's happening via live browser streaming
3. **Playbook Library** - Users duplicate and modify existing playbooks
4. **Secure by Default** - Credentials encrypted, never in playbooks

## Git Workflow

```bash
# Commit format
git commit -m "Brief summary

Detailed explanation:
- What changed
- Why it changed

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

# Create release
git tag v3.0.15
git push origin v3.0.15  # Triggers GitHub Actions build
```

## CI/CD - GitHub Actions (CRITICAL)

**All production builds happen via GitHub Actions on platform-specific runners.**

GitHub Actions workflows in `.github/workflows/`:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push to main, PRs | Build verification (Windows + Ubuntu) |
| `build.yml` | Tag push (`v*`) or manual | **Production multi-platform build** (Windows, Linux, macOS x64/arm64) |

### Release Process
1. Make code changes and test locally (Python backend, frontend)
2. Update version in `package.json` and `frontend/package.json`
3. Commit all changes to main branch
4. Create version tag: `git tag v3.0.15`
5. Push tag: `git push origin v3.0.15`
6. GitHub Actions automatically:
   - Builds on 4 runners: `windows-latest`, `ubuntu-latest`, `macos-latest` (x64), `macos-latest` (arm64)
   - Packages with PyInstaller + electron-builder per platform
   - Creates GitHub Release with all installers (`.exe`, `.AppImage`, `.dmg` x2)
   - Uploads auto-update manifests (`latest.yml`, `latest-mac.yml`, `latest-linux.yml`)
   - Users get auto-update notification

### Manual Build Trigger
You can also trigger builds from GitHub Actions UI:
1. Go to Actions → Build
2. Click "Run workflow"
3. Optionally specify version

**NEVER attempt to build production installer locally** - PyInstaller creates platform-specific binaries.

## Security

- **Credentials**: Fernet encryption, stored in user data directory
- **IPC**: Context isolation, validated channels
- **Updates**: Signed releases from GitHub

## Important Files

| File | Purpose |
|------|---------|
| `package.json` | Electron config, scripts, dependencies |
| `electron-builder.yml` | Distribution configuration |
| `backend/requirements.txt` | Python dependencies |
| `frontend/vite.config.ts` | Vite build configuration |
| `PROJECT_GOALS.md` | Project goals and decision framework |
| `ARCHITECTURE.md` | Architecture decision records |

---

**Last Updated**: 2026-02-23
**Maintainer**: Nigel G
**Status**: Production Ready (v3.0.15) - All Development Phases Complete

## Development Phases

See `ROADMAP_PHASES.md` for the detailed development roadmap with phases:
- Phase 0: Critical Updates (Electron v40) ✅ COMPLETE
- Phase 1: Code Quality & Stability ✅ COMPLETE
- Phase 2: Testing Foundation ✅ COMPLETE
- Phase 3: Documentation & UX ✅ COMPLETE
- Phase 4: Feature Completion ✅ COMPLETE
- Phase 5: Performance & Scale ✅ COMPLETE
- Phase 6: Advanced Features ✅ COMPLETE
  - 6.1 Parallel Execution (queue, resource limiting)
  - 6.2 Multi-User Support (API keys, RBAC, audit logging)
  - 6.3 Reporting & Analytics (trends, exports)
