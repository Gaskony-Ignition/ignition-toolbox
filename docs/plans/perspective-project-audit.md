# Perspective Project Audit — Design & Plan for a Future Agent Session

**Status:** PLANNED (written 2026-07-06). The perspective playbook library is
currently **empty** (its README advertises 7 playbooks that don't exist —
fixed to say "planned" as part of this work).
**Migration note (31/07/2026):** predates the strangler migration decision
(`../../../toolbox-projects/MIGRATION.md`, D11) — the Electron app is being
replaced by native Ignition projects; re-scope before executing.
**Goal:** Run against a customer's Perspective project and produce a
professional report of recommendations — consistency, layout, quality, best
practice. This is the flagship deliverable for Nigel's consulting work with
Ignition customers. Load skills `add-api-endpoint`, `playbook-authoring`,
`testing-and-verification` first.

## Two modes, one report

### Mode A — Static analysis (primary; works offline on a project export)

Customer sends a project export zip (Designer → Export, or gateway backup).
Perspective resources are plain JSON/py on disk:

```text
com.inductiveautomation.perspective/
├── views/**/view.json        # component tree: root → children, each with
│                              #   type ("ia.container.flex"…), meta.name,
│                              #   props, custom, params, propConfig (bindings)
├── page-config/  styles/  session-props/
ignition/script-python/**     # project library scripts
```

(Real samples to develop against: `/home/nigel/claude/ignition/home/project_mirror/`
and `…/internal/project_mirror/` — actual gateway view.json files, including
genuine smells, e.g. a component named `71oUI5FZdKL._SL1500_` after an Amazon
image filename.)

Static analysis needs **no browser and no gateway** — it's a linter. That
makes it fast, safe on customer data, and fully unit-testable.

### Mode B — Runtime playbooks (fills the empty perspective library)

Generic playbooks using existing step types (`perspective.discover_page`,
`perspective.extract_component_metadata`, `browser.*` — all already
implemented in `playbook/executors/perspective_executor.py`):

1. `session_smoke.yaml` — open project URL, login, verify session starts
2. `page_crawl.yaml` — walk page-config routes, screenshot each, collect
   console errors and load times
3. `navigation_audit.yaml` — verify docks/navigation work on every page
4. `visual_baseline.yaml` — screenshot set for before/after comparisons

These become the library content the README promises, and their outputs
(screenshots, console errors, timings) feed the same report as Mode A.

## Rule engine (the shared core — see also udt-builder-design.md)

```text
backend/ignition_toolkit/audit/
├── engine.py      # generic: Rule → list[Finding]; Finding = severity,
│                  #   location (view path / component path), message,
│                  #   recommendation, rule_id
├── project.py     # loads a project export zip into a queryable model
├── rules/perspective/   # one module per rule family
└── report.py      # findings → markdown/HTML via existing reporting/export.py
```

### Seed rule set

Derived from hard-won conventions in `/home/nigel/claude/ignition/CLAUDE.md` —
already battle-tested on a real gateway.

| Rule family | Examples |
| --- | --- |
| Naming | default/meaningless component names (`Label_1`, image-filename names); inconsistent view/folder casing |
| Layout | coord containers where flex would serve; missing `minHeight/minWidth: 0` on flex children; fixed pixel sizing of children instead of basis/grow |
| Bindings | polling rates < 5 s; expression bindings that should be tag bindings; broken/orphaned tag paths; direct writes from display components |
| Scripts | periodic work in view tick/startup scripts (belongs in gateway timer scripts); `system.util.invokeAsynchronous` daemons; script click-handlers where native nav actions work |
| Consistency | hardcoded colors instead of style classes / theme vars; duplicated styles across views; mixed font strategies |
| Hygiene | unused views (not reachable from page-config), unused params, empty containers, oversized embedded images |
| Structure | deep nesting (>N levels), god-views (>N components — suggest embedded views) |

Every rule carries a **recommendation string written for a customer report**,
not just a lint message. Severity: critical / high / medium / info.

## Output

`report.py` renders: executive summary (score per family), findings table
grouped by view, and a remediation appendix — exported as markdown + HTML
via the existing `reporting/export.py` machinery. This document *is* the
customer deliverable.

## Execution phases

| Phase | Deliverable | Done when |
| --- | --- | --- |
| 0 ✅ DONE 2026-07-06 | Fix `backend/playbooks/perspective/README.md` (advertised 7 nonexistent playbooks → marked planned) | README truthful |
| 1 ✅ DONE 2026-07-06 | `audit/project.py` loader + inventory | Loads dir or zip; smoke-run on real project mirror: 5 views / 470 components / 379 bindings |
| 2 ✅ DONE 2026-07-06 | `audit/engine.py` + 10 seed rules + 34 tests | All rules have positive+negative fixtures; real-mirror run yields 366 findings incl. the Barometer smells. Open tuning question: `consistency-hardcoded-color` fired 261× on one view — needs per-view aggregation/threshold before customer use |
| 3 ✅ DONE 2026-07-06 | `report.py` + `/api/audit/perspective` (+ `/markdown` download) + Audit page/tab | End-to-end verified on the real project mirror: 366 findings → 16 aggregated rows, markdown report downloads; 400 non-zip / 413 >50MB; upload chunk-checked + temp-dir only. Nigel to review: report tone/wording, remediation appendix uses first finding's text as representative |
| 4 ✅ DONE 2026-07-06 | Mode B playbooks 1–2 (`session_smoke`, `page_crawl`) + `test-project/ToolboxAudit` | Both proven on the docker gateway (page_crawl 9/9); 12/12 playbooks validate. Deploy procedure: docker cp + ownership fix + gateway "Scan File System" button (no restart). Gotcha documented: expired Perspective trial → run `gateway/reset_trial.yaml` first |
| 5 ✅ DONE 2026-07-06 | navigation_audit + visual_baseline playbooks; runtime results merged into report | All 4 playbooks proven on the docker gateway (14/14 validate); `audit/runtime.py` maps playbook executions to a "Runtime Checks" report section (additive — static-only reports byte-identical). Bonus: found+fixed engine bug (Playwright TimeoutError not caught → `browser.verify exists:false` never worked). Known gap: console_errors not captured (no step type yet). **All phases complete.** Future: rule pack growth as customer projects surface new smells |

Phases 1–3 are pure backend+frontend work, fully testable headless — ideal
for an autonomous agent session. Phase 4 needs the test gateway
(`http://192.168.153.128:8088`) with a Perspective project present.

## Decisions Nigel must make (agents: ask, don't assume)

1. Report tone/branding (it goes in front of customers).
2. Rule thresholds (polling-rate floor, nesting depth, component-count caps).
3. Whether audit ever *writes* anything to a gateway — recommendation: never;
   read-only on exports keeps it safe to point at production customer systems.
