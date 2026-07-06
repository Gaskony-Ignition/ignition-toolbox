# Perspective Playbooks

Playbooks for Perspective (web-based HMI) browser automation using Playwright.

## Status: Phase 4 done — 2 playbooks available, 2 more planned

`session_smoke.yaml` and `page_crawl.yaml` ship and are verified (run green
against the `ignition-module-testing` docker gateway's `ToolboxAudit` test
project - see `test-project/README.md`). The remaining two are still planned
as part of the **Perspective Project Audit** feature — see
`docs/plans/perspective-project-audit.md`.

## Available Playbooks

| Playbook | Description |
| -------- | ----------- |
| `session_smoke.yaml` | Open a Perspective project's client URL, verify a session starts and a page renders (no login required for public/anonymous projects; best-effort login otherwise) |
| `page_crawl.yaml` | Navigate a small fixed set of page-config routes, screenshot each, and run `perspective.discover_page` to inventory components |

> **Unlicensed/trial gateways:** Perspective's 2-hour trial expiring makes
> both playbooks fail at the "wait for page to render" step — the client
> shows a "Trial Expired" screen instead of the view. Run the library's
> `gateway/reset_trial.yaml` playbook first, then re-run. (Confirmed the
> hard way on the docker test gateway, 06/07/2026.)

## Planned Playbooks

| Playbook | Description |
| -------- | ----------- |
| `navigation_audit.yaml` | Verify docks/navigation work on every page |
| `visual_baseline.yaml` | Screenshot set for before/after comparisons |

## Test project

`test-project/ToolboxAudit/` is a minimal 2-page Perspective project used to
prove the two available playbooks against a real gateway, plus a README with
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

## Usage (once playbooks exist)

1. Navigate to the **Playbooks** page in the Toolbox
2. Select a Perspective playbook
3. Configure the gateway URL and credentials
4. Click **Run** to execute with live browser preview

See `docs/playbook_syntax.md` for the full YAML syntax reference.
