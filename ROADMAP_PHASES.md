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

- [ ] Split `clouddesigner/manager.py` (1,169 lines) into:
  - `clouddesigner/lifecycle.py` - Container start/stop/cleanup
  - `clouddesigner/auth.py` - Auto-login automation
  - `clouddesigner/paths.py` - WSL path handling
  - Effort: 12h

- [ ] Split `api/routers/stackbuilder.py` (1,084 lines) into:
  - `routers/stackbuilder/catalog.py` - Service catalog operations
  - `routers/stackbuilder/generator.py` - Compose generation
  - `routers/stackbuilder/deployment.py` - Stack deployment
  - Effort: 10h

- [ ] Split `api/routers/executions.py` (953 lines):
  - Extract scheduling to `routers/scheduling.py`
  - Effort: 8h

### 1.2 Error Handling Improvements (~15h)

- [ ] Replace generic `Exception` catches with specific types
- [ ] Add `recovery_hint` field to custom exceptions
- [ ] Include YAML line numbers in parser errors
- [ ] Add WebSocket reconnection with exponential backoff
- [ ] Effort: 15h

### 1.3 Logging Standardization (~15h)

- [ ] Replace 221 `print()` statements with proper `logging` calls
- [ ] Standardize log levels across all modules
- [ ] Remove debug `console.log` from production frontend
- [ ] Effort: 15h

---

## Phase 2: Testing Foundation (3-4 weeks, ~80h)

**Goal:** Establish comprehensive test coverage for critical paths

### 2.1 Backend Unit Tests (~40h)

- [ ] **Playbook Engine Tests** (`playbook/engine.py`)
  - Test step execution flow
  - Test error handling and recovery
  - Test timeout behavior
  - Test variable interpolation
  - Effort: 16h

- [ ] **API Endpoint Tests**
  - Test all CRUD operations
  - Test validation errors
  - Test authentication (if added)
  - Effort: 12h

- [ ] **Credential Vault Tests**
  - Test encryption/decryption
  - Test key rotation
  - Test invalid credentials handling
  - Effort: 6h

- [ ] **CloudDesigner Tests**
  - Test Docker detection logic
  - Test WSL path conversion
  - Test container lifecycle
  - Effort: 6h

### 2.2 Integration Tests (~25h)

- [ ] Full playbook execution workflows
- [ ] WebSocket message broadcasting
- [ ] Database operations with real SQLite
- [ ] Effort: 25h

### 2.3 Frontend Tests (~15h)

- [ ] Add Vitest configuration
- [ ] Test critical components (PlaybookCard, ExecutionStepper)
- [ ] Test hooks (useWebSocket, useExecution)
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

- [ ] Create `SECURITY.md`
  - Credential storage locations
  - Key rotation procedures
  - Production deployment security
  - Effort: 6h

- [ ] Create `API_GUIDE.md`
  - Endpoint examples (curl/fetch)
  - Error codes reference
  - WebSocket message format
  - Effort: 6h

### 3.2 UX Improvements (~20h)

- [ ] Add first-time user welcome modal
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

- [ ] **Playbook YAML Editor UI**
  - Monaco editor integration
  - Syntax highlighting for YAML
  - Real-time validation
  - Save/cancel with confirmation
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

- [ ] WebSocket message batching (>10 events)
- [ ] Frontend code splitting (lazy load routes)
- [ ] Screenshot compression (WebP format)
- [ ] Database query optimization
- [ ] Effort: 25h

### 5.2 Maintenance Features (~25h)

- [ ] **Database Cleanup**
  - Configurable retention policy
  - Auto-delete executions >30 days
  - Manual purge UI
  - Effort: 10h

- [ ] **Screenshot Storage Management**
  - Disk usage monitoring
  - Auto-cleanup old screenshots
  - Compression on save
  - Effort: 8h

- [ ] **Health Monitoring**
  - `/api/health/database` - DB size, execution count
  - `/api/health/storage` - Screenshot disk usage
  - Dashboard widget for system health
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
