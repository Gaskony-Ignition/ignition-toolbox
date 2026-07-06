# Perspective Playbooks

Playbooks for Perspective (web-based HMI) browser automation using Playwright.

## Status: Phase 5 done — all 4 playbooks available

`session_smoke.yaml`, `page_crawl.yaml`, `navigation_audit.yaml`, and
`visual_baseline.yaml` all ship and are verified (run green against the
`ignition-module-testing` docker gateway's `ToolboxAudit` test project - see
`test-project/README.md`). This completes the Mode B playbook library for
the **Perspective Project Audit** feature — see
`docs/plans/perspective-project-audit.md`. Their runtime results can be
folded into the same audit report as Mode A's static findings via
`ignition_toolkit.audit.runtime.build_runtime_results_from_execution`.

## Available Playbooks

| Playbook | Description |
| -------- | ----------- |
| `session_smoke.yaml` | Open a Perspective project's client URL, verify a session starts and a page renders (no login required for public/anonymous projects; best-effort login otherwise) |
| `page_crawl.yaml` | Navigate a small fixed set of page-config routes, screenshot each, and run `perspective.discover_page` to inventory components |
| `navigation_audit.yaml` | Verify each page-config route renders directly *and* that the in-app navigation button actually drives the client between routes (`perspective.verify_navigation` against the observed URL after each navigation) |
| `visual_baseline.yaml` | Full-page screenshot set for every configured route, with filenames keyed by a `baseline_name` parameter so two runs (e.g. "before"/"after") produce a diffable pair |

> **Unlicensed/trial gateways:** Perspective's 2-hour trial expiring makes
> these playbooks fail at the "wait for page to render" step — the client
> shows a "Trial Expired" screen instead of the view. Run the library's
> `gateway/reset_trial.yaml` playbook first, then re-run. (Confirmed the
> hard way on the docker test gateway, 06/07/2026.)

## Test project

`test-project/ToolboxAudit/` is a minimal 2-page Perspective project used to
prove all four available playbooks against a real gateway, plus a README with
the exact deploy steps (including a gotcha around the gateway's project
scan needing a manual "Scan File System" click for brand-new project
directories).

## Capabilities (already implemented in the engine)

- Automated UI testing for Perspective applications
- Session management and authentication testing
- Component interaction validation (buttons, inputs, dropdowns)
- View navigation and dock panel testing
- Component discovery and metadata extraction
  (`perspective.discover_page`, `perspective.extract_component_metadata`)
- Live browser streaming during execution (2 FPS)

## Usage

1. Navigate to the **Playbooks** page in the Toolbox
2. Select a Perspective playbook
3. Configure the gateway URL and credentials
4. Click **Run** to execute with live browser preview

See `docs/playbook_syntax.md` for the full YAML syntax reference.
