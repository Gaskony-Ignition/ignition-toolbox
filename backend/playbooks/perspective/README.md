# Perspective Playbooks

Playbooks for Perspective (web-based HMI) browser automation using Playwright.

## Status: library is empty — playbooks are planned

No Perspective playbooks ship yet. The engine support is fully implemented
(`perspective.*` step types, live browser streaming, component discovery);
the library content is being built as part of the **Perspective Project
Audit** feature — see `docs/plans/perspective-project-audit.md`.

## Planned Playbooks

| Playbook | Description |
| -------- | ----------- |
| `session_smoke.yaml` | Open project URL, login, verify a session starts |
| `page_crawl.yaml` | Walk page-config routes, screenshot each, collect console errors and load times |
| `navigation_audit.yaml` | Verify docks/navigation work on every page |
| `visual_baseline.yaml` | Screenshot set for before/after comparisons |

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
