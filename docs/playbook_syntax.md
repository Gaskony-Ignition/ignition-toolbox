# Playbook Syntax Reference

Complete guide to writing YAML playbooks.

## Basic Structure

```yaml
name: "Playbook Name"
version: "1.0"
description: "What this playbook does"

parameters:
  - name: param_name
    type: string
    required: true
    description: "Parameter description"

steps:
  - id: step_id
    name: "Step Name"
    type: step.type
    parameters:
      key: value
```

## Parameters

### Parameter Types

- `string` - Text value
- `integer` - Whole number
- `float` - Decimal number
- `boolean` - true/false
- `file` - File path
- `credential` - Credential reference
- `list` - List of values
- `dict` - Dictionary/object

### Parameter Options

```yaml
parameters:
  - name: gateway_url
    type: string
    required: true           # Must be provided
    default: "http://localhost:8088"  # Default value
    description: "Gateway URL"
```

## Steps

### Gateway Steps

```yaml
# Login
- id: login
  type: gateway.login
  parameters:
    username: "admin"
    password: "{{ credential.gateway_admin.password }}"

# List modules
- id: list_modules
  type: gateway.list_modules

# Upload module
- id: upload
  type: gateway.upload_module
  parameters:
    file: "./perspective.modl"

# Wait for module
- id: wait_module
  type: gateway.wait_for_module_installation
  parameters:
    module_name: "Perspective"
    timeout: 300

# Restart Gateway
- id: restart
  type: gateway.restart
  parameters:
    wait_for_ready: true
```

### Browser Steps

```yaml
# Navigate
- id: navigate
  type: browser.navigate
  parameters:
    url: "http://example.com"
    wait_until: "networkidle"

# Click element
- id: click
  type: browser.click
  parameters:
    selector: "#submit-button"

# Fill form field
- id: fill
  type: browser.fill
  parameters:
    selector: "#username"
    value: "admin"

# Take screenshot
- id: screenshot
  type: browser.screenshot
  parameters:
    name: "page_capture"
    full_page: true

# Wait for element
- id: wait
  type: browser.wait
  parameters:
    selector: ".success-message"
    timeout: 10000

# Verify element exists or doesn't exist
- id: verify_login
  type: browser.verify
  parameters:
    selector: ".user-profile"
    exists: true  # Verifies element EXISTS (default)
    timeout: 5000

# Verify element does NOT exist (e.g., no error messages)
- id: verify_no_errors
  type: browser.verify
  parameters:
    selector: ".error-message"
    exists: false  # Verifies element DOES NOT exist
    timeout: 5000
```

### Playbook Steps (Composable Playbooks)

**New in v2.2.0**: Use verified playbooks as steps in other playbooks.

```yaml
# Execute a verified playbook as a single step
- id: login
  name: "Login to Gateway"
  type: playbook.run
  parameters:
    playbook: "examples/gateway_login.yaml"  # Relative to playbooks/
    # Map parent parameters to child playbook
    gateway_url: "{{ parameter.gateway_url }}"
    username: "{{ parameter.username }}"
    password: "{{ parameter.password }}"
  timeout: 120

# Another example - module upload
- id: upload_module
  name: "Upload Perspective Module"
  type: playbook.run
  parameters:
    playbook: "examples/module_upload.yaml"
    module_file: "{{ parameter.module_path }}"
  timeout: 300
```

**Requirements:**
- Target playbook **MUST** be marked as "Verified" (via 3-dot menu on playbook card)
- Prevents circular dependencies (playbook cannot call itself)
- Maximum nesting depth: 3 levels
- Parameters are mapped from parent to child

**Benefits:**
- Build complex workflows from tested building blocks
- Reuse common sequences (login, module upload, etc.) across playbooks
- Maintain and update logic in one place
- Playbook shows as single step in execution view
- **New in v4.1.0**: Nested step progress visible in real-time
- **New in v4.1.0**: Live Browser View works during nested execution

### Utility Steps

```yaml
# Sleep
- id: wait
  type: utility.sleep
  parameters:
    seconds: 5

# Log message
- id: log
  type: utility.log
  parameters:
    message: "Operation complete"
    level: "info"  # debug, info, warning, error

# Set variable
- id: set_var
  type: utility.set_variable
  parameters:
    name: "result"
    value: "success"
```

## Parameter References

### Types of References

```yaml
# Parameter reference (from playbook parameters)
"{{ parameter.gateway_url }}"

# Credential reference (from credential vault)
"{{ credential.gateway_admin }}"
"{{ credential.gateway_admin.username }}"
"{{ credential.gateway_admin.password }}"

# Variable reference (set during execution via utility.set_variable)
"{{ variable.module_name }}"

# Step output reference (from previous step outputs - NEW in v3.4)
"{{ step.step_id.output_key }}"
```

### Step Output References

**New Feature (v3.4+):** Reference outputs from previous steps using `{{ step.step_id.output_key }}` syntax.

**How it works:**
1. Steps that produce output (like `utility.python`) store their results
2. Later steps can reference these outputs using the step ID and output key
3. Step outputs are only available from **previously completed steps**

**Example:**

```yaml
steps:
  # Step 1: Extract data using Python
  - id: detect_module
    name: "Detect Module Metadata"
    type: utility.python
    parameters:
      script: |
        import zipfile
        # ... extraction logic ...
        print(f"DETECTED_MODULE_NAME=Perspective")
        print(f"DETECTED_MODULE_FILE=/path/to/module.modl")

  # Step 2: Store module name as variable (for reuse)
  - id: store_name
    name: "Store Module Name"
    type: utility.set_variable
    parameters:
      name: "module_name"
      value: "{{ step.detect_module.DETECTED_MODULE_NAME }}"

  # Step 3: Use the variable in browser automation
  - id: search_module
    name: "Search for Module"
    type: browser.fill
    parameters:
      selector: "input[type='search']"
      value: "{{ variable.module_name }}"  # Uses stored variable

  # Step 4: Use step output directly
  - id: upload_module
    name: "Upload Module File"
    type: browser.fill
    parameters:
      selector: "input[type='file']"
      value: "{{ step.detect_module.DETECTED_MODULE_FILE }}"
```

**Key Points:**
- Step outputs are stored in a dictionary with keys from `print()` statements in `utility.python` steps
- The pattern `KEY=value` in printed output is automatically parsed
- You can reference any key from the step's output dictionary
- Step references can be used in templates, browser.fill, utility.set_variable, and any parameter

**Valid output sources:**
- `utility.python` - Outputs from print(KEY=value) statements
- `gateway.*` - Some gateway operations return structured data
- `browser.screenshot` - Returns screenshot path
- Any step type that returns a dictionary with string keys

### Reference in Strings

```yaml
parameters:
  url: "http://{{ parameter.host }}:{{ parameter.port }}"
  message: "User {{ credential.admin.username }} logged in"
  status: "Module {{ step.detect.module_name }} version {{ step.detect.version }} detected"
```

## Step Options

### Timeout

```yaml
- id: step1
  type: gateway.restart
  timeout: 600  # seconds
```

### Retry

```yaml
- id: step1
  type: gateway.ping
  retry_count: 3      # Retry 3 times
  retry_delay: 5      # Wait 5 seconds between retries
```

### Error Handling

```yaml
- id: step1
  type: gateway.upload_module
  on_failure: abort     # abort, continue, rollback
```

## Complete Example

```yaml
name: "Gateway Module Upgrade"
version: "1.0"
description: "Upload and install a Gateway module"

parameters:
  - name: gateway_url
    type: string
    required: true
    description: "Gateway URL"

  - name: gateway_credential
    type: credential
    required: true
    description: "Gateway admin credential"

  - name: module_file
    type: file
    required: true
    description: "Path to .modl file"

  - name: module_name
    type: string
    required: true
    description: "Module name (e.g., Perspective)"

steps:
  - id: login
    name: "Login to Gateway"
    type: gateway.login
    parameters:
      username: "{{ credential.gateway_credential.username }}"
      password: "{{ credential.gateway_credential.password }}"
    timeout: 30

  - id: list_before
    name: "List Modules Before"
    type: gateway.list_modules
    on_failure: continue

  - id: upload
    name: "Upload Module"
    type: gateway.upload_module
    parameters:
      file: "{{ parameter.module_file }}"
    timeout: 300
    retry_count: 2
    retry_delay: 10

  - id: wait
    name: "Wait for Installation"
    type: gateway.wait_for_module_installation
    parameters:
      module_name: "{{ parameter.module_name }}"
      timeout: 300

  - id: restart
    name: "Restart Gateway"
    type: gateway.restart
    parameters:
      wait_for_ready: true
    timeout: 600

  - id: verify
    name: "Verify Health"
    type: gateway.get_health
    retry_count: 3
    retry_delay: 5

metadata:
  author: "Your Name"
  category: "gateway"
  tags: ["module", "upgrade"]
```

## Best Practices

1. **Use descriptive IDs** - Make step IDs clear and unique
2. **Add descriptions** - Document what parameters do
3. **Set timeouts** - Prevent hanging on slow operations
4. **Handle failures** - Use `on_failure` appropriately
5. **Use retries** - For flaky operations
6. **Secure credentials** - Use credential references, not plain text
7. **Add metadata** - Author, category, tags for organization
