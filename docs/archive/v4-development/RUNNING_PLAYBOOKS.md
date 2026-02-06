# Running Playbooks - Quick Start Guide

This guide shows you how to run playbooks with the Ignition Automation Toolkit.

## Prerequisites

1. **Install the toolkit** (if not already done):
   ```bash
   cd /git/ignition-playground
   pip install -e .
   ```

2. **Initialize the credential vault**:
   ```bash
   ignition-toolkit init
   ```

3. **Add Gateway credentials**:
   ```bash
   ignition-toolkit credential add gateway_admin
   # You'll be prompted for username and password
   ```

## Running Playbooks

### Basic Syntax

```bash
ignition-toolkit playbook run <playbook_path> --param <name>=<value>
```

### Example: Simple Health Check

```bash
ignition-toolkit playbook run playbooks/examples/simple_health_check.yaml \
  --param gateway_url=http://localhost:8088 \
  --param gateway_credential=gateway_admin
```

### Example: Reset Gateway Trial

```bash
ignition-toolkit playbook run playbooks/gateway/reset_trial.yaml \
  --param gateway_url=http://localhost:8088 \
  --param gateway_credential=gateway_admin
```

### Example: Module Upgrade

```bash
ignition-toolkit playbook run playbooks/gateway/module_upgrade.yaml \
  --param gateway_url=http://localhost:8088 \
  --param gateway_credential=gateway_admin \
  --param module_file=/path/to/your-module.modl
```

## Alternative Syntax (Using Shortcuts)

You can also use these convenient options instead of `--param`:

```bash
ignition-toolkit playbook run playbooks/examples/simple_health_check.yaml \
  --gateway-url http://localhost:8088 \
  --gateway-credential gateway_admin
```

## Common Issues

### 1. "Required credential parameter"

**Error**: Required credential parameter: gateway_credential

**Solution**: You need to:
1. Create a credential first: `ignition-toolkit credential add <name>`
2. Pass it to the playbook: `--param gateway_credential=<name>`

### 2. "No credentials stored yet"

**Solution**: Add a credential before running playbooks:
```bash
ignition-toolkit credential add gateway_admin
Username: admin
Password: ********
```

### 3. Playbook "didn't seem to do anything"

**Cause**: Missing required parameters. The playbook will prompt for them interactively, which may not work in all terminal environments.

**Solution**: Always provide parameters explicitly:
```bash
ignition-toolkit playbook run <path> \
  --param gateway_url=http://localhost:8088 \
  --param gateway_credential=gateway_admin
```

## List Available Playbooks

```bash
ignition-toolkit playbook list
```

## List Stored Credentials

```bash
ignition-toolkit credential list
```

## Example: Complete Workflow

Here's a complete example from start to finish:

```bash
# 1. Initialize (one-time setup)
ignition-toolkit init

# 2. Add Gateway credentials (one-time)
ignition-toolkit credential add my_gateway
# Enter username: admin
# Enter password: password

# 3. List available playbooks
ignition-toolkit playbook list

# 4. Run a playbook
ignition-toolkit playbook run playbooks/examples/simple_health_check.yaml \
  --param gateway_url=http://localhost:8088 \
  --param gateway_credential=my_gateway

# 5. View results in the terminal output
```

## Expected Output

When running a playbook successfully, you should see:

```
Loading playbook: playbooks/examples/simple_health_check.yaml

  Name: Simple Health Check
  Version: 1.0
  Steps: 7

Executing playbook...

⠋ Running... Step 7/7

Execution Status: completed

                    Step Results
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Step ID       ┃ Status    ┃ Duration ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━┩
│ login         │ completed │ 0.5s     │
│ ping          │ completed │ 0.1s     │
│ get_info      │ completed │ 0.2s     │
│ get_health    │ completed │ 0.2s     │
│ list_modules  │ completed │ 0.3s     │
│ list_projects │ completed │ 0.2s     │
│ logout        │ completed │ 0.1s     │
└───────────────┴───────────┴──────────┘
```

## Troubleshooting

### Connection Issues

If you get connection errors:
1. Verify your Gateway is running: `curl http://localhost:8088/StatusPing`
2. Check the Gateway URL is correct (port 8088 by default)
3. Verify your credentials are correct

### Parameter Resolution Errors

If you see errors about missing variables:
1. Check the playbook requirements: look at the `parameters:` section in the YAML
2. Ensure you've passed all required parameters
3. Verify credential names match what's in your vault: `ignition-toolkit credential list`

## Web UI Alternative

You can also run playbooks from the web UI:

1. Start the server:
   ```bash
   ignition-toolkit serve --port 8080
   ```

2. Open browser: http://localhost:8080

3. Click on a playbook card and fill in the form

## Advanced: Creating Your Own Playbooks

See the existing playbooks in `playbooks/` for examples. The YAML syntax is documented in the project README.

Key tips:
- Use `{{ parameter.name }}` to reference input parameters
- Use `{{ credential.name.username }}` and `{{ credential.name.password }}` to reference credentials
- Use `{{ variable.step_id.field }}` to reference outputs from previous steps
