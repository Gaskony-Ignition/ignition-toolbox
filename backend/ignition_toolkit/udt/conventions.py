"""
UDT conventions — THE STANDARD.

This module is the single source of truth for what makes a generated (or
hand-authored) Ignition UDT "convention-conforming" for this project. It is
deliberately written as **data + predicates**, not prose, so:

- ``builder.py`` can self-check every UDT it emits before returning it, and
- Phase 4's ``linter.py`` can import the exact same constants/functions to
  score arbitrary/real UDT exports, rather than re-encoding the rules.

Status: DRAFT, ratified-by-instruction for Phase 2 (see
``docs/plans/udt-builder-design.md`` "The conventions" — Nigel authorised
implementing the draft as written; it may be refined once his reference UDT
exports are available). Anywhere this module had to resolve an ambiguity not
spelled out in the design doc, that judgement call is noted in a comment so
it can be flagged for ratification.

Convention summary (see the design doc for the original draft):

1. **Naming** — UDT *type* names are always PascalCase. Every *member*
   (atomic tag, folder, or nested UDT instance) is **either** camelCase
   **or** PascalCase — user-selectable per build via ``builder.build()``'s
   ``naming_style`` option (see ``NAMING_STYLES``/``DEFAULT_NAMING_STYLE``
   below); a single UDT is internally consistent (one style throughout, never
   mixed). No spaces, no Designer-default placeholder names (``NewTag_0``,
   ...). Parameter names stay PascalCase and alarm names stay the
   standardised bare names (``HiHi``/``Fault``/...) regardless of the
   member-naming style in effect — neither is a "member" for this rule.
2. **Documentation** — every member carries non-empty ``documentation``.
3. **Engineering units** — every analog member (``Float4``/``Float8``)
   carries a non-empty ``engUnit``.
4. **OPC paths from parameters** — ``opcItemPath`` always references at
   least one ``{Parameter}``; ``opcServer`` is *only* ever a parameter
   reference (``{OpcServer}``), never a hardcoded connection name.
5. **Alarms** — priority is one of the ISA-18.2-aligned levels below;
   deadbands are mandatory on any alarm defined against an analog member;
   alarm names are drawn from the standardised set (``HiHi``/``Hi``/``Lo``/
   ``LoLo``/``Fault``/``Trip``/``Warning``).
6. **History** — ``historyEnabled`` must be an explicit per-member choice
   (never left unset/defaulted); if enabled, ``historyProvider`` must be set
   and analog members must also set ``historicalDeadband``.
7. **Structure** — larger device classes group members under ``status``/
   ``command``/``config`` folders (camelCase, per rule 1 — see the "Judgement
   calls" note below).

Judgement calls made resolving the draft (flag for Nigel's ratification):

- The design doc's prose example writes folder names capitalised
  ("status/command/config"). Rule 1 (member naming) is applied uniformly to
  folders and UDT instances as well as atomic tags, since a folder is a
  member of its parent UDT like any other tag node — whichever naming style
  is selected, ``status``/``command``/``config`` fold in the same as any
  other member name (``Status``/``Command``/``Config`` under PascalCase).
- The Phase 1 synthetic fixtures (``motor_simple.json``,
  ``valve_nested_inheritance.json``) use PascalCase member names
  (``Speed``, ``Running``, ``Actuator``...). Those fixtures predate this
  module and exist only to exercise the lossless round-trip in
  ``models.py`` — they are **not** examples of convention-conforming output
  and are intentionally not migrated here.
- "Alarm names standardised (HiHi/Hi/Lo/LoLo/Fault/...)" is implemented as
  the literal ``AlarmConfig.name`` value (e.g. ``"HiHi"``), not a
  member-name-prefixed variant (e.g. ``"SpeedHiHi"``) — the member is already
  identified by the tag's own path in any alarm summary/journal view.
  **RATIFIED by Nigel on 2026-07-06** — no longer a draft judgement call.
- ISA-18.2 does not itself define Ignition's five built-in priority levels;
  ``ALARM_PRIORITY_GUIDANCE`` below is this project's mapping of Ignition's
  Diagnostic/Low/Medium/High/Critical onto ISA-18.2's consequence-and-
  response-time philosophy. **RATIFIED by Nigel on 2026-07-06.**
- Member/folder naming *style* (camelCase vs. PascalCase) was originally a
  single fixed rule (camelCase only, per the design doc draft). **Nigel
  decided on 2026-07-06 that this is user-selectable**, not fixed: templates
  keep a single canonical (camelCase) spelling of every member/folder name,
  and ``builder.build()``'s ``naming_style`` argument renders it in whichever
  style the user chose at build time. ``NAMING_STYLES`` enumerates the valid
  options and ``DEFAULT_NAMING_STYLE`` is the fallback when unspecified.
- The Phase 3 delivery-mechanism question in the design doc ("download-JSON-
  only" vs. a direct push via the 8.3 tag config API) was **RATIFIED by
  Nigel on 2026-07-06: download-JSON-only** — future agents should stop
  flagging this as an open question when they reach Phase 3; it is settled,
  not a draft assumption. (Noted here, alongside the other now-ratified
  items, even though delivery is a Phase 3/API concern rather than a
  `conventions.py` rule, so one place records every 2026-07-06 ratification.)
"""

import logging
import re

from ignition_toolkit.udt.models import AlarmConfig, TagElement

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Naming
# --------------------------------------------------------------------------

_PASCAL_CASE_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
_CAMEL_CASE_RE = re.compile(r"^[a-z][A-Za-z0-9]*$")

# Designer's own placeholder names for freshly-created nodes — a name
# matching one of these was almost certainly never renamed by a human.
_DEFAULT_NAME_RE = re.compile(
    r"^(new_?tag|new_?folder|new_?udt|new_?type|tag)_?\d*$", re.IGNORECASE
)

# Member node kinds that "camelCase, documented, ..." apply to. UdtType is
# excluded — it is the type itself, checked separately with PascalCase rules.
MEMBER_TAG_TYPES = frozenset({"AtomicTag", "Folder", "UdtInstance"})

# Data types treated as "analog" for the engUnit/deadband rules below.
# Deliberately narrow: booleans, strings, and (currently) integers are not
# considered analog even though Ignition allows engineering units on them,
# because the common case (raw discrete counts) rarely wants one.
ANALOG_DATA_TYPES = frozenset({"Float4", "Float8"})

# Folder names larger device classes should use to group members. Written in
# their canonical camelCase spelling; ``apply_naming_style`` renders them (and
# every other member name) in whichever style a build selected.
STANDARD_FOLDERS = ("status", "command", "config")

# Valid member/folder naming styles a builder consumer may select, and the
# fallback used when a caller doesn't specify one. Nigel-decided
# (2026-07-06): naming style is user-selectable, not fixed — see the module
# docstring's "Judgement calls" note. A future API/UI should enumerate this
# constant rather than hardcoding the two option strings.
NAMING_STYLES: tuple[str, ...] = ("camelCase", "PascalCase")
DEFAULT_NAMING_STYLE = "camelCase"


def is_pascal_case(name: str) -> bool:
    """True if ``name`` is PascalCase (UDT type name shape): no spaces/underscores."""
    return bool(_PASCAL_CASE_RE.match(name))


def is_camel_case(name: str) -> bool:
    """True if ``name`` is camelCase (member tag name shape): no spaces/underscores."""
    return bool(_CAMEL_CASE_RE.match(name))


def is_default_name(name: str) -> bool:
    """True if ``name`` looks like an un-renamed Designer default (``NewTag_0``, ...)."""
    return bool(_DEFAULT_NAME_RE.match(name.strip()))


def is_valid_type_name(name: str) -> bool:
    """A UDT *type* name: PascalCase, no spaces, not a default placeholder."""
    return bool(name) and " " not in name and is_pascal_case(name) and not is_default_name(name)


def is_valid_member_name(name: str) -> bool:
    """
    A UDT *member* name (atomic tag/folder/instance): no spaces, not a default
    placeholder, and shaped like **either** naming style in ``NAMING_STYLES``
    (camelCase or PascalCase) — the style is a per-build user choice (see
    ``apply_naming_style``), not something a single name can be judged wrong
    against in isolation.
    """
    if not name or " " in name or is_default_name(name):
        return False
    return is_camel_case(name) or is_pascal_case(name)


def to_camel_case(name: str) -> str:
    """Render a canonical member/folder ``name`` in camelCase (lowercase the first letter only)."""
    return name[:1].lower() + name[1:] if name else name


def to_pascal_case(name: str) -> str:
    """Render a canonical member/folder ``name`` in PascalCase (uppercase the first letter only)."""
    return name[:1].upper() + name[1:] if name else name


def apply_naming_style(name: str, style: str) -> str:
    """
    Render a template's canonical (camelCase-authored) member/folder ``name``
    in the requested ``style``.

    Only the first character changes — canonical names are already
    multi-word-boundary-correct camelCase (e.g. ``highSpeedSetpoint``), so
    PascalCase is just that first letter capitalised (``HighSpeedSetpoint``)
    and camelCase is a no-op (or lowercases an already-Pascal name's first
    letter, for symmetry). No other mangling is performed.

    Raises:
        ValueError: ``style`` is not one of ``NAMING_STYLES``.
    """
    if style == "camelCase":
        return to_camel_case(name)
    if style == "PascalCase":
        return to_pascal_case(name)
    raise ValueError(f"Unknown naming style {style!r}; expected one of {NAMING_STYLES}")


# --------------------------------------------------------------------------
# Documentation / engineering units
# --------------------------------------------------------------------------


def is_analog_data_type(data_type: str | None) -> bool:
    """True if ``data_type`` is one of the analog data types (see ``ANALOG_DATA_TYPES``)."""
    return data_type in ANALOG_DATA_TYPES


def has_documentation(element: TagElement) -> bool:
    """True if ``element`` carries non-empty ``documentation``."""
    return bool(element.documentation and element.documentation.strip())


def requires_eng_unit(element: TagElement) -> bool:
    """True if convention requires ``element`` to declare an ``engUnit`` (analog atomic tags)."""
    return element.tag_type == "AtomicTag" and is_analog_data_type(element.data_type)


def has_eng_unit(element: TagElement) -> bool:
    """True if ``element`` carries a non-empty ``engUnit``."""
    return bool(element.eng_unit and element.eng_unit.strip())


# --------------------------------------------------------------------------
# OPC paths built from parameters
# --------------------------------------------------------------------------

_PARAM_REF_RE = re.compile(r"\{(\w+)\}")
_PURE_PARAM_REF_RE = re.compile(r"^\{\w+\}$")


def is_parameterised(value: str | None) -> bool:
    """True if ``value`` is *only* a single ``{Param}`` reference (used for ``opcServer``)."""
    return bool(value) and bool(_PURE_PARAM_REF_RE.match(value.strip()))


def opc_item_path_uses_parameters(opc_item_path: str | None) -> bool:
    """True if ``opc_item_path`` contains at least one ``{Param}`` reference anywhere in it."""
    return bool(opc_item_path) and bool(_PARAM_REF_RE.search(opc_item_path))


# --------------------------------------------------------------------------
# Alarms — ISA-18.2-aligned priority mapping
# --------------------------------------------------------------------------

# Ignition's five built-in alarm priorities, ordered lowest to highest.
ALARM_PRIORITIES: tuple[str, ...] = ("Diagnostic", "Low", "Medium", "High", "Critical")

# ISA-18.2 frames alarm priority as a function of *consequence severity* and
# *allowable response time*. This is this project's mapping of that
# philosophy onto Ignition's five levels — the usage guidance a future
# linter (and human authors) should apply when choosing a priority.
ALARM_PRIORITY_GUIDANCE: dict[str, str] = {
    "Diagnostic": (
        "Not a process alarm. Equipment/communication health information only "
        "(e.g. device offline, OPC bad quality). No operator response required; "
        "excluded from operator alarm-rate KPIs and shelving reviews."
    ),
    "Low": (
        "Abnormal condition with no immediate risk of escalation; operator "
        "response time is long (minutes-to-hours). Use for early-warning "
        "deviations and the standardised 'Warning' alarm."
    ),
    "Medium": (
        "Requires operator action within a defined time to prevent escalation "
        "into equipment damage, quality loss, or a minor safety/environmental "
        "issue. Default level for standard process 'Hi'/'Lo' deviation alarms."
    ),
    "High": (
        "Requires prompt operator action to prevent significant equipment "
        "damage, production loss, or a safety/environmental consequence. "
        "Default level for 'HiHi'/'LoLo' and equipment 'Fault' alarms."
    ),
    "Critical": (
        "Highest priority: potential for serious safety, environmental, or "
        "major asset-loss consequence if not corrected immediately, typically "
        "tied to trip/shutdown logic. Use sparingly (ISA-18.2 target: a small "
        "minority of configured alarms) — reserve for the standardised "
        "'Trip' alarm and genuine safety-instrumented conditions."
    ),
}

# Standardised alarm names and their default priority/mode. Templates use
# these as starting points; a device-class questionnaire may still let the
# user pick a different (still-valid) priority for a specific instance.
STANDARD_ALARM_DEFAULTS: dict[str, dict[str, str]] = {
    "HiHi": {"priority": "High", "mode": "AboveValue"},
    "Hi": {"priority": "Medium", "mode": "AboveValue"},
    "Lo": {"priority": "Medium", "mode": "BelowValue"},
    "LoLo": {"priority": "High", "mode": "BelowValue"},
    "Fault": {"priority": "High", "mode": "BooleanTrue"},
    "Trip": {"priority": "Critical", "mode": "BooleanTrue"},
    "Warning": {"priority": "Low", "mode": "BooleanTrue"},
}

STANDARD_ALARM_NAMES: tuple[str, ...] = tuple(STANDARD_ALARM_DEFAULTS)


def is_standard_alarm_name(name: str | None) -> bool:
    """True if ``name`` is one of the standardised alarm names."""
    return name in STANDARD_ALARM_DEFAULTS


def is_valid_alarm_priority(priority: str | None) -> bool:
    """True if ``priority`` is one of Ignition's five ISA-18.2-mapped priorities."""
    return priority in ALARM_PRIORITIES


def alarm_deadband_required(member_data_type: str | None) -> bool:
    """True if any alarm on a member of ``member_data_type`` must carry a deadband.

    Convention: mandatory on analog members, never required on discrete
    (Boolean/String) members where a deadband would be meaningless.
    """
    return is_analog_data_type(member_data_type)


def has_valid_deadband(alarm: AlarmConfig) -> bool:
    """True if ``alarm.deadband`` is set and is a positive number (0 gives no hysteresis)."""
    if alarm.deadband is None:
        return False
    try:
        return float(alarm.deadband) > 0
    except (TypeError, ValueError):
        return False


# --------------------------------------------------------------------------
# History — deliberate per-member policy
# --------------------------------------------------------------------------


def has_deliberate_history_choice(element: TagElement) -> bool:
    """True if ``element`` makes an explicit historyEnabled choice (or doesn't need one)."""
    if element.tag_type != "AtomicTag":
        return True
    return element.history_enabled is not None


def history_config_complete(element: TagElement) -> bool:
    """True if, whenever history is enabled, provider (+ deadband for analogs) is also set."""
    if not element.history_enabled:
        return True
    if not element.history_provider:
        return False
    if is_analog_data_type(element.data_type) and element.historical_deadband is None:
        return False
    return True


# --------------------------------------------------------------------------
# Aggregate checks — reusable by builder.py's self-check and Phase 4's linter
# --------------------------------------------------------------------------


def check_naming(element: TagElement, path: str) -> list[str]:
    """Naming-convention issues for ``element`` alone (not its descendants)."""
    issues: list[str] = []
    name = element.name
    if not name:
        return issues
    if element.tag_type == "UdtType":
        if not is_valid_type_name(name):
            issues.append(f"{path}: UDT type name '{name}' is not valid PascalCase")
    elif element.tag_type in MEMBER_TAG_TYPES:
        if not is_valid_member_name(name):
            issues.append(f"{path}: member name '{name}' is not valid camelCase or PascalCase")
    return issues


def check_documentation(element: TagElement, path: str) -> list[str]:
    """Documentation-convention issues for ``element`` alone."""
    if element.tag_type in MEMBER_TAG_TYPES and not has_documentation(element):
        return [f"{path}: missing documentation"]
    return []


def check_eng_unit(element: TagElement, path: str) -> list[str]:
    """Engineering-unit-convention issues for ``element`` alone."""
    if requires_eng_unit(element) and not has_eng_unit(element):
        return [f"{path}: analog member missing engUnit"]
    return []


def check_opc_path(element: TagElement, path: str) -> list[str]:
    """OPC-path-from-parameters issues for ``element`` alone."""
    if element.tag_type != "AtomicTag" or element.value_source != "opc":
        return []
    issues: list[str] = []
    if not opc_item_path_uses_parameters(element.opc_item_path):
        issues.append(f"{path}: opcItemPath does not reference any {{Parameter}}")
    if element.opc_server is not None and not is_parameterised(element.opc_server):
        issues.append(f"{path}: opcServer '{element.opc_server}' is hardcoded, not a {{Parameter}}")
    return issues


def check_history(element: TagElement, path: str) -> list[str]:
    """History-policy issues for ``element`` alone."""
    if element.tag_type != "AtomicTag":
        return []
    issues: list[str] = []
    if not has_deliberate_history_choice(element):
        issues.append(f"{path}: historyEnabled not explicitly set")
    elif not history_config_complete(element):
        issues.append(f"{path}: history enabled but historyProvider/historicalDeadband incomplete")
    return issues


def check_alarms(element: TagElement, path: str) -> list[str]:
    """Alarm-convention issues for every alarm on ``element`` alone."""
    issues: list[str] = []
    for alarm in element.alarms or []:
        label = f"{path} alarm '{alarm.name}'"
        if not is_standard_alarm_name(alarm.name):
            issues.append(f"{label}: name is not one of the standardised alarm names")
        if not is_valid_alarm_priority(alarm.priority):
            issues.append(f"{label}: priority '{alarm.priority}' is not a valid ISA-18.2 level")
        if alarm_deadband_required(element.data_type) and not has_valid_deadband(alarm):
            issues.append(f"{label}: analog member alarm is missing a positive deadband")
    return issues


def find_convention_issues(element: TagElement, path: str = "") -> list[str]:
    """
    Recursively check ``element`` and every descendant against this module's
    conventions. Returns a flat list of human-readable issue strings (empty
    == fully conformant).

    This function is the shared core between ``builder.py`` (self-checks its
    own output before returning) and the Phase 4 linter (checks arbitrary/
    real UDT exports) — keep it free of any builder- or template-specific
    assumptions.

    Args:
        element: Any node in a tag tree — typically a ``UdtDefinition`` root.
        path: Slash-separated path prefix for issue messages, built up
            automatically as the recursion descends; callers normally omit
            it (or pass the UDT type name).

    Returns:
        A list of issue description strings, one per violation found.
    """
    current_path = f"{path}/{element.name}" if element.name else (path or "<root>")

    issues: list[str] = []
    issues.extend(check_naming(element, current_path))
    issues.extend(check_documentation(element, current_path))
    issues.extend(check_eng_unit(element, current_path))
    issues.extend(check_opc_path(element, current_path))
    issues.extend(check_history(element, current_path))
    issues.extend(check_alarms(element, current_path))

    for child in element.tags or []:
        issues.extend(find_convention_issues(child, current_path))

    return issues
