# Ignition Toolbox

A desktop app for visual acceptance testing of Ignition SCADA gateways — reusable playbooks, live browser streaming, and full execution history, instead of throwaway scripts.

## Why this exists

Ignition acceptance testing is usually done by hand or with throwaway scripts:
results aren't repeatable, visual UI problems slip past blind scripts, the same
login and navigation flows get rewritten for every job, and the knowledge walks
out the door with whoever wrote them. The Toolbox makes gateway and Perspective
acceptance testing repeatable and visible — a library of reusable,
domain-separated playbooks runs against Gateways and Perspective sessions with
real-time browser streaming, so the tester *sees* what happened, backed by
encrypted credentials and full execution history.

The full problem statement, target users, and decision framework live in
[PROJECT_GOALS.md](PROJECT_GOALS.md).

## What it looks like

![Gateway playbook library, nine reusable playbooks ready to run](docs/images/playbooks-library.png)
The Gateway playbook library. Nine playbooks ship out of the box — login,
restart, module install/upgrade/uninstall, trial reset, backup, API key setup —
each versioned and ready to configure and run against a real gateway.

![A completed Module Install execution expanded to its step-by-step timeline](docs/images/execution-detail.png)
A completed run, expanded in place. Every step is timestamped and reported
individually — "Navigate to Modules Page", "Upload Module File", "Verify
Install Button is Enabled" — not just a single pass/fail line, so a failure
points straight at the step that caused it.

![Stack Builder with Ignition, PostgreSQL and an MQTT broker added, showing auto-detected integrations](docs/images/stack-builder.png)
Stack Builder assembling a Docker Compose deployment. Services are added from
a categorised catalog; adding a database or MQTT broker is auto-detected as an
integration Ignition can use, shown under "Detected Integrations" before you
deploy.

![The API Explorer's curated Ignition 8.3 REST API documentation](docs/images/api-explorer.png)
The built-in API Explorer's curated Ignition 8.3 REST API reference, grouped
by area (Gateway, Modules, Projects, Resources, Diagnostics, Performance,
Perspective) — no separate reference tab needed to look up an endpoint.

![UDT Builder's quick-start presets for Analog Input, Motor and Valve](docs/images/udt-builder.png)
UDT Builder's quick-start presets — ISA-18.2-aligned alarm ladders for Analog
Input, Motor and Valve types, or a guided wizard for anything else.
Download-only: nothing is pushed to a gateway, you import the JSON yourself.

## What it does

| Page | Description |
| ------ | ------------- |
| **Playbooks** | Browse, duplicate, edit, and run the YAML playbook library (Gateway and Perspective domains, kept separate) |
| **Executions** | Live execution monitoring with pause/resume/skip/cancel, filterable by status |
| **Execution Detail** | Step-by-step results, screenshots, and log output for a run in progress |
| **Credentials** | Fernet-encrypted credential vault for Gateway/Perspective auth — never stored in playbooks |
| **Stack Builder** | Generate Docker Compose deployments for IIoT/SCADA infrastructure from a service catalog |
| **UDT Builder** | Guided wizard or quick-start presets for standardised, alarm-ladder-complete UDTs (download-only) |
| **API Explorer** | Interactive REST API browser plus curated Ignition 8.3 API documentation |
| **Audit** | Upload a Perspective project export and get a findings report (executive summary + markdown download) |
| **Settings** | Application configuration and preferences |

## How to use it

**Prerequisites:** Node.js 22+, Python 3.13+, npm.

```bash
# 1. Install dependencies
npm install
cd frontend && npm install && cd ..
cd backend && python3 -m venv .venv && source .venv/bin/activate \
  && pip install -r requirements.txt && cd ..

# 2. Run it (Electron shell + backend + frontend together)
npm run dev
```

First run: dismiss the welcome dialog, open **Credentials** and add the
gateway (or Perspective session) you're testing against, then open
**Playbooks → Gateway**, pick one (e.g. *Gateway Login*), **Configure** it with
that credential, and **Execute**. Watch it run live under **Active Execution**;
find it again afterwards under **Past Executions**.

For a permanent install rather than a dev checkout, use a packaged build from
[GitHub Releases](../../releases) — it auto-updates in-app.

---

## Architecture

```mermaid
graph TB
    subgraph Electron["Electron Desktop App"]
        Main["Main Process<br/>(TypeScript)"]
        Renderer["Renderer Process<br/>(React 19 + MUI v7)"]
    end

    subgraph Backend["Python Backend (FastAPI :5000)"]
        API["REST API +<br/>WebSocket"]
        Engine["Playbook Engine<br/>(37 step types)"]
        PW["Playwright<br/>Browser Automation"]
        GW["Gateway Client"]
        Vault["Credential Vault<br/>(Fernet)"]
        DB["SQLite"]
        SBM["Stack Builder"]
    end

    subgraph External["External Systems"]
        IG["Ignition Gateway"]
        Docker["Docker Engine"]
    end

    Main -->|spawns| API
    Main <-->|IPC| Renderer
    Renderer -->|HTTP / WS| API
    API --> Engine
    Engine --> PW
    Engine --> GW
    Engine --> Vault
    Engine --> DB
    API --> SBM
    GW --> IG
    PW -->|browser| IG
    SBM -->|Docker Compose| Docker
```

<details>
<summary>ASCII diagram (non-GitHub contexts)</summary>

```text
┌──────────────── Electron Desktop App ──────────────────┐
│  Main Process (TS)  ←──IPC──→  Renderer (React 19)    │
└────────┬───────────────────────────────┬───────────────┘
         │ spawns                        │ HTTP / WS
         ▼                              ▼
┌──────────────── Python Backend (FastAPI :5000) ────────┐
│  REST API + WebSocket                                  │
│  ├── Playbook Engine (37 step types)                   │
│  ├── Playwright Browser Automation                     │
│  ├── Gateway REST Client                                │
│  ├── Credential Vault (Fernet)                          │
│  ├── SQLite Database                                    │
│  └── Stack Builder                                      │
└────────┬──────────────────────────────┬────────────────┘
         │                              │
         ▼                              ▼
  Ignition Gateway                Docker Engine
```

</details>

## Run Modes

### 1. Electron App (production)

The standard way end-users run the application. Electron spawns the Python
backend as a subprocess and serves the React frontend.

Install from [GitHub Releases](../../releases) or receive auto-update
notifications in-app.

### 2. Plain Development Server

Run the backend and frontend separately for development:

```bash
# Terminal 1 - Python backend
cd backend && source .venv/bin/activate
python run_backend.py          # FastAPI on :5000

# Terminal 2 - React frontend
cd frontend && npm run dev     # Vite on :3000
```

### 3. Docker (optional)

```bash
docker compose up              # Backend + frontend in containers
```

## Release Process

**All production builds happen via GitHub Actions on `windows-latest` runners.**

```bash
# 1. Update version in package.json and frontend/package.json
# 2. Commit changes
# 3. Create and push a version tag:
git tag v2.0.0
git push origin v2.0.0
```

GitHub Actions (`build-windows.yml`) automatically builds the Windows
installer with PyInstaller + electron-builder, publishes to GitHub Releases,
and triggers auto-update notifications for existing users.

You can also trigger builds manually from the GitHub Actions UI
(workflow_dispatch).

> **Note:** Do not use `npm run dist:win` for production releases. That script
> is for local development builds only and produces platform-specific binaries
> that depend on the build machine.

## Project Structure

```text
ignition-toolbox/
├── electron/                      # Electron main process (TypeScript)
│   ├── main.ts                    # App entry, window creation
│   ├── preload.ts                 # Context bridge for IPC
│   ├── ipc/handlers.ts            # IPC handler registration
│   └── services/                  # Backend manager, updater, settings
│
├── backend/                       # Python backend
│   ├── ignition_toolkit/          # Main package
│   │   ├── api/                   # FastAPI REST API + WebSocket
│   │   ├── playbook/              # Playbook engine (37 step types)
│   │   ├── browser/               # Playwright browser automation
│   │   ├── gateway/               # Ignition Gateway REST client
│   │   ├── credentials/           # Fernet-encrypted credential vault
│   │   ├── storage/                # SQLite database
│   │   ├── stackbuilder/          # Docker Compose generator
│   │   ├── auth/                  # API key auth + RBAC
│   │   ├── execution/             # Parallel execution queue
│   │   └── reporting/             # Analytics and report exports
│   ├── playbooks/                 # Playbook library (YAML)
│   └── run_backend.py             # Subprocess entry point
│
├── frontend/                      # React 19 + TypeScript + MUI v7
│   ├── src/
│   │   ├── pages/                 # 9 pages (see What it does)
│   │   ├── components/            # Reusable UI components
│   │   ├── hooks/                 # WebSocket, playbook order hooks
│   │   ├── store/                 # Zustand global state
│   │   └── api/                   # HTTP API client
│   └── dist/                      # Built output
│
├── docs/                          # Documentation
├── .claude/                       # Claude Code configuration
├── package.json                   # Electron + build config
└── electron-builder.yml           # Distribution config
```

## Documentation

| Document | Description |
| ---------- | ------------- |
| [Developer Guide](docs/DEVELOPER_GUIDE.md) | Setup, development workflow, testing |
| [Architecture](ARCHITECTURE.md) | System design and ADRs |
| [Project Goals](PROJECT_GOALS.md) | Vision and decision framework |
| [API Guide](docs/API_GUIDE.md) | REST and WebSocket API reference |
| [Playbook Syntax](docs/playbook_syntax.md) | YAML playbook reference |
| [Security](SECURITY.md) | Security architecture and best practices |
| [Versioning](docs/VERSIONING_GUIDE.md) | Version scheme and release process |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues and solutions |

## Status

Production ready and actively maintained (currently v3.7.x — see
`package.json` for the exact version) — regular releases for playbook fixes
and incremental features.

Longer term, this Electron app is being progressively superseded by
Ignition-native successors in a sister repo (the "Toolbox" suite of Perspective
projects, migrated straight into Ignition rather than run alongside it). That
migration is mid-flight, not finished: several features here — Stack Builder
and UDT Builder among them — have no replacement yet. Nothing here is
deprecated on the strength of that plan alone; this app remains the
day-to-day tool until its replacements actually cover the same ground.

## License

MIT
