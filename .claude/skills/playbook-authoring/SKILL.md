---
name: playbook-authoring
description: Rules for writing and fixing library playbooks (YAML schema, versioning, selectors, credentials, validation, publishing). Load before editing anything under backend/playbooks/ or playbooks-index.json.
user-invocable: true
---

# Playbook Authoring

Library playbooks live in `backend/playbooks/<domain>/*.yaml` where domain is
`gateway`, `designer`, or `perspective` (one domain per playbook — never mix).
Reference docs: `docs/playbook_syntax.md`, `docs/PLAYBOOK_BEST_PRACTICES.md`.

## Schema (enforced by `scripts/validate-playbooks.py`)

Required top-level: `name`, `version`, `description`, `domain`, `steps`.
Also used: `group` (UI grouping), `verified` (bool). Each step:
`id`, `name`, `type` (must exist in the step-type registry), `parameters`.

```yaml
steps:
  - id: step1
    name: "Step 1: Open Gateway Webpage"
    type: browser.navigate
    parameters:
      url: "{{ parameter.gateway_url }}"
```

## Versioning (important convention)

Every playbook carries its **own** `version` string, independent of the app
version. Any behavioural edit bumps it, and the commit message names it —
e.g. `Fix module_install v5.0: correct license dialog flow`. Never edit a
library playbook without bumping its version.

## Rules

- **Credentials**: only ever `{{ credential.xxx }}` references — never literal
  usernames/passwords, and exports must preserve the references (see
  `security-checking`).
- **Selectors**: Ignition gateway pages change between 8.3.x versions. Use
  multi-selector fallbacks (comma-separated CSS list) and explicit `timeout`
  parameters; screenshot steps around fragile interactions should be non-fatal.
- **Parameters**: declare with `type`, `required`, `default`, `description` —
  they become the execution dialog UI.
- Timeouts for gateway restart / module install are long by design
  (`core/timeouts.py`); don't shorten them to "speed up" a playbook.

## Validate + test

```bash
backend/.venv/bin/python scripts/validate-playbooks.py
```

Then run the playbook against a real gateway (Nigel's test gateways: VMware VM
`http://192.168.153.128:8088` or the `ignition-module-testing` Docker
container) via the app or API before calling it fixed — selector bugs only
show at runtime.

## Remote library / publishing

`playbooks-index.json` (repo root) is the published index; the app fetches it
from GitHub (`playbook/registry.py`) and installs playbooks from it.
`playbook/submitter.py` builds the PR that updates the index. Schema:
`docs/playbooks-index-schema.json`. If you add/rename a library playbook,
the index entry must match, and `toolbox-manifest.json` governs other remote
data components (stackbuilder catalog, API docs).
