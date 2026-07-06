"""
UDT data models — Pydantic models mirroring Ignition tag-export JSON.

Ignition 8.x exports tags (including User-Defined Types) as JSON. A UDT type
definition is a tag node with ``"tagType": "UdtType"``; it carries a
``parameters`` dict (instance inputs referenced as ``{ParamName}`` inside
member properties) and a ``tags`` array of member nodes. Members may be:

- atomic tags (OPC / memory / expression / derived / query — distinguished by
  ``valueSource``, not by a separate Python class here, see below)
- folders (``"tagType": "Folder"``) containing a nested ``tags`` array
- nested UDT instances (``"tagType": "UdtInstance"``) referencing a parent
  type via ``typeId``
- a UDT type definition can itself inherit from another type via ``typeId``

Because the exact set of optional/undocumented properties Ignition emits
varies by version, edit history, and tag type, the design favours **losslessness
over exhaustive typing**: a single recursive :class:`TagElement` model with
``extra="allow"`` represents every node in the tree (tag, folder, UDT type, or
UDT instance), and :func:`parse_tag_export` / :func:`to_tag_export` round-trip
via ``model_dump(exclude_unset=True, by_alias=True)`` so fields never present
in the input are never invented on output.

.. note::
   **Known limitation (accepted):** ``populate_by_name=True`` lets Python
   callers construct models with snake_case kwargs, but it also means an
   *input file* using a snake_case twin of a modelled key (``"tag_type"``
   instead of ``"tagType"``) has that key consumed and re-emitted as
   camelCase — a round-trip rename. Genuine Ignition exports are always
   camelCase, so this only affects hand-edited files. Pinned by a test in
   ``test_models.py``.

.. important::
   **Synthetic fixtures.** The reference project (real Designer-exported UDTs)
   is not yet on this machine — see
   ``docs/plans/udt-builder-design.md`` prerequisite note. All fixtures under
   ``backend/tests/test_udt/fixtures/`` are hand-authored to match the
   documented/observed shape of Ignition 8.x tag-export JSON as closely as
   possible, but MUST be re-validated once Nigel imports real exports into
   ``docs/reference/udt-examples/`` (Phase 2 prerequisite). Treat every
   concrete field name/shape below as "best effort, pending confirmation".
"""

import logging
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

# Matches Ignition parameter references like "{DevicePath}" inside strings
# such as opcItemPath ("{DevicePath}/Speed") or alarm setpoints
# ("{HighSpeedSetpoint}"). Kept intentionally simple (word chars only) —
# real exports may use a broader charset that we haven't seen yet.
_PARAM_REF_RE = re.compile(r"\{(\w+)\}")


class ParameterDefinition(BaseModel):
    """
    One entry in a UDT's ``parameters`` dict.

    Ignition parameter entries are typically ``{"dataType": "String", "value":
    ...}`` but may carry additional undocumented keys — those are preserved
    via ``extra="allow"``.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    data_type: str | None = Field(default=None, alias="dataType")
    value: Any = None


class AlarmConfig(BaseModel):
    """
    One entry in a member tag's ``alarms`` array.

    Only the commonly-documented alarm properties are modelled explicitly;
    everything else (ack pipelines, labels, associated data, custom
    properties, etc.) passes through untouched via ``extra="allow"``.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    name: str | None = None
    mode: str | None = None
    priority: str | None = None
    # Setpoints are frequently parameter references ("{HighSpeedSetpoint}")
    # rather than bare numbers, so they're kept as Any rather than float.
    setpoint_a: Any = Field(default=None, alias="setpointA")
    setpoint_b: Any = Field(default=None, alias="setpointB")
    deadband: Any = None
    enabled: bool | None = None


class TagElement(BaseModel):
    """
    A single node in an Ignition tag tree: an atomic tag, a folder, a UDT
    type definition, or a UDT instance.

    One recursive model is used for all of these (rather than a discriminated
    union per tag/valueSource) because the plan for this phase explicitly
    prefers "simple + lossless over exhaustive typing" — the properties that
    distinguish a member's role (``tagType``, ``valueSource``, ``typeId``,
    presence/absence of ``tags``) are all present as plain optional fields.

    Ignition's wire format uses camelCase keys (``opcItemPath``, ``tagType``,
    ...). Python/ruff (pep8-naming) require snake_case attributes, so each
    camelCase key is mapped via ``Field(alias=...)`` with
    ``populate_by_name=True`` — ``parse_tag_export``/``to_tag_export`` read
    and write the original camelCase keys (via ``by_alias=True`` on dump)
    while the rest of this codebase can use normal snake_case attributes
    (``element.tag_type``, ``element.opc_item_path``, ...). Unknown keys are
    never touched by this mapping — they pass through verbatim via
    ``extra="allow"``.

    Only fields that were actually present in the source JSON are re-emitted
    on ``to_tag_export`` (via ``model_dump(exclude_unset=True)``); unset
    optional fields never appear in the output, so a member that omits
    ``readOnly`` in the input will still omit it in the output rather than
    gaining an explicit ``false``.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    # Identity / structure
    name: str | None = None
    tag_type: str | None = Field(
        default=None, alias="tagType"
    )  # "AtomicTag" | "Folder" | "UdtType" | "UdtInstance" | ...
    value_source: str | None = Field(
        default=None, alias="valueSource"
    )  # "opc" | "memory" | "expr" | "derived" | "query" | ...
    type_id: str | None = Field(
        default=None, alias="typeId"
    )  # parent UDT type name (on a UdtType def or a UdtInstance)

    # Value / data type
    data_type: str | None = Field(default=None, alias="dataType")
    value: Any = None

    # OPC binding
    opc_server: str | None = Field(default=None, alias="opcServer")
    opc_item_path: str | None = Field(default=None, alias="opcItemPath")

    # Engineering / scaling
    eng_unit: str | None = Field(default=None, alias="engUnit")
    eng_low: Any = Field(default=None, alias="engLow")
    eng_high: Any = Field(default=None, alias="engHigh")
    scale_mode: str | None = Field(default=None, alias="scaleMode")
    deadband: Any = None

    # Documentation / behaviour
    documentation: str | None = None
    tooltip: str | None = None
    read_only: bool | None = Field(default=None, alias="readOnly")

    # History
    history_enabled: bool | None = Field(default=None, alias="historyEnabled")
    history_provider: str | None = Field(default=None, alias="historyProvider")
    historical_deadband: Any = Field(default=None, alias="historicalDeadband")
    sample_mode: str | None = Field(default=None, alias="sampleMode")

    # UDT-specific
    parameters: dict[str, ParameterDefinition] | None = None
    tags: list["TagElement"] | None = None

    # Alarming
    alarms: list[AlarmConfig] | None = None


TagElement.model_rebuild()


class UdtDefinition(TagElement):
    """
    Root of a parsed UDT tag-export document.

    This is a :class:`TagElement` with no additional fields — the
    distinction exists purely so callers get a semantically clear return
    type from :func:`parse_tag_export`. Ignition UDT type exports normally
    have ``tagType == "UdtType"`` at the root, but this is *not* enforced
    here: the real reference exports aren't available yet to confirm every
    root shape Designer can produce (e.g. exporting a single UDT instance
    rather than a type), so validation stays permissive by design. See the
    module docstring's "Synthetic fixtures" note.
    """


def parse_tag_export(data: dict[str, Any]) -> UdtDefinition:
    """
    Parse an Ignition tag-export JSON document (already loaded from JSON)
    into a :class:`UdtDefinition`.

    Args:
        data: The parsed JSON object (``dict``) as produced by
            ``json.load``/``json.loads`` on a Designer tag export.

    Returns:
        A :class:`UdtDefinition` model preserving every field present in
        ``data``, including unknown/undocumented ones.
    """
    return UdtDefinition.model_validate(data)


def to_tag_export(model: UdtDefinition) -> dict[str, Any]:
    """
    Dump a :class:`UdtDefinition` (or any :class:`TagElement`) back to a
    plain ``dict`` suitable for ``json.dump``.

    Only fields that were explicitly present when the model was parsed (or
    explicitly set afterwards) are included — this is what makes the
    round-trip lossless without polluting the output with every optional
    field's default (``None``). ``by_alias=True`` restores the original
    camelCase Ignition keys (e.g. ``tag_type`` -> ``"tagType"``).

    Args:
        model: The model to serialise.

    Returns:
        A JSON-serialisable ``dict`` semantically identical to the source
        document the model was parsed from (key order may differ).
    """
    return model.model_dump(exclude_unset=True, by_alias=True)


def find_parameter_references(element: TagElement) -> set[str]:
    """
    Recursively collect every ``{ParamName}`` reference used anywhere under
    ``element`` (its own fields, extras, nested members, alarms, etc.).

    This is a lightweight convenience helper, not a full validator: it does
    not check that referenced parameters are actually declared in any
    ``parameters`` dict, nor does it distinguish which member used which
    reference — it just answers "what parameter names does this subtree
    depend on".

    Args:
        element: Any node in the tag tree (typically a :class:`UdtDefinition`
            root, but works for any :class:`TagElement`).

    Returns:
        A set of parameter names (without braces), e.g. ``{"DevicePath",
        "OpcServer"}``.
    """
    refs: set[str] = set()
    _collect_param_refs(element.model_dump(exclude_unset=True, by_alias=True), refs)
    return refs


def _collect_param_refs(value: Any, refs: set[str]) -> None:
    """Walk an arbitrary JSON-like structure collecting {Param} references."""
    if isinstance(value, str):
        refs.update(_PARAM_REF_RE.findall(value))
    elif isinstance(value, dict):
        for item in value.values():
            _collect_param_refs(item, refs)
    elif isinstance(value, list):
        for item in value:
            _collect_param_refs(item, refs)
