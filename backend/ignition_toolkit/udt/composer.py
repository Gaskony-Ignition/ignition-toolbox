"""
UDT Composer — turns a UI-friendly "composition" tree into a
convention-conforming :class:`~ignition_toolkit.udt.models.UdtDefinition`.

See ``docs/plans/udt-composer-design.md`` for the fixed API contract this
module implements. Where the composer is the wizard's guided-generic-UDT
counterpart to ``udt/builder.py``'s device-class templates: the frontend
edits a :class:`Composition` (this module's Pydantic models — snake_case,
UI-friendly, no Ignition wire-format quirks), :func:`compose` turns it into a
:class:`~ignition_toolkit.udt.models.UdtDefinition` by applying every
convention server-side (naming style, ISA-18.2 alarm priority defaults) —
the frontend never re-implements convention logic.

Contract notes resolved here (not spelled out verbatim in the design doc):

- ``value_source: "expression"`` (the composition's UI-friendly name) is
  translated to Ignition's real wire-format ``valueSource: "expr"`` when
  building the :class:`~ignition_toolkit.udt.models.TagElement` — real
  Ignition tag exports use ``"expr"``, never ``"expression"``.
- ``CompositionAlarm.setpoint`` (singular, matching the design doc's example)
  maps onto :class:`~ignition_toolkit.udt.models.AlarmConfig`'s
  ``setpointA`` — the composition wire format never exposes ``setpointB``
  (two-setpoint/deviation alarm modes aren't part of this guided flow yet).
  ``CompositionAlarm`` also carries an optional ``deadband`` (not shown in
  the design doc's illustrative JSON snippet, but required by the
  conventions this feature exists to enforce — rule 5, "deadbands are
  mandatory on any alarm defined against an analog member") which maps
  straight onto ``AlarmConfig.deadband``.
- ``CompositionHistory.tag_group`` maps onto ``historyProvider`` (the only
  single free-text history field ``models.TagElement`` has); ``sampleMode``
  is filled in as ``"OnChange"`` whenever history is enabled, matching
  ``builder.py``'s template convention. ``deadband_style: "Auto"`` fills
  ``historicalDeadband`` with ``0`` (Ignition auto-manages the deadband, so
  there's no manual number to carry — ``0`` still satisfies
  ``conventions.history_config_complete``'s "was a value set at all" check);
  any other ``deadband_style`` string that parses as a number is used
  directly as ``historicalDeadband``, otherwise it is recorded verbatim as an
  extra ``historicalDeadbandStyle`` field (passed through by
  ``TagElement``'s ``extra="allow"``) and no numeric deadband is invented —
  a lint finding ("incomplete history config") will surface that gap rather
  than the composer silently guessing a number.
- Structural validation (this module) is deliberately narrower than
  ``conventions.find_convention_issues`` (used by ``builder.py``'s
  self-check): it only rejects a composition that literally cannot become a
  valid tag tree (bad type name, unknown/invalid parameter reference, sibling
  name collisions, unknown data type, alarm on a folder, expression/memory
  members missing their payload, unknown naming style). Everything else
  (missing docs, hardcoded OPC paths, non-ISA alarm priorities, ...) is a
  *lint* concern (``audit/rules/udt/``) — per the design doc, "a lint-dirty
  UDT still composes".
"""

import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from ignition_toolkit.udt.conventions import (
    NAMING_STYLES,
    STANDARD_ALARM_DEFAULTS,
    apply_naming_style,
    is_valid_type_name,
)
from ignition_toolkit.udt.models import UdtDefinition

logger = logging.getLogger(__name__)

# Mirrors ignition_toolkit.udt.models._PARAM_REF_RE ({Param} reference
# syntax) and the semantics of models.find_parameter_references — duplicated
# here (rather than imported) because that regex is a private module-level
# constant of models.py, and this module needs per-field, per-member
# location context that the whole-subtree find_parameter_references helper
# doesn't provide.
_PARAM_REF_RE = re.compile(r"\{(\w+)\}")

# Ignition tag data types actually seen in this codebase's templates/fixtures
# (models.py conventions.ANALOG_DATA_TYPES) plus the rest of the documented
# Ignition 8.x tag data type enum. Kept local to composer.py: this is the
# only place a UDT composition's member ``data_type`` is validated against a
# closed set (builder.py's templates are hand-authored and trusted; a
# composition comes from a user-facing wizard and needs this guard).
KNOWN_DATA_TYPES: frozenset[str] = frozenset(
    {
        "Boolean",
        "Short",
        "Integer",
        "Long",
        "Float4",
        "Float8",
        "String",
        "DateTime",
        "Text",
        "Document",
        "ByteArray",
    }
)

# Composition value_source -> Ignition wire-format valueSource.
_VALUE_SOURCE_TO_WIRE: dict[str, str] = {
    "opc": "opc",
    "memory": "memory",
    "expression": "expr",
}


class UdtComposerError(ValueError):
    """Raised when a composition is structurally invalid (see module docstring)."""


# ============================================================================
# Composition wire-format models
# ============================================================================


class CompositionParameter(BaseModel):
    """One entry in a composition's ``parameters`` list.

    Becomes one key of the emitted UDT's ``parameters`` dict. Parameter
    *names* are never restyled by ``compose()`` — see the module docstring
    of ``conventions.py``: parameter names follow the existing ratified
    rules there, independent of the member ``naming_style`` choice.
    """

    name: str
    data_type: str
    default_value: Any = None
    description: str | None = None


class CompositionAlarm(BaseModel):
    """One entry in a tag member's ``alarms`` list.

    ``priority: None`` means "apply the ISA-18.2 default for this alarm name"
    (``conventions.STANDARD_ALARM_DEFAULTS``); an explicit value overrides.
    Alarm *names* are never restyled — they stay bare/standard (``HiHi``,
    ...) regardless of the composition's ``naming_style``. ``deadband`` is
    mandatory (by convention) on any alarm against an analog member — see
    ``conventions.alarm_deadband_required`` — but is not itself
    structurally validated here; an analog alarm with no deadband still
    composes, surfaced instead as an ``udt-missing-alarm-deadband`` lint
    finding.
    """

    name: str
    setpoint: Any = None
    deadband: Any = None
    mode: str | None = None
    priority: str | None = None


class CompositionHistory(BaseModel):
    """History configuration block on a tag member. See module docstring for field mapping."""

    enabled: bool
    tag_group: str | None = None
    deadband_style: str | None = None


class CompositionMember(BaseModel):
    """
    One node in a composition's member tree: a folder or a tag.

    ``kind="folder"`` members nest further members via ``members``; every
    other field is a tag-only concern (ignored for folders — the folder/tag
    split lives in one model, not a discriminated union, to keep the
    recursive ``members`` list simple to build in the wizard UI).
    """

    kind: Literal["folder", "tag"]
    name: str
    documentation: str | None = None
    tooltip: str | None = None

    # Tag-only fields.
    value_source: Literal["opc", "memory", "expression"] | None = None
    data_type: str | None = None
    opc_item_path: str | None = None
    opc_server: str | None = None
    expression: str | None = None
    value: Any = None
    eng_unit: str | None = None
    eng_low: float | None = None
    eng_high: float | None = None
    history: CompositionHistory | None = None
    alarms: list[CompositionAlarm] = Field(default_factory=list)

    # Folder-only field.
    members: list["CompositionMember"] = Field(default_factory=list)


CompositionMember.model_rebuild()


class Composition(BaseModel):
    """Root of a UDT composition — the wizard's wire format, see the module docstring."""

    type_name: str
    description: str | None = None
    naming_style: str = "camelCase"
    parameters: list[CompositionParameter] = Field(default_factory=list)
    members: list[CompositionMember] = Field(default_factory=list)


# ============================================================================
# compose()
# ============================================================================


def _param_refs(text: str | None) -> set[str]:
    """Extract every ``{ParamName}`` reference in ``text`` (see module-level regex note)."""
    if not text:
        return set()
    return set(_PARAM_REF_RE.findall(text))


def _build_alarm(alarm: CompositionAlarm) -> dict[str, Any]:
    """Build one wire-format alarm dict, filling in the ISA-18.2 default priority/mode."""
    defaults = STANDARD_ALARM_DEFAULTS.get(alarm.name)
    priority = alarm.priority if alarm.priority is not None else (defaults or {}).get("priority")
    mode = alarm.mode if alarm.mode is not None else (defaults or {}).get("mode")

    node: dict[str, Any] = {"name": alarm.name, "enabled": True}
    if mode is not None:
        node["mode"] = mode
    if priority is not None:
        node["priority"] = priority
    if alarm.setpoint is not None:
        node["setpointA"] = alarm.setpoint
    if alarm.deadband is not None:
        node["deadband"] = alarm.deadband
    return node


def _build_history(history: CompositionHistory) -> dict[str, Any]:
    """Build the history-related wire-format fields for one tag member. See module docstring."""
    node: dict[str, Any] = {"historyEnabled": history.enabled}
    if not history.enabled:
        return node

    if history.tag_group:
        node["historyProvider"] = history.tag_group
    node["sampleMode"] = "OnChange"

    if history.deadband_style:
        node["historicalDeadbandStyle"] = history.deadband_style
        if history.deadband_style == "Auto":
            node["historicalDeadband"] = 0
        else:
            try:
                node["historicalDeadband"] = float(history.deadband_style)
            except (TypeError, ValueError):
                # Not "Auto" and not a bare number — record the style verbatim
                # (above) but don't invent a deadband value; the "incomplete
                # history config" lint rule will flag the gap for analog tags.
                pass
    return node


def _build_members(
    members: list[CompositionMember],
    style: str,
    declared_params: set[str],
    path: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Recursively build wire-format tag dicts for ``members``, collecting every
    structural-validation problem found (rather than raising on the first
    one) so :func:`compose` can report them all together.
    """
    errors: list[str] = []
    result: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    for member in members:
        styled_name = (
            apply_naming_style(member.name, style) if style in NAMING_STYLES else member.name
        )
        current_path = f"{path}/{styled_name}" if path else styled_name

        if styled_name in seen_names:
            location = path or "<root>"
            errors.append(f"duplicate sibling member name '{styled_name}' under '{location}'")
        seen_names.add(styled_name)

        if member.kind == "folder":
            if member.alarms:
                errors.append(f"{current_path}: a folder cannot have alarms")
            child_tags, child_errors = _build_members(
                member.members, style, declared_params, current_path
            )
            errors.extend(child_errors)
            node: dict[str, Any] = {"name": styled_name, "tagType": "Folder"}
            if member.documentation:
                node["documentation"] = member.documentation
            if member.tooltip:
                node["tooltip"] = member.tooltip
            node["tags"] = child_tags
            result.append(node)
            continue

        # kind == "tag"
        node = {"name": styled_name, "tagType": "AtomicTag"}

        if member.data_type is None or member.data_type not in KNOWN_DATA_TYPES:
            errors.append(f"{current_path}: unknown data type '{member.data_type}'")
        else:
            node["dataType"] = member.data_type

        value_source = member.value_source
        if value_source is None:
            errors.append(f"{current_path}: tag member has no value_source")
        else:
            node["valueSource"] = _VALUE_SOURCE_TO_WIRE[value_source]
            if value_source == "opc":
                node["opcServer"] = member.opc_server
                node["opcItemPath"] = member.opc_item_path
                for ref in _param_refs(member.opc_item_path):
                    if ref not in declared_params:
                        errors.append(
                            f"{current_path}: unknown parameter reference '{{{ref}}}' "
                            "in opc_item_path"
                        )
            elif value_source == "memory":
                if member.value is None:
                    errors.append(f"{current_path}: memory member missing value")
                else:
                    node["value"] = member.value
            elif value_source == "expression":
                if not member.expression:
                    errors.append(f"{current_path}: expression member missing expression")
                else:
                    node["expression"] = member.expression
                    for ref in _param_refs(member.expression):
                        if ref not in declared_params:
                            errors.append(
                                f"{current_path}: unknown parameter reference '{{{ref}}}' "
                                "in expression"
                            )

        if member.documentation:
            node["documentation"] = member.documentation
        if member.tooltip:
            node["tooltip"] = member.tooltip
        if member.eng_unit:
            node["engUnit"] = member.eng_unit
        if member.eng_low is not None:
            node["engLow"] = member.eng_low
        if member.eng_high is not None:
            node["engHigh"] = member.eng_high

        if member.history is not None:
            node.update(_build_history(member.history))

        if member.alarms:
            node["alarms"] = [_build_alarm(alarm) for alarm in member.alarms]

        result.append(node)

    return result, errors


def compose(composition: Composition) -> UdtDefinition:
    """
    Convert a wizard :class:`Composition` into a convention-conforming
    :class:`~ignition_toolkit.udt.models.UdtDefinition`.

    Applies the member/folder naming style, fills ISA-18.2 default alarm
    priorities, and builds the tag tree. UDT type name and parameter names
    are never restyled (see the module docstring).

    Raises:
        UdtComposerError: with every structural problem found joined into
            one ``"; "``-separated message (same style as
            ``builder.UdtBuilderError``) — invalid type name, invalid/unknown
            parameter reference, duplicate sibling member names (after
            naming-style application), unknown data type, alarm on a folder,
            expression member without ``expression``, memory member without
            ``value``, or unknown ``naming_style``.
    """
    errors: list[str] = []

    style = composition.naming_style
    if style not in NAMING_STYLES:
        errors.append(f"unknown naming_style '{style}'; expected one of {', '.join(NAMING_STYLES)}")
        style = "camelCase"  # fallback so the rest of composing can still be checked

    if not is_valid_type_name(composition.type_name):
        errors.append(f"UDT type name '{composition.type_name}' is not valid PascalCase")

    declared_params = {p.name for p in composition.parameters}
    tags, member_errors = _build_members(composition.members, style, declared_params, path="")
    errors.extend(member_errors)

    if errors:
        raise UdtComposerError("Invalid composition: " + "; ".join(errors))

    udt_data: dict[str, Any] = {"name": composition.type_name, "tagType": "UdtType"}
    if composition.description:
        udt_data["documentation"] = composition.description
    if composition.parameters:
        udt_data["parameters"] = {
            p.name: {"dataType": p.data_type, "value": p.default_value}
            for p in composition.parameters
        }
    udt_data["tags"] = tags

    return UdtDefinition.model_validate(udt_data)


# ============================================================================
# UdtDefinition -> Composition (used to derive the /api/udt/presets response
# from builder.py's existing device-class templates — see module docstring
# and the GET /api/udt/presets contract in docs/plans/udt-composer-design.md)
# ============================================================================

# Reverse of _VALUE_SOURCE_TO_WIRE.
_WIRE_TO_VALUE_SOURCE: dict[str, str] = {v: k for k, v in _VALUE_SOURCE_TO_WIRE.items()}


def _tag_element_to_member(element: Any) -> CompositionMember:
    """Convert one built ``TagElement`` (folder or atomic tag) into a ``CompositionMember``."""
    if element.tag_type == "Folder":
        return CompositionMember(
            kind="folder",
            name=element.name,
            documentation=element.documentation,
            tooltip=element.tooltip,
            members=[_tag_element_to_member(child) for child in element.tags or []],
        )

    value_source = _WIRE_TO_VALUE_SOURCE.get(element.value_source or "")
    kwargs: dict[str, Any] = {
        "kind": "tag",
        "name": element.name,
        "documentation": element.documentation,
        "tooltip": element.tooltip,
        "value_source": value_source,
        "data_type": element.data_type,
        "eng_unit": element.eng_unit,
        "eng_low": element.eng_low,
        "eng_high": element.eng_high,
    }
    if value_source == "opc":
        kwargs["opc_item_path"] = element.opc_item_path
        kwargs["opc_server"] = element.opc_server
    elif value_source == "memory":
        kwargs["value"] = element.value
    elif value_source == "expression":
        kwargs["expression"] = (element.model_extra or {}).get("expression")

    if element.history_enabled is not None:
        deadband_style = None
        if element.historical_deadband is not None:
            deadband_style = (
                "Auto" if element.historical_deadband == 0 else str(element.historical_deadband)
            )
        kwargs["history"] = CompositionHistory(
            enabled=bool(element.history_enabled),
            tag_group=element.history_provider,
            deadband_style=deadband_style,
        )

    kwargs["alarms"] = [
        CompositionAlarm(
            name=alarm.name,
            setpoint=alarm.setpoint_a,
            deadband=alarm.deadband,
            mode=alarm.mode,
            priority=alarm.priority,
        )
        for alarm in element.alarms or []
    ]

    return CompositionMember(**kwargs)


def udt_to_composition(udt: UdtDefinition, naming_style: str = "camelCase") -> Composition:
    """
    Convert an already-built :class:`~ignition_toolkit.udt.models.UdtDefinition`
    back into a :class:`Composition` — the inverse of :func:`compose`, used
    only to derive ``GET /api/udt/presets`` entries from the existing
    ``builder.py`` device-class templates (so a preset's composition is
    mechanically kept in sync with its template rather than hand-duplicated
    JSON that could drift). Not part of the fixed wire-format contract in the
    design doc; not called for anything the frontend submits.

    History reconstruction is a best-effort approximation (``deadband_style``
    is inferred, not read back verbatim, since ``TagElement`` doesn't record
    it) — this is acceptable because the preset-parity test only asserts
    member names/nesting, alarms, and parameters, not history fields.
    """
    parameters = [
        CompositionParameter(
            name=name,
            data_type=param.data_type or "String",
            default_value=param.value,
        )
        for name, param in (udt.parameters or {}).items()
    ]
    members = [_tag_element_to_member(child) for child in udt.tags or []]
    return Composition(
        type_name=udt.name,
        description=udt.documentation,
        naming_style=naming_style,
        parameters=parameters,
        members=members,
    )
