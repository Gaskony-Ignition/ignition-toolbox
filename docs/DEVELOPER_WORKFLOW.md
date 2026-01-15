# Developer Workflow Guide

**Last Updated:** 2025-11-02
**Version:** 4.1.0

This guide provides clear, unambiguous instructions for common development tasks in the Ignition Automation Toolkit.

---

## 📋 Table of Contents

1. [Starting the Server](#starting-the-server)
2. [Making Changes](#making-changes)
3. [Troubleshooting](#troubleshooting)
4. [Development Tips](#development-tips)

---

## 🚀 Starting the Server

### Production Mode (Recommended)

Start the server with all pre-flight checks:

```bash
ignition-toolkit server start
```

**What happens:**
- ✅ Checks if server already running
- ✅ Checks if port 5000 is available
- ✅ Checks if frontend build is stale
- ✅ Rebuilds frontend if needed (asks for confirmation)
- ✅ Clears Python bytecode cache
- ✅ Checks database accessibility
- ✅ Starts server

**Expected output:**
```
Starting Ignition Automation Toolkit Server

Running pre-flight checks...

✓ Frontend build is fresh
✓ No bytecode cache to clear
✓ Database accessible

✓ All pre-flight checks passed

Starting server on http://0.0.0.0:5000
Production mode
  Tip: Use --dev flag for auto-reload during development

Press CTRL+C to stop the server
```

---

### Development Mode (Auto-reload)

For faster development cycles with automatic code reloading:

```bash
ignition-toolkit server start --dev
```

**What this does:**
- **Backend changes:** Server automatically restarts when Python files change
- **Frontend changes:** Still requires manual rebuild (handled by pre-flight checks on restart)

**Use when:**
- You're actively developing backend Python code
- You want to see changes immediately without manually restarting

**⚠️ Note:** Development mode uses `uvicorn --reload` which can be slower on large codebases.

---

### Fast Startup (Skip Checks)

Skip pre-flight checks for faster startup (use with caution):

```bash
ignition-toolkit server start --skip-checks
```

**When to use:**
- You know the frontend is already built
- You're doing rapid restart cycles for testing
- You're confident everything is up to date

**⚠️ Warning:** Skipping checks may lead to serving stale frontend builds!

---

### Custom Port

Start server on a different port:

```bash
ignition-toolkit server start --port 8000
```

**Use when:**
- Port 5000 is already in use
- You want to run multiple instances
- You're running behind a reverse proxy

---

## 🔄 Making Changes

### Backend Changes (Python)

**Location:** `/git/ignition-playground/ignition_toolkit/`

**Workflow:**

1. **Edit Python files** in `ignition_toolkit/` directory

2. **Restart server:**

   **Option A: Development mode (recommended)**
   ```bash
   ignition-toolkit server start --dev
   ```
   - Changes auto-reload
   - No manual restart needed

   **Option B: Production mode**
   ```bash
   # Stop server
   CTRL+C (or: ignition-toolkit server stop)

   # Start server
   ignition-toolkit server start
   ```
   - Pre-flight checks run automatically
   - Bytecode cache cleared automatically

3. **Verify changes** in browser

**Example:**
```bash
# Edit file
vim ignition_toolkit/api/routers/playbooks.py

# If using --dev mode: changes apply automatically
# If using production mode: restart server
ignition-toolkit server stop
ignition-toolkit server start
```

---

### Frontend Changes (React/TypeScript)

**Location:** `/git/ignition-playground/frontend/src/`

**Workflow:**

1. **Edit files** in `frontend/src/` directory

2. **Restart server** (pre-flight checks will detect stale build):

   ```bash
   ignition-toolkit server start
   ```

   **Expected output:**
   ```
   Running pre-flight checks...

   ⚠ Frontend build is stale
     Source changed: ExecutionControls.tsx
     Rebuild frontend? [Y/n]: y
   Running frontend rebuild...
   ✓ Frontend rebuilt successfully
   ```

3. **Refresh browser** (frontend is now updated)

**Alternative: Manual rebuild**

If you want to rebuild without restarting server:

```bash
./rebuild-frontend.sh
```

**Then refresh browser** - no server restart needed!

---

### Database Schema Changes

**Location:** `/git/ignition-playground/ignition_toolkit/storage/models.py`

**Workflow:**

1. **Edit model files**

2. **Create migration** (future: Alembic integration)
   ```bash
   # TODO: Add migration command
   # alembic revision --autogenerate -m "Description"
   ```

3. **Run migration**
   ```bash
   # TODO: Add migration command
   # alembic upgrade head
   ```

4. **Restart server**
   ```bash
   ignition-toolkit server start
   ```

---

### Playbook Changes

**Location:** `/git/ignition-playground/playbooks/`

**Workflow:**

1. **Edit YAML files** in `playbooks/` directory

2. **No restart needed!**
   - Playbooks are loaded fresh on each execution
   - Just refresh browser and run the playbook

**Example:**
```bash
# Edit playbook
vim playbooks/gateway/module_upgrade.yaml

# Just run it - no restart needed
# (Playbooks are loaded dynamically)
```

---

## 🔧 Troubleshooting

### Problem: Changes Not Showing Up

**Symptom:** You made changes but don't see them in the UI.

**Solution:** Follow this checklist:

1. **Check if you restarted the server:**
   ```bash
   ignition-toolkit server stop
   ignition-toolkit server start
   ```

2. **Check if frontend was rebuilt:**
   - Pre-flight checks should have prompted for rebuild
   - If you see "Frontend build is fresh" but changes aren't showing:
     ```bash
     ./rebuild-frontend.sh
     ```

3. **Clear browser cache (unlikely, but possible):**
   - Hard refresh: `CTRL+SHIFT+R` (Linux/Windows) or `CMD+SHIFT+R` (Mac)
   - Clear browser cache in settings

4. **Check if correct file was edited:**
   ```bash
   # Verify file modification time
   stat frontend/src/components/ExecutionControls.tsx
   stat frontend/dist/index.html

   # Source should be NEWER than build if stale
   ```

---

### Problem: Server Won't Start (Port Already in Use)

**Symptom:** "ERROR: Port 5000 is already in use"

**Solution:**

```bash
# Option 1: Stop existing server
ignition-toolkit server stop --force

# Option 2: Use different port
ignition-toolkit server start --port 8000

# Option 3: Find and kill process manually
lsof -i :5000
kill <PID>
```

---

### Problem: Server Won't Start (Already Running)

**Symptom:** "ERROR: Server already running"

**Solution:**

```bash
# Stop server gracefully
ignition-toolkit server stop

# If that doesn't work, force kill
ignition-toolkit server stop --force

# Check status
ignition-toolkit server status
```

---

### Problem: Frontend Build Fails

**Symptom:** "Frontend rebuild failed" during pre-flight checks

**Possible causes:**

1. **npm not installed:**
   ```bash
   # Install Node.js and npm
   # See: https://nodejs.org/
   ```

2. **node_modules missing:**
   ```bash
   cd frontend
   npm install
   ```

3. **TypeScript errors:**
   ```bash
   cd frontend
   npm run build
   # Review error messages
   ```

---

### Problem: Database is Locked

**Symptom:** "Database is locked (may be in use by another process)"

**Solution:**

```bash
# Stop all server processes
ignition-toolkit server stop --force

# Check for SQLite lock files
ls -la ~/.ignition-toolkit/*.db*

# Remove lock files (ONLY if server is stopped!)
rm ~/.ignition-toolkit/database.db-wal
rm ~/.ignition-toolkit/database.db-shm

# Restart server
ignition-toolkit server start
```

---

### Problem: Python Import Errors After Changes

**Symptom:** "ImportError: cannot import name ..."

**Cause:** Stale bytecode cache

**Solution:**

```bash
# Clear all bytecode cache
find ignition_toolkit -name "*.pyc" -delete
find ignition_toolkit -type d -name "__pycache__" -exec rm -rf {} +

# Restart server (pre-flight checks will also clear cache)
ignition-toolkit server start
```

---

## 💡 Development Tips

### 1. Use Development Mode for Backend Work

```bash
ignition-toolkit server start --dev
```

**Benefits:**
- Automatic reload on Python file changes
- Faster development cycle
- No manual restarts needed

**When to avoid:**
- Testing production performance
- Checking startup time
- Debugging startup issues

---

### 2. Keep Terminal Output Visible

**Why:**
- Pre-flight checks show what's happening
- Error messages appear immediately
- You see when auto-reload triggers (in dev mode)

**Tip:** Use a terminal multiplexer like tmux or screen to keep server logs visible.

---

### 3. Use Git for Version Control

```bash
# Before making changes
git checkout -b feature/my-new-feature

# After making changes
git add <files>
git commit -m "Description of changes"

# If something breaks, easy to revert
git checkout main
```

---

### 4. Run Tests Before Committing

```bash
# Run backend tests
/git/ignition-playground/venv/bin/python -m pytest tests/ -v

# Run frontend tests (if available)
cd frontend
npm test
```

---

### 5. Check Server Status

```bash
# Comprehensive health check
ignition-toolkit server status

# Just check if running
ignition-toolkit server status || echo "Server is not running"
```

---

## 📊 Common Workflows

### Workflow 1: Fix a Bug

```bash
# 1. Create branch
git checkout -b fix/issue-123

# 2. Edit code
vim ignition_toolkit/api/routers/playbooks.py

# 3. Test changes
ignition-toolkit server start --dev
# Make requests, verify fix

# 4. Run tests
/git/ignition-playground/venv/bin/python -m pytest tests/ -v

# 5. Commit
git add ignition_toolkit/api/routers/playbooks.py
git commit -m "Fix: ..."

# 6. Push
git push origin fix/issue-123
```

---

### Workflow 2: Add New Frontend Feature

```bash
# 1. Create branch
git checkout -b feature/new-ui-component

# 2. Edit frontend code
vim frontend/src/components/NewComponent.tsx

# 3. Restart server (auto-rebuilds frontend)
ignition-toolkit server start
# Answer 'y' to rebuild prompt

# 4. Test in browser
# Open http://localhost:5000

# 5. Iterate quickly
# Edit code -> CTRL+C -> restart server -> test
# OR use ./rebuild-frontend.sh + browser refresh (no server restart)

# 6. Commit when done
git add frontend/src/components/NewComponent.tsx
git commit -m "Add: ..."
```

---

### Workflow 3: Test on Different Port

```bash
# Start on port 8000
ignition-toolkit server start --port 8000

# In another terminal, start on port 9000
ignition-toolkit server start --port 9000

# Now you have two instances running
# Useful for testing concurrent access
```

---

## 🎯 Quick Reference

| Task | Command |
|------|---------|
| Start server (production) | `ignition-toolkit server start` |
| Start server (development) | `ignition-toolkit server start --dev` |
| Stop server | `ignition-toolkit server stop` |
| Force stop server | `ignition-toolkit server stop --force` |
| Check server status | `ignition-toolkit server status` |
| Rebuild frontend manually | `./rebuild-frontend.sh` |
| Clear Python cache | `find ignition_toolkit -name "*.pyc" -delete` |
| Run tests | `/git/ignition-playground/venv/bin/python -m pytest tests/ -v` |
| Skip pre-flight checks | `ignition-toolkit server start --skip-checks` |
| Custom port | `ignition-toolkit server start --port 8000` |

---

## 📚 Related Documentation

- [README.md](../README.md) - Project overview
- [PROJECT_GOALS.md](../PROJECT_GOALS.md) - Project vision and goals
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture
- [CHANGELOG.md](../CHANGELOG.md) - Version history
- [docs/getting_started.md](getting_started.md) - Installation guide
- [docs/playbook_syntax.md](playbook_syntax.md) - YAML reference

---

**Questions or Issues?**
- Check the [Troubleshooting](#troubleshooting) section above
- Review existing issues on GitHub
- Create a new issue with reproduction steps

---

**Last Updated:** 2025-11-02
**Maintainer:** Nigel G
**Version:** 4.1.0
