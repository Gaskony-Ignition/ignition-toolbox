# Package Update Workflow

**Document Version:** 1.0
**Created:** 2025-10-26
**Last Updated:** 2025-10-26
**Owner:** Nigel G

This document defines the ongoing workflow for monitoring, evaluating, and applying package updates to the Ignition Automation Toolkit project.

---

## 🎯 Workflow Objectives

1. **Security:** Keep dependencies current to avoid known vulnerabilities
2. **Stability:** Test updates incrementally to minimize disruption
3. **Transparency:** Notify owner of available updates for approval
4. **Traceability:** Maintain detailed update history

---

## 📅 Update Check Schedule

### Monthly Routine Check
- **Frequency:** First Monday of each month
- **Scope:** All packages (Python + Frontend)
- **Process:** See "Monthly Check Procedure" below

### Security Alert Response
- **Trigger:** GitHub Security Advisory, CVE announcement, or security mailing list
- **Response Time:** Within 24 hours
- **Process:** See "Emergency Security Update" below

### User-Requested Check
- **Trigger:** User asks "Are there any updates available?"
- **Response:** Run immediate version check and report

---

## 🔍 Monthly Check Procedure

### Step 1: Search for Latest Versions

Run web searches for critical packages:

```bash
# Python Backend
- fastapi latest version
- pydantic latest version
- playwright python latest version
- anthropic sdk latest version
- cryptography python latest version
- sqlalchemy latest version
- uvicorn latest version

# Frontend
- react latest version
- vite latest version
- material-ui latest version
- typescript latest version
```

### Step 2: Update VERSION_TRACKING.md

1. Update "Last Checked" date
2. Update "Latest" column for each package
3. Update "Status" column (🟢/🟡/🔴)
4. Add notes for breaking changes
5. Update "Next Check Date"

### Step 3: Generate Update Notification

If updates are available, create notification using template below.

### Step 4: Await User Approval

Do NOT proceed with updates until user approves.

---

## 📢 Update Notification Template

When packages have updates available, notify the user with:

```markdown
## 📦 Package Updates Available - [Date]

I've checked for package updates. Here's what's available:

### 🔴 Critical Updates (Security/Major Versions Behind)
- **[package-name]**: [current] → [latest] - [reason why critical]

### 🟡 Recommended Updates (Features/Bug Fixes)
- **[package-name]**: [current] → [latest] - [brief description]

### 🟢 Optional Updates (Minor/Patch Versions)
- **[package-name]**: [current] → [latest]

### ⚠️ Known Issues
- **[package-name]**: [describe breaking changes or compatibility concerns]

### 📊 Summary
- Total packages outdated: [X]
- Critical: [X]
- Recommended: [X]
- Optional: [X]

Would you like me to proceed with updating these packages? I'll update them in tested groups and verify functionality after each group.

**Estimated Time:** [X] hours
**Risk Level:** [Low/Medium/High]
```

---

## ✅ Update Execution Process

Once user approves, follow this process:

### Phase 1: Preparation
1. ✅ Ensure working directory is clean (`git status`)
2. ✅ Create backup branch if needed
3. ✅ Update TodoWrite with all update groups
4. ✅ Note current package versions

### Phase 2: Group Updates

For each update group (see grouping strategy below):

1. **Update package.json or pyproject.toml**
2. **Install packages**
   - Python: `pip install -e .` or `pip install -e .[ai,dev]`
   - Frontend: `cd frontend && npm install`
3. **Run group-specific tests** (see testing matrix below)
4. **Mark todo as completed**
5. **If tests fail:** Rollback immediately, document issue

### Phase 3: Final Verification
1. Run full pytest suite
2. Start server and verify all endpoints
3. Build frontend and test UI
4. Test end-to-end workflow
5. Update VERSION_TRACKING.md with new versions
6. Add update history entry

### Phase 4: Commit
Create git commit with detailed message:
```
Update dependencies - [Date]

Updated packages:
- [package]: [old] → [new]
- [package]: [old] → [new]

Testing performed:
- pytest suite: ✅ [X tests passed]
- Server startup: ✅
- Frontend build: ✅
- Integration tests: ✅

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 📦 Update Grouping Strategy

### Group 1: Low-Risk Utilities (Backend)
**Packages:** python-dotenv, pyyaml, click, rich, python-multipart

**Update:**
```toml
# pyproject.toml
python-dotenv = ">=1.0.1"
pyyaml = ">=6.0.2"
click = ">=8.1.9"
rich = ">=13.10.1"
python-multipart = ">=0.0.20"
```

**Test:**
```bash
ignition-toolkit --version
ignition-toolkit credential list
```

---

### Group 2: Database Layer
**Packages:** sqlalchemy, aiosqlite

**Update:**
```toml
sqlalchemy = ">=2.0.44"
aiosqlite = ">=0.20.1"
```

**Test:**
```bash
pytest tests/test_credentials.py -v
pytest tests/test_startup/ -v
```

---

### Group 3: HTTP & Server
**Packages:** httpx, uvicorn, websockets

**Update:**
```toml
httpx = ">=0.28.1"
uvicorn[standard] = ">=0.38.0"
websockets = ">=14.0"
```

**Test:**
```bash
# Start server
./venv/bin/uvicorn ignition_toolkit.api.main:app --reload --port 8000

# In another terminal
curl http://localhost:8000/api/health
```

---

### Group 4: Core Framework
**Packages:** pydantic, pydantic-settings, fastapi

**Update:**
```toml
pydantic = ">=2.12.3"
pydantic-settings = ">=2.7.1"
fastapi = ">=0.120.0"
```

**Test:**
```bash
pytest tests/ -v
# Test all API endpoints
curl http://localhost:8000/api/playbooks
curl http://localhost:8000/api/credentials
```

---

### Group 5: Security (Critical)
**Packages:** cryptography

**Update:**
```toml
cryptography = ">=46.0.3"
```

**Pre-check:**
```bash
# Verify Rust toolchain supports MSRV 1.83.0
rustc --version
```

**Test:**
```bash
pytest tests/test_credentials.py -v
ignition-toolkit credential add test_cred
ignition-toolkit credential list
ignition-toolkit credential delete test_cred
```

---

### Group 6: Browser Automation
**Packages:** playwright

**Update:**
```toml
playwright = ">=1.55.0"
```

**Post-Install:**
```bash
PLAYWRIGHT_BROWSERS_PATH=/git/ignition-playground/data/.playwright-browsers \
./venv/bin/playwright install chromium
```

**Test:**
```bash
# Run Perspective test playbook
pytest tests/test_browser/ -v  # if exists
# Or manually test browser step
```

---

### Group 7: Frontend Dependencies
**Packages:** react, react-dom, @emotion/react, @tanstack/react-query, react-router-dom

**Update in frontend/package.json:**
```json
{
  "react": "^19.2.0",
  "react-dom": "^19.2.0",
  "@emotion/react": "^11.14.2",
  "@tanstack/react-query": "^5.90.8",
  "react-router-dom": "^7.11.2"
}
```

**Install & Test:**
```bash
cd frontend
npm install
npm run build
npm run preview  # Test build
```

---

### Group 8: Dev Tools (Code Quality)
**Packages:** pytest, pytest-asyncio, pytest-cov, black, ruff, mypy

**Update:**
```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.3.4",
    "pytest-asyncio>=0.25.3",
    "pytest-cov>=6.0.0",
    "black>=25.2.0",
    "ruff>=0.11.4",
    "mypy>=1.15.0",
]
```

**Test:**
```bash
pytest tests/ -v --cov=ignition_toolkit
black --check ignition_toolkit/
ruff check ignition_toolkit/
mypy ignition_toolkit/
```

**Note:** May find new issues - address before proceeding.

---

### Group 9: Build Tools
**Packages:** vite, eslint

**Pre-check:**
```bash
node --version  # Must be 20.19+ or 22.12+
```

**Update in frontend/package.json:**
```json
{
  "vite": "^7.1.9",
  "eslint": "^9.42.0"
}
```

**Test:**
```bash
cd frontend
npm run build
npm run lint
```

---

### Group 10: AI SDK (Special Handling)
**Package:** anthropic

**Update:**
```toml
[project.optional-dependencies]
ai = [
    "anthropic>=0.71.0",
]
```

**⚠️ REQUIRES CODE REFACTORING:**
1. Review migration guide: https://github.com/anthropics/anthropic-sdk-python/blob/main/CHANGELOG.md
2. Update `ignition_toolkit/ai/assistant.py`
3. Update AI step types in playbook engine
4. Test all AI-related functionality

**Test:**
```bash
pytest tests/test_ai/ -v  # if exists
# Manual test of AI features in UI
```

---

## 🔄 Server Restart Procedure

**IMPORTANT:** After ANY code changes (Python backend or JavaScript frontend), ALWAYS restart both servers to ensure changes are loaded.

### Kill Existing Servers
```bash
# Find and kill existing uvicorn processes
pkill -f uvicorn || true

# Find and kill existing vite dev server
pkill -f "vite" || true

# Or kill by port (if needed)
lsof -ti:8000 | xargs kill -9 2>/dev/null || true  # Backend
lsof -ti:5173 | xargs kill -9 2>/dev/null || true  # Frontend dev
```

### Start Backend Server
```bash
cd /git/ignition-playground
PLAYWRIGHT_BROWSERS_PATH=/git/ignition-playground/data/.playwright-browsers \
./venv/bin/uvicorn ignition_toolkit.api.app:app --reload --port 8000
```

### Start Frontend (Development Mode)
```bash
cd /git/ignition-playground/frontend
export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
npm run dev
```

### Verify Services Running
```bash
# Check backend
curl http://localhost:8000/api/health

# Check frontend (in browser)
# Navigate to http://localhost:5173
```

### When to Restart
- ✅ **After package updates** (Python or JavaScript)
- ✅ **After code changes** (backend or frontend)
- ✅ **After git pull** (if changes affect code)
- ✅ **Before testing new features**
- ✅ **If UI appears broken or outdated**

---

## 🧪 Testing Matrix

After each group update, run these tests:

| Test Type | Command | Pass Criteria |
|-----------|---------|---------------|
| **Unit Tests** | `pytest tests/ -v` | All tests pass |
| **CLI** | `ignition-toolkit --version` | Displays version |
| **Credentials** | `ignition-toolkit credential list` | No errors |
| **Server Restart** | See "Server Restart Procedure" above | Both servers running |
| **API Health** | `curl localhost:8000/api/health` | Returns {"status": "ok"} |
| **Frontend Build** | `cd frontend && npm run build` | Builds successfully |
| **Frontend Access** | Open http://localhost:5173 | UI loads, no console errors |
| **WebSocket** | Open UI, check console | WebSocket connects |
| **Browser** | Test Perspective playbook | Playwright works |

---

## 🚨 Emergency Security Update

If a critical security vulnerability is announced:

### Immediate Response (Within 24 hours)

1. **Assess Impact:**
   - Is the vulnerable package used in production?
   - What's the severity (CVSS score)?
   - Is there an exploit in the wild?

2. **Notify User:**
   ```markdown
   ## 🚨 CRITICAL SECURITY UPDATE REQUIRED

   **Package:** [package-name]
   **Current Version:** [version]
   **Vulnerable:** Yes
   **Severity:** [Critical/High/Medium]
   **CVE:** [CVE-####-####]

   **Vulnerability:** [brief description]

   **Recommended Action:** Update to [version] immediately.

   **Impact on Project:** [assess if this affects deployed instances]

   Shall I proceed with emergency update?
   ```

3. **If Approved:** Update immediately, test critical paths only, deploy ASAP

---

## 🔄 Rollback Procedure

If update causes issues:

### Immediate Rollback
```bash
# Revert config files
git checkout HEAD -- pyproject.toml frontend/package.json

# Reinstall old versions
pip install -e .
cd frontend && npm install

# Verify
pytest tests/test_startup/ -v
```

### Partial Rollback
Edit specific package versions in config files, reinstall.

### Document Issue
Add to VERSION_TRACKING.md:
```markdown
### [Date] - Failed Update: [package-name]
- **Attempted:** [old] → [new]
- **Issue:** [description of what broke]
- **Rollback:** Reverted to [old]
- **Action:** Investigate before next attempt
```

---

## 📋 Pre-Update Checklist

Before starting any update:

- [ ] Git working directory is clean
- [ ] VERSION_TRACKING.md is up to date
- [ ] TodoWrite has all update tasks
- [ ] User has approved the update plan
- [ ] Backup/branch created if doing major updates
- [ ] Node.js version verified (for frontend updates)
- [ ] Rust toolchain verified (for cryptography)
- [ ] Time allocated for testing (don't rush)

---

## 📊 Post-Update Checklist

After completing updates:

- [ ] All todos marked as completed
- [ ] VERSION_TRACKING.md updated with new versions
- [ ] Update history entry added
- [ ] Git commit created with detailed message
- [ ] Full integration test passed
- [ ] User notified of completion
- [ ] Next check date set in VERSION_TRACKING.md

---

## 🛠️ Troubleshooting Common Issues

### Playwright Installation Fails
```bash
# Ensure PLAYWRIGHT_BROWSERS_PATH is set
export PLAYWRIGHT_BROWSERS_PATH=/git/ignition-playground/data/.playwright-browsers
./venv/bin/playwright install chromium
```

### cryptography Build Fails
```bash
# Check Rust version
rustc --version  # Should be >= 1.83.0

# Update Rust if needed
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup update
```

### Frontend Build Fails After vite Update
```bash
# Check Node version
node --version  # Should be >= 20.19 or >= 22.12

# Update Node if needed via nvm
nvm install 20
nvm use 20
```

### Pydantic Validation Errors After Update
- Review Pydantic v2 migration guide
- Check for deprecated validator syntax
- Update `@validator` to `@field_validator`
- Update `Config` class to `model_config`

---

## 📚 Reference Links

- **Python Package Index:** https://pypi.org/
- **npm Registry:** https://www.npmjs.com/
- **Playwright Release Notes:** https://playwright.dev/python/docs/release-notes
- **FastAPI Release Notes:** https://fastapi.tiangolo.com/release-notes/
- **Pydantic Migration Guide:** https://docs.pydantic.dev/latest/migration/
- **Anthropic SDK Changelog:** https://github.com/anthropics/anthropic-sdk-python/blob/main/CHANGELOG.md
- **GitHub Security Advisories:** https://github.com/advisories

---

## 🤖 Claude Code Integration

This workflow is designed to be executed by Claude Code with user approval at key checkpoints:

1. **Monthly Check:** Claude runs searches, updates VERSION_TRACKING.md, notifies user
2. **User Approves:** User reviews notification and approves update plan
3. **Incremental Updates:** Claude updates in groups, tests after each group
4. **Issue Handling:** Claude stops if tests fail, notifies user, awaits guidance
5. **Completion:** Claude commits changes, updates docs, confirms with user

**User Interaction Points:**
- Approval before starting updates
- Notification if tests fail (decision to rollback or fix)
- Notification when updates complete
- Monthly update availability notifications

---

**Next Review:** 2025-11-26
**Version:** 1.0
**Status:** Active
