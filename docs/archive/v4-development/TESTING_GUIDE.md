# Testing Guide - Ignition Automation Toolkit

This guide walks you through testing all the features we just built in Phases 3-6.

---

## 🔧 Prerequisites

1. **Python 3.10+** installed
2. **Git repository** at `/git/ignition-playground`
3. **Ignition Gateway** (optional, for Gateway tests)

---

## 📦 Installation

```bash
# Navigate to project
cd /git/ignition-playground

# Install in development mode
pip install -e .

# Install Playwright browsers (for browser automation)
playwright install chromium

# Verify installation
ignition-toolkit --version
```

---

## ✅ Test 1: Credential Management

```bash
# Initialize vault
ignition-toolkit init

# Add a test credential
ignition-toolkit credential add test_gateway \
  --username admin \
  --password password123 \
  --description "Test Gateway Credential"

# List credentials
ignition-toolkit credential list

# Should see: test_gateway | admin | Test Gateway Credential
```

**Expected Result**: Credential stored and encrypted in `~/.ignition-toolkit/`

---

## ✅ Test 2: Playbook Listing

```bash
# List available playbooks
ignition-toolkit playbook list
```

**Expected Result**: Should show 6 playbooks:
- examples/simple_health_check.yaml
- gateway/module_upgrade.yaml
- gateway/backup_and_restart.yaml
- browser/web_login_test.yaml
- browser/ignition_web_test.yaml
- browser/screenshot_audit.yaml

---

## ✅ Test 3: YAML Parsing

```bash
# Try to load a playbook (this will validate YAML)
python3 << 'EOF'
from pathlib import Path
from ignition_toolkit.playbook.loader import PlaybookLoader

loader = PlaybookLoader()
playbook = loader.load_from_file(Path("playbooks/examples/simple_health_check.yaml"))

print(f"✅ Loaded: {playbook.name} v{playbook.version}")
print(f"   Parameters: {len(playbook.parameters)}")
print(f"   Steps: {len(playbook.steps)}")
EOF
```

**Expected Result**:
```
✅ Loaded: Simple Health Check v1.0
   Parameters: 2
   Steps: 7
```

---

## ✅ Test 4: Parameter Resolution

```bash
# Test parameter resolution
python3 << 'EOF'
from ignition_toolkit.playbook.parameters import ParameterResolver
from ignition_toolkit.credentials import CredentialVault, Credential

# Create test credential
vault = CredentialVault()
vault.save_credential(Credential(
    name="test_param",
    username="testuser",
    password="testpass"
))

# Test resolver
resolver = ParameterResolver(
    credential_vault=vault,
    parameters={"url": "http://localhost:8088"},
    variables={"step_name": "Login"}
)

# Test resolution
result1 = resolver.resolve("{{ parameter.url }}")
result2 = resolver.resolve("{{ variable.step_name }}")
result3 = resolver.resolve("{{ credential.test_param }}")

print(f"✅ Parameter resolution:")
print(f"   URL: {result1}")
print(f"   Variable: {result2}")
print(f"   Credential: {result3.username} / {result3.password}")

# Cleanup
vault.delete_credential("test_param")
EOF
```

**Expected Result**: All three types of references resolved correctly

---

## ✅ Test 5: Playbook Export/Import

```bash
# Export a playbook to JSON
ignition-toolkit playbook export \
  playbooks/examples/simple_health_check.yaml \
  --output /tmp/test_export.json

# Check the exported file
cat /tmp/test_export.json | jq '.name, ._export_metadata'

# Import it back
ignition-toolkit playbook import /tmp/test_export.json \
  --output-dir /tmp/imported

# Verify import
ls -la /tmp/imported/

# Cleanup
rm /tmp/test_export.json
rm -rf /tmp/imported
```

**Expected Result**: Playbook exported, credentials stripped, and successfully re-imported

---

## ✅ Test 6: FastAPI Server

```bash
# Start the server in background
ignition-toolkit serve --port 5000 &
SERVER_PID=$!

# Wait for server to start
sleep 3

# Test health endpoint
curl http://localhost:5000/health | jq

# Test playbooks endpoint
curl http://localhost:5000/api/playbooks | jq

# Stop server
kill $SERVER_PID
```

**Expected Result**:
- Health check returns `{"status": "healthy", ...}`
- Playbooks endpoint returns list of 6 playbooks

---

## ✅ Test 7: Web UI

```bash
# Start server
ignition-toolkit serve --port 5000

# Open browser to http://localhost:5000
# Should see:
# - Dashboard with stats
# - Playbook count (6)
# - WebSocket status (green when connected)
# - List of available playbooks
```

**Expected Result**: Web UI loads and displays correctly

---

## ✅ Test 8: Browser Automation (Basic)

```bash
# Test browser manager
python3 << 'EOF'
import asyncio
from ignition_toolkit.browser import BrowserManager

async def test_browser():
    async with BrowserManager(headless=False, slow_mo=500) as browser:
        await browser.navigate("https://example.com")
        await browser.screenshot("test_example_com")
        print("✅ Browser automation works!")
        print(f"   Screenshot saved to: {browser.screenshots_dir}")

asyncio.run(test_browser())
EOF
```

**Expected Result**:
- Browser opens
- Navigates to example.com
- Screenshot saved to `./data/screenshots/test_example_com.png`

---

## ✅ Test 9: Playbook Execution (No Gateway)

Create a simple test playbook without Gateway dependencies:

```bash
# Create test playbook
cat > /tmp/test_simple.yaml << 'EOF'
name: "Simple Test"
version: "1.0"
description: "Test playbook without Gateway"

parameters:
  - name: test_message
    type: string
    required: false
    default: "Hello from playbook!"

steps:
  - id: log1
    name: "Log Start"
    type: utility.log
    parameters:
      message: "Starting test execution"
      level: "info"

  - id: sleep
    name: "Wait a Bit"
    type: utility.sleep
    parameters:
      seconds: 2

  - id: set_var
    name: "Set Variable"
    type: utility.set_variable
    parameters:
      name: "test_var"
      value: "test_value"

  - id: log2
    name: "Log End"
    type: utility.log
    parameters:
      message: "{{ parameter.test_message }}"
      level: "info"
EOF

# Run it
ignition-toolkit playbook run /tmp/test_simple.yaml \
  --param test_message="Test completed successfully!"

# Cleanup
rm /tmp/test_simple.yaml
```

**Expected Result**:
- Playbook executes all 4 steps
- Shows progress in CLI
- Final status: COMPLETED

---

## ✅ Test 10: Gateway Operations (Requires Gateway)

**Prerequisites**: Running Ignition Gateway at http://localhost:8088

```bash
# Run the health check playbook
ignition-toolkit playbook run \
  playbooks/examples/simple_health_check.yaml \
  --param gateway_url=http://localhost:8088 \
  --param gateway_credential=test_gateway

# Check execution in database
python3 << 'EOF'
from ignition_toolkit.storage import get_database

db = get_database()
with db.session_scope() as session:
    from ignition_toolkit.storage.models import ExecutionModel
    executions = session.query(ExecutionModel).all()
    for exec in executions:
        print(f"Execution: {exec.playbook_name} - {exec.status}")
EOF
```

**Expected Result**:
- Connects to Gateway
- Runs all health check steps
- Execution saved to database

---

## ✅ Test 11: Pause/Resume/Skip Control

```bash
# Create test with long steps
cat > /tmp/test_control.yaml << 'EOF'
name: "Control Test"
version: "1.0"

steps:
  - id: step1
    name: "Step 1"
    type: utility.sleep
    parameters:
      seconds: 5

  - id: step2
    name: "Step 2"
    type: utility.sleep
    parameters:
      seconds: 5

  - id: step3
    name: "Step 3"
    type: utility.sleep
    parameters:
      seconds: 5
EOF

# Run with API in background
ignition-toolkit serve --port 5000 &
SERVER_PID=$!
sleep 3

# Start execution
EXEC_ID=$(curl -s -X POST http://localhost:5000/api/executions \
  -H "Content-Type: application/json" \
  -d '{"playbook_path": "/tmp/test_control.yaml", "parameters": {}}' \
  | jq -r '.execution_id')

echo "Execution started: $EXEC_ID"

# Wait a bit, then pause
sleep 3
curl -X POST http://localhost:5000/api/executions/$EXEC_ID/pause
echo "Paused"

# Wait, then resume
sleep 2
curl -X POST http://localhost:5000/api/executions/$EXEC_ID/resume
echo "Resumed"

# Cleanup
sleep 10
kill $SERVER_PID
rm /tmp/test_control.yaml
```

**Expected Result**: Execution pauses and resumes as commanded

---

## ✅ Test 12: WebSocket Real-Time Updates

```bash
# Start server
ignition-toolkit serve --port 5000 &
SERVER_PID=$!
sleep 3

# In another terminal, use websocat or browser console:
# websocat ws://localhost:5000/ws/executions

# Then trigger execution:
curl -X POST http://localhost:5000/api/executions \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_path": "playbooks/examples/simple_health_check.yaml",
    "parameters": {
      "gateway_url": "http://localhost:8088",
      "gateway_credential": "test_gateway"
    },
    "gateway_url": "http://localhost:8088"
  }'

# Should see real-time updates in WebSocket connection

# Cleanup
kill $SERVER_PID
```

**Expected Result**: WebSocket receives execution updates in real-time

---

## 🎯 Success Criteria

All tests should pass with:
- ✅ No Python import errors
- ✅ No YAML parsing errors
- ✅ Credentials encrypted correctly
- ✅ Playbooks load and validate
- ✅ API endpoints respond
- ✅ WebSocket connects
- ✅ Browser automation works
- ✅ Database tracking works

---

## 🐛 Troubleshooting

### Import Errors
```bash
# Reinstall package
pip install -e . --force-reinstall
```

### Playwright Issues
```bash
# Reinstall browsers
playwright install --force chromium
```

### Database Issues
```bash
# Reset database
rm -f ./data/toolkit.db
# Restart application - will recreate
```

### Port Already in Use
```bash
# Kill existing process
lsof -ti:5000 | xargs kill -9

# Or use different port
ignition-toolkit serve --port 5001
```

---

## 📊 Test Results Template

Use this to track your testing:

```
[ ] Test 1: Credential Management
[ ] Test 2: Playbook Listing
[ ] Test 3: YAML Parsing
[ ] Test 4: Parameter Resolution
[ ] Test 5: Export/Import
[ ] Test 6: FastAPI Server
[ ] Test 7: Web UI
[ ] Test 8: Browser Automation
[ ] Test 9: Playbook Execution (No Gateway)
[ ] Test 10: Gateway Operations (with Gateway)
[ ] Test 11: Pause/Resume/Skip
[ ] Test 12: WebSocket Updates

Overall Status: [ PASS / FAIL ]
Notes:
```

---

**Ready to test! Good luck! 🚀**
