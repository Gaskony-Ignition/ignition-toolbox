# UDT Builder — Design & Plan for a Future Agent Session

**Status:** PLANNED (written 2026-07-06). Nothing is built yet ("coming soon").
**Goal:** Make it super easy to build high-quality, best-practice Ignition
UDTs — standardised structure, alarms, history, and documentation — instead of
hand-assembling them in Designer. Load skills `add-api-endpoint`,
`toolbox-conventions`, and `testing-and-verification` first.

## ⚠️ Prerequisite: import the reference project (Nigel action)

The prior customer-specific "Ignition UDTs" project was built in the Claude
desktop app on the old Windows machine — **it is not on this machine** (searched
2026-07-06: `~/claude`, `~/Downloads`, NAS snapshot archives). Before an agent
starts Phase 2, Nigel should export/copy that material into
`docs/reference/udt-examples/` (tag-export JSON files and any conventions
docs). Phase 1 does not depend on it.

## What a UDT actually is (design surface)

An Ignition UDT (`tagType: "UdtType"` in tag-export JSON) bundles:

- **Parameters** — instance inputs (device name, OPC path root, engineering
  ranges) referenced as `{ParamName}` in member properties
- **Member tags** — OPC / memory / expression / derived / query tags, nested
  folders, and *nested UDT instances* (composition) plus **inheritance**
  (parent type)
- **Per-member config** — data type, engineering units, scaling, deadband,
  documentation/tooltip, security, read-only
- **Alarms** — per member: modes, setpoints (often parameter-bound),
  priorities, deadbands, associated data
- **History** — storage provider, sample mode, deadband — per member

"Streamlining" = users answer a small structured questionnaire; the tool emits
a complete, convention-conforming UDT JSON they import into Designer (Tag
Browser → Import) or push via the 8.3 tag config API later.

## Architecture (shared core with the Perspective audit — build once)

```text
backend/ignition_toolkit/udt/
├── models.py        # Pydantic models mirroring Ignition tag-export JSON
├── templates/       # Device-class templates as data (JSON): motor, valve,
│                    #   analog_input, digital_input, pid_loop, drive, tank …
├── builder.py       # questionnaire answers + template → UDT JSON
├── conventions.py   # THE STANDARD: naming, alarm, history, docs rules
└── linter.py        # score an existing UDT export against conventions.py
```

The linter reuses the generic rule-engine core proposed in
`perspective-project-audit.md` (`ignition_toolkit/audit/`): rule → finding
(severity, location, recommendation) → report. Build that core in whichever
plan is executed first; the other consumes it.

### The conventions (draft — Nigel to ratify before Phase 2)

- Naming: PascalCase UDT type names, camelCase member tags (matches the
  existing SCADA-designer conventions), no spaces, no default names
- Every member: `documentation` populated; `engUnit` on analogs
- OPC paths built from parameters (`{OpcServer}`, `{DevicePath}`) — never
  hardcoded server/device names inside the type
- Alarms: ISA-18.2-aligned priority mapping, deadbands mandatory on analog
  alarms, alarm names standardised (HiHi/Hi/Lo/LoLo/Fault/…)
- History: deliberate per-member choice (provider + deadband), never
  blanket-enabled
- Structure: status/command/config subfolders for larger device classes

### Frontend

New page `frontend/src/pages/UdtBuilder.tsx` (nav entry exists as "coming
soon"): pick device class → dynamic form (from template metadata, same
pattern as playbook `parameters` → execution dialog) → live JSON preview →
Download / Copy. Later: "Lint existing UDT" tab (upload export JSON → findings
table). Follow `add-api-endpoint` for the wiring; API under `/api/udt/`.

## Execution phases

| Phase | Deliverable | Done when |
| --- | --- | --- |
| 1 ✅ DONE 2026-07-06 (synthetic fixtures — re-validate against real exports when available) | `udt/models.py` + round-trip tests | 15 tests green; lossless `TagElement` model with camelCase aliases; known limitation pinned (snake_case input keys rewritten) |
| 2 | `conventions.py` + 3 templates (motor, valve, analog_input) + `builder.py` | Generated JSON imports cleanly into the test gateway's Designer and instances work against simulator tags |
| 3 | API endpoints + UdtBuilder page (form → preview → download) | End-to-end: build a Motor UDT in the UI, import to gateway, no manual edits needed |
| 4 | `linter.py` + lint tab | Nigel's reference UDTs (see prerequisite) produce a sensible findings report |
| 5 | Template library growth seeded from reference project + community feedback | ≥8 device classes |

Phase 1–2 tests are pure pytest (`backend/tests/test_udt/`). Phase 2's "done"
requires a real import into the VMware test gateway
(`http://192.168.153.128:8088`) — an agent can generate and validate; Nigel
does the Designer import check or it's driven via a gateway playbook.

## Decisions Nigel must make (agents: ask, don't assume)

1. Ratify the naming + alarm-priority conventions above (they become the
   product's opinion — hard to change later).
2. Export the reference UDT project from the Claude Windows GUI / old machine.
3. Delivery mechanism v1: download-JSON-only (recommended — zero gateway risk)
   vs direct push via 8.3 tag config API.
