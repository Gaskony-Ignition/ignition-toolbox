# Refactoring Plan - Ignition Automation Toolkit

**Version:** 3.17.0 → 4.0.0
**Created:** 2025-10-29
**Goal:** Systematic code simplification and architectural improvements

---

## Executive Summary

Based on comprehensive reviews by tech-lead-architect and code-reviewer-simplifier agents, this plan addresses:

- **175+ lines of code duplication** in executions.py
- **Global state management anti-pattern** affecting testability
- **906-line router file** mixing concerns (target: <500)
- **242-line function** exceeding complexity targets (target: <50)

**Projected Impact:**
- Reduce executions.py: 906 → ~650 lines (-28%)
- Eliminate duplication: 175 → ~20 lines (-88%)
- Improve testability: 3-5x through isolation
- Reduce max cyclomatic complexity: 18 → <10 (-44%)

---

## Phase 1: Quick Wins (Week 1) - IN PROGRESS

**Status:** Starting implementation
**Risk:** LOW (additive changes only)
**Expected Savings:** ~165 lines of duplication

### 1.1 Extract StepResultResponse Conversion Helper

**Issue:** List comprehension repeated 4 times (lines 366-376, 413-422, 456-465, 495-504)

**Files Changed:**
- `ignition_toolkit/api/routers/executions.py`

**Implementation:**
```python
def _convert_step_results_to_response(
    step_results: list[StepResult]
) -> list[StepResultResponse]:
    """
    Convert internal StepResult objects to API response format

    Args:
        step_results: List of StepResult objects

    Returns:
        List of StepResultResponse objects for API
    """
    return [
        StepResultResponse(
            step_id=result.step_id,
            step_name=result.step_name,
            status=result.status.value if hasattr(result.status, 'value') else result.status,
            error=result.error,
            started_at=result.started_at,
            completed_at=result.completed_at,
        )
        for result in step_results
    ]
```

**Locations to Replace:**
- Line 366-376 (get_execution_status - active engine)
- Line 413-422 (get_execution_status - database)
- Line 456-465 (list_executions - active)
- Line 495-504 (list_executions - database)

**Savings:** 40 lines

---

### 1.2 Extract ExecutionStatusResponse Factory

**Issue:** ExecutionStatusResponse construction repeated 4 times

**Implementation:**
```python
def _build_execution_status_response(
    execution_id: str,
    execution_state: ExecutionState | None = None,
    execution_model: ExecutionModel | None = None,
    engine: PlaybookEngine | None = None,
) -> ExecutionStatusResponse:
    """
    Build ExecutionStatusResponse from either live engine or database model

    Args:
        execution_id: Execution UUID
        execution_state: Live execution state from engine
        execution_model: Database execution model
        engine: Optional PlaybookEngine for live executions

    Returns:
        ExecutionStatusResponse for API

    Raises:
        ValueError: If neither execution_state nor execution_model provided
    """
    if execution_state:
        # Live execution from engine
        step_results = _convert_step_results_to_response(execution_state.step_results)
        return ExecutionStatusResponse(
            execution_id=execution_id,
            playbook_name=execution_state.playbook_name,
            status=execution_state.status.value,
            started_at=execution_state.started_at,
            completed_at=execution_state.completed_at,
            current_step_index=execution_state.current_step_index,
            total_steps=engine.get_total_steps() if engine else 0,
            error=execution_state.error,
            debug_mode=engine.state_manager.is_debug_mode_enabled() if engine else False,
            step_results=step_results,
        )
    elif execution_model:
        # Historical execution from database
        step_results = _convert_step_results_to_response(execution_model.step_results)
        return ExecutionStatusResponse(
            execution_id=execution_model.execution_id,
            playbook_name=execution_model.playbook_name,
            status=execution_model.status,
            started_at=execution_model.started_at,
            completed_at=execution_model.completed_at,
            current_step_index=len(step_results),
            total_steps=len(step_results),
            error=execution_model.error_message,
            debug_mode=execution_model.execution_metadata.get("debug_mode", False) if execution_model.execution_metadata else False,
            step_results=step_results,
        )
    else:
        raise ValueError("Must provide either execution_state or execution_model")
```

**Prerequisite:** Add `get_total_steps()` method to PlaybookEngine

**Savings:** 80 lines

---

### 1.3 Create get_engine_or_404 Dependency

**Issue:** `if execution_id not in active_engines: raise HTTPException...` repeated 15 times

**Implementation:**
```python
from fastapi import Depends, Path as PathParam

async def get_engine_or_404(
    execution_id: str = PathParam(..., description="Execution UUID")
) -> PlaybookEngine:
    """
    FastAPI dependency to retrieve active engine or raise 404

    Args:
        execution_id: Execution UUID from path parameter

    Returns:
        Active PlaybookEngine

    Raises:
        HTTPException: 404 if execution not found
    """
    active_engines = get_active_engines()
    engine = active_engines.get(execution_id)

    if engine is None:
        raise HTTPException(
            status_code=404,
            detail=f"Execution {execution_id} not found"
        )

    return engine
```

**Usage Example:**
```python
# BEFORE:
@router.post("/{execution_id}/pause")
async def pause_execution(execution_id: str):
    active_engines = get_active_engines()

    if execution_id not in active_engines:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")

    engine = active_engines[execution_id]
    engine.pause()
    return {"message": "Execution paused"}

# AFTER:
@router.post("/{execution_id}/pause")
async def pause_execution(engine: PlaybookEngine = Depends(get_engine_or_404)):
    engine.pause()
    return {"message": "Execution paused"}
```

**Endpoints to Update (15 total):**
- pause_execution (line ~552)
- resume_execution (line ~572)
- skip_step (line ~592)
- skip_backward (line ~612)
- enable_debug (line ~632)
- disable_debug (line ~652)
- get_current_screenshot (line ~672)
- get_execution_logs (line ~692)
- get_debug_context (line ~712)
- send_ai_message (line ~782)
- click_in_browser (line ~857)
- And 4 more...

**Savings:** 45 lines

---

### 1.4 Extract Constants for Magic Numbers

**Issue:** Hardcoded values scattered throughout

**Implementation:**
```python
# Add to top of executions.py after imports:

# Execution Configuration Constants
DEFAULT_EXECUTION_TIMEOUT_SECONDS = 3600  # 1 hour
DEFAULT_EXECUTION_LIST_LIMIT = 50
DEFAULT_TTL_MINUTES = 60

# Screenshot Configuration
DEFAULT_SCREENSHOT_WAIT_MS = 500
```

**Locations to Replace:**
- Line 324: `await asyncio.sleep(3600)` → `await asyncio.sleep(DEFAULT_EXECUTION_TIMEOUT_SECONDS)`
- Line 353: `limit: int = 50` → `limit: int = DEFAULT_EXECUTION_LIST_LIMIT`
- Other magic numbers as identified

**Savings:** 5 lines (improved maintainability)

---

### 1.5 Create ExecutionContext Dataclass

**Issue:** 4 separate getter functions for global state

**Implementation:**
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ExecutionContext:
    """Encapsulates all execution-related global state"""

    active_engines: dict[str, PlaybookEngine]
    active_tasks: dict[str, asyncio.Task]
    completion_times: dict[str, datetime]
    ttl_minutes: int

    def get_engine(self, execution_id: str) -> PlaybookEngine | None:
        """Get engine by execution ID"""
        return self.active_engines.get(execution_id)

    def add_engine(self, execution_id: str, engine: PlaybookEngine, task: asyncio.Task) -> None:
        """Register new execution"""
        self.active_engines[execution_id] = engine
        self.active_tasks[execution_id] = task

    def remove_engine(self, execution_id: str) -> None:
        """Remove completed execution"""
        self.active_engines.pop(execution_id, None)
        self.active_tasks.pop(execution_id, None)
        self.completion_times[execution_id] = datetime.now()

    def is_expired(self, execution_id: str) -> bool:
        """Check if execution has exceeded TTL"""
        if completion_time := self.completion_times.get(execution_id):
            elapsed_minutes = (datetime.now() - completion_time).total_seconds() / 60
            return elapsed_minutes > self.ttl_minutes
        return False

def get_execution_context() -> ExecutionContext:
    """Get execution context from app state"""
    from ignition_toolkit.api.app import (
        active_engines,
        active_tasks,
        engine_completion_times,
        EXECUTION_TTL_MINUTES,
    )
    return ExecutionContext(
        active_engines=active_engines,
        active_tasks=active_tasks,
        completion_times=engine_completion_times,
        ttl_minutes=EXECUTION_TTL_MINUTES,
    )
```

**Replaces 4 Functions:**
- `get_active_engines()`
- `get_active_tasks()`
- `get_engine_completion_times()`
- `get_execution_ttl_minutes()`

**Savings:** 15 lines

---

### Phase 1 Summary

**Total Changes:**
- 5 new helper functions/classes
- 4 old functions removed
- 15+ endpoints simplified
- ~165 lines eliminated

**Testing Strategy:**
```python
# tests/test_execution_helpers.py
def test_convert_step_results_to_response()
def test_build_execution_status_response_from_engine()
def test_build_execution_status_response_from_database()
def test_execution_context_lifecycle()
def test_get_engine_or_404_success()
def test_get_engine_or_404_not_found()
```

**Migration Steps:**
1. Add helper functions (keep old code)
2. Write unit tests for helpers
3. Update one endpoint at a time
4. Run integration tests after each change
5. Remove old code once all endpoints updated

---

## Phase 2: Service Layer Extraction (Week 2-3)

**Status:** Planned
**Risk:** MEDIUM (behavior changes require extensive testing)
**Expected Impact:** Reduce executions.py to ~400 lines

### 2.1 Add get_total_steps() to PlaybookEngine

**File:** `ignition_toolkit/playbook/engine.py`

**Implementation:**
```python
def get_total_steps(self) -> int:
    """
    Get total number of steps in current playbook

    Returns:
        Number of steps, or 0 if no playbook loaded
    """
    return len(self._current_playbook.steps) if self._current_playbook else 0
```

**Usage:** Required by ExecutionStatusResponse factory (Phase 1.2)

---

### 2.2 Extract ExecutionParameterService

**File:** Create `ignition_toolkit/api/services/execution_parameters.py`

**Purpose:** Handle credential auto-fill and parameter resolution

**Extracts from:** Lines 146-184 in executions.py

**Interface:**
```python
class ExecutionParameterService:
    """Handles parameter resolution and credential auto-fill"""

    def __init__(self, vault: CredentialVault):
        self.vault = vault

    def resolve_parameters(
        self,
        playbook: Playbook,
        request_parameters: dict[str, str],
        credential_name: str | None,
    ) -> tuple[str | None, dict[str, str]]:
        """
        Resolve execution parameters with credential auto-fill

        Args:
            playbook: Loaded playbook
            request_parameters: User-provided parameters
            credential_name: Optional credential to auto-fill

        Returns:
            Tuple of (gateway_url, resolved_parameters)
        """
        # Implementation moves from start_execution
```

**Savings:** 38 lines from start_execution

---

### 2.3 Extract Screenshot Helpers

**File:** Create `ignition_toolkit/api/services/screenshot_service.py`

**Purpose:** Centralize screenshot path extraction and deletion

**Interface:**
```python
class ScreenshotService:
    """Manages screenshot file operations"""

    @staticmethod
    def extract_paths(step_results: list[StepResultModel]) -> list[Path]:
        """Extract all screenshot paths from step results"""
        # Moves from delete_execution lines 750-767

    @staticmethod
    def delete_files(screenshot_paths: list[Path]) -> int:
        """Delete screenshot files, return count deleted"""
        # Moves from delete_execution lines 790-800
```

**Savings:** 30 lines from delete_execution

---

### 2.4 Break Down start_execution (242 → ~80 lines)

**Strategy:** Extract into 5 helper functions

**New Structure:**
```python
@router.post("", response_model=ExecutionResponse)
async def start_execution(
    request: ExecutionRequest,
    background_tasks: BackgroundTasks,
):
    """Start playbook execution"""
    # 1. Validate and load playbook (~10 lines)
    playbook_path, playbook = await _validate_and_load_playbook(request.playbook_path)

    # 2. Resolve parameters (~5 lines)
    param_service = ExecutionParameterService(get_vault())
    gateway_url, parameters = param_service.resolve_parameters(
        playbook, request.parameters, request.credential_name
    )

    # 3. Create execution (~10 lines)
    execution_id = str(uuid.uuid4())
    engine = await _create_execution_engine(
        gateway_url, execution_id, request.debug_mode
    )

    # 4. Start execution task (~20 lines)
    ctx = get_execution_context()
    task = asyncio.create_task(
        _run_execution_workflow(
            engine, playbook, parameters, playbook_path,
            execution_id, gateway_url, ctx
        )
    )
    ctx.add_engine(execution_id, engine, task)

    # 5. Schedule background tasks (~10 lines)
    background_tasks.add_task(cleanup_old_executions)
    asyncio.create_task(_execution_timeout_watchdog(execution_id, task, engine, ctx))

    # 6. Return response (~10 lines)
    return ExecutionResponse(
        execution_id=execution_id,
        playbook_name=playbook.name,
        status="started",
        message=f"Execution started with ID: {execution_id}",
    )
```

**Helper Functions to Create:**
- `_validate_and_load_playbook()`
- `_create_execution_engine()`
- `_run_execution_workflow()`
- `_execution_timeout_watchdog()`
- `_handle_execution_cancellation()`

**Savings:** 160 lines reduced to ~80 (net -80 lines)

---

### 2.5 Simplify delete_execution

**Before:** 90 lines with complex screenshot logic

**After:** 40 lines using ScreenshotService

```python
@router.delete("/{execution_id}")
async def delete_execution(execution_id: str):
    """Delete execution and associated screenshots"""
    db = get_database()

    with db.session_scope() as session:
        # Get execution
        execution = session.query(ExecutionModel).filter_by(
            execution_id=execution_id
        ).first()

        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        # Extract screenshot paths before deletion
        screenshot_service = ScreenshotService()
        screenshot_paths = screenshot_service.extract_paths(execution.step_results)

        # Delete execution (cascades to step_results)
        session.delete(execution)
        session.commit()

    # Delete screenshots after database commit
    deleted_count = screenshot_service.delete_files(screenshot_paths)

    logger.info(f"Deleted execution {execution_id} and {deleted_count} screenshots")

    return {
        "message": f"Execution {execution_id} deleted",
        "screenshots_deleted": deleted_count,
    }
```

**Savings:** 50 lines

---

### Phase 2 Summary

**Total Changes:**
- 2 new service classes
- 5 new helper functions
- start_execution: 242 → 80 lines (-162)
- delete_execution: 90 → 40 lines (-50)

**Testing Requirements:**
- Unit tests for ExecutionParameterService
- Unit tests for ScreenshotService
- Integration tests for start_execution flow
- Integration tests for delete_execution cascade

---

## Phase 3: Structural Improvements (Week 4-5)

**Status:** Planned
**Risk:** MEDIUM-HIGH (architectural changes)

### 3.1 Create ExecutionManager Service

**File:** Create `ignition_toolkit/api/services/execution_manager.py`

**Purpose:** Replace global state with managed service

**Benefits:**
- Proper lifecycle management
- Thread-safe operations
- Automatic cleanup
- Testable in isolation

**Implementation:**
```python
class ExecutionManager:
    """Manages execution lifecycle and state"""

    def __init__(self, ttl_minutes: int = 60):
        self._engines: dict[str, PlaybookEngine] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._completion_times: dict[str, datetime] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None
        self.ttl_minutes = ttl_minutes

    async def start(self) -> None:
        """Start background cleanup task"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop and cleanup all executions"""
        if self._cleanup_task:
            self._cleanup_task.cancel()

        # Cancel all running tasks
        for task in self._tasks.values():
            task.cancel()

    async def add_execution(
        self,
        execution_id: str,
        engine: PlaybookEngine,
        task: asyncio.Task,
    ) -> None:
        """Register new execution"""
        async with self._lock:
            self._engines[execution_id] = engine
            self._tasks[execution_id] = task

    async def get_engine(self, execution_id: str) -> PlaybookEngine | None:
        """Get engine by ID"""
        return self._engines.get(execution_id)

    async def remove_execution(self, execution_id: str) -> None:
        """Remove completed execution"""
        async with self._lock:
            self._engines.pop(execution_id, None)
            self._tasks.pop(execution_id, None)
            self._completion_times[execution_id] = datetime.now()

    async def _cleanup_loop(self) -> None:
        """Automatic TTL-based cleanup"""
        while True:
            await asyncio.sleep(60)  # Check every minute
            await self._cleanup_expired()

    async def _cleanup_expired(self) -> int:
        """Remove expired executions"""
        now = datetime.now()
        expired = []

        async with self._lock:
            for execution_id, completion_time in list(self._completion_times.items()):
                elapsed_minutes = (now - completion_time).total_seconds() / 60
                if elapsed_minutes > self.ttl_minutes:
                    expired.append(execution_id)

            for execution_id in expired:
                self._engines.pop(execution_id, None)
                self._tasks.pop(execution_id, None)
                self._completion_times.pop(execution_id, None)

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired executions")

        return len(expired)
```

**Migration:**
- Add to app lifespan context
- Replace global dictionaries
- Update all access points

---

### 3.2 Repository Pattern for Database Access

**File:** Create `ignition_toolkit/storage/repositories/execution_repository.py`

**Purpose:** Centralize all execution database operations

**Benefits:**
- Single source of truth for queries
- Easier to optimize queries
- Consistent error handling
- Mockable for testing

**Interface:**
```python
class ExecutionRepository:
    """Repository for execution persistence"""

    def __init__(self, db: Database):
        self.db = db

    def create(self, execution_state: ExecutionState) -> ExecutionModel:
        """Create new execution record"""
        ...

    def get_by_id(self, execution_id: str) -> ExecutionModel | None:
        """Get execution by UUID"""
        ...

    def list_all(
        self,
        limit: int = 50,
        status: str | None = None,
    ) -> list[ExecutionModel]:
        """List executions with filters"""
        ...

    def update_status(
        self,
        execution_id: str,
        status: str,
        error: str | None = None,
    ) -> None:
        """Update execution status"""
        ...

    def delete(self, execution_id: str) -> bool:
        """Delete execution and cascade to step results"""
        ...
```

---

### 3.3 Fix Database Schema (Execution ID as Primary Key)

**Risk:** HIGH - Requires migration

**Current Schema:**
```python
class ExecutionModel:
    id = Column(Integer, primary_key=True)           # Auto-increment
    execution_id = Column(String(255), unique=True)  # UUID

class StepResultModel:
    execution_id = Column(Integer, ForeignKey("executions.id"))  # Links to ID, not UUID!
```

**Target Schema:**
```python
class ExecutionModel:
    execution_id = Column(String(36), primary_key=True)  # UUID is primary key

class StepResultModel:
    execution_id = Column(String(36), ForeignKey("executions.execution_id"))  # Links to UUID
```

**Migration Script:**
```python
# migrations/001_uuid_primary_key.py
def upgrade():
    """Convert execution_id to primary key"""
    # 1. Create new table with correct schema
    # 2. Copy data with UUID casting
    # 3. Update foreign keys in step_results
    # 4. Drop old table, rename new table

def downgrade():
    """Rollback to integer primary key"""
    # Reverse migration
```

**Testing:**
- Backup database before migration
- Test on development database
- Verify all queries work after migration
- Test rollback procedure

---

## Phase 4: Advanced Patterns (Week 6-8)

**Status:** Future planning
**Risk:** MEDIUM

### 4.1 Command Pattern for Step Execution

**File:** Create `ignition_toolkit/playbook/commands/`

**Eliminates:** 500+ line if-elif chain in step_executor.py

### 4.2 Observer Pattern for Execution Events

**File:** Create `ignition_toolkit/playbook/events/`

**Decouples:** Engine from WebSocket broadcasting

### 4.3 Configuration Management with Pydantic

**File:** Create `ignition_toolkit/config/settings.py`

**Centralizes:** All configuration with validation

---

## Testing Strategy

### Unit Tests (Phase 1)
```bash
pytest tests/test_execution_helpers.py -v
pytest tests/test_execution_context.py -v
```

### Integration Tests (Phase 2)
```bash
pytest tests/integration/test_execution_lifecycle.py -v
pytest tests/integration/test_screenshot_cleanup.py -v
```

### Regression Tests (All Phases)
```bash
pytest tests/ -v --cov=ignition_toolkit --cov-report=html
```

### Manual Testing Checklist
- [ ] Start execution → appears immediately on UI
- [ ] Pause/resume execution → works correctly
- [ ] Cancel execution → terminates properly
- [ ] Delete execution → removes screenshots
- [ ] Browser click during pause → no errors
- [ ] Debug mode toggle → functions as expected
- [ ] WebSocket updates → real-time reflection

---

## Rollback Strategy

Each phase is independently reversible:

**Phase 1 Rollback:**
1. Remove helper functions
2. Restore original endpoint code
3. Git revert to previous commit

**Phase 2 Rollback:**
1. Remove service classes
2. Restore inline logic
3. Run integration tests

**Phase 3 Rollback:**
1. Restore global state pattern
2. Remove ExecutionManager
3. Database migration rollback script

---

## Success Metrics

### Code Quality Metrics

| Metric | Before | Phase 1 Target | Phase 2 Target | Final Target |
|--------|--------|----------------|----------------|--------------|
| executions.py LOC | 906 | 780 (-14%) | 650 (-28%) | 400 (-56%) |
| Max Function Length | 242 | 200 | 100 | <50 |
| Cyclomatic Complexity | 18 | 15 | 12 | <10 |
| Code Duplication | 175 lines | 20 lines | 10 lines | <5 lines |
| Test Coverage | ~60% | 70% | 80% | >90% |

### Performance Metrics
- No degradation in execution speed
- WebSocket latency <100ms
- API response time <200ms
- Database query time <50ms

### Reliability Metrics
- Zero regression bugs
- All existing features functional
- No breaking changes to API

---

## Timeline

| Phase | Duration | Start Date | End Date | Status |
|-------|----------|------------|----------|--------|
| Phase 1 | 5 days | 2025-10-29 | 2025-11-02 | IN PROGRESS |
| Phase 2 | 10 days | 2025-11-05 | 2025-11-15 | Planned |
| Phase 3 | 10 days | 2025-11-18 | 2025-11-29 | Planned |
| Phase 4 | 15 days | 2025-12-02 | 2025-12-20 | Future |

**Total Duration:** ~6 weeks for Phases 1-3 (critical improvements)

---

## Risk Mitigation

### High-Risk Changes
1. **Database schema migration** (Phase 3.3)
   - Mitigation: Full backup, rollback script, staging testing

2. **Global state removal** (Phase 3.1)
   - Mitigation: Parallel implementation, gradual migration

### Medium-Risk Changes
1. **start_execution breakdown** (Phase 2.4)
   - Mitigation: Extensive integration testing, incremental changes

2. **Repository pattern** (Phase 3.2)
   - Mitigation: Mock-based unit tests, query verification

### Low-Risk Changes
1. **Helper function extraction** (Phase 1.1, 1.2)
   - Mitigation: Unit tests, side-by-side verification

---

## Next Steps

### Immediate Actions (Today)
1. ✅ Create this refactoring plan
2. ⏳ Implement Phase 1.1 (StepResultResponse helper)
3. ⏳ Implement Phase 1.2 (ExecutionStatusResponse factory)
4. ⏳ Write unit tests for helpers
5. ⏳ Update 4 endpoints to use helpers

### This Week
- Complete all Phase 1 tasks
- Run full regression test suite
- Commit Phase 1 changes
- Update version to 3.18.0

### Next Week
- Begin Phase 2 implementation
- Create service classes
- Extract start_execution logic

---

## Notes

- Each phase is independently deployable
- No breaking changes to external API
- All changes backward compatible
- Comprehensive tests before each merge
- Documentation updated with each phase

---

**Last Updated:** 2025-10-29
**Author:** Nigel G + Claude Code
**Status:** Phase 1 in progress
