---
name: testing-and-verification
description: Exact commands to test, lint, and run the Ignition Toolbox locally (backend pytest, frontend vitest, eslint, ruff/black, playbook validation). Load before verifying any change and before claiming work is done.
user-invocable: true
---

# Testing & Verification

All commands run from the repo root (`ignition-toolbox/`). The backend venv is
`backend/.venv` (Python 3.14) — always use its binaries, never system Python.

## Backend (pytest — ~112 test files)

```bash
cd backend && .venv/bin/python -m pytest tests/ -q            # full suite
cd backend && .venv/bin/python -m pytest tests/test_playbook -q   # one area (~9 s)
cd backend && .venv/bin/python -m pytest -m "not integration and not slow" -q
```

Config in `backend/pyproject.toml` (`asyncio_mode = auto` — async tests need no
decorator). Test dirs mirror packages: `tests/test_api`, `test_playbook`,
`test_gateway`, `test_browser`, `test_credentials`, `test_storage`, etc.

## Frontend (vitest — 26 files, ~45 s)

```bash
cd frontend && npx vitest run                 # full suite
cd frontend && npx vitest run src/pages/Playbooks.test.tsx   # one file
```

Tests live next to their components (`Foo.tsx` → `Foo.test.tsx`).

## Lint / format (CI enforces all of these)

```bash
cd frontend && npx eslint src/ --max-warnings 0   # CI fails on any warning
cd backend && .venv/bin/ruff check ignition_toolkit tests
cd backend && .venv/bin/black --check ignition_toolkit   # line length 100
npm run build:electron                            # tsc type-check of electron/
```

## Playbook library validation

After editing anything under `backend/playbooks/`:

```bash
backend/.venv/bin/python scripts/validate-playbooks.py
```

Validates schema, domains, and step types against the live registry.

## Running the app

```bash
# Headless backend only (FastAPI on :5000) — enough for most API work
cd backend && .venv/bin/python run_backend.py

# Backend + frontend in a browser (no Electron needed)
cd frontend && npm run dev        # Vite on :3000, proxies to :5000

# Full Electron app (requires a display)
npm run dev
```

## What CI runs (`.github/workflows/ci.yml`)

`pytest tests/ -v` (backend), `vitest run` (frontend), `eslint src/
--max-warnings 0`, plus Windows + Ubuntu build verification. If it fails
locally it will fail CI — run the relevant suite before committing.

Production builds are GitHub Actions only (`build.yml`, tag push `v*`) — see
`toolbox-conventions` for the release process.
