---
name: toolbox-conventions
description: Code style, commit, and release conventions for the Ignition Toolbox (Python backend + TS/React frontend + Electron). Load before writing code, committing, or releasing.
user-invocable: true
---

# Toolbox Conventions

Condensed from the former WAYS_OF_WORKING.md (project is in maintenance mode; all
development phases are complete).

## Python (backend/)

- **Black** (line length 100), **Ruff**, imports sorted (isort order: stdlib,
  third-party, local), type hints + docstrings on all public functions.
- Naming: `PascalCase` classes, `snake_case` functions, `UPPER_SNAKE_CASE`
  constants, `_leading_underscore` private.
- Module template: docstring → imports (3 groups) → constants →
  `logger = logging.getLogger(__name__)` → code.
- Pydantic models / dataclasses for structured data; comments explain **why**,
  not what.

## TypeScript / React (frontend/, electron/)

- React 19 + Material-UI v7 + Zustand. Match existing component patterns in
  `frontend/src/`.
- IPC always goes through `electron/preload.ts` context bridge — never expose
  Node APIs directly to the renderer.

## Tests

- Arrange-Act-Assert, descriptive test names, mock external services
  (Gateway, Playwright, filesystem).

## Commits

```text
Brief summary (imperative mood, <50 chars)

Detailed explanation:
- What changed and why

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

Commit after each logical unit; before committing run the `security-checking`
skill's quick scan. Never stage `.env` or anything under `~/.ignition-toolkit/`.

## Releases

Production builds run on **GitHub Actions only** (4 platform runners;
PyInstaller + electron-builder). Never `npm run dist:*` for production.

1. Bump version in `package.json` **and** `frontend/package.json` (keep in sync)
2. Commit to main, then `git tag vX.Y.Z && git push origin vX.Y.Z`
3. `build.yml` builds installers, publishes the GitHub Release + auto-update
   manifests

Semantic versioning: MAJOR = breaking/architecture, MINOR = features,
PATCH = fixes/docs.
