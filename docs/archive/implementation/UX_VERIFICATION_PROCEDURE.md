# UX Verification Procedure

**Created:** 2025-10-26
**Purpose:** Standard checklist before asking user to test UX changes
**Owner:** Claude Code

---

## ⚠️ CRITICAL RULE

**NEVER ask the user to test the UX without completing ALL steps in this procedure first.**

---

## 📋 Pre-Test Verification Checklist

### Step 1: Clean Environment

**Kill all old servers:**
```bash
cd /git/ignition-playground
pkill -9 -f "uvicorn ignition_toolkit" || true
pkill -9 -f "vite.*dev" || true
pkill -9 -f "npm run dev" || true
sleep 2
```

**Verify only expected processes remain:**
```bash
echo "=== Ignition Backend (should see ZERO) ==="
ps aux | grep "uvicorn ignition_toolkit" | grep -v grep | wc -l

echo "=== npm/vite dev servers (should see ZERO) ==="
ps aux | grep -E "npm run dev|vite" | grep -v grep | wc -l
```

**Expected output:** Both commands should show `0`

**Clean up ports:**
```bash
# Kill anything on our ports
lsof -ti:5000 | xargs -r kill -9
lsof -ti:8000 | xargs -r kill -9
lsof -ti:8001 | xargs -r kill -9
sleep 2
```

---

### Step 2: Frontend Build Check

**Check if rebuild needed:**
```bash
ls -lt frontend/dist/assets/*.js | head -1
ls -lt frontend/src/components/*.tsx | head -1
```

**If frontend source files are newer than dist, rebuild:**
```bash
cd frontend
npm run build
cd ..
```

**Verify:** Build completes successfully with "✓ built in X.XXs"

---

### Step 3: Get Current Version
```bash
grep '"version"' frontend/package.json | head -1
```

**Record the version number** (e.g., "1.0.34")

---

### Step 4: Start Backend on Port 5000

```bash
cd /git/ignition-playground
PLAYWRIGHT_BROWSERS_PATH=/git/ignition-playground/data/.playwright-browsers \
./venv/bin/uvicorn ignition_toolkit.api.app:app --reload --port 5000 \
> /tmp/backend_$(date +%Y%m%d_%H%M%S).log 2>&1 &

echo $! > /tmp/backend.pid
```

**Record the PID** from /tmp/backend.pid

---

### Step 5: Wait for Backend Ready

```bash
for i in {1..30}; do
  curl -s http://localhost:5000/health > /dev/null 2>&1 && break
  sleep 1
done
```

**Verify:** Command exits successfully (backend responds)

---

### Step 6: Test API Health
```bash
curl -s http://localhost:5000/health
```

**Expected output:** `{"status":"healthy","ready":true,"version":"1.0.34",...}`

---

### Step 7: Test Frontend Serving
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/
```

**Expected output:** `200`

---

### Step 8: Verify Static Files
```bash
curl -s http://localhost:5000/ | grep -o 'index-[^"]*\.js'
```

**Verify:** Shows the latest JavaScript bundle name (matches frontend/dist/index.html)

---

### Step 9: Check Version Endpoint
```bash
curl -s http://localhost:5000/api/health
```

**Note:** Version should match package.json

---

### Step 10: Final Process Verification

**Verify only ONE backend is running:**
```bash
echo "=== FINAL CHECK: Backend Processes ==="
ps aux | grep "uvicorn ignition_toolkit" | grep -v grep
```

**Expected:** Should see exactly ONE process on port 5000

**Verify no dev servers:**
```bash
echo "=== FINAL CHECK: Dev Servers ==="
ps aux | grep -E "npm run dev|vite" | grep -v grep || echo "None (GOOD!)"
```

**Expected:** Should see "None (GOOD!)" or empty output

---

### Step 11: Document in Response

When all checks pass, include this in your response to the user:

```markdown
## ✅ UX Verification Complete

**Status:** Ready for testing
**Version:** [VERSION from package.json]
**Access URL:** http://localhost:5000
**Backend PID:** [PID]
**Backend logs:** `tail -f /tmp/backend_[timestamp].log`

**Process Status:**
- ✅ Exactly 1 backend server running (PID: [PID])
- ✅ 0 npm/vite dev servers
- ✅ All old servers cleaned up

### What to Check:
1. Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
2. Verify version number in UI footer matches: [VERSION]
3. Check browser console (F12) for errors
4. Test the specific changes made

### If UI Shows Old Version:
1. Hard refresh (Ctrl+Shift+R)
2. Clear browser cache
3. Check version in footer
4. If still old, check backend logs for static file serving errors
```

---

## 🔴 Common Failure Causes

| Issue | Cause | Fix |
|-------|-------|-----|
| UX not loading | Frontend not built | Run `npm run build` in frontend/ |
| Old version showing | Browser cache | Hard refresh (Ctrl+Shift+R) |
| 404 errors | Wrong port (8000 not 5000) | Always use port 5000 |
| Backend errors | Multiple servers running | Kill all, start fresh |
| Static files 404 | Dist files not found | Rebuild frontend |

---

## 📝 Backend Server Management

### Standard Start Command (ALWAYS USE THIS)
```bash
cd /git/ignition-playground
PLAYWRIGHT_BROWSERS_PATH=/git/ignition-playground/data/.playwright-browsers \
./venv/bin/uvicorn ignition_toolkit.api.app:app --reload --port 5000
```

### Find Running Backend
```bash
ps aux | grep "uvicorn ignition_toolkit" | grep -v grep
```

### Kill Backend
```bash
pkill -9 -f "uvicorn ignition_toolkit"
```

### Check Backend Logs
```bash
tail -f /tmp/backend_*.log
```

---

## ⚡ Quick Verification Script

For quick checks, run these commands:

```bash
# 1. Clean start
cd /git/ignition-playground
pkill -9 -f "uvicorn ignition_toolkit" || true
sleep 2

# 2. Start backend
PLAYWRIGHT_BROWSERS_PATH=/git/ignition-playground/data/.playwright-browsers \
./venv/bin/uvicorn ignition_toolkit.api.app:app --reload --port 5000 &

# 3. Wait and test
sleep 5
curl -s http://localhost:5000/health
curl -s -o /dev/null -w "Frontend: %{http_code}\n" http://localhost:5000/

# 4. Get version
grep version frontend/package.json | head -1
```

---

## 🎯 Version Number Verification

### Where Version is Defined
- **Package:** `frontend/package.json` - `"version": "X.X.X"`
- **Pyproject:** `pyproject.toml` - `version = "X.X.X"`

### Where Version Should Display
- **UI Footer:** Check bottom of every page
- **About/Settings:** If implemented
- **Console:** Check on page load

### Verify Version Match
```bash
# Frontend version
grep '"version"' frontend/package.json | head -1 | awk -F'"' '{print $4}'

# Backend version
grep '^version' pyproject.toml | head -1 | awk -F'"' '{print $2}'

# They should match!
```

---

## 📌 Remember

1. **ALWAYS** use port 5000 (NOT 8000, NOT 8001)
2. **ALWAYS** rebuild frontend after code changes
3. **ALWAYS** kill old servers before starting new ones
4. **ALWAYS** verify health endpoint before declaring ready
5. **ALWAYS** include version number in response to user
6. **ALWAYS** remind user to hard refresh browser

---

## 🔄 After Code Changes

| Change Type | Actions Required |
|-------------|------------------|
| **Frontend code** | Rebuild (`npm run build`), restart backend, hard refresh |
| **Backend code** | Restart backend (reload mode auto-restarts) |
| **Playbook YAML** | No restart needed (loaded dynamically) |
| **Package updates** | Reinstall packages, rebuild frontend, restart backend |

---

**Last Updated:** 2025-10-26
**Review Frequency:** Update when UX verification fails
**Status:** Active
