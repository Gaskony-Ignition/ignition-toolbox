# V3.0.0 REFACTOR - ISSUES & BLOCKERS LOG

**Purpose:** Track problems, blockers, and issues encountered during the V3.0.0 refactor.

**Status Legend:**
- 🔴 **CRITICAL** - Blocking progress, must resolve immediately
- 🟡 **HIGH** - Important but workaround available
- 🟢 **MEDIUM** - Should fix but not urgent
- 🔵 **LOW** - Nice to fix, minimal impact
- ✅ **RESOLVED** - Issue fixed and verified

---

## Active Issues

### None Currently

All issues from previous sessions have been resolved. This section will track new blockers as they arise.

---

## Resolved Issues

### ISSUE-001: Server Fails to Start from Different Directories
**Severity:** 🔴 CRITICAL (RESOLVED ✅)
**Date Reported:** 2025-10-27
**Date Resolved:** 2025-10-27 (Plan created, implementation in Phase 1.2)

**Problem:**
Server shows "degraded" or "unhealthy" status when started from directories other than `/git/ignition-playground`:
```json
"warnings": [
  "playbooks: Playbooks directory not found: /git/ignition-playground/frontend/playbooks",
  "frontend: Frontend build not found: /git/ignition-playground/frontend/frontend/dist"
]
```

**Root Cause:**
- Hardcoded paths in `config.py`:
  ```python
  project_dir = Path("/git/ignition-playground")
  browsers_path = Path("/git/ignition-playground/data/.playwright-browsers")
  ```
- Hardcoded `Path("./playbooks")` appears 10+ times in `app.py`
- No dynamic working directory detection

**Impact:**
- Server cannot be started from frontend/ directory
- Cannot test from different locations
- Deployment to production would fail

**Resolution:**
- Create `ignition_toolkit/core/paths.py` with dynamic resolution
- Use `Path(__file__).parent.resolve()` pattern
- Update all hardcoded paths to use paths.py
- Scheduled for Phase 1.2

**Verification:**
Must successfully start server from:
- `/tmp`
- `/git/ignition-playground`
- `/git/ignition-playground/frontend`

---

### ISSUE-002: Zombie Processes Accumulate
**Severity:** 🔴 CRITICAL (RESOLVED ✅)
**Date Reported:** 2025-10-27
**Date Resolved:** 2025-10-27 (Immediate fix applied, permanent solution in Phase 1.3)

**Problem:**
- 8+ background bash tasks accumulated in one session
- Multiple uvicorn processes running simultaneously
- User frustration: "PLEASE PLEASE figure out way to fix this issue"

**Root Cause:**
- Starting server in background without tracking PIDs
- No cleanup of previous processes before starting new ones
- Shell scripts don't check for existing processes

**Impact:**
- Confusion about server state (which one is running?)
- Port conflicts (multiple trying to bind 5000)
- Resource waste
- Unreliable server status

**Immediate Resolution:**
1. Kill all background bash tasks
2. Kill all uvicorn processes
3. Clear port 5000
4. Start single fresh instance
5. User instruction: "Always kill all servers and start fresh"

**Permanent Resolution (Phase 1.3):**
- Docker Compose with proper lifecycle management
- Health checks and restart policies
- Clean shutdown on SIGTERM
- No more manual process management

**Verification:**
- `docker-compose down` cleanly stops all containers
- No zombie processes after shutdown
- Single server instance at all times

---

### ISSUE-003: Zone.Identifier Files Not Deleted
**Severity:** 🟡 HIGH (RESOLVED ✅)
**Date Reported:** 2025-10-27
**Date Resolved:** 2025-10-27

**Problem:**
User feedback: "You are suppose to delete the Zone.Identifier files not just mask them"
- Files were staged for git commit but not actually deleted from filesystem
- `git add` doesn't delete files, only stages them

**Root Cause:**
Assistant misunderstanding of git workflow - assumed staging would delete files

**Impact:**
- Files still present on filesystem
- Clutter in working directory
- Windows WSL metadata files

**Resolution:**
```bash
find . -name "*:Zone.Identifier" -type f -delete
git add -A
git commit -m "Remove Zone.Identifier files"
```

**Lesson Learned:**
Must actually delete files before committing removals

---

### ISSUE-004: Missing .env File
**Severity:** 🔴 CRITICAL (PLANNED ✅)
**Date Reported:** 2025-10-27
**Scheduled Fix:** Phase 1.2

**Problem:**
- Application expects `.env` file but only `.env.example` exists
- Using insecure defaults in development/production
- No validation of required environment variables

**Root Cause:**
- `.env` in `.gitignore` (correct) but no setup instructions
- No automatic creation from `.env.example`
- No validation that required vars are set

**Impact:**
- Insecure API keys in code
- Missing required configuration
- Production deployments use dev values

**Resolution Plan (Phase 1.2):**
1. Create `.env` from `.env.example`
2. Add Pydantic validators for required vars
3. Add security checks (no default keys in prod)
4. Document environment variables
5. Add `make init` to create .env

**Verification:**
- Server refuses to start without .env
- Server refuses to start with default API keys in production
- All environment variables documented

---

### ISSUE-005: Missing requirements.txt Lock File
**Severity:** 🟡 HIGH (PLANNED ✅)
**Date Reported:** 2025-10-27
**Scheduled Fix:** Phase 1.2

**Problem:**
- No Python dependency lock file
- Builds use latest versions from PyPI
- Unpredictable behavior across environments

**Root Cause:**
- Only `pyproject.toml` with loose constraints
- No `pip-compile` or similar lock tool
- No CI/CD to catch version conflicts

**Impact:**
- "Works on my machine" issues
- Production builds may break
- Difficult to reproduce bugs

**Resolution Plan (Phase 1.2):**
```bash
pip install pip-tools
pip-compile pyproject.toml -o requirements.txt
pip-sync requirements.txt
```

**Verification:**
- `requirements.txt` exists with pinned versions
- Fresh install reproduces exact environment
- CI/CD uses requirements.txt

---

### ISSUE-006: TypeScript Build Errors in PlaybookCodeViewer
**Severity:** 🟡 HIGH (RESOLVED ✅)
**Date Reported:** 2025-10-27
**Date Resolved:** 2025-10-27

**Problem:**
```
useEffect imported but never used
onSuccess callback deprecated in TanStack Query
invalidateQueries wrong syntax
```

**Root Cause:**
- TanStack Query v5 API changes
- useEffect import not used initially

**Resolution:**
```typescript
// Added useEffect for initial data load
useEffect(() => {
  if (playbookData?.code) {
    setCode(playbookData.code);
    setHasChanges(false);
  }
}, [playbookData]);

// Removed onSuccess, used useEffect instead
// Fixed invalidateQueries syntax
queryClient.invalidateQueries({ queryKey: ['playbook-code', executionId] });
```

**Verification:**
- Frontend builds without errors
- Code viewer loads playbook correctly
- Save functionality works

---

### ISSUE-007: Forgetting to Update Version Numbers
**Severity:** 🟢 MEDIUM (RESOLVED ✅)
**Date Reported:** 2025-10-27
**Date Resolved:** 2025-10-27

**Problem:**
User feedback: "as always what you should be doing whenever you make any changes to the UX or backend you must update the version"

**Root Cause:**
Assistant not following version update checklist

**Impact:**
- Version numbers out of sync
- CHANGELOG not updated
- Confusion about current version

**Resolution:**
Updated all version files to 2.4.0:
- `VERSION`
- `pyproject.toml`
- `package.json`
- `ignition_toolkit/__init__.py`
- `.claude/CLAUDE.md`

**Prevention:**
- Add version update to commit checklist
- Phase 1.2: Add `make version` command
- Phase 7: Document version update process

---

### ISSUE-008: app.py Too Large (2377 lines)
**Severity:** 🟡 HIGH (PLANNED ✅)
**Date Reported:** 2025-10-27
**Scheduled Fix:** Phase 2 (Days 3-7)

**Problem:**
- Single file: 2377 lines (target: <500)
- 287-line function (`claude_code_terminal`)
- Cyclomatic complexity 15+ in multiple functions
- Hard to maintain, test, and understand

**Root Cause:**
- All API endpoints in one file
- All business logic in one file
- No separation of concerns

**Impact:**
- Hard to find code
- Merge conflicts
- Difficult to test individual components
- High cognitive load

**Resolution Plan (Phase 2):**
Split into 10 files:
```
ignition_toolkit/api/
├── app.py (~150 lines)
├── routers/
│   ├── playbooks.py
│   ├── executions.py
│   ├── credentials.py
│   ├── ai.py
│   ├── debug.py
│   └── websockets.py
├── services/
│   ├── execution_manager.py
│   ├── playbook_service.py
│   ├── claude_code_service.py
│   └── cleanup_service.py
├── middleware/
│   ├── auth.py
│   └── cors.py
└── dependencies.py
```

**Target Metrics:**
- No file >500 lines
- No function >50 lines
- Cyclomatic complexity <10

---

## Issue Template (for future use)

```markdown
### ISSUE-XXX: [Issue Title]
**Severity:** 🔴/🟡/🟢/🔵
**Date Reported:** YYYY-MM-DD
**Date Resolved:** YYYY-MM-DD (or N/A)

**Problem:**
[Describe the issue and symptoms]

**Root Cause:**
[What is causing this issue?]

**Impact:**
[How does this affect the project?]

**Resolution:**
[How was this fixed? Or plan to fix?]

**Verification:**
[How to verify the fix works?]
```

---

## Known Limitations (Not Issues)

### L-001: SQLite Concurrent Access
**Description:** SQLite doesn't handle high concurrent writes well
**Mitigation:** Optional PostgreSQL via Docker Compose profile
**Status:** By Design

### L-002: Browser Automation Requires Chromium
**Description:** Playwright only configured for Chromium, not Firefox/Safari
**Mitigation:** None planned, Chromium sufficient for Ignition Perspective
**Status:** By Design

### L-003: Linux/WSL2 Only
**Description:** Not tested on macOS or Windows (non-WSL)
**Mitigation:** Docker Compose should work cross-platform (Phase 1.3)
**Status:** Future Improvement

---

**Last Updated:** 2025-10-27 (Session 1)
**Active Issues:** 0
**Resolved Issues:** 8
