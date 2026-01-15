# V3.0.0 REFACTOR - MASTER PLAN

**Priority:** 🚨 CRITICAL - Must complete 100%
**Status:** ✅ APPROVED - In Progress
**Start Date:** 2025-10-27
**Target Completion:** 2025-11-17 (3 weeks)
**Version:** v2.4.0 → v3.0.0

---

## EXECUTIVE SUMMARY

Complete architectural refactor to solve recurring server startup issues and establish long-term maintainability.

**Problems Being Solved:**
1. Server fails to start from different directories (hardcoded paths)
2. Zombie processes accumulate
3. No reliable process management
4. Code too complex (2377-line app.py)
5. Step types not extensible
6. Missing dependency locking

**Solutions:**
1. Dynamic path resolution
2. Docker Compose with health checks
3. Makefile for unified commands
4. Split app.py into modules (<300 lines each)
5. Plugin architecture for step types
6. Locked dependencies + comprehensive tests

---

## ARCHITECTURAL DECISIONS

### AD-001: Docker Compose (REVERSES ADR-003)
**Decision:** Use Docker Compose for development & production
**Rationale:** Solves startup issues, ensures consistency, simplifies deployment
**Profiles:** dev (hot reload), prod (optimized), postgres (optional)

### AD-002: PostgreSQL Optional
**Decision:** SQLite default, PostgreSQL via --profile postgres
**Rationale:** Maintains simplicity while offering production option

### AD-003: Plugin Architecture
**Decision:** Entry point-based plugins for all step types
**Rationale:** Users can add custom steps without modifying core

### AD-004: API Versioning
**Decision:** URL path versioning (/api/v1/*)
**Rationale:** Future-proof, backward compatible

### AD-005: Version 3.0.0
**Decision:** Major version bump for major refactor
**Rationale:** Signals breaking changes, clear for users

---

## PHASES OVERVIEW

| Phase | Days | Description | Status |
|-------|------|-------------|--------|
| 1 | 1-2 | Foundation & Docker | ⏳ In Progress |
| 2 | 3-7 | Code Architecture | ⏸️ Pending |
| 3 | 8-9 | Config & Logging | ⏸️ Pending |
| 4 | 10-14 | Plugin Architecture | ⏸️ Pending |
| 5 | 15-17 | Testing | ⏸️ Pending |
| 6 | 18 | API Versioning | ⏸️ Pending |
| 7 | 19-20 | Documentation | ⏸️ Pending |
| 8 | 21 | Security & Performance | ⏸️ Pending |
| 9 | 22 | Final Verification | ⏸️ Pending |

---

## PHASE 1: FOUNDATION & DOCKER (Days 1-2)

### 1.1 Context Preservation ✅
- [x] Create .refactor/ directory
- [ ] Create MASTER_PLAN.md
- [ ] Create PROGRESS.md
- [ ] Create DECISIONS.md
- [ ] Create ISSUES.md
- [ ] Create ROLLBACK.md

### 1.2 Fix Critical Paths
**Files to Create:**
- `ignition_toolkit/core/paths.py` - Dynamic path resolution
- `.env` (from .env.example)
- `requirements.txt` (pip-compile from pyproject.toml)

**Files to Modify:**
- `ignition_toolkit/core/config.py` - Use paths.py
- `ignition_toolkit/api/app.py` - Use paths.py

**Verification:**
```bash
# Must work from all these directories:
cd /tmp && python3 /git/ignition-playground/venv/bin/uvicorn ignition_toolkit.api.app:app
cd /git/ignition-playground && make start
cd /git/ignition-playground/frontend && ../venv/bin/uvicorn ignition_toolkit.api.app:app
```

### 1.3 Docker Compose
**Files to Create:**
- `docker-compose.yml` (3 profiles: default, dev, postgres)
- `Dockerfile` (multi-stage)
- `.dockerignore`
- `docker-entrypoint.sh`

**Profiles:**
```bash
docker-compose up                      # Production: backend only (SQLite)
docker-compose --profile dev up        # Dev: backend + frontend-dev (hot reload)
docker-compose --profile postgres up   # Production: backend + PostgreSQL
```

### 1.4 Makefile
**Commands Required:**
```makefile
install, start, start-docker, stop, restart, logs
test, test-fast, lint, format, clean, build, health
docker-build, docker-push, migrate, backup
```

---

## PHASE 2: CODE ARCHITECTURE (Days 3-7)

### Goal: Split app.py (2377 lines) → 10 files (<300 lines each)

**New Structure:**
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

**Daily Commits:**
- Day 3: Extract playbook & execution routers
- Day 4: Extract credential, debug, AI routers
- Day 5: Extract WebSocket router
- Day 6: Extract execution manager & playbook services
- Day 7: Extract Claude Code service & cleanup service, middleware

---

## PHASE 3: CONFIG & LOGGING (Days 8-9)

### 3.1 Complete config.py
- Add all 40+ environment variables
- Add Pydantic validators
- Security checks (no default keys in production)
- Multi-environment support

### 3.2 Logging System
- Create `ignition_toolkit/core/logging.py`
- Rotating file handlers (50MB, 10 backups)
- Separate error logs
- JSON logs for production
- Remove ALL print() statements

### 3.3 Remove Hardcoded Values
- Search codebase for remaining hardcoded paths/keys/URLs
- Replace with config.py references

---

## PHASE 4: PLUGIN ARCHITECTURE (Days 10-14)

### 4.1 Plugin Base Class (Day 10)
**File:** `ignition_toolkit/playbook/step_plugin.py`
```python
class StepPlugin(ABC):
    @property
    @abstractmethod
    def step_type(self) -> str: pass

    @abstractmethod
    async def execute(self, parameters, **kwargs) -> Dict: pass
```

### 4.2 Migrate Step Types (Days 11-14)

**Gateway Steps** (8 total):
- gateway.login, logout, restart, wait_for_ready, health_check, list_projects, backup, restore

**Perspective Steps** (5 total):
- perspective.navigate, click, fill, verify, screenshot

**Utility Steps** (8 total):
- utility.wait, log, set_variable
- playbook.run (nested)
- ai.assist, generate, validate
- debug.breakpoint

**Registry:**
- Entry points in pyproject.toml
- Plugin loader in step_executor.py
- Deprecation warnings for old format

### 4.3 Migration Tool
**Command:** `ignition-toolkit migrate-playbooks`
- Auto-convert old format → new format
- Create backups
- Report changes

---

## PHASE 5: TESTING (Days 15-17)

### Test Files to Create:
```
tests/
├── test_startup.py (lifespan, validators)
├── test_paths.py (dynamic resolution)
├── test_config.py (environment loading)
├── test_logging.py (rotation, formatting)
├── test_websocket.py (auth, messages, cleanup)
├── test_plugins.py (all 21 plugins)
├── integration/
│   ├── test_full_execution.py
│   ├── test_docker_startup.py
│   └── test_process_cleanup.py
└── test_performance.py (memory leaks, concurrency)
```

**Target:** 80%+ code coverage

---

## PHASE 6: API VERSIONING (Day 18)

### Move to Versioned API
- All endpoints: `/api/*` → `/api/v1/*`
- Add redirects for backward compatibility
- Update frontend to use `/api/v1/`
- Document API changelog and deprecation policy

---

## PHASE 7: DOCUMENTATION (Days 19-20)

### Operational Runbooks:
- deployment.md, troubleshooting.md, backup_restore.md, monitoring.md, docker.md

### Developer Guides:
- contributing.md, adding_step_types.md, testing.md, architecture.md

### ADRs:
- ADR-012: Process Management (Docker Compose)
- ADR-013: Lock Files
- ADR-014: Plugin Architecture
- ADR-015: Centralized Config
- ADR-016: API Versioning
- ADR-003-UPDATED: Docker Decision Reversal

### Update Main Docs:
- README.md, CHANGELOG.md, ARCHITECTURE.md

---

## PHASE 8: SECURITY & PERFORMANCE (Day 21)

### Security:
- Replace API key auth with JWT
- Add rate limiting
- Add security headers
- Audit default values
- Run bandit security scan

### Performance:
- Convert blocking I/O to async
- Add playbook metadata cache
- Add connection pooling
- Background cleanup task

### Monitoring:
- Prometheus metrics endpoint
- Enhanced health check
- Error tracking

---

## PHASE 9: FINAL VERIFICATION (Day 22)

### Acceptance Criteria:
- [ ] Server starts from any directory
- [ ] Docker Compose works (3 profiles)
- [ ] All Makefile commands work
- [ ] No zombie processes after shutdown
- [ ] No hardcoded paths in codebase
- [ ] All 21 plugins working
- [ ] All tests passing (80%+ coverage)
- [ ] No memory leaks (24hr test)
- [ ] API versioned to v1
- [ ] Documentation complete
- [ ] Security audit passed
- [ ] Performance benchmarks met
- [ ] Frontend UI/UX unchanged
- [ ] All existing playbooks work
- [ ] Migration tool works

### Regression Testing:
- All example playbooks
- All UI features
- WebSocket connections
- Claude Code integration
- Browser automation
- Nested playbooks
- Debug mode
- AI assistance

---

## VERSION UPDATES

**Files to Update:**
- VERSION
- pyproject.toml
- package.json
- ignition_toolkit/__init__.py
- .claude/CLAUDE.md

**Git Tags:**
```bash
git tag v2.4.0-final-stable  # Before refactor
git tag v3.0.0              # After refactor
git push --tags
```

---

## ROLLBACK PLAN

**Revert Points:**
- v2.4.0-final-stable: Clean state before refactor
- After Phase 1: Docker + paths working
- After Phase 2: Code split working
- After Phase 4: Plugins working
- After Phase 5: Tests passing

**Rollback Command:**
```bash
git checkout v2.4.0-final-stable
```

---

## CRITICAL SUCCESS FACTORS

1. ✅ **Context Preservation:** Update PROGRESS.md after EVERY session
2. ✅ **No Regressions:** Test existing functionality after EVERY change
3. ✅ **Incremental:** Commit working code frequently
4. ✅ **Reversible:** Can rollback to v2.4.0 at any point
5. ✅ **Test First:** Write tests BEFORE refactoring code
6. ✅ **Document:** Document decisions immediately

---

## DEPENDENCIES

**Python:**
- pip-tools (for pip-compile)
- docker-compose
- pytest, pytest-cov

**Node.js:**
- Keep existing (already locked)

**System:**
- Docker & Docker Compose
- Make

---

## COMMUNICATION

**Progress Updates:** See `.refactor/PROGRESS.md`
**Decisions Log:** See `.refactor/DECISIONS.md`
**Issues/Blockers:** See `.refactor/ISSUES.md`
**Rollback Guide:** See `.refactor/ROLLBACK.md`

---

**Last Updated:** 2025-10-27
**Status:** Phase 1 in progress
**Next Milestone:** Complete Docker Compose setup
