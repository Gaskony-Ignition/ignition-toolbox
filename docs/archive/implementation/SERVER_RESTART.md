# Server Restart Procedure

**IMPORTANT: Follow this procedure EVERY TIME you need to restart the server after version updates or code changes.**

## When to Restart the Server

1. After version bumps (pyproject.toml)
2. After updating `__init__.py` version
3. After backend code changes (ignition_toolkit/*)
4. After frontend builds (frontend/dist/ changes)

## ✅ CORRECT Restart Procedure

```bash
# Step 1: Kill ALL running server instances (handles multiple background processes)
ps aux | grep "[i]gnition-toolkit serve" | awk '{print $2}' | xargs -r kill -9

# Step 2: Wait 2 seconds for ports to release
sleep 2

# Step 3: Start server in background with version-specific log file
source venv/bin/activate && \
nohup ignition-toolkit serve --host 0.0.0.0 --port 5000 > /tmp/ignition-v$(python -c "from ignition_toolkit import __version__; print(__version__)").log 2>&1 &

# Step 4: Wait 3 seconds for server to start
sleep 3

# Step 5: Verify health endpoint shows correct version
curl -s http://localhost:5000/health | jq -r '.version'
```

## Alternative: One-liner Restart

```bash
ps aux | grep "[i]gnition-toolkit serve" | awk '{print $2}' | xargs -r kill -9 && \
sleep 2 && \
source venv/bin/activate && \
nohup ignition-toolkit serve --host 0.0.0.0 --port 5000 > /tmp/ignition-server.log 2>&1 & \
sleep 3 && \
curl -s http://localhost:5000/health
```

## Common Mistakes to Avoid

### ❌ WRONG: Using pkill without -f
```bash
pkill ignition-toolkit  # Doesn't work - need full command match
```

### ❌ WRONG: Not waiting for port release
```bash
kill PID && ignition-toolkit serve  # Port 5000 still in use!
```

### ❌ WRONG: Using & without nohup
```bash
ignition-toolkit serve &  # Dies when terminal closes
```

### ❌ WRONG: Forgetting to activate venv
```bash
nohup ignition-toolkit serve &  # Uses wrong Python environment
```

## Version Update Checklist

When bumping version, update these files IN ORDER:

1. `pyproject.toml` - Update version field
2. `ignition_toolkit/__init__.py` - Update `__version__` and `__build_date__`
3. `CHANGELOG.md` - Add new version entry
4. Reinstall: `source venv/bin/activate && pip install -e . --force-reinstall --no-deps`
5. Commit: Version bump commit with all 3 files
6. Restart server: Use procedure above
7. Verify: `curl http://localhost:5000/health` shows new version

## Troubleshooting

### Server won't start
```bash
# Check if port 5000 is in use
lsof -i :5000

# Check server logs
tail -f /tmp/ignition-server.log
```

### Version shows old number
- Check you updated `__init__.py` (not just pyproject.toml)
- Verify reinstall worked: `pip show ignition-toolkit | grep Version`
- Ensure server was fully restarted (kill + start, not just restart)

### Multiple servers running
```bash
# Find all instances
ps aux | grep ignition-toolkit

# Kill all
ps aux | grep "[i]gnition-toolkit serve" | awk '{print $2}' | xargs -r kill -9
```

## Background Process Management

### Check running servers
```bash
ps aux | grep "[i]gnition-toolkit serve"
```

### View server logs
```bash
# Latest log file
tail -f /tmp/ignition-server.log

# Version-specific log
tail -f /tmp/ignition-v1.0.4.log
```

### Stop server gracefully
```bash
# Find PID
ps aux | grep "[i]gnition-toolkit serve"

# Send SIGTERM (graceful)
kill PID

# If hung, force kill
kill -9 PID
```

---

**Last Updated:** 2025-10-24
**Version:** 1.0.4
