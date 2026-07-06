# StackBuilder Test Strategy — Plan for a Future Agent Session

**Status:** PLANNED (written 2026-07-06, verified against v3.2.5 code)
**Goal:** Make the beta StackBuilder trustworthy without manually testing every
service combination. An agent session (Sonnet-class) should be able to execute
this plan phase by phase. Load skills `testing-and-verification` and
`toolbox-conventions` first.

## Why brute force is impossible — and why it isn't needed

The combination space (verified from `data/stackbuilder/catalog.json` and
`integrations.json`):

- 25 services, 8 integration types, 24 capability entries
- 126 version choices, 115 configurable options across services
- `ignition` supports multiple instances; rules for mutual exclusivity,
  dependencies, and recommendations in `integrations.json`

Subsets alone are 2^25 ≈ 33M stacks. But two facts collapse the problem:

1. **Generation is pure.** `ComposeGenerator.generate(instances)`
   (`backend/ignition_toolkit/stackbuilder/compose_generator.py:108`) maps a
   list of instance dicts to text artefacts (compose YAML, .env, configs,
   README). No Docker, no network — thousands of generations run in seconds
   under pytest.
2. **Integrations are pairwise.** The integration engine connects a provider
   capability to a consumer (db_provider→ignition, oauth_provider→grafana, …).
   Bugs live in pairs (and in each service alone), not in 15-service
   ensembles. **All-pairs coverage ≈ full integration coverage.**

## The five tiers

### T1 — Single-service sweep (pure, CI)

For each of the 25 services: generate alone with default config, then once per
configurable option set to a non-default value (~140 generations). Assert:
parseable YAML, service present, image:tag matches catalog, every `${VAR}`
referenced in compose exists in the generated `.env`.

### T2 — All-pairs sweep (pure, CI) — the core of this plan

All C(25,2) = 300 pairs (+ ignition×2 for multi-instance). For each pair:

- If `integrations.json` declares an integration between them → assert the
  integration materialises (expected env vars / config files / depends_on).
- If the rules declare mutual exclusivity → assert generation **fails with a
  clean StackBuilder exception** (negative tests matter as much).
- Always: unique container names, no host-port collisions, valid YAML.

Drive the pair list *from the data files*, not a hardcoded list, so new
catalog services are automatically covered. Emit one parametrised pytest case
per pair (`pytest.mark.parametrize`) so failures name the exact pair.

### T3 — Compose-spec validation (needs docker CLI, no containers)

`docker compose -f - config -q` validates generated YAML against the real
compose spec without starting anything. Run it over every T1/T2 artefact.
Mark `@pytest.mark.integration`; skip cleanly when docker is absent so CI
(GitHub runners have docker on ubuntu-latest) and dev machines both work.

### T4 — Golden files for representative stacks (pure, CI)

6–8 curated realistic stacks (e.g. ignition+postgres;
ignition+postgres+keycloak+traefik; ignition+emqx+nodered;
full monitoring: ignition+prometheus+grafana+dozzle; ignition×2+mariadb).
Snapshot every generated artefact under `backend/tests/test_stackbuilder/goldens/`
and diff exactly. Catches accidental regressions in templates, README text,
startup scripts. Provide a `--update-goldens` conftest flag.

### T5 — Live smoke (manual / on-demand, NOT CI)

Actually `docker compose up -d` 2–3 curated stacks, poll health endpoints
(gateway `/StatusPing`, grafana `/api/health`, …), then tear down with
volumes. Implement as a pytest module marked `slow integration`, or reuse
`stackbuilder/stack_runner.py` (it already locates docker incl. WSL paths).
Run on Nigel's machine before releases that touch StackBuilder — never in CI.

## Property-based option (stretch)

`hypothesis` strategy: random subsets of ≤6 services + random valid option
values; invariants = T2's assertions. Good ROI only after T1–T4 are green.

## Execution phases (each is one agent session unit, committable alone)

| Phase | Deliverable | Done when |
| --- | --- | --- |
| 1 ✅ DONE 2026-07-06 | `test_singles_sweep.py` (T1) | 126 cases green (22 enabled services; `mssql`/`authentik`/`authelia` are `enabled: false` in the catalog) |
| 2 ✅ DONE 2026-07-06 | `test_pairs_sweep.py` (T2) | 234 cases green incl. negative mutual-exclusivity + ignition×2. Surfaced and fixed 3 real generator bugs (dead port options, unenforced conflicts → now `IntegrationConflictError` → HTTP 422, wrong provider instance names). Feature gaps found are listed in `docs/OPEN_WORK.md`. |
| 3 ✅ DONE 2026-07-06 | `test_compose_spec.py` (T3) | 29 integration tests; ran green against real docker compose v5.1.3; skips cleanly without docker |
| 4 ✅ DONE 2026-07-06 | `goldens/` + `test_goldens.py` (T4) | 7 golden stacks, `--update-goldens` flag, OAuth/Keycloak secrets normalised (see goldens/README.md). Surfaced + fixed a real nondeterminism bug: `depends_on` order varied per run (`set()` → `dict.fromkeys()`). Known gap: mosquitto password-file salt is nondeterministic but unexercised |
| 5 ✅ DONE 2026-07-06 | `test_live_smoke.py` (T5) | Both stacks up/healthy/torn-down in ~94 s (ports 18000-18999; resident gateway untouched; slow tests force-skipped unless `-m` selected). Found + fixed: generated Grafana datasource provisioning file was never bind-mounted. **All 5 tiers complete — beta label can come off with the next release.** |

Expect phases 1–2 to surface real generator bugs (that's the point) — fix
them in `stackbuilder/`, not by loosening assertions. When the suite is
green through phase 4, remove the "beta" label from the StackBuilder UI.

## Verification commands

```bash
cd backend && .venv/bin/python -m pytest tests/test_stackbuilder -q
cd backend && .venv/bin/python -m pytest tests/test_stackbuilder -m integration -q  # T3/T5
```

Existing suite (8 files, ~3,300 lines) must stay green; new tests extend it.
