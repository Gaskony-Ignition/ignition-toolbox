# UDT Composer — guided generic UDT creation

Status: **in progress** (started 06/07/2026). Supersedes the questionnaire
flow in [udt-builder-design.md](udt-builder-design.md) as the primary UX;
that doc's models/conventions/template phases (1–3, shipped v3.3.x) are the
foundation and stay.

## Why (Nigel, 06/07/2026)

> "The UDT section is too specific. I don't really want to have such
> specific UDTs. In theory I would like to be able to just create good
> quality UDTs in a guided format from this space."

Device-class templates only help when the device matches one of three
archetypes. The tool's real job is: build **any** UDT and make it come out
conforming — naming, `{Parameter}` refs, ISA-18.2 alarm priorities, history
config, documentation.

Ratified decisions (06/07/2026):

- Existing templates become **quick-start presets** that pre-fill the
  composer (blank start also available). The old questionnaire UI goes away.
- **Wizard + live quality checks**: Basics → Structure → Alarms → History →
  Review, with a lint panel that updates as you build. This pulls the
  planned phase-4 UDT linter forward into this feature.
- Ships as v3.4.0 (lead releases; agents never bump versions).

All earlier UDT conventions still apply (bare alarm names `HiHi`/`Hi`/`Lo`/
`LoLo`, ISA-18.2 priority mapping, naming style user-selectable with
camelCase default, download-JSON-only delivery).

## Architecture

- The **composition** is the wire format the wizard edits. It is a
  simplified, UI-friendly tree that the backend converts to a
  `UdtDefinition` (udt/models.py) and then to Ignition tag-export JSON via
  `to_tag_export()`. All conventions (naming style application, alarm
  priority defaults) are applied server-side in `udt/composer.py` — the
  frontend never re-implements convention logic.
- The **UDT lint rule pack** lives at `ignition_toolkit/audit/rules/udt/`
  on the shared audit engine (`audit/engine.py`) — the same
  Rule → Finding(severity, location, message, recommendation, rule_id)
  shape as the Perspective rules. Rules wrap the existing check functions
  in `udt/conventions.py` (check_naming, check_documentation, eng-unit,
  alarm priority/deadband, deliberate-history, parameterised OPC paths…).
- Every compose response includes lint findings, so "live" lint is one
  debounced POST from the frontend.

## API contract (fixed — both agents build to this)

`POST /api/udt/compose` — body:

```json
{
  "type_name": "ConveyorMotor",
  "description": "…",
  "naming_style": "camelCase",
  "parameters": [
    {"name": "DevicePath", "data_type": "String", "default_value": "", "description": "…"}
  ],
  "members": [
    {"kind": "folder", "name": "status", "members": [
      {"kind": "tag", "name": "speed", "value_source": "opc",
       "data_type": "Float4",
       "opc_item_path": "ns=1;s={DevicePath}/Speed", "opc_server": "Ignition OPC UA Server",
       "eng_unit": "rpm", "eng_low": 0, "eng_high": 1500,
       "documentation": "…", "tooltip": "…",
       "history": {"enabled": true, "tag_group": "Default Historical", "deadband_style": "Auto"},
       "alarms": [
         {"name": "HiHi", "setpoint": 1400, "mode": "AboveValue", "priority": null}
       ]}
    ]}
  ]
}
```

Response `200`:

```json
{
  "udt": { "…tag-export JSON…": true },
  "filename": "ConveyorMotor_udt.json",
  "findings": [
    {"rule_id": "udt-missing-documentation", "severity": "medium",
     "location": "status/speed", "message": "…", "recommendation": "…"}
  ]
}
```

- `value_source`: `"opc" | "memory" | "expression"` (expression members
  carry `expression`; memory carry `value`).
- `alarms[].priority: null` means "apply the ISA-18.2 default for this
  alarm name"; an explicit value overrides.
- Structural errors (bad type name, unknown parameter reference, duplicate
  sibling names, invalid data type) → `422` with a message listing each
  problem, same joined format as the existing `/api/udt/build`. Lint
  findings are NOT errors — a lint-dirty UDT still composes.

`GET /api/udt/presets` — `[{"id": "motor", "label": "Motor", "description":
"…", "composition": {…same shape as the compose body…}}]`. Presets are
derived from the existing three templates; a test must assert each preset,
run through `/compose`, produces a UDT equivalent to the old
`/build`-with-default-answers output (member names, structure, alarms).

Existing `/api/udt/templates` and `/api/udt/build` stay (tested, used by
presets internally); they are no longer called by the UI.

## Phases

| Phase | What | State |
| --- | --- | --- |
| C1 backend | `udt/composer.py` (composition models + convert + validate), UDT lint pack on audit engine, `/api/udt/compose`, `/api/udt/presets`, tests incl. preset-parity | ✅ 06/07/2026 |
| C2 frontend | Wizard (Basics → Structure → Alarms → History → Review), tree member editor, debounced live lint panel, preset quick-start cards, download/copy; replaces questionnaire UI in UdtBuilder.tsx; tests | ✅ 06/07/2026 |
| C3 lead | Integration verify (dev run), docs/OPEN_WORK update, v3.4.0 release | ✅ 06/07/2026 |

Lead integration verification (06/07/2026) caught and fixed three
frontend/backend contract gaps the parallel agents couldn't see: data-type
names (UI offered legacy 7.x `Bool`/`Int2/4/8`; exports use
`Boolean`/`Short`/`Integer`/`Long` — UI would have 422'd), Boolean alarm
convention (UI invented a `State`/`EqualTo` alarm; the standard is
`Fault`/`Trip`/`Warning` with `BooleanTrue` + ISA defaults), and a missing
deadband input (analog alarms lint for a positive deadband the UI couldn't
set). Lesson for future parallel agent builds: enumerate *all* value
vocabularies (data types, alarm names, modes) in the contract, not just
field names.

Later (unchanged from udt-builder-design.md): more presets, Designer
import check, validation against Nigel's reference exports (still not on
this machine).
