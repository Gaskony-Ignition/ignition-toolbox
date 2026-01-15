# PHASE 2 - ROUTE ANALYSIS

**Created:** 2025-10-27
**Purpose:** Systematic analysis of app.py (2377 lines) for modular extraction

---

## Route Inventory (38 total routes)

### Playbook Routes (6 routes)
- `GET /api/playbooks` - List all playbooks (line 238)
- `GET /api/playbooks/{playbook_path:path}` - Get specific playbook (line 306)
- `PUT /api/playbooks/update` - Update playbook content (line 973)
- `PATCH /api/playbooks/metadata` - Update playbook metadata (line 1042)
- `DELETE /api/playbooks/{playbook_path:path}` - Delete playbook (estimated)
- Helper functions: `validate_playbook_path()`, `get_relative_playbook_path()`

### Execution Routes (12 routes)
- `POST /api/executions` - Start execution (line 419)
- `GET /api/executions` - List executions (line 546)
- `GET /api/executions/{execution_id}` - Get execution status (line 632)
- `GET /api/executions/{execution_id}/status` - Get execution status with path (line 718)
- `POST /api/executions/{execution_id}/pause` - Pause execution (line 724)
- `POST /api/executions/{execution_id}/resume` - Resume execution (line 736)
- `POST /api/executions/{execution_id}/skip` - Skip current step (line 748)
- `POST /api/executions/{execution_id}/skip_back` - Skip backward (line 760)
- `POST /api/executions/{execution_id}/cancel` - Cancel execution (line 772)
- `GET /api/executions/{execution_id}/playbook/code` - Get playbook code (line 869)
- `PUT /api/executions/{execution_id}/playbook/code` - Update playbook code (line 912)
- Background task: `cleanup_old_executions()` (line 215)

### Debug Routes (3 routes)
- `POST /api/executions/{execution_id}/debug/enable` - Enable debug mode (line 786)
- `POST /api/executions/{execution_id}/debug/disable` - Disable debug mode (line 798)
- `GET /api/executions/{execution_id}/debug/context` - Get debug context (line 810)
- `GET /api/executions/{execution_id}/debug/dom` - Get DOM snapshot (line 825)

### Browser Automation Routes (1 route)
- `POST /api/executions/{execution_id}/browser/click` - Click at coordinates (line 850)

### Credential Routes (4 routes)
- `GET /api/credentials` - List credentials (line 1114)
- `POST /api/credentials` - Add credential (line 1134)
- `PUT /api/credentials/{name}` - Update credential (line 1169)
- `DELETE /api/credentials/{name}` - Delete credential (line 1204)

### AI/Claude Code Routes (estimated 5-8 routes)
- AI assistance endpoints
- Claude Code integration endpoints

### WebSocket Routes (1 route)
- `GET /api/ws/stream/{execution_id}` - WebSocket connection (estimated)

### Health/System Routes (2-3 routes)
- Already extracted to `routers/health.py`
- Health check endpoints

---

## Extraction Plan

### Phase 2.1 (Day 3) - Playbooks & Executions ✅ READY
**Target Files:**
- `routers/playbooks.py` (~300 lines)
- `routers/executions.py` (~400 lines)

**Extraction Order:**
1. Create `routers/playbooks.py` with 6 playbook routes + helpers
2. Create `routers/executions.py` with 12 execution routes + cleanup task
3. Update `app.py` to import and include routers
4. Test server startup and basic functionality
5. Commit: "V3 Refactor: Phase 2.1 - Extract playbook and execution routers"

### Phase 2.2 (Day 4) - Credentials, Debug, AI
**Target Files:**
- `routers/credentials.py` (~200 lines)
- `routers/debug.py` (~150 lines)
- `routers/ai.py` (~200 lines)

### Phase 2.3 (Day 5) - WebSocket
**Target Files:**
- `routers/websockets.py` (~300 lines)

### Phase 2.4 (Day 6) - Services
**Target Files:**
- `services/execution_manager.py`
- `services/playbook_service.py`

### Phase 2.5 (Day 7) - Middleware & Final
**Target Files:**
- `middleware/auth.py`
- `middleware/cors.py`
- `services/cleanup_service.py`
- `dependencies.py`

---

## Success Criteria

### For Each Extraction:
1. ✅ Extract routes to new router file
2. ✅ Import router in app.py
3. ✅ Server starts without errors
4. ✅ Test at least one route from extracted router
5. ✅ Commit with descriptive message
6. ✅ Update PROGRESS.md

### Final Phase 2 Success:
- app.py reduced from 2377 lines to <500 lines
- All 38 routes functional
- All tests passing
- No regressions in functionality

---

## Notes

- **Current app.py size**: 2377 lines
- **Target app.py size**: <500 lines (<300 lines ideal)
- **Total routes**: 38
- **Estimated reduction**: ~1900 lines moved to routers/services
- **Testing strategy**: Test after each extraction, full regression test at end

---

**Last Updated:** 2025-10-27 (Phase 2 start)
