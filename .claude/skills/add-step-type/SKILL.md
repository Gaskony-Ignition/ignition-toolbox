---
name: add-step-type
description: Recipe for adding or changing a playbook step type — the exact backend touchpoints, dispatch wiring, tests, and docs. Load before touching StepType, the step registry, or executors.
user-invocable: true
---

# Adding / Changing a Playbook Step Type

Step types are named `<domain>.<action>` (e.g. `browser.keyboard`). Domains:
`gateway`, `browser`, `designer`, `perspective`, `playbook`, `utility`, `fat`.
There are ~69 types — the source of truth is the `StepType` enum.

## The five backend touchpoints (all required)

1. **Enum** — `backend/ignition_toolkit/playbook/models.py`, `StepType`:
   `BROWSER_KEYBOARD = "browser.keyboard"`

2. **Registry definition** — `backend/ignition_toolkit/playbook/step_type_registry.py`:
   add a `StepTypeDefinition(step_type=…, description=…, parameters=[StepParameter(…)],
   timeout_category=TimeoutKeys.…)`. This single definition drives the
   `/api/playbooks/step-types` endpoint, the frontend step editor UI, and
   `scripts/validate-playbooks.py` — get parameters/defaults right here.
   Use `TimeoutDefaults.*` from `core/timeouts.py` for timeout defaults, never
   magic numbers.

3. **Handler class** — `backend/ignition_toolkit/playbook/executors/<domain>_executor.py`:
   a class with `async def execute(self, params: dict[str, Any]) -> dict[str, Any]`,
   taking its manager (BrowserManager / GatewayClient / DesignerManager) in
   `__init__`. Match the neighbouring handlers' pattern.

4. **Export** — `backend/ignition_toolkit/playbook/executors/__init__.py`:
   export the new handler.

5. **Dispatch** — `backend/ignition_toolkit/playbook/step_executor.py`,
   `_create_handler_registry()`: map `StepType.X → XHandler(…)` inside the
   correct manager-guard block (gateway handlers only exist when
   `gateway_client` is set, browser handlers when `browser_manager` is set, …).

## Then

- **Tests** in `backend/tests/test_playbook/` — registry definition present,
  handler behaviour (mock the manager). Run
  `cd backend && .venv/bin/python -m pytest tests/test_playbook -q`.
- **Docs** — update `docs/playbook_syntax.md` if it enumerates step types.
- **No frontend change needed** — the UI discovers step types dynamically via
  `/api/playbooks/step-types`.
- If library playbooks should use the new step, see `playbook-authoring`
  (bump each playbook's own `version`).

## Gotchas

- Missing touchpoint 2 → step invisible in UI and validator rejects playbooks
  using it. Missing touchpoint 5 → runtime "no handler" failure only.
- Domain prefix matters: it determines which manager must be live and how the
  engine groups execution — don't put a browser-driven action under `gateway.`.
