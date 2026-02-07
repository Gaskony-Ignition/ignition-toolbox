# Claude Code Instructions for Playbook Development

**Welcome, Claude Code Assistant!** This document provides essential context for helping with Ignition Toolbox playbooks.

## What You're Looking At

You are in the playbooks directory, which contains YAML-based playbooks for testing Ignition SCADA systems.

## Project Context

- **Project**: Ignition Toolbox - Visual acceptance testing platform for Ignition SCADA
- **Version**: 1.5.3 (Production Ready)
- **Primary Language**: Python 3.10+ backend, React 19 + TypeScript frontend
- **Playbook Format**: YAML files defining automated test sequences

## Playbook Structure

Playbooks are domain-separated into folders:
- `gateway/` - Gateway-only playbooks (REST API operations)
- `perspective/` - Perspective-only playbooks (browser automation)
- `designer/` - Designer playbooks (future)
- `examples/` - Example playbooks for learning

## YAML Playbook Syntax

```yaml
name: "Playbook Name"
version: "1.0"
description: "What this playbook does"

parameters:
  - name: gateway_url
    type: string
    required: true
    default: "http://localhost:8088"
    description: "Gateway URL"

  - name: username
    type: string
    required: true
    description: "Gateway username"

steps:
  - id: step1
    name: "Step 1: Open Gateway Webpage"
    type: browser.navigate
    parameters:
      url: "{{ gateway_url }}"
    timeout: 30
    retry_count: 1
    on_failure: abort  # abort (default), continue, rollback
```

## Available Step Types

### Browser Steps (Perspective Testing)
- `browser.navigate` - Navigate to URL
- `browser.click` - Click element by selector
- `browser.fill` - Fill input field
- `browser.wait` - Wait for element to appear
- `browser.screenshot` - Capture screenshot
- `browser.verify` - Verify element exists/has text

### Gateway Steps (REST API)
- `gateway.login` - Authenticate to Gateway
- `gateway.upload_module` - Upload .modl file
- `gateway.wait_for_module` - Wait for module to be running
- `gateway.restart` - Restart Gateway
- `gateway.wait_for_ready` - Wait for Gateway to be ready

### Utility Steps
- `utility.wait` - Wait for N seconds
- `utility.set_variable` - Store value in execution variables

### AI Steps (Optional)
- `ai.assist` - Get AI help for complex logic
- `ai.validate` - AI-powered validation
- `ai.generate` - AI-powered content generation

## Parameter Resolution

- `{{ parameter_name }}` - Replace with parameter value
- `{{ credential.username }}` - Load from credential vault
- `{{ credential.password }}` - Load from credential vault (encrypted)
- `{{ variable.name }}` - Use execution variable from previous step

## Common Patterns

### Building Block Playbook (Gateway Login)
```yaml
# playbooks/gateway/gateway_login.yaml
# This is a reusable authentication playbook
name: "Gateway Login"
version: "2.0"
description: "Base building block: Login to Gateway and verify authentication"

steps:
  - id: step1
    name: "Open Gateway"
    type: browser.navigate
    parameters:
      url: "{{ gateway_url }}"

  - id: step2
    name: "Click Login"
    type: browser.click
    parameters:
      selector: "a.login-link, a[href*='login']"

  # ... more steps
```

### Module Upgrade Playbook
```yaml
name: "Module Upgrade"
version: "1.0"
description: "Upload and install Ignition module"

parameters:
  - name: module_file_path
    type: string
    required: true
    description: "Path to .modl file"

steps:
  - id: step1
    name: "Login to Gateway"
    type: playbook.run
    parameters:
      playbook: "gateway/gateway_login.yaml"
      parameters:
        gateway_url: "{{ gateway_url }}"
        username: "{{ credential.username }}"
        password: "{{ credential.password }}"

  - id: step2
    name: "Upload Module"
    type: gateway.upload_module
    parameters:
      module_file_path: "{{ module_file_path }}"
```

## Debugging Failed Steps

When a playbook execution fails, you'll typically see:
1. **Step name** - Which step failed
2. **Error message** - What went wrong
3. **Screenshot** - Visual state at failure (for browser steps)

Common issues:
- **Selector not found**: Element selector is wrong or element doesn't exist
  - Fix: Use more flexible selectors (comma-separated fallbacks)
  - Example: `"input[name='username'], input[type='text'], .username-field"`

- **Timeout**: Step took too long
  - Fix: Increase `timeout` value or add `retry_count`

- **Wrong parameter type**: Parameter value doesn't match expected type
  - Fix: Check parameter definition and ensure value is correct type

## Best Practices

1. **Use Building Blocks** - Create reusable playbooks for common tasks (login, logout, etc.)
2. **Flexible Selectors** - Use comma-separated selector lists for browser steps
3. **Meaningful Names** - Step names should describe what's happening
4. **Add Screenshots** - Add `browser.screenshot` after critical steps for debugging
5. **Set Timeouts** - Adjust timeouts based on expected duration
6. **Handle Failures** - Use `on_failure: continue` for optional steps
7. **Validate Results** - Use `browser.verify` to check success conditions

## Testing Changes

After editing a playbook:
1. Save the YAML file
2. The web UI will auto-detect changes
3. Run the playbook from the UI with debug mode enabled
4. Step through execution to verify fixes

## Common User Requests

1. **"Step X is failing"** - Check selector specificity, timeout, and add retry_count
2. **"Simplify this playbook"** - Remove unnecessary steps, use playbook.run for common sequences
3. **"Make this more robust"** - Add flexible selectors, increase timeouts, add verification steps
4. **"Create a building block"** - Extract reusable sequence into separate playbook

## File Locations

- **Playbooks**: `/git/ignition-toolbox/playbooks/`
- **Documentation**: `/git/ignition-toolbox/docs/`
- **Project Goals**: `/git/ignition-toolbox/PROJECT_GOALS.md`
- **Syntax Reference**: `/git/ignition-toolbox/docs/playbook_syntax.md`

## Important Notes

- **Never commit credentials** - Use `{{ credential.xxx }}` placeholders only
- **Domain separation** - Gateway OR Perspective OR Designer (never mixed)
- **Version control** - All playbooks are in git, commit meaningful changes
- **Validation** - Backend validates YAML on load, syntax errors will be shown

## Getting Help

- Read `/git/ignition-toolbox/docs/playbook_syntax.md` for complete syntax
- Read `/git/ignition-toolbox/PROJECT_GOALS.md` for design decisions
- Read `/git/ignition-toolbox/.claude/CLAUDE.md` for development patterns

---

**Your Role**: Help the user debug failed steps, improve playbook robustness, create new playbooks, and simplify complex sequences. Focus on practical solutions using the step types and patterns above.
