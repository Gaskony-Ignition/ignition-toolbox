# Architectural Debt Audit - Single Source of Truth Analysis
**Date**: 2026-02-22
**Scope**: Full codebase - Python backend, Electron main, React frontend, cross-layer contracts

---

## Summary

Four parallel agents reviewed 346 source files across all layers.
The core finding: **a small number of central constants files would eliminate ~150+ scattered duplications** across the codebase.

---

## TIER 1 — Quick Wins (New constants files, no logic changes)

These are pure additions that consolidate existing scattered values. Low risk, high impact.

### T1-A: Backend Timeout Constants (`backend/ignition_toolkit/core/timeouts.py`)
**Severity**: CRITICAL
**Problem**: 5 timeout values (120s, 300s, 30000ms, 5000ms, 60s) and 4 override key strings scattered across 15+ files.
**Files with magic numbers**: `step_executor.py`, `engine.py`, `gateway/client.py`, `browser_executor.py` (10+ classes), `gateway_executor.py`, `step_types.py`, `playbook_crud.py`, `startup/playwright_installer.py`
**Fix**: Create single file:
```python
# core/timeouts.py
class TimeoutDefaults:
    GATEWAY_RESTART = 120     # seconds
    MODULE_INSTALL = 300      # seconds
    BROWSER_ACTION = 30000    # milliseconds
    BROWSER_VERIFY = 5000     # milliseconds
    DESIGNER_LAUNCH = 60      # seconds

class TimeoutKeys:
    GATEWAY_RESTART = "gateway_restart"
    MODULE_INSTALL = "module_install"
    BROWSER_OPERATION = "browser_operation"
    DESIGNER_LAUNCH = "designer_launch"
```

### T1-B: Electron IPC Channel Constants (`electron/ipc/channels.ts`)
**Severity**: CRITICAL
**Problem**: 17 invoke channels + 9 event channels duplicated across `preload.ts`, `ipc/handlers.ts`, `services/auto-updater.ts`, `frontend/pages/Settings.tsx`, `frontend/components/Layout.tsx`.
**Fix**: Create single constants file. Both preload.ts and handlers.ts import from it. Frontend event subscriptions use the same constants via `electron.d.ts` re-export.

### T1-C: Frontend localStorage Keys (`frontend/src/utils/localStorage.ts`)
**Severity**: HIGH
**Problem**: 14 distinct key patterns, 50+ access points across 8+ files. Key patterns: `playbook_config_*`, `playbook_debug_*`, `playbook_order_*`, `category_order`, `mainTab`, `theme`, `selectedCredentialName`, etc.
**Fix**: Central `STORAGE_KEYS` object with typed getter/setter utilities.

### T1-D: Frontend Execution Status Constants (`frontend/src/constants/executionStatus.ts`)
**Severity**: CRITICAL
**Problem**: `getStatusColor()` function defined 5 times with different return types (MUI color strings vs hex colors). `getStatusIcon()` defined 3 times. Status values `'running'`, `'completed'`, `'failed'` scattered across 10+ files.
**Fix**: Single file with `ExecutionStatus` type, `STATUS_CHIP_COLOR`, `STATUS_HEX_COLOR`, `STATUS_ICON` maps.

### T1-E: Frontend Timing Constants (`frontend/src/config/timing.ts`)
**Severity**: MEDIUM
**Problem**: 20+ hardcoded timing values: polling intervals (2000, 3000, 5000, 30000, 300000ms), snackbar durations (3000ms), WebSocket heartbeat (15000ms), reconnect delays.
**Fix**: `TIMING.POLLING.*`, `TIMING.DELAYS.*`, `TIMING.WEBSOCKET.*` constants.

### T1-F: Electron Backend Config (`electron/config.ts`)
**Severity**: CRITICAL
**Problem**: Port `5000` hardcoded in 5 files: `python-backend.ts`, `api/client.ts`, `useWebSocket.ts`, `EmbeddedTerminal.tsx`, `.env.example`. Port range `5000-5099` only defined in `python-backend.ts`.
**Fix**: Single config file with `DEFAULT_BACKEND_PORT`, `PORT_RANGE_START/END`, `getBackendUrl(port)`, `getWebSocketUrl(port)`.

---

## TIER 2 — Architecture Improvements (Logic changes required)

### T2-A: Step Type Domain Property (Backend)
**Severity**: MEDIUM
**Problem**: Domain detection done via string prefix matching (`step.type.value.startswith("browser.")`) in 7+ locations across `step_executor.py`, `engine.py`, `playbook_crud.py`.
**Fix**: Add `.domain` property to `StepType` enum:
```python
@property
def domain(self) -> str:
    return self.value.split(".")[0]
```
Replace all `startswith("browser.")` calls with `step.type.domain == "browser"`.

### T2-B: Fix "started" Status Mismatch (Backend)
**Severity**: MEDIUM
**Problem**: `api/routers/executions/main.py:87` returns `status="started"` in API response, but `ExecutionStatus` enum has no STARTED value. Frontend receives a status string it cannot type-check.
**Fix**: Either add `STARTED = "started"` to `ExecutionStatus`, or return `ExecutionStatus.PENDING.value` from the endpoint.

### T2-C: Replace Status String Literals with Enum References (Backend)
**Severity**: HIGH
**Problem**: Status strings `"cancelled"`, `"started"`, `"completed"` etc. used as raw string literals in `websocket_manager.py`, `execution_service.py`, `execution_response_builder.py` instead of `ExecutionStatus.CANCELLED.value`.
**Fix**: Replace all hardcoded status string comparisons with enum references. Add `Literal` constraint to DB model columns.

### T2-D: Backend-Frontend Type Mismatch (Cross-layer)
**Severity**: HIGH
**Problem**: `ExecutionRequest.parameters` typed as `Record<string, string>` in frontend but `dict[str, Any]` in backend. Backend accepts booleans/integers; frontend forces all values to strings. Also: `current_step_index` is optional in backend but non-optional in frontend type.
**Fix**: Update `frontend/src/types/api.ts` - parameters to `Record<string, string | boolean | number>`, mark optional fields with `?`.
**Long-term**: Generate TypeScript types from backend's OpenAPI schema (`/openapi.json`).

### T2-E: Validation Limit Constants (Backend)
**Severity**: LOW
**Problem**: Magic numbers in validators: max 50 params, 255 char keys, 10000 char values, 500 char URLs, 200 char playbook names, 2000 char descriptions. Scattered across `api/routers/models.py` and `api/routers/playbook_crud.py`.
**Fix**: `core/validation_limits.py` with `ValidationLimits` class.

### T2-F: Frontend Navigation Tab Types (Frontend)
**Severity**: MEDIUM
**Problem**: Tab union types (`MainTab`, `PlaybookSubTab`, `StackSubTab`) defined in `store/index.ts`, then tab config arrays defined independently in page components. Adding a tab requires updating both.
**Fix**: `frontend/src/constants/navigation.ts` with typed tab arrays + derived union types using `typeof TABS[number]`.

### T2-G: Clouddesigner Type Dead Code (Electron)
**Severity**: LOW
**Problem**: `frontend/src/types/electron.d.ts` declares optional `cloudDesigner.openWindow()` but `electron/preload.ts` doesn't expose this method. Dead type declaration.
**Fix**: Remove `cloudDesigner` from `electron.d.ts` or implement it in `preload.ts`.

---

## TIER 3 — Step Type System Refactoring (Largest Change)

**This is the highest-leverage refactoring in the codebase.**

### Current State: Adding 1 Step Type = 9 File Changes
1. `playbook/models.py` — Add `StepType` enum entry
2. `api/routers/step_types.py` — Add `StepTypeInfo` + parameters (10+ lines)
3. Create `executors/custom_executor.py` — Handler class (30+ lines)
4. `playbook/executors/__init__.py` — Add import
5. `playbook/executors/__init__.py` — Add to `__all__`
6. `playbook/step_executor.py` — Add import
7. `playbook/step_executor.py` — Add to `_create_handler_registry()`
8. `api/routers/playbook_crud.py` — Add to timeout computation (if needed)
9. `frontend/src/components/StepTypeSelector.tsx` — Add domain icon (if new domain)

### Target State: Adding 1 Step Type = 3 File Changes
1. `playbook/registry.py` — Add one `StepTypeDefinition` entry
2. Create `executors/custom_executor.py` — Handler class
3. Tests

### How to Get There:

**T3-A: Create Unified Step Registry**
```python
# playbook/registry.py
@dataclass
class StepTypeDefinition:
    type: StepType
    domain: str
    handler_class: type[BaseStepHandler]
    handler_args: list[str]     # which services to inject
    description: str
    parameters: list[StepParameter]
    timeout_category: str | None = None

STEP_REGISTRY: list[StepTypeDefinition] = [
    StepTypeDefinition(
        type=StepType.GATEWAY_LOGIN,
        domain="gateway",
        handler_class=GatewayLoginHandler,
        handler_args=["gateway_client"],
        description="Login to Ignition Gateway",
        parameters=[StepParameter(name="credential", type="credential", required=True)],
        timeout_category=TimeoutKeys.GATEWAY_RESTART,
    ),
    # ... 43 more
]
```

**T3-B: Generate StepType Enum from Registry**
Change `models.py` to derive the enum from registry, or validate that all registry entries have corresponding enum values in tests.

**T3-C: Auto-build Handler Registry in `step_executor.py`**
`_create_handler_registry()` builds from `STEP_REGISTRY` instead of 60 lines of manual mapping.

**T3-D: Auto-build STEP_TYPE_METADATA from Registry**
`api/routers/step_types.py` generates from `STEP_REGISTRY` instead of 44 duplicated `StepTypeInfo` objects.

**T3-E: Auto-build Timeout Computation in `playbook_crud.py`**
`_compute_relevant_timeouts()` uses `timeout_category` from registry instead of hardcoded string checks.

**T3-F: API Endpoint for Domain Config**
Add `/api/step-types/domains` endpoint returning domain metadata (label, icon). Frontend `StepTypeSelector.tsx` fetches this instead of hardcoding `DOMAIN_CONFIG`.

---

## TIER 4 — Version Management (Low Priority)

**Severity**: MEDIUM
**Problem**: Version `3.0.1` in 4 independent files: `package.json`, `frontend/package.json`, `backend/ignition_toolkit/__init__.py`, `backend/pyproject.toml`. Release process requires manual sync of all 4.
**Fix**: A version bump script or `version.json` as source of truth, read by the others. The MEMORY.md release process already documents all 4 files — at minimum, add a CI check that asserts all 4 match.

---

## Implementation Roadmap

### Phase 1 — Constants (No Logic Changes, ~4 hours total)
| Task | New File | Files Touched |
|------|----------|---------------|
| T1-A: Backend timeout constants | `core/timeouts.py` | 8 backend files |
| T1-B: Electron IPC channels | `electron/ipc/channels.ts` | 4 files |
| T1-C: Frontend localStorage | `frontend/src/utils/localStorage.ts` | 8 frontend files |
| T1-D: Frontend execution status | `frontend/src/constants/executionStatus.ts` | 5 frontend files |
| T1-E: Frontend timing | `frontend/src/config/timing.ts` | 10 frontend files |
| T1-F: Electron backend config | `electron/config.ts` | 4 files |

### Phase 2 — Quick Logic Fixes (~2 hours total)
| Task | Files Changed |
|------|---------------|
| T2-A: StepType.domain property | `playbook/models.py` + 3 consumers |
| T2-B: Fix "started" status | `api/routers/executions/main.py` |
| T2-C: Status enum refs | `websocket_manager.py`, `execution_service.py`, `execution_response_builder.py` |
| T2-D: Frontend type fixes | `frontend/src/types/api.ts` |
| T2-G: Remove dead cloudDesigner | `frontend/src/types/electron.d.ts` |

### Phase 3 — Step Type System (~8 hours, plan carefully)
| Task | Impact |
|------|--------|
| T3-A: Create unified registry | Core new file |
| T3-B: Validate enum/registry sync | Test added |
| T3-C: Auto-build handler registry | Removes 60 lines from step_executor.py |
| T3-D: Auto-build step metadata | Removes 490 lines from step_types.py |
| T3-E: Auto-build timeout computation | Removes string matching from playbook_crud.py |
| T3-F: Domain config API endpoint | Frontend fetches instead of hardcodes |

### Phase 4 — Lower Priority Polish (~2 hours)
- T2-E: Validation limits constants
- T2-F: Navigation tab constants
- T4: Version management script/CI check

---

## Files to Create (Net New)

| File | Purpose |
|------|---------|
| `backend/ignition_toolkit/core/timeouts.py` | Timeout defaults + override keys |
| `backend/ignition_toolkit/playbook/registry.py` | Unified step type registry |
| `electron/ipc/channels.ts` | IPC channel name constants |
| `electron/config.ts` | Backend port/host configuration |
| `frontend/src/constants/executionStatus.ts` | Status → color/icon mapping |
| `frontend/src/utils/localStorage.ts` | localStorage key constants + typed access |
| `frontend/src/config/timing.ts` | Polling intervals, delays, timeouts |
| `frontend/src/constants/navigation.ts` | Tab names and types |

---

## Key Metrics

| Metric | Before | After Phase 1+2 | After Phase 3 |
|--------|--------|-----------------|---------------|
| Files to change for new timeout value | 8-15 | 1 | 1 |
| Files to change for new execution status | 8+ | 2-3 | 2-3 |
| Files to change for new step type | 9 | 7 | 3 |
| localStorage key strings scattered | 50+ | 1 | 1 |
| Status color functions | 5 | 1 | 1 |
| Port 5000 hardcoded instances | 5 | 1 | 1 |
| IPC channel strings scattered | 3 files | 1 | 1 |
