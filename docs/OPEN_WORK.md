# Open Work

The single live list of unfinished work in this repo. Supersedes the
banner-marked historical snapshots (`IMPROVEMENT_PLAN.md`,
`architectural-debt-audit.md`) — do not mine those for tasks.

Last verified against code: 2026-07-06 (v3.2.5).

## Major (planned, agent-executable — see `docs/plans/`)

| Area | Plan | Next phase |
| --- | --- | --- |
| StackBuilder is beta | [plans/stackbuilder-test-strategy.md](plans/stackbuilder-test-strategy.md) | Phases 1–4 done (398 new tests incl. compose-spec + goldens; 4 generator bugs fixed). Next: phase 5 live smoke (Nigel's machine), then remove the beta label |
| UDT Builder: "coming soon" | [plans/udt-builder-design.md](plans/udt-builder-design.md) | Phase 1 done (lossless data model, 15 tests). Next: phase 2 conventions + templates — blocked on Nigel (see below) |
| Perspective project audit + empty playbook library | [plans/perspective-project-audit.md](plans/perspective-project-audit.md) | Phases 0–3 done (rule engine, 10 rules, report + API + Audit tab, end-to-end verified). Next: phase 4 runtime playbooks (needs test gateway) |

## StackBuilder feature gaps (found by the 2026-07-06 pair-sweep work; declared in data but not implemented)

- `metrics_collector` and `secrets_management` integration types exist in
  `integrations.json` but `IntegrationEngine.detect_integrations()` has no
  branch for them — never detected or materialised.
- `nginx-proxy-manager` is declared a `reverse_proxy` provider but has zero
  implementation in `compose_generator.py` — only traefik works.
- `portainer`, `vault`, `guacamole`, `nodered` are declared OAuth/DB/MQTT
  clients but have no `_apply_app_config`/dependency branches.
- Keycloak's DB client is hardcoded to postgres; `keycloak+mariadb` yields no
  `KC_DB_*` env vars despite the declared capability.
- `generate_emqx_config()` exists and is unit-tested but is never called by
  `_generate_integration_configs` (only mosquitto is wired).
- `ServiceCatalog.validate_instance_config()` reads a `config_schema` key that
  no catalog entry has (they use `configurable_options`) — permanent no-op.
- 3 catalog services ship `enabled: false`: `mssql`, `authentik`, `authelia`.

Decide per item: implement, or strip the capability from the data so the UI
doesn't advertise it. Either way the pair sweep will enforce the outcome.

Note: the UDT linter and the project audit share one rule-engine core
(`ignition_toolkit/audit/`) — whichever plan runs first builds it.

## Blocked on Nigel

- Export the customer "Ignition UDTs" reference project from the Claude
  Windows GUI / old machine into `docs/reference/udt-examples/`
  (needed for UDT plan phases 2+; searched this machine 2026-07-06 — absent).
- Ratify UDT naming/alarm conventions (see udt-builder-design.md decisions).
- Decide: sandbox or accept `exec()` in the `utility.python` step
  (`playbook/executors/utility_executor.py:134`). Fine for self-authored
  playbooks; risky if users install community playbooks from the remote index.

## Minor cleanups (no urgency)

- `UpdateStatus` type defined in 4 places across electron/frontend boundary
- One remaining `window.location.reload()` in the frontend
- Deprecated `ignition_toolkit/config.py` re-export shim (remove once
  importers migrate to `core/config.py`)
- ErrorBoundary TODO: no error-reporting backend (likely permanent won't-do)
- ARCHITECTURE.md says 19 routers; there are now 24 router modules
