# V3.0.0 REFACTOR - ROLLBACK GUIDE

**Purpose:** Emergency procedures for reverting the V3.0.0 refactor if critical issues arise.

**⚠️ CRITICAL:** This guide provides safe revert points and rollback procedures to ensure we can always return to a working state.

---

## Revert Points (Git Tags)

### v2.4.0-final-stable (Pre-Refactor Baseline)
**Date:** 2025-10-27 (Before V3 refactor)
**Status:** ✅ Stable, Production-Ready
**Description:** Last stable release before V3.0.0 refactor begins

**Features:**
- Playbook Code Viewer/Editor (v2.4.0 feature)
- Claude Code integration Phase 1 (Manual Launch)
- All 8 phases complete from original roadmap
- WebSocket stability fixes
- Nested playbook execution
- Debug mode with step-by-step execution

**Rollback Command:**
```bash
# Save current work first (if needed)
git stash save "WIP: V3 refactor in progress"

# Revert to v2.4.0
git checkout v2.4.0-final-stable

# Reinstall dependencies
pip install -e .
cd frontend && npm install && npm run build && cd ..

# Start server (old method)
./venv/bin/uvicorn ignition_toolkit.api.app:app --host 0.0.0.0 --port 5000
```

**When to Use:**
- V3 refactor introduces critical bugs
- Need stable version for demo or production use
- Must continue existing work without V3 changes

---

### v3.0.0-phase1 (After Foundation & Docker)
**Date:** TBD (After Phase 1 complete)
**Status:** 🔄 Future Tag
**Description:** Docker Compose working, paths fixed, Makefile ready

**Features (Added in Phase 1):**
- Dynamic path resolution (works from any directory)
- Docker Compose with 3 profiles
- Makefile for unified commands
- .env file with validation
- requirements.txt lock file

**Rollback Command:**
```bash
git checkout v3.0.0-phase1

# Use new Makefile commands
make install
make start
```

**When to Use:**
- Phase 2+ introduces issues but Phase 1 is solid
- Want Docker benefits without code restructuring
- Need stable base for continuing refactor

---

### v3.0.0-phase2 (After Code Architecture)
**Date:** TBD (After Phase 2 complete)
**Status:** 🔄 Future Tag
**Description:** app.py split into 10 modular files

**Features (Added in Phase 2):**
- Modular API structure (routers/, services/, middleware/)
- Code complexity <10
- Better maintainability
- All Phase 1 features

**Rollback Command:**
```bash
git checkout v3.0.0-phase2
make install
make start
```

**When to Use:**
- Phase 3+ introduces logging/config issues
- Want modular code without plugin architecture
- Phase 2 refactor is stable

---

### v3.0.0-phase4 (After Plugin Architecture)
**Date:** TBD (After Phase 4 complete)
**Status:** 🔄 Future Tag
**Description:** Plugin-based step types working

**Features (Added in Phase 4):**
- Entry point-based plugins (21 types)
- Custom step type support
- Migration tool for old playbooks
- All Phase 1-3 features

**Rollback Command:**
```bash
git checkout v3.0.0-phase4
make install
make start
```

**When to Use:**
- Phase 5+ testing reveals critical issues
- Want plugin architecture without new tests
- Phase 4 is stable for production

---

### v3.0.0-phase5 (After Testing)
**Date:** TBD (After Phase 5 complete)
**Status:** 🔄 Future Tag
**Description:** 80%+ test coverage, all tests passing

**Features (Added in Phase 5):**
- Comprehensive test suite
- Integration tests
- Performance tests
- All Phase 1-4 features

**Rollback Command:**
```bash
git checkout v3.0.0-phase5
make install
make test
make start
```

**When to Use:**
- Phase 6+ introduces API versioning issues
- Want well-tested code without API changes
- Phase 5 is production-ready

---

## Emergency Rollback Procedures

### Procedure 1: Quick Rollback (5 minutes)
**When:** Critical production issue, need immediate revert

```bash
# 1. Stop all servers
make stop
# OR
pkill -f uvicorn
docker-compose down

# 2. Revert to last stable tag
git checkout v2.4.0-final-stable
# OR for later phases
git checkout v3.0.0-phase1

# 3. Reinstall dependencies
pip install -e .

# 4. Start server
./venv/bin/uvicorn ignition_toolkit.api.app:app --host 0.0.0.0 --port 5000
# OR if Makefile exists
make start

# 5. Verify health
curl http://localhost:5000/health
```

---

### Procedure 2: Rollback with Data Preservation (15 minutes)
**When:** Need to revert but preserve execution history and credentials

```bash
# 1. Backup current data
mkdir -p /tmp/ignition-backup-$(date +%Y%m%d-%H%M%S)
cp -r ~/.ignition-toolkit /tmp/ignition-backup-$(date +%Y%m%d-%H%M%S)/
cp -r data/ /tmp/ignition-backup-$(date +%Y%m%d-%H%M%S)/

# 2. Export database (if schema changed)
sqlite3 ~/.ignition-toolkit/executions.db .dump > /tmp/ignition-backup-$(date +%Y%m%d-%H%M%S)/db_dump.sql

# 3. Stop servers
make stop

# 4. Revert code
git checkout <stable-tag>

# 5. Restore data (if compatible)
# If schema is same:
# (data already in ~/.ignition-toolkit, no action needed)

# If schema changed:
# Must manually migrate or use old schema

# 6. Reinstall and start
pip install -e .
make start
```

---

### Procedure 3: Rollback with Work Preservation (20 minutes)
**When:** Need to revert but save current WIP for later

```bash
# 1. Create WIP branch
git checkout -b wip/v3-refactor-$(date +%Y%m%d-%H%M%S)
git add -A
git commit -m "WIP: Save V3 refactor progress before rollback"
git push origin wip/v3-refactor-$(date +%Y%m%d-%H%M%S)

# 2. Backup data
mkdir -p /tmp/ignition-backup-$(date +%Y%m%d-%H%M%S)
cp -r ~/.ignition-toolkit /tmp/ignition-backup-$(date +%Y%m%d-%H%M%S)/
cp -r data/ /tmp/ignition-backup-$(date +%Y%m%d-%H%M%S)/

# 3. Stop servers
make stop

# 4. Revert to stable
git checkout master
git checkout <stable-tag>

# 5. Clean install
pip install -e .
cd frontend && npm install && npm run build && cd ..

# 6. Start server
make start

# 7. Document rollback
echo "Rolled back from V3 refactor on $(date)" >> .refactor/ROLLBACK_LOG.md
echo "WIP saved to branch: wip/v3-refactor-$(date +%Y%m%d-%H%M%S)" >> .refactor/ROLLBACK_LOG.md
echo "Data backed up to: /tmp/ignition-backup-$(date +%Y%m%d-%H%M%S)" >> .refactor/ROLLBACK_LOG.md
```

---

## Database Schema Migrations

### If Database Schema Changed

**Problem:** V3 changes database schema, can't directly use old data

**Solution 1: Use Old Schema (Simple)**
```bash
# Revert code, use old database
rm ~/.ignition-toolkit/executions.db
git checkout <old-tag>
pip install -e .
# Database will be recreated with old schema
```

**Solution 2: Migrate Data (Complex)**
```bash
# Export from new schema
sqlite3 ~/.ignition-toolkit/executions.db .dump > /tmp/new_schema.sql

# Checkout old version
git checkout <old-tag>

# Create old schema database
pip install -e .
./venv/bin/python -c "from ignition_toolkit.storage import get_database; get_database()"

# Manual migration required (write custom script)
# This is complex and depends on specific schema changes
```

**Solution 3: Start Fresh (Easiest)**
```bash
# Backup old data
cp -r ~/.ignition-toolkit ~/.ignition-toolkit.backup

# Remove database
rm ~/.ignition-toolkit/executions.db

# Revert and recreate
git checkout <old-tag>
pip install -e .
# Fresh database will be created
```

---

## Credentials Vault Rollback

**Important:** Credentials vault format should NOT change between versions.

**If Vault Format Changes:**
```bash
# 1. Export credentials from V3 (if possible)
./venv/bin/ignition-toolkit credential list

# 2. Manually record credentials (SECURELY)
# Write down credential names and values

# 3. Rollback code
git checkout <old-tag>

# 4. Re-add credentials
./venv/bin/ignition-toolkit credential add <name>
# Enter values manually
```

---

## Docker Rollback

### If Docker Compose Issues

**Problem:** Docker Compose not working, need to revert to shell scripts

```bash
# 1. Stop Docker
docker-compose down -v

# 2. Revert to pre-Docker version
git checkout v2.4.0-final-stable

# 3. Use old startup method
./venv/bin/uvicorn ignition_toolkit.api.app:app --host 0.0.0.0 --port 5000
```

---

## Verification After Rollback

### Checklist:
- [ ] Server starts successfully
- [ ] Health check returns "healthy"
- [ ] Frontend accessible at http://localhost:5000
- [ ] Can view playbooks list
- [ ] Can view executions history
- [ ] Can view credentials (encrypted, not plaintext)
- [ ] WebSocket connections work
- [ ] Can execute a simple test playbook
- [ ] Credentials vault accessible
- [ ] No errors in logs

### Verification Commands:
```bash
# Server health
curl http://localhost:5000/health | python3 -m json.tool

# API endpoints
curl http://localhost:5000/api/playbooks
curl http://localhost:5000/api/executions
curl http://localhost:5000/api/credentials

# Frontend
curl -I http://localhost:5000/

# Database
sqlite3 ~/.ignition-toolkit/executions.db "SELECT COUNT(*) FROM executions;"
```

---

## Common Rollback Scenarios

### Scenario 1: "Server won't start after V3 changes"
**Solution:** Procedure 1 (Quick Rollback) to v2.4.0-final-stable

### Scenario 2: "Plugin architecture broke existing playbooks"
**Solution:** Procedure 2 (with data) to v3.0.0-phase2 (before plugins)

### Scenario 3: "Need to demo working version urgently"
**Solution:** Procedure 1 (Quick) to v2.4.0-final-stable

### Scenario 4: "Docker issues, can't run locally"
**Solution:** Procedure 1 to v2.4.0-final-stable (uses direct uvicorn)

### Scenario 5: "Want to continue V3 later"
**Solution:** Procedure 3 (Work Preservation) to save WIP branch

---

## Rollback Decision Tree

```
Critical Issue?
├─ YES → Procedure 1 (Quick Rollback to v2.4.0)
└─ NO
   │
   Need to preserve data?
   ├─ YES → Procedure 2 (Rollback with Data Preservation)
   └─ NO
      │
      Want to continue V3 later?
      ├─ YES → Procedure 3 (Rollback with Work Preservation)
      └─ NO → Procedure 1 (Quick Rollback)
```

---

## Prevention (Before Needing Rollback)

### Best Practices:
1. **Commit frequently** - Small, working commits
2. **Test before committing** - Verify server starts and basic functionality works
3. **Tag at phase boundaries** - Create git tags after each phase completion
4. **Backup data** - Regular backups of ~/.ignition-toolkit/ and data/
5. **Document blockers** - Update ISSUES.md immediately when problems arise
6. **Incremental changes** - Don't change too much at once
7. **Keep v2.4.0 branch** - Maintain stable branch for emergency use

### Before Each Major Change:
```bash
# 1. Verify current state works
make test
make start
curl http://localhost:5000/health

# 2. Create checkpoint
git add -A
git commit -m "Checkpoint: Before <major change>"
git tag checkpoint-$(date +%Y%m%d-%H%M%S)

# 3. Make changes

# 4. Test immediately
make test
make start
curl http://localhost:5000/health

# 5. If broken, rollback immediately
git reset --hard HEAD^
```

---

## Contact Information (Emergency)

**User:** Nigel G
**Project:** Ignition Automation Toolkit
**Repository:** /git/ignition-playground

**If Claude Code Session Lost:**
1. Read `.refactor/PROGRESS.md` for current status
2. Read `.refactor/MASTER_PLAN.md` for overall plan
3. Read `.refactor/ISSUES.md` for known problems
4. Read `.refactor/DECISIONS.md` for architectural context

---

**Last Updated:** 2025-10-27 (Session 1)
**Current Version:** v2.4.0 (pre-refactor)
**Target Version:** v3.0.0 (in progress)
