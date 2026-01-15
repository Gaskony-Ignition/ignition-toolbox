# Playbook Best Practices

**Version:** 3.0
**Last Updated:** 2025-10-27
**Audience:** Playbook authors and test engineers

This guide provides best practices for writing maintainable, reliable, and reusable playbooks in the Ignition Automation Toolkit.

---

## Table of Contents

1. [Domain Separation (Critical Rule)](#domain-separation-critical-rule)
2. [Credential Management](#credential-management)
3. [Parameter Design](#parameter-design)
4. [Step Organization](#step-organization)
5. [Error Handling](#error-handling)
6. [Composable Playbooks](#composable-playbooks)
7. [Browser Automation Tips](#browser-automation-tips)
8. [Testing Playbooks](#testing-playbooks)
9. [Common Pitfalls](#common-pitfalls)
10. [Example Patterns](#example-patterns)

---

## Domain Separation (Critical Rule)

**⚠️ CRITICAL: Playbooks must be Gateway-only OR Perspective-only OR Designer-only - NEVER mixed.**

### Why Domain Separation?

- **Simpler execution model** - Clear lifecycle (Gateway vs Browser)
- **Easier debugging** - Problems isolated to single domain
- **Better composability** - Mix verified playbooks from same domain
- **Cleaner step types** - No ambiguity about context

### ✅ CORRECT Domain Separation

```yaml
# playbooks/gateway/module_upgrade.yaml
name: "Module Upgrade"
category: "gateway"  # ← Gateway domain

steps:
  - type: gateway.login       # ← Gateway step
  - type: gateway.upload_module
  - type: gateway.wait_for_module_installation
  - type: gateway.restart
```

```yaml
# playbooks/perspective/login_test.yaml
name: "Perspective Login Test"
category: "perspective"  # ← Perspective domain

steps:
  - type: browser.navigate    # ← Browser step
  - type: browser.fill
  - type: browser.click
  - type: browser.verify
```

### ❌ WRONG - Mixed Domains

```yaml
# ❌ DON'T DO THIS
name: "Module Upload and Test"
category: "mixed"  # ← BAD

steps:
  - type: gateway.upload_module  # Gateway domain
  - type: browser.navigate        # ← Browser domain - WRONG!
  - type: browser.verify          # ← Mixing domains breaks execution
```

### Solution: Use Separate Playbooks

Instead of mixing, create two playbooks:

1. `gateway/module_upload.yaml` - Gateway operations
2. `perspective/test_new_module.yaml` - Browser testing

Then run them sequentially or create a third playbook that calls both using `playbook.run`.

---

## Credential Management

### Never Hardcode Credentials

**❌ INSECURE - Don't do this:**
```yaml
parameters:
  - name: username
    type: string
    default: "admin"        # ← Hardcoded!
  - name: password
    type: string
    default: "password123"  # ← INSECURE! Never commit passwords
```

### ✅ Use Credential References

**Option 1: Direct credential reference (recommended)**
```yaml
name: "Gateway Login"
credentials:
  - gateway_admin  # ← Reference to stored credential

steps:
  - type: gateway.login
    parameters:
      username: "{{ credential.gateway_admin.username }}"
      password: "{{ credential.gateway_admin.password }}"
```

**Option 2: Parameters with no defaults (user provides at runtime)**
```yaml
parameters:
  - name: username
    type: string
    required: true
    # No default - user must provide

  - name: password
    type: string
    required: true
    # No default - safer
```

### Credential Creation

Before using credentials in playbooks:

```bash
# Create credential via CLI
ignition-toolkit credential add gateway_admin

# Or via Web UI
# → Navigate to Credentials page
# → Click "Add Credential"
# → Enter name, username, password
```

### Credential Naming Conventions

Use clear, descriptive names:

- ✅ `gateway_admin`
- ✅ `gateway_readonly`
- ✅ `perspective_test_user`
- ❌ `cred1` (unclear purpose)
- ❌ `admin` (too generic)

---

## Parameter Design

### Required vs Optional Parameters

**Required parameters** - Critical for playbook to work:
```yaml
parameters:
  - name: gateway_url
    type: string
    required: true  # ← Must be provided
    description: "Gateway URL (e.g., http://localhost:8088)"
```

**Optional parameters** - Have sensible defaults:
```yaml
parameters:
  - name: timeout
    type: integer
    required: false
    default: 30  # ← Sensible default
    description: "Operation timeout in seconds"
```

### Parameter Types

Choose the right type:

```yaml
parameters:
  # String - text, URLs, selectors
  - name: gateway_url
    type: string
    default: "http://localhost:8088"

  # Integer - counts, timeouts (whole numbers)
  - name: retry_count
    type: integer
    default: 3

  # Float - decimal numbers
  - name: wait_time
    type: float
    default: 2.5

  # Boolean - flags
  - name: wait_for_ready
    type: boolean
    default: true

  # File - file paths
  - name: module_file
    type: file
    description: "Path to .modl file"
```

### Parameter Descriptions

Write clear, helpful descriptions:

❌ **Vague:**
```yaml
- name: url
  description: "The URL"
```

✅ **Clear:**
```yaml
- name: gateway_url
  type: string
  required: true
  description: "Ignition Gateway URL including protocol and port (e.g., http://localhost:8088)"
```

### Parameter References

Use double-brace syntax to reference parameters:

```yaml
parameters:
  - name: gateway_url
    type: string
    required: true

steps:
  - type: browser.navigate
    parameters:
      url: "{{ parameter.gateway_url }}/web/home"  # ← Reference
```

---

## Step Organization

### Use Descriptive Step Names

Step names should explain WHAT and WHY:

❌ **Vague:**
```yaml
- id: step1
  name: "Click button"
  type: browser.click
```

✅ **Clear:**
```yaml
- id: login_submit
  name: "Submit login form"
  type: browser.click
  parameters:
    selector: "#login-button"
```

### Use Semantic Step IDs

IDs should be meaningful and follow naming conventions:

```yaml
# ✅ Good IDs
- id: login
- id: wait_for_module
- id: verify_login_success
- id: navigate_to_backup_page

# ❌ Bad IDs
- id: step1
- id: step2
- id: s3
```

### Group Related Steps

Use comments to organize long playbooks:

```yaml
steps:
  # Authentication
  - id: navigate_login
    name: "Navigate to Gateway login page"
    type: browser.navigate
    parameters:
      url: "{{ parameter.gateway_url }}"

  - id: submit_credentials
    name: "Submit login credentials"
    type: browser.fill
    # ...

  # Module Operations
  - id: navigate_modules
    name: "Navigate to Modules page"
    type: browser.navigate
    # ...

  - id: upload_module
    name: "Upload module file"
    type: gateway.upload_module
    # ...

  # Verification
  - id: verify_module_loaded
    name: "Verify module loaded successfully"
    type: browser.verify
    # ...
```

### Step Timeout Strategy

Set timeouts appropriately:

```yaml
# Fast operations - 10-30 seconds
- id: click_button
  type: browser.click
  timeout: 10

# Module operations - 2-5 minutes
- id: wait_module
  type: gateway.wait_for_module_installation
  timeout: 300  # 5 minutes

# Gateway restart - 1-3 minutes
- id: restart
  type: gateway.restart
  timeout: 180  # 3 minutes
```

**Timeout Guidelines:**
- Browser clicks/fills: 10-30s
- Page navigation: 30-60s
- Module installation: 2-5 min
- Gateway restart: 1-3 min
- Backup operations: 1-2 min

---

## Error Handling

### Use `on_failure` Strategically

**Abort on critical failures:**
```yaml
- id: login
  name: "Login to Gateway"
  type: gateway.login
  on_failure: abort  # ← Stop if login fails
```

**Continue on non-critical failures:**
```yaml
- id: cleanup
  name: "Clean up temp files"
  type: utility.log
  on_failure: continue  # ← Keep going even if this fails
```

**Skip remaining steps:**
```yaml
- id: optional_check
  name: "Optional health check"
  type: browser.verify
  on_failure: skip  # ← Skip remaining steps but don't fail playbook
```

### When to Use Each Strategy

| Strategy | When to Use | Example |
|----------|-------------|---------|
| `abort` | Critical operations that must succeed | Login, module upload, database connection |
| `continue` | Optional operations, cleanup | Logging, screenshots, metric collection |
| `skip` | Pre-flight checks, feature detection | Optional feature verification |

### Add Meaningful Error Messages

Use `utility.log` to provide context:

```yaml
- id: login
  name: "Login to Gateway"
  type: gateway.login
  parameters:
    username: "{{ credential.gateway_admin.username }}"
    password: "{{ credential.gateway_admin.password }}"
  on_failure: abort

# Add context if login fails
- id: login_failed_message
  name: "Log login failure details"
  type: utility.log
  parameters:
    message: "Login failed. Check credentials and Gateway URL."
    level: "error"
```

---

## Composable Playbooks

### Mark Building Blocks as Verified

Before a playbook can be called by `playbook.run`, it must be marked as **Verified**:

1. Test the playbook thoroughly
2. Click the 3-dot menu on the playbook card
3. Select "Mark as Verified"

### Use Verified Playbooks as Steps

**Parent playbook:**
```yaml
name: "Full Module Upgrade"
version: "1.0"

parameters:
  - name: gateway_url
    type: string
    required: true

steps:
  # Call verified login playbook
  - id: login
    name: "Execute Gateway Login"
    type: playbook.run
    parameters:
      playbook: "gateway/gateway_login.yaml"  # ← Must be verified
      gateway_url: "{{ parameter.gateway_url }}"
      username: "{{ parameter.username }}"
      password: "{{ parameter.password }}"
    timeout: 60

  # Call verified upload playbook
  - id: upload
    name: "Execute Module Upload"
    type: playbook.run
    parameters:
      playbook: "gateway/module_upload.yaml"
      module_file: "{{ parameter.module_file }}"
    timeout: 300
```

### Composability Guidelines

1. **Create atomic playbooks** - Each playbook does ONE thing well
2. **Test independently** - Verify each playbook works standalone
3. **Mark as verified** - Only verified playbooks can be called
4. **Avoid deep nesting** - Maximum 3 levels deep
5. **Document dependencies** - List required playbooks in description

**Example hierarchy:**
```
backup_and_restore.yaml (Level 1)
  ├─ gateway_login.yaml (Level 2)
  ├─ backup_gateway.yaml (Level 2)
  │   └─ gateway_login.yaml (Level 3) ← Reused
  └─ restore_gateway.yaml (Level 2)
```

---

## Browser Automation Tips

### Use Robust Selectors

**Prefer:**
1. **Role selectors** - `[role='button']`
2. **Test IDs** - `#submit-button`, `[data-testid='login-btn']`
3. **Text content** - `button >> text=/login/i`

**Avoid:**
- Fragile class names - `.MuiButton-root-xyz123`
- Deep DOM paths - `div > div > div > button`
- Index-based - `:nth-child(3)`

**Examples:**
```yaml
# ✅ Good - role + text
selector: "[role='button'] >> text=/submit/i"

# ✅ Good - semantic ID
selector: "#login-button"

# ✅ Good - combination
selector: "button[type='submit'], button >> text=/login/i"

# ❌ Bad - fragile class
selector: ".css-1234-MuiButton"

# ❌ Bad - index-based
selector: "button:nth-child(3)"
```

### Use Wait Steps Before Actions

Always wait for elements before interacting:

```yaml
# Wait for element to be visible
- id: wait_button
  type: browser.wait
  parameters:
    selector: "#submit-button"
    timeout: 10

# Then click it
- id: click_button
  type: browser.click
  parameters:
    selector: "#submit-button"
```

### Use browser.verify for Assertions

Verify expected state after actions:

```yaml
# Verify login succeeded
- id: verify_login
  type: browser.verify
  parameters:
    selector: ".user-profile"
    exists: true  # Element should exist
    timeout: 5

# Verify no error messages
- id: verify_no_errors
  type: browser.verify
  parameters:
    selector: ".error-message"
    exists: false  # Element should NOT exist
    timeout: 5
```

### Handle Dynamic Content

For SPAs and dynamic content:

```yaml
# Wait for network to be idle
- id: navigate
  type: browser.navigate
  parameters:
    url: "{{ parameter.gateway_url }}"
    wait_until: "networkidle"  # ← Wait for all requests

# Or wait for specific element
- id: wait_content
  type: browser.wait
  parameters:
    selector: ".dashboard-loaded"
    timeout: 30
```

### Take Screenshots for Debugging

Capture screenshots at key points:

```yaml
- id: screenshot_after_login
  type: browser.screenshot
  parameters:
    name: "after_login"
    full_page: false

- id: screenshot_error
  type: browser.screenshot
  parameters:
    name: "error_state"
    full_page: true  # ← Capture entire page
```

---

## Testing Playbooks

### Test Locally First

Before committing or sharing:

1. **Run in development** - Test against dev Gateway
2. **Test with different parameters** - Try edge cases
3. **Test failure scenarios** - Verify `on_failure` works
4. **Check screenshots** - Review captured images

### Use Debug Mode

Enable debug mode for step-by-step execution:

```yaml
# In execution UI:
# → Click "Debug Mode" toggle
# → Run playbook
# → Step through one at a time
# → Inspect browser state at each step
```

### Test Parameter Validation

Ensure parameters are validated:

```yaml
# Test with missing required parameters
# → Should fail with clear error

# Test with invalid types
# → gateway_url: 12345 (not a string)
# → Should fail validation

# Test with invalid values
# → gateway_url: "not-a-url"
# → Should fail at runtime with clear error
```

### Test Error Paths

Intentionally cause failures to verify error handling:

- Invalid credentials
- Wrong Gateway URL
- Missing files
- Timeout scenarios

---

## Common Pitfalls

### 1. Hardcoded Values

❌ **Don't:**
```yaml
steps:
  - type: browser.navigate
    parameters:
      url: "http://192.168.1.50:8088"  # ← Hardcoded IP
```

✅ **Do:**
```yaml
parameters:
  - name: gateway_url
    type: string
    required: true

steps:
  - type: browser.navigate
    parameters:
      url: "{{ parameter.gateway_url }}"  # ← Parameterized
```

### 2. Missing Timeouts

❌ **Don't:**
```yaml
- type: gateway.wait_for_module_installation
  parameters:
    module_name: "Perspective"
    # ← No timeout, could hang forever
```

✅ **Do:**
```yaml
- type: gateway.wait_for_module_installation
  parameters:
    module_name: "Perspective"
  timeout: 300  # ← Explicit timeout
```

### 3. Weak Selectors

❌ **Don't:**
```yaml
selector: "div > div > button"  # ← Fragile
```

✅ **Do:**
```yaml
selector: "button[type='submit'], button >> text=/submit/i"  # ← Robust
```

### 4. No Error Handling

❌ **Don't:**
```yaml
- type: gateway.login
  # ← No on_failure specified
```

✅ **Do:**
```yaml
- type: gateway.login
  on_failure: abort  # ← Explicit error handling
```

### 5. Mixing Domains

❌ **Don't:**
```yaml
steps:
  - type: gateway.upload_module
  - type: browser.click  # ← Mixed domains!
```

✅ **Do:**
Create separate playbooks or use `playbook.run`.

---

## Example Patterns

### Pattern 1: Login Template

```yaml
name: "Gateway Login"
version: "1.0"
description: "Reusable login playbook"

parameters:
  - name: gateway_url
    type: string
    required: true
  - name: username
    type: string
    required: true
  - name: password
    type: string
    required: true

steps:
  - id: navigate
    name: "Navigate to Gateway login"
    type: browser.navigate
    parameters:
      url: "{{ parameter.gateway_url }}"
      wait_until: "networkidle"
    timeout: 30

  - id: fill_username
    name: "Enter username"
    type: browser.fill
    parameters:
      selector: "#username"
      value: "{{ parameter.username }}"

  - id: fill_password
    name: "Enter password"
    type: browser.fill
    parameters:
      selector: "#password"
      value: "{{ parameter.password }}"

  - id: submit
    name: "Click login button"
    type: browser.click
    parameters:
      selector: "button[type='submit']"
    on_failure: abort

  - id: verify
    name: "Verify login success"
    type: browser.verify
    parameters:
      selector: ".user-menu, .logout-button"
      exists: true
      timeout: 10

metadata:
  author: "Your Name"
  category: "gateway"
  tags: ["authentication", "reusable"]
```

### Pattern 2: Module Upgrade with Verification

```yaml
name: "Module Upgrade"
version: "1.0"

credentials:
  - gateway_admin

parameters:
  - name: gateway_url
    type: string
    required: true
  - name: module_file
    type: file
    required: true
  - name: module_name
    type: string
    required: true

steps:
  # Login
  - id: login
    name: "Login to Gateway"
    type: gateway.login
    parameters:
      username: "{{ credential.gateway_admin.username }}"
      password: "{{ credential.gateway_admin.password }}"
    on_failure: abort

  # Upload
  - id: upload
    name: "Upload module file"
    type: gateway.upload_module
    parameters:
      file: "{{ parameter.module_file }}"
    on_failure: abort

  # Wait for installation
  - id: wait_install
    name: "Wait for module installation"
    type: gateway.wait_for_module_installation
    parameters:
      module_name: "{{ parameter.module_name }}"
    timeout: 300
    on_failure: abort

  # Restart
  - id: restart
    name: "Restart Gateway"
    type: gateway.restart
    parameters:
      wait_for_ready: true
    timeout: 180

  # Verify
  - id: list_modules
    name: "List modules to verify"
    type: gateway.list_modules

  - id: success_log
    name: "Log success"
    type: utility.log
    parameters:
      message: "Module {{ parameter.module_name }} upgraded successfully"
      level: "info"

metadata:
  author: "Your Name"
  category: "gateway"
  tags: ["module", "upgrade", "maintenance"]
```

### Pattern 3: Composite Playbook

```yaml
name: "Full System Test"
version: "1.0"
description: "Runs multiple verified playbooks in sequence"

parameters:
  - name: gateway_url
    type: string
    required: true

steps:
  # Step 1: Login
  - id: login_playbook
    name: "Execute Login Playbook"
    type: playbook.run
    parameters:
      playbook: "gateway/gateway_login.yaml"
      gateway_url: "{{ parameter.gateway_url }}"
      username: "{{ parameter.username }}"
      password: "{{ parameter.password }}"
    timeout: 60
    on_failure: abort

  # Step 2: Health Check
  - id: health_playbook
    name: "Execute Health Check"
    type: playbook.run
    parameters:
      playbook: "gateway/health_check.yaml"
      gateway_url: "{{ parameter.gateway_url }}"
    timeout: 30

  # Step 3: Backup
  - id: backup_playbook
    name: "Execute Backup"
    type: playbook.run
    parameters:
      playbook: "gateway/backup_gateway.yaml"
      gateway_url: "{{ parameter.gateway_url }}"
    timeout: 120

  - id: complete
    name: "Log completion"
    type: utility.log
    parameters:
      message: "Full system test complete"
      level: "info"
```

---

## Checklist for New Playbooks

Before marking a playbook as complete:

- [ ] **Domain separation** - Gateway OR Perspective OR Designer (never mixed)
- [ ] **No hardcoded credentials** - Use credential references or parameters
- [ ] **Clear parameter descriptions** - Helpful hints for users
- [ ] **Descriptive step names** - What and why, not just what
- [ ] **Appropriate timeouts** - Set explicitly, not too short or too long
- [ ] **Error handling** - `on_failure` specified for critical steps
- [ ] **Metadata filled** - Author, category, tags
- [ ] **Tested locally** - Runs successfully in dev environment
- [ ] **Screenshots reviewed** - Visual feedback looks correct
- [ ] **Documented** - Clear description of what playbook does

---

## Related Documentation

- **playbook_syntax.md** - Complete syntax reference
- **RUNNING_PLAYBOOKS.md** - How to execute playbooks
- **ARCHITECTURE.md** - Technical architecture and execution engine
- **PROJECT_GOALS.md** - Project vision and use cases

---

**Last Updated:** 2025-10-27
**Maintainer:** Nigel G
**Feedback:** Open GitHub issue or pull request
