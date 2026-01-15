# PHASE 2.1 - EXTRACTION SPECIFICATION

**Created:** 2025-10-27
**Purpose:** Detailed specification for extracting playbooks and executions routers

---

## Models to Extract (Shared Dependencies)

### Pydantic Models (currently in app.py lines 96-208):
```python
# These models are used by MULTIPLE routers, keep in app.py for now
# Will move to models.py in Phase 2.4

class ParameterInfo(BaseModel):         # Line 96
class StepInfo(BaseModel):              # Line 106
class PlaybookInfo(BaseModel):          # Line 116
class ExecutionRequest(BaseModel):      # Line 135
class ExecutionResponse(BaseModel):     # Line 177
class StepResultResponse(BaseModel):    # Line 185
class ExecutionStatusResponse(BaseModel): # Line 195
```

### Global State Variables (keep in app.py):
```python
active_engines: Dict[str, PlaybookEngine] = {}           # Line 67
engine_completion_times: Dict[str, datetime] = {}        # Line 68
websocket_connections: List[WebSocket] = []              # Line 69
claude_code_processes: Dict[str, subprocess.Popen] = {}  # Line 70
ai_assistant = AIAssistant()                             # Line 73
metadata_store = PlaybookMetadataStore()                 # Line 79
```

---

## PLAYBOOKS ROUTER EXTRACTION

### File: `ignition_toolkit/api/routers/playbooks.py`

### Routes to Extract (10 routes):

1. **GET /api/playbooks** (line 238-304)
   - Function: `list_playbooks()`
   - Dependencies: PlaybookLoader, metadata_store, get_playbooks_dir()

2. **GET /api/playbooks/{playbook_path:path}** (line 306-355)
   - Function: `get_playbook(playbook_path: str)`
   - Dependencies: PlaybookLoader, metadata_store, get_playbook_path()

3. **PUT /api/playbooks/update** (line 973-1040)
   - Function: `update_playbook(request: PlaybookUpdateRequest)`
   - Dependencies: shutil, Path, yaml

4. **PATCH /api/playbooks/metadata** (line 1042-1112)
   - Function: `update_playbook_metadata(request: PlaybookMetadataUpdateRequest)`
   - Dependencies: metadata_store

5. **POST /api/playbooks/{playbook_path:path}/verify** (line 1224-1242)
   - Function: `verify_playbook(playbook_path: str)`
   - Dependencies: metadata_store

6. **POST /api/playbooks/{playbook_path:path}/unverify** (line 1244-1260)
   - Function: `unverify_playbook(playbook_path: str)`
   - Dependencies: metadata_store

7. **POST /api/playbooks/{playbook_path:path}/enable** (line 1262-1278)
   - Function: `enable_playbook(playbook_path: str)`
   - Dependencies: metadata_store

8. **POST /api/playbooks/{playbook_path:path}/disable** (line 1280-1296)
   - Function: `disable_playbook(playbook_path: str)`
   - Dependencies: metadata_store

9. **DELETE /api/playbooks/{playbook_path:path}** (line 1298-1318)
   - Function: `delete_playbook(playbook_path: str)`
   - Dependencies: os, metadata_store

10. **POST /api/playbooks/edit-step** (line 2310-2375)
    - Function: `edit_playbook_step(request: EditPlaybookStepRequest)`
    - Dependencies: yaml, Path

### Helper Functions to Extract:

1. **validate_playbook_path(path_str: str)** (line 357-394)
   - Validates playbook path for security
   - Prevents directory traversal attacks

2. **get_relative_playbook_path(path_str: str)** (line 396-417)
   - Converts absolute path to relative
   - Used for canonical path handling

### Additional Models Needed:

```python
class PlaybookUpdateRequest(BaseModel):
    playbook_path: str
    content: str

class PlaybookMetadataUpdateRequest(BaseModel):
    playbook_path: str
    verified: Optional[bool] = None
    enabled: Optional[bool] = None

class EditPlaybookStepRequest(BaseModel):
    playbook_path: str
    step_index: int
    field: str
    value: Any
```

### Imports Required:

```python
import os
import shutil
import yaml
from pathlib import Path
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ignition_toolkit.playbook.loader import PlaybookLoader
from ignition_toolkit.playbook.metadata import PlaybookMetadataStore
from ignition_toolkit.core.paths import get_playbooks_dir, get_playbook_path
```

### Router Setup:

```python
router = APIRouter(prefix="/api/playbooks", tags=["playbooks"])

# Dependency injection for metadata store
def get_metadata_store():
    from ignition_toolkit.api.app import metadata_store
    return metadata_store
```

---

## EXECUTIONS ROUTER EXTRACTION

### File: `ignition_toolkit/api/routers/executions.py`

### Routes to Extract (12 routes):

1. **POST /api/executions** (line 419-544)
   - Function: `start_execution(request: ExecutionRequest, background_tasks: BackgroundTasks)`
   - Dependencies: PlaybookEngine, active_engines, Background tasks

2. **GET /api/executions** (line 546-630)
   - Function: `list_executions(limit: int = 50, status: Optional[str] = None)`
   - Dependencies: get_database(), active_engines

3. **GET /api/executions/{execution_id}** (line 632-716)
   - Function: `get_execution_status(execution_id: str)`
   - Dependencies: active_engines, get_database()

4. **GET /api/executions/{execution_id}/status** (line 718-722)
   - Function: `get_execution_status_with_path(execution_id: str)`
   - Duplicate of above, calls get_execution_status()

5. **POST /api/executions/{execution_id}/pause** (line 724-734)
   - Function: `pause_execution(execution_id: str)`
   - Dependencies: active_engines

6. **POST /api/executions/{execution_id}/resume** (line 736-746)
   - Function: `resume_execution(execution_id: str)`
   - Dependencies: active_engines

7. **POST /api/executions/{execution_id}/skip** (line 748-758)
   - Function: `skip_step(execution_id: str)`
   - Dependencies: active_engines

8. **POST /api/executions/{execution_id}/skip_back** (line 760-770)
   - Function: `skip_back_step(execution_id: str)`
   - Dependencies: active_engines

9. **POST /api/executions/{execution_id}/cancel** (line 772-784)
   - Function: `cancel_execution(execution_id: str)`
   - Dependencies: active_engines

10. **GET /api/executions/{execution_id}/playbook/code** (line 869-910)
    - Function: `get_playbook_code(execution_id: str)`
    - Dependencies: active_engines

11. **PUT /api/executions/{execution_id}/playbook/code** (line 912-971)
    - Function: `update_playbook_code(execution_id: str, request: PlaybookCodeUpdateRequest)`
    - Dependencies: active_engines

12. **Background cleanup task: cleanup_old_executions()** (line 215-234)
    - Removes completed executions older than TTL
    - Dependencies: active_engines, engine_completion_times

### Additional Models Needed:

```python
class PlaybookCodeUpdateRequest(BaseModel):
    code: str
```

### Imports Required:

```python
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ignition_toolkit.playbook.engine import PlaybookEngine
from ignition_toolkit.playbook.models import ExecutionState
from ignition_toolkit.storage import get_database
```

### Router Setup:

```python
router = APIRouter(prefix="/api/executions", tags=["executions"])

# Dependency injection for global state
def get_active_engines():
    from ignition_toolkit.api.app import active_engines
    return active_engines

def get_engine_completion_times():
    from ignition_toolkit.api.app import engine_completion_times
    return engine_completion_times
```

---

## INTEGRATION STEPS

### 1. Create routers/playbooks.py
- Extract 10 routes
- Extract 2 helper functions
- Create 3 new Pydantic models
- Set up dependency injection

### 2. Create routers/executions.py
- Extract 12 routes
- Extract cleanup task
- Create 1 new Pydantic model
- Set up dependency injection

### 3. Update app.py
```python
# Add imports
from ignition_toolkit.api.routers.playbooks import router as playbooks_router
from ignition_toolkit.api.routers.executions import router as executions_router

# Register routers (after health router)
app.include_router(playbooks_router)
app.include_router(executions_router)
```

### 4. Remove extracted code from app.py
- Remove 22 route functions
- Remove 2 helper functions
- Keep all Pydantic models (for now)
- Keep all global state variables

---

## TESTING STRATEGY

### 1. After playbooks router extraction:
```bash
# Start server
make dev-backend

# Test playbook routes
curl http://localhost:5000/api/playbooks
curl http://localhost:5000/api/playbooks/examples/gateway_login.yaml
```

### 2. After executions router extraction:
```bash
# Test execution routes
curl -X POST http://localhost:5000/api/executions -H "Content-Type: application/json" -d '{...}'
curl http://localhost:5000/api/executions
```

### 3. Full regression test:
```bash
# Run all tests
make test

# Check all routes work
make verify-ux
```

---

## ESTIMATED LINE REDUCTION

**Current app.py:** 2377 lines

**After extraction:**
- Playbooks router: ~400 lines removed
- Executions router: ~400 lines removed
- **Expected app.py size:** ~1577 lines (34% reduction)

---

## SUCCESS CRITERIA

✅ Server starts without errors
✅ All playbook routes respond correctly
✅ All execution routes respond correctly
✅ No regressions in existing functionality
✅ All tests passing
✅ Code committed with detailed message

---

**Last Updated:** 2025-10-27
**Ready for extraction:** ✅ YES
**Next Session:** Begin with playbooks router extraction
