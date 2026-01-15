# Phase 2 Session Start Guide

**Quick reference for starting Phase 2 Claude Code implementation**

## Current Status (v2.2.0)

✅ **Phase 1 Complete** - Manual copy/paste workflow
- Backend endpoint: `POST /api/ai/claude-code-session`
- Frontend dialog: `ClaudeCodeDialog.tsx`
- Button in `ExecutionControls.tsx`
- Full documentation: `docs/CLAUDE_CODE_INTEGRATION.md`

## Phase 2 Goals

Implement embedded terminal with WebSocket proxy for seamless Claude Code integration.

## Session Checklist

### 1. Review Documentation
- [ ] Read `docs/CLAUDE_CODE_PHASE2_PLAN.md` (complete implementation plan)
- [ ] Review Phase 1 code to understand existing integration
- [ ] Check current server status (`curl http://localhost:5000/health`)

### 2. Install Dependencies

**Backend:**
```bash
pip install python-pty
```

**Frontend (already attempted, may need to complete):**
```bash
cd frontend
npm install xterm xterm-addon-fit xterm-addon-web-links
```

### 3. Implementation Order

1. **Backend WebSocket Proxy** (2-3 hours)
   - Add `/ws/claude-code/{execution_id}` endpoint
   - PTY process spawning and management
   - stdin/stdout proxying
   - Process cleanup

2. **Frontend Terminal Component** (2-3 hours)
   - Create `EmbeddedTerminal.tsx`
   - xterm.js integration
   - WebSocket connection
   - Keyboard input forwarding

3. **Update Dialog Component** (1 hour)
   - Add mode toggle (embedded/manual)
   - Integrate EmbeddedTerminal component
   - Maintain Phase 1 fallback

4. **Testing** (2-3 hours)
   - Manual testing of terminal
   - Process lifecycle testing
   - Error handling
   - Multiple session support

### 4. Key Files to Modify

**Backend:**
- `ignition_toolkit/api/app.py` - Add WebSocket endpoint

**Frontend:**
- `frontend/src/components/EmbeddedTerminal.tsx` - NEW FILE
- `frontend/src/components/ClaudeCodeDialog.tsx` - Add mode toggle
- `frontend/src/api/client.ts` - No changes needed (WebSocket is direct)

### 5. Testing Commands

```bash
# Start server
./start_server.sh

# Test health endpoint
curl http://localhost:5000/health

# Check WebSocket endpoint (after implementation)
# Use browser console or wscat:
# wscat -c ws://localhost:5000/ws/claude-code/test-execution-id
```

### 6. Common Pitfalls

1. **PTY on Windows**: Python `pty` module doesn't work on Windows
   - Use WSL2 or implement Windows-specific PTY using `pywinpty`

2. **Binary Data Encoding**: WebSocket binary frames need proper handling
   - Use TextEncoder/TextDecoder for UTF-8

3. **Process Cleanup**: Zombie processes if not handled correctly
   - Always use try/finally blocks
   - Implement proper signal handling

4. **Terminal Sizing**: xterm.js needs manual resize
   - Use FitAddon with window resize listener

### 7. Success Criteria

- [ ] WebSocket connects successfully
- [ ] Terminal displays output in real-time
- [ ] Keyboard input works (type in terminal)
- [ ] Process terminates cleanly on disconnect
- [ ] Multiple sessions work independently
- [ ] Error messages display clearly
- [ ] Phase 1 manual mode still works
- [ ] Terminal resizes correctly
- [ ] Colors/formatting render properly

### 8. Documentation Updates

After implementation:
- [ ] Update `docs/CLAUDE_CODE_INTEGRATION.md` with Phase 2 details
- [ ] Update CHANGELOG.md for v2.3.0
- [ ] Update VERSION files
- [ ] Rebuild frontend (`npm run build`)

## Estimated Timeline

- **Total Effort:** 7-11 hours
- **Minimum Viable:** 5-6 hours (basic functionality)
- **Full Implementation:** 8-10 hours (with error handling, testing)
- **Polish & Docs:** 1-2 hours

## Resources

- **Phase 2 Plan:** `docs/CLAUDE_CODE_PHASE2_PLAN.md`
- **Phase 1 Docs:** `docs/CLAUDE_CODE_INTEGRATION.md`
- **xterm.js Docs:** https://xtermjs.org/
- **FastAPI WebSocket:** https://fastapi.tiangolo.com/advanced/websockets/

## Quick Start Command

```bash
# When ready to start Phase 2 implementation:
cd /git/ignition-playground
./stop_server.sh  # Clean slate
git status        # Check current state
git diff          # Review any uncommitted changes

# Start implementation!
```

---

**Status:** Ready for implementation
**Version:** v2.2.0 (Phase 1 complete)
**Next Version:** v2.3.0 (Phase 2)
**Last Updated:** 2025-10-27
