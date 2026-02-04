# Ignition Toolbox - Development Phases

> Generated: February 2026
> Total Estimated Effort: ~470 hours

---

## Phase 0: Critical Updates (1 week, ~20h)

**Goal:** Update critical dependencies and fix the CloudDesigner issue

### Tasks

- [x] **Update Electron** from v33.3.1 to v40 (latest stable) ✅ DONE (v1.4.63)
  - Update `package.json`: `"electron": "^40.0.0"`
  - Update `electron-builder` to latest compatible version
  - Test all IPC handlers still work
  - Test auto-updater functionality
  - Effort: 8h

- [x] **Fix CloudDesigner startup issue** ✅ DONE (v1.4.65)
  - Diagnose why API requests aren't reaching backend
  - Fix the root cause (CORS policy was blocking requests)
  - Add proper error reporting
  - Effort: 8h

- [x] **Fix bare `except:` clauses** (7 instances) ✅ DONE (v1.4.63)
  - `designer/detector.py`
  - `designer/platform_windows.py`
  - `designer/platform_linux.py`
  - `api/routers/websockets.py`
  - Effort: 4h

---

## Phase 1: Code Quality & Stability (2-3 weeks, ~60h)

**Goal:** Improve code quality, reduce technical debt, stabilize core functionality

### 1.1 Refactor Large Files (~30h)

- [x] Split `clouddesigner/manager.py` (1,169 lines) into: ✅ DONE (v1.4.67)
  - `clouddesigner/docker.py` - Docker/WSL detection and path utilities
  - `clouddesigner/models.py` - Data models (DockerStatus, CloudDesignerStatus)
  - `clouddesigner/manager.py` - CloudDesignerManager class only
  - Effort: 12h

- [x] Split `api/routers/stackbuilder.py` (1,084 lines) into: ✅ DONE (v1.4.67)
  - `routers/stackbuilder/models.py` - Pydantic request/response models
  - `routers/stackbuilder/installer_scripts.py` - Docker installer scripts
  - `routers/stackbuilder/main.py` - Router with all endpoints
  - Effort: 10h

- [x] Split `api/routers/executions.py` (953 lines) into: ✅ DONE (v1.4.68)
  - `routers/executions/models.py` - Pydantic request/response models
  - `routers/executions/helpers.py` - ExecutionContext, helper functions, background tasks
  - `routers/executions/main.py` - Router with all endpoints
  - Effort: 8h

### 1.2 Error Handling Improvements (~15h)

- [x] Add `recovery_hint` field to custom exceptions ✅ DONE (v1.4.68)
  - Enhanced `playbook/exceptions.py` with recovery hints
  - Added `YAMLParseError` with line/column information
  - Added `BrowserNotAvailableError`, `GatewayNotConfiguredError`
- [x] Include YAML line numbers in parser errors ✅ DONE (v1.4.68)
  - Updated `playbook/loader.py` to extract line numbers from YAML errors
- [x] WebSocket reconnection with exponential backoff ✅ Already implemented
  - `useWebSocket.ts` has backoff multiplier of 1.5x, max 30s
- [ ] Replace generic `Exception` catches with specific types (ongoing - 243 occurrences)
- [ ] Effort: 15h

### 1.3 Logging Standardization (~15h)

- [x] Audit print() statements - most are intentional ✅ DONE (v1.4.67)
  - User-facing startup messages (auth.py) - keep as print()
  - Generated script content (ignition_db_registration.py) - keep as print()
  - Docstring examples - keep as print()
  - Fixed 1 actual logging issue in auth.py
- [x] Create frontend logging utility ✅ DONE (v1.4.68)
  - Added `frontend/src/utils/logger.ts` - createLogger() with scoped prefixes
  - Debug logs disabled in production builds
  - Updated `useWebSocket.ts` to use new logger
- [ ] Continue migrating console.log to logger (91 occurrences across 19 files)
- [ ] Effort: 15h

---

## Phase 2: Testing Foundation (3-4 weeks, ~80h)

**Goal:** Establish comprehensive test coverage for critical paths

### 2.1 Backend Unit Tests (~40h)

- [x] **Playbook Engine Tests** (`playbook/engine.py`) ✅ DONE (v1.4.68)
  - 29 tests for engine initialization, timeouts, control methods
  - Test parameter validation
  - Test credential preprocessing
  - Test domain detection for resource setup
  - Effort: 16h

- [x] **Playbook Loader Tests** ✅ DONE (v1.4.68)
  - 19 tests covering YAML parsing, validation, error handling
  - Tests for YAMLParseError with line numbers
  - Tests for parameter and step validation

- [x] **API Endpoint Tests** ✅ DONE (v1.4.68)
  - 15 tests for playbook CRUD validation
  - Tests for XSS/injection prevention
  - Tests for path traversal security
  - Tests for input validation
  - Effort: 12h

- [x] **Credential Vault Tests** ✅ DONE (v1.4.68)
  - 20 tests covering encryption/decryption
  - Test persistence, edge cases, special characters
  - Test file permissions and security
  - Effort: 6h

- [x] **CloudDesigner Tests** ✅ DONE (v1.4.69)
  - 31 tests for Docker utilities (path conversion, URL translation, WSL detection)
  - Test Docker detection logic, WSL path conversion
  - Platform-specific tests with proper skip markers
  - Effort: 6h

### 2.2 Integration Tests (~25h)

- [ ] Full playbook execution workflows
- [ ] WebSocket message broadcasting
- [ ] Database operations with real SQLite
- [ ] Effort: 25h

### 2.3 Frontend Tests (~15h)

- [x] Add Vitest configuration ✅ DONE (v1.4.68)
  - vitest.config.ts with jsdom environment
  - Test setup with @testing-library/react
  - localStorage and ResizeObserver mocks
- [x] Test WelcomeDialog component (6 tests)
- [x] Test logger utility (5 tests)
- [x] Test Zustand store (16 tests)
- [x] Test ErrorBoundary component (10 tests) ✅ DONE (v1.4.69)
- [x] Test useWebSocket hook (16 tests) ✅ DONE (v1.4.69)
  - Connection lifecycle, callbacks, heartbeat, reconnect with backoff
- [x] Test PlaybookCard component (14 tests) ✅ DONE (v1.4.69)
  - Rendering, buttons, menus, dialogs, callbacks
- [x] Test ExecutionCard component (18 tests) ✅ DONE (v1.4.69)
  - Progress display, control buttons, step results, edge cases
- [ ] Test more hooks and components
- [ ] Effort: 15h

---

## Phase 3: Documentation & UX (2 weeks, ~40h)

**Goal:** Improve documentation and user experience

### 3.1 Documentation (~20h)

- [x] Create `TROUBLESHOOTING.md` ✅ DONE (v1.4.66)
  - Common errors and solutions
  - Debug mode instructions
  - Log file locations
  - Effort: 8h

- [x] Create `SECURITY.md` ✅ DONE (v1.4.68)
  - Credential storage and encryption details
  - Key rotation procedures
  - WebSocket/API security
  - Environment variables reference
  - Effort: 6h

- [x] Create `API_GUIDE.md` ✅ DONE (v1.4.68)
  - REST API endpoints with examples
  - WebSocket message format
  - Error codes reference
  - cURL and JavaScript examples
  - Effort: 6h

### 3.2 UX Improvements (~20h)

- [x] Add first-time user welcome modal ✅ DONE (v1.4.68)
  - Quick start guide for new users
  - Dismissible with localStorage persistence
- [ ] Add inline help tooltips to complex fields
- [ ] Improve error messages with recovery hints
- [ ] Add step-by-step execution timeline view
- [ ] Effort: 20h

---

## Phase 4: Feature Completion (4-6 weeks, ~120h)

**Goal:** Complete partially implemented features

### 4.1 Playbook Management (~45h)

- [x] **Playbook Duplication UI** ✅ DONE (v1.4.66)
  - Add "Duplicate" button to PlaybookCard
  - POST `/api/playbooks/duplicate` endpoint
  - Auto-rename with "(Copy)" suffix
  - Effort: 8h

- [x] **Playbook YAML Editor UI** ✅ DONE (v1.4.68)
  - Monaco editor integration with @monaco-editor/react
  - Syntax highlighting for YAML
  - Lazy-loaded to avoid bundle bloat
  - Code folding, minimap, line numbers
  - Read-only when not in debug/paused mode
  - Effort: 24h

- [ ] **Form-based Playbook Editor**
  - Step-by-step wizard
  - Parameter configuration UI
  - Drag-and-drop step reordering
  - Effort: 13h

### 4.2 Visual Testing (~40h)

- [ ] **Screenshot Comparison**
  - Capture baseline screenshots
  - Pixel-diff comparison algorithm
  - Threshold configuration
  - Effort: 20h

- [ ] **Baseline Management UI**
  - View/approve/reject baselines
  - Side-by-side comparison view
  - Ignore regions (dynamic content)
  - Effort: 20h

### 4.3 AI Integration (~35h)

- [ ] **`perspective.verify_with_ai` step type**
  - Send screenshot to Claude Vision
  - Natural language assertions
  - Confidence scoring
  - Effort: 20h

- [ ] **Clawdbot Improvements**
  - Context-aware suggestions
  - Playbook generation from description
  - Error analysis and fixes
  - Effort: 15h

---

## Phase 5: Performance & Scale (2-3 weeks, ~50h)

**Goal:** Optimize for larger deployments

### 5.1 Performance Optimizations (~25h)

- [x] WebSocket message batching (>10 events) ✅ DONE (v1.4.68)
  - Backend queues high-frequency messages (screenshots)
  - Batches sent when queue exceeds 10 or every 100ms
  - Frontend unwraps batch messages transparently
- [x] Frontend code splitting (lazy load routes) ✅ DONE (v1.4.68)
  - React.lazy() for Designer, APIExplorer, StackBuilder, ExecutionDetail
  - Reduces initial bundle load, pages load on-demand
- [x] Screenshot compression (WebP format) ✅ DONE (v1.4.68)
  - Added SCREENSHOT_FORMAT config (webp/png)
  - WebP provides ~2-3x smaller file sizes
  - Added pillow dependency
- [ ] Database query optimization
- [ ] Effort: 25h

### 5.2 Maintenance Features (~25h)

- [x] **Database Cleanup** ✅ Partially DONE (v1.4.68)
  - POST /health/cleanup endpoint with dry_run support
  - Configurable older_than_days parameter
  - [ ] Auto-delete scheduled job (APScheduler)
  - [ ] Manual purge UI in frontend
  - Effort: 10h

- [x] **Screenshot Storage Management** ✅ Partially DONE (v1.4.68)
  - GET /health/storage endpoint for disk usage monitoring
  - Cleanup integrated with /health/cleanup endpoint
  - [x] Compression on save (WebP format)
  - [ ] Dashboard widget in frontend
  - Effort: 8h

- [x] **Health Monitoring** ✅ DONE (v1.4.68)
  - `/api/health/database` - DB size, execution count, status breakdown
  - `/api/health/storage` - Screenshot disk usage, file counts
  - `/api/health/cleanup` - Cleanup old data with dry_run support
  - 10 tests for health endpoints
  - Effort: 7h

---

## Phase 6: Advanced Features (6+ weeks, ~100h)

**Goal:** Enterprise-ready features

### 6.1 Parallel Execution (~40h)

- [ ] Run multiple playbooks concurrently
- [ ] Parallel steps within playbooks
- [ ] Execution queue management
- [ ] Resource limiting
- [ ] Effort: 40h

### 6.2 Multi-User Support (~40h)

- [ ] API key authentication
- [ ] Role-based access control (RBAC)
- [ ] User-scoped credentials
- [ ] Audit logging
- [ ] Effort: 40h

### 6.3 Reporting & Analytics (~20h)

- [ ] Execution history reports
- [ ] Pass/fail trends over time
- [ ] Export to PDF/CSV
- [ ] Scheduled report emails
- [ ] Effort: 20h

---

## Summary

| Phase | Focus | Effort | Duration |
|-------|-------|--------|----------|
| 0 | Critical Updates | 20h | 1 week |
| 1 | Code Quality | 60h | 2-3 weeks |
| 2 | Testing | 80h | 3-4 weeks |
| 3 | Docs & UX | 40h | 2 weeks |
| 4 | Features | 120h | 4-6 weeks |
| 5 | Performance | 50h | 2-3 weeks |
| 6 | Advanced | 100h | 6+ weeks |
| **Total** | | **470h** | **~20-25 weeks** |

---

## Recommended Priority

1. **Phase 0** - Do immediately (Electron update is security-critical)
2. **Phase 1** - Start next (code quality enables everything else)
3. **Phase 2** - Essential for confidence in changes
4. **Phase 3** - Quick wins for user experience
5. **Phase 4-6** - Feature work based on user demand

---

## Notes

- Phases can overlap (e.g., start Phase 2 while finishing Phase 1)
- Effort estimates assume familiarity with codebase
- Each phase should end with a version release
- Consider hiring/contracting for Phase 6 if needed
