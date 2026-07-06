# Open Work

The single live list of unfinished work in this repo. Supersedes the
banner-marked historical snapshots (`IMPROVEMENT_PLAN.md`,
`architectural-debt-audit.md`) — do not mine those for tasks.

Last verified against code: 06/07/2026 (v3.4.0).

## Major (planned, agent-executable — see `docs/plans/`)

| Area | Plan | State (2026-07-06) |
| --- | --- | --- |
| StackBuilder | [plans/stackbuilder-test-strategy.md](plans/stackbuilder-test-strategy.md) | **All 5 tiers done** (400+ new tests; 5 generator bugs fixed). Remaining: remove the beta label with the next release |
| UDT Builder | [plans/udt-composer-design.md](plans/udt-composer-design.md) | **Composer shipped v3.4.0** — guided wizard + live lint pack (`audit/rules/udt/`), templates demoted to quick-start presets; supersedes the questionnaire flow (old phase-4 linter now exists as the lint pack). Remaining: preset growth; Designer import check + validation against Nigel's reference exports |
| Perspective project audit | [plans/perspective-project-audit.md](plans/perspective-project-audit.md) | **All phases done** — static audit + report + UI + 4 proven playbooks + runtime section. Future: rule pack growth; wire runtime results into the Audit tab |

All three shipped across v3.3.0-v3.4.0. Still open: Stacks/UDTs Beta badges
(Nigel's call; UDT composer is freshly rebuilt so Beta is fair there), and
UDT validation against Nigel's reference exports once they reach this machine.

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

## Review backlog (from the 2026-07-06 pre-release deep review; none block release)

- `audit/engine.py`: each of the 10 rules independently re-walks every view
  (O(rules × views × components)); one shared walk dispatching to all rules
  would cut audit time ~10× on large customer projects.
- `compose_generator.py`: config generators should declare their own bind
  mounts (catalog `default_config.volumes` pattern) instead of the
  grafana-specific mount loop — any future provisioned config file can
  silently repeat the "generated but never mounted" bug.
- catalog.json: add an explicit `host_port_option` key per port mapping so
  `_get_host_port` matches structurally instead of by default-value
  coincidence (safe today; validated by the singles sweep).
- Normalise Playwright's TimeoutError at the browser-manager boundary so no
  handler can regress the `except TimeoutError` bug class.
- `POST /api/udt/build` 422s: return structured field errors instead of a
  joined string (UdtBuilder.tsx currently regex-parses the message).
- `api/routers/udt.py`: drop the `list_templates()` existence pre-check
  (re-parses every template per request); map builder's own unknown-template
  error to 404.
- Move `MAX_UPLOAD_BYTES` (audit.py) into `core/validation_limits.py`.
- Frontend: extract a shared `saveBlobAsFile()` helper (6 inline copies of
  the blob→anchor download dance).
- `page_crawl.yaml`: remove the informational-only `page_paths` parameter
  (must be hand-synced with `pageN_path`).
- Audit tab "Download report" re-uploads and re-audits the zip; reuse the
  already-fetched report data instead.

## Blocked on Nigel

- Export the customer "Ignition UDTs" reference project from the Claude
  Windows GUI / old machine into `docs/reference/udt-examples/`
  (wanted to validate composer conventions against real-world exports;
  searched this machine 2026-07-06 — absent).
- Decide: remove the Stacks Beta badge? (test strategy complete since
  v3.3.0). UDTs Beta badge should stay until the composer has field use.
- Decide: sandbox or accept `exec()` in the `utility.python` step
  (`playbook/executors/utility_executor.py:134`). Fine for self-authored
  playbooks; risky if users install community playbooks from the remote index.

## Minor cleanups (no urgency)

- No step type captures browser console output — `PageRuntimeResult.console_errors`
  is always empty; a `browser.get_console_errors` step type would complete the
  runtime audit story.
- UDT Builder preview is an explicit button (not live/debounced); inline 422
  field-error mapping parses builder.py's message strings (loosely coupled).

- Nested-playbook verification UX: `playbook.run` steps require the child
  playbook to be marked verified in the *local metadata store*
  (`playbook_metadata.json`) even when the YAML ships `verified: true` —
  a fresh install can't run `reset_trial.yaml` headless until
  `gateway_login.yaml` is marked verified via the UI. Consider seeding the
  metadata store from the shipped YAML's `verified` flag for built-ins.

- `UpdateStatus` type defined in 4 places across electron/frontend boundary
- One remaining `window.location.reload()` in the frontend
- Deprecated `ignition_toolkit/config.py` re-export shim (remove once
  importers migrate to `core/config.py`)
- ErrorBoundary TODO: no error-reporting backend (likely permanent won't-do)
- ARCHITECTURE.md says 19 routers; there are now 24 router modules
