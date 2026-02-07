# Ignition Toolbox - Comprehensive Improvement Plan

**Generated:** 2026-02-06
**Based on:** 4 parallel code review agents (Documentation, Security, Code Quality, Architecture)
**Current Version:** 1.5.2
**Total Findings:** ~100+ across all reviews

---

## Phase 1: Critical Security Fixes (Priority: URGENT)

These issues represent direct paths to remote code execution or system compromise. Must be addressed before any other work.

### 1.1 Disable or Authenticate `/ws/shell` WebSocket Endpoint
- **File:** `backend/ignition_toolkit/api/routers/websockets.py:419-578`
- **Risk:** Unauthenticated interactive bash shell accessible to any network client
- **Action:** Disable this endpoint in production builds. If kept for development, enforce API key authentication and restrict `working_dir` to an allow-list
- **Effort:** Small

### 1.2 Sandbox `exec()` in Playbook Steps
- **Files:** `backend/ignition_toolkit/playbook/steps/utility.py:114`, `backend/ignition_toolkit/playbook/executors/utility_executor.py:155`
- **Risk:** Arbitrary Python code execution with `os`, `subprocess`, `asyncio` in scope
- **Action:** Remove `os`, `subprocess`, `asyncio` from `exec_globals`. Implement restricted builtins whitelist. Add playbook integrity verification
- **Effort:** Medium

### 1.3 Remove Hardcoded WebSocket API Key Fallback
- **File:** `backend/ignition_toolkit/api/routers/websockets.py:75`
- **Risk:** Well-known default key `"dev-key-change-in-production"`
- **Action:** Read from centralized `get_settings().websocket_api_key` instead of `os.getenv()` with hardcoded fallback
- **Effort:** Small

### 1.4 Remove `--dangerously-skip-permissions` from Claude CLI
- **File:** `electron/services/claude-executor.ts:80`
- **Risk:** AI assistant can execute arbitrary system commands without user approval
- **Action:** Remove the flag. Use restricted permission model. Sanitize user input
- **Effort:** Small

### 1.5 Implement Content Security Policy (CSP)
- **File:** `electron/main.ts`
- **Risk:** XSS in renderer has unrestricted access to scripts, network, IPC bridge
- **Action:** Add CSP via `session.defaultSession.webRequest.onHeadersReceived`. Restrict `script-src` to `'self'`, `connect-src` to backend URL
- **Effort:** Small

### 1.6 Validate `shell:openPath` IPC Handler
- **File:** `electron/ipc/handlers.ts:140-142`
- **Risk:** Compromised renderer can open arbitrary files/executables
- **Action:** Validate path against allow-list of safe directories (app data, playbooks). Check path is not executable
- **Effort:** Small

---

## Phase 2: CI/CD Hardening (Priority: HIGH)

### 2.1 Add Tests to CI Pipeline
- **File:** `.github/workflows/ci.yml`
- **Action:** Add `pytest` step for backend tests (with venv setup). Add `vitest run` step for frontend tests. Add coverage thresholds
- **Impact:** The single highest-impact improvement for regression prevention
- **Effort:** Small

### 2.2 Fix Lint Enforcement
- **File:** `.github/workflows/ci.yml:78`
- **Action:** Remove `|| true` from `npm run lint` so lint failures block PRs
- **Effort:** Trivial

### 2.3 Separate Build Dependencies
- **File:** `backend/requirements.txt`
- **Action:** Move `pyinstaller==6.11.1` to `requirements-build.txt`. Update CI workflow to install from the correct file
- **Effort:** Small

---

## Phase 3: Code Cleanup (Priority: HIGH)

### 3.1 Delete Dead Code
Remove unused files that add maintenance burden:

| File | Lines | Reason |
|------|-------|--------|
| `frontend/src/pages/About.tsx` | 353 | Orphaned; About functionality is in Settings.tsx |
| `frontend/src/pages/AICredentials.tsx` | 232 | Never imported; uses raw fetch instead of API client |
| `frontend/src/components/GlobalCredentialSelector.tsx` | ~100 | Never imported externally; selector built into Layout.tsx |
| `frontend/src/components/ErrorMessage.tsx` | ~50 | Never used; codebase uses inline Alert components |
| `frontend/src/assets/react.svg` | 1 | Default Vite template asset, never referenced |
| `electron/services/auto-updater.ts` (showUpdateDialog, showInstallDialog) | ~50 | Dead functions, never called |
| `electron/services/claude-executor.ts` (fs import) | 1 | Unused import |

**Effort:** Small

### 3.2 Extract Shared Utilities - Electron
- **`isWSL()` + `openExternalUrl()`** - duplicated in `electron/main.ts` and `electron/ipc/handlers.ts`
- **Action:** Create `electron/utils/platform.ts`, export both functions, import in both files
- **Effort:** Small

### 3.3 Consolidate Type Definitions
- **`UpdateStatus`** - defined in 5 locations
- **`ScreenshotFrame`** - defined in 2 locations
- **Action:** Single canonical export from `frontend/src/types/` and `electron/types/`. Import everywhere else
- **Effort:** Small

### 3.4 Extract Shared Utilities - Frontend
- **`isElectron()`** - duplicated in 4 frontend files
- **Action:** Create `frontend/src/utils/platform.ts`, export function, import in Layout.tsx, Settings.tsx, useClaudeCode.ts, ParameterInput.tsx
- **Effort:** Small

### 3.5 Deduplicate Theme Creation
- **File:** `frontend/src/App.tsx`
- **Action:** Create theme once outside components, share between `AppContent` and `ExecutionDetailWrapper`
- **Effort:** Small

### 3.6 Use Existing Hooks in Playbooks.tsx
- **File:** `frontend/src/pages/Playbooks.tsx:178-218`
- **Action:** Replace inline localStorage functions with existing `usePlaybookOrder`, `useCategoryOrder`, `useCategoryExpanded`, `useGroupExpanded` hooks
- **Effort:** Small

---

## Phase 4: Code Quality Improvements (Priority: MEDIUM)

### 4.1 Replace `alert()` with Snackbar Notifications
- **File:** `frontend/src/pages/Playbooks.tsx` (13 occurrences) + other pages (~7 more)
- **Action:** Add Snackbar state to Playbooks page (same pattern as Executions page). Replace all `alert()` calls
- **Effort:** Medium

### 4.2 Replace `window.location.reload()` with React Query Invalidation
- **File:** `frontend/src/pages/Playbooks.tsx` (4 occurrences)
- **Action:** Use `queryClient.invalidateQueries()` for data refresh instead of full page reload
- **Effort:** Small

### 4.3 Split Playbooks.tsx (1,278 lines)
- **Action:** Extract into:
  - `PlaybookCategorySection.tsx` - categorization/grouping logic
  - `CreatePlaybookDialog.tsx` - create playbook dialog
  - `PlaybookDragHandlers.ts` - drag-end handlers (unify 3 identical handlers into 1 parameterized function)
  - `PlaybookImportExport.ts` - import/export logic
- **Effort:** Medium

### 4.4 Add TypeScript Types to API Client
- **File:** `frontend/src/api/client.ts` (~20 `any` types)
- **Action:** Define proper interfaces for StackBuilder and API Explorer responses. Replace `any` with typed interfaces
- **Effort:** Medium

### 4.5 Fix API Key Timing Attack
- **File:** `backend/ignition_toolkit/api/middleware/auth.py:114`
- **Action:** Replace `api_key != API_KEY` with `not hmac.compare_digest(api_key, API_KEY)`
- **Effort:** Trivial

### 4.6 Consolidate Config Modules
- **Files:** `backend/ignition_toolkit/config.py` + `backend/ignition_toolkit/core/config.py`
- **Action:** Merge into single `core/config.py` module. Update 7 importers of top-level config.py
- **Effort:** Medium

---

## Phase 5: Documentation Overhaul (Priority: MEDIUM)

### 5.1 Update Version Numbers (7 files)
Update all references from `1.5.0` to `1.5.2`:

| File | Lines to Update |
|------|----------------|
| `.claude/CLAUDE.md` | Lines 11, 204, 263 |
| `ARCHITECTURE.md` | Line 5 |
| `PROJECT_GOALS.md` | Lines 3, 762 |
| `docs/VERSIONING_GUIDE.md` | Lines 9-10, 60 |
| `docs/API_GUIDE.md` | Lines 283, 437 |
| `docs/PLAYBOOK_LIBRARY.md` | Line 2 |
| `docs/CANCELLATION_PATTERN.md` | Line 356 |

**Effort:** Small

### 5.2 Update ARCHITECTURE.md Backend Structure
- Router count: 6 -> 19
- Fix file references: `resolver.py` -> `parameters.py`, `executor.py` -> `step_executor.py`, `state.py` -> `state_manager.py`, `ai/assistant.py` -> `ai/client.py`, etc.
- Remove non-existent `ai.py` router reference
- Fix frontend component names: `BrowserView.tsx` -> `LiveBrowserView.tsx`, `CredentialForm.tsx` -> `AddCredentialDialog.tsx`/`EditCredentialDialog.tsx`
- Fix hooks listing
- **Effort:** Medium

### 5.3 Update PROJECT_GOALS.md Feature Statuses
- Playbook Duplication: Partial -> Done (v1.4.66)
- Playbook Editor: Partial -> Done (v1.4.68/v1.4.75)
- AI-Injectable Steps: Not Implemented -> Done (v1.4.75)
- Visual Regression: Not Implemented -> Removed from codebase
- **Effort:** Small

### 5.4 Fix ROADMAP_PHASES.md Visual Testing Section
- Mark visual regression features as "Removed" instead of "Done"
- **Effort:** Small

### 5.5 Update API_GUIDE.md Authentication Section
- Remove "no authentication required" statement
- Document API key authentication (Phase 6 feature)
- **Effort:** Small

### 5.6 Fix Broken Documentation References
Remove or update references to non-existent files:
- `RUNNING_PLAYBOOKS.md`, `CHANGELOG.md`, `VERSION`, `getting_started.md`, `PLAYBOOK_MANAGEMENT.md`, `COMPARISON.md`, `TESTING_GUIDE.md`, `ROADMAP.md`, `rebuild-frontend.sh`
- **Effort:** Small

### 5.7 Fix Repository URL Inconsistencies
- `backend/pyproject.toml:70-73` - Change `ignition-playground` to `ignition-toolbox`
- `frontend/src/pages/About.tsx` - Same fix (if not deleted in Phase 3)
- **Effort:** Trivial

### 5.8 Update Perspective Playbooks README
- **File:** `backend/playbooks/perspective/README.md`
- Change from "Coming Soon" to reflect actual state
- **Effort:** Small

---

## Phase 6: Infrastructure Improvements (Priority: LOW)

### 6.1 Add Database Migrations (Alembic)
- **Current:** `create_all()` only adds new tables, cannot alter existing ones
- **Action:** Add Alembic, create initial migration from current schema, configure auto-generation
- **Effort:** Medium

### 6.2 Unify Version Management
- **Current:** `package.json` (1.5.2), `frontend/package.json` (1.5.2), `pyproject.toml` (5.1.2)
- **Action:** Single source of truth. Either:
  - (a) Align backend to Electron version, or
  - (b) Auto-read version from `package.json` in build scripts
- **Effort:** Medium

### 6.3 Add Root-Level Setup Script
- **Action:** Add `npm run setup` that chains: `npm install`, `cd frontend && npm install`, `cd backend && python3 -m venv .venv && pip install -r requirements.txt`
- **Effort:** Small

### 6.4 Encrypt GitHub Token in Electron Store
- **File:** `electron/services/settings.ts`
- **Action:** Use `electron-store`'s `encryptionKey` option or OS keychain via `safeStorage`
- **Effort:** Medium

### 6.5 Restrict CORS for Docker Deployment
- **File:** `backend/ignition_toolkit/api/app.py:135-141`
- **Action:** When `CORS_ORIGINS` is not explicitly set AND binding to `0.0.0.0`, default to specific origins rather than `["*"]`
- **Effort:** Small

### 6.6 Docker Security Hardening
- Add non-root `USER` directive to Dockerfile
- Use Docker socket proxy instead of direct mount
- Generate random VNC password at container startup
- **Effort:** Medium

### 6.7 Fix Command Injection in WSL URL Opening
- **Files:** `electron/main.ts:36-37`, `electron/ipc/handlers.ts:31-32`
- **Action:** Use `execFile` instead of `exec` to avoid shell metacharacter interpretation
- **Effort:** Small

---

## Effort Summary

| Phase | Items | Est. Effort | Priority | Status |
|-------|-------|-------------|----------|--------|
| 1: Security Fixes | 6 | 1-2 sessions | URGENT | DONE (v1.5.3) |
| 2: CI/CD Hardening | 3 | 1 session | HIGH | DONE (v1.5.3) |
| 3: Code Cleanup | 6 | 1-2 sessions | HIGH | DONE (v1.5.3-1.5.5) |
| 4: Code Quality | 6 | 2-3 sessions | MEDIUM | DONE (v1.5.3) |
| 5: Documentation | 8 | 1-2 sessions | MEDIUM | DONE (v1.5.3-1.5.4) |
| 6: Infrastructure | 7 | 2-3 sessions | LOW | DONE (v1.5.5) |
| **Total** | **36** | **~8-13 sessions** | | **ALL COMPLETE** |

---

## Recommended Execution Order

1. **Phase 1.1-1.4** (Critical security) - Do these first, they're all small changes with massive risk reduction
2. **Phase 2.1-2.2** (CI tests + lint) - Establish the safety net before making more changes
3. **Phase 1.5-1.6** (CSP + openPath) - Complete security fixes
4. **Phase 3.1-3.6** (Dead code + dedup) - Clean foundation for quality work
5. **Phase 5.1** (Version numbers) - Quick win, 7 files
6. **Phase 4.1-4.3** (alert/reload/split) - Biggest quality impact
7. **Phase 5.2-5.8** (Full doc update) - Comprehensive documentation pass
8. **Phase 4.4-4.6** (Types/config) - Ongoing quality
9. **Phase 6** (Infrastructure) - Long-term improvements

Each phase should be a separate commit (or small set of commits) to keep changes reviewable and reversible.
