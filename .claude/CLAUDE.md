# CLAUDE.md - Development Guide for Claude Code

This file provides guidance to Claude Code when working with the Ignition Toolbox.

> **Note:** This is the distributable Electron version of the Ignition Automation Toolkit.

## Project Overview

**Ignition Toolbox** is a distributable desktop application for visual acceptance testing of Ignition SCADA systems. It packages the Ignition Automation Toolkit as a standalone Electron app with an embedded Python backend.

**Current Version:** 1.4.70
**Architecture:** Electron + Python subprocess
**Target Platform:** Windows (primary), cross-platform possible
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
- Node.js 20+
- Python 3.10+
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
```bash
# Build Windows installer
npm run dist:win

# Output: release/Ignition-Toolbox-Setup-1.0.0.exe
```

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

### Frontend (`frontend/`)

React 19 + TypeScript + Material-UI v7 frontend:

| Directory | Purpose |
|-----------|---------|
| `src/pages/` | Main pages (Playbooks, Executions, Credentials) |
| `src/components/` | Reusable UI components |
| `src/hooks/` | WebSocket hook, playbook order hook |
| `src/store/` | Zustand global state |
| `src/api/` | HTTP API client |

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

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

# Create release
git tag v1.0.1
git push origin v1.0.1  # Triggers GitHub Actions build
```

## CI/CD

GitHub Actions workflows in `.github/workflows/`:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push to main, PRs | Build verification |
| `build-windows.yml` | Tag push (`v*`) | Build Windows installer, publish release |

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

**Last Updated**: 2026-02-04
**Maintainer**: Nigel G
**Status**: Production Ready (v1.4.70)

## Development Phases

See `ROADMAP_PHASES.md` for the detailed development roadmap with phases:
- Phase 0: Critical Updates (Electron v40 - DONE)
- Phase 1: Code Quality & Stability
- Phase 2: Testing Foundation
- Phase 3: Documentation & UX
- Phase 4: Feature Completion
- Phase 5: Performance & Scale
- Phase 6: Advanced Features
