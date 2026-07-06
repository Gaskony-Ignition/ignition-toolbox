"""
UDT builder — turns a questionnaire answer set into a convention-conforming
:class:`~ignition_toolkit.udt.models.UdtDefinition`.

Templates (``templates/*.json``) describe a device class as data: metadata,
a questionnaire schema (mirrors the ``PlaybookParameter`` pattern in
``playbook/models.py`` — name/type/required/default/description, so a future
dynamic form can render it unchanged), and a UDT skeleton to emit.

The skeleton is plain Ignition tag-export JSON (camelCase keys) with a small
set of embedded directives resolved against the answers before the result is
handed to :class:`~ignition_toolkit.udt.models.UdtDefinition` for validation:

- ``{"$ref": "field_name"}`` — replaced with ``answers["field_name"]``,
  preserving its type (float/int/str/bool).
- ``{"$if": "field_name", ...}`` — if ``answers["field_name"]`` is falsy, the
  *entire* directive (and everything inside it) is dropped: from a dict
  member of a ``tags``/alarms list this omits that member/alarm outright;
  from a dict value paired with ``"$then"`` it omits just that key. If
  truthy, resolves to ``$then`` (when present) or to the remaining keys of
  the directive (when not).

Because the resolved structure is fed straight into
:class:`~ignition_toolkit.udt.models.UdtDefinition`'s pydantic validation
(never assembled as a hand-built dict returned directly), the output always
goes through the Phase 1 models and their camelCase aliasing.

Templates author every member/folder ``name`` in one canonical spelling
(camelCase). :func:`build` accepts a ``naming_style`` option
(``"camelCase"`` or ``"PascalCase"``, see
``conventions.NAMING_STYLES``/``DEFAULT_NAMING_STYLE`` — Nigel-decided
2026-07-06 that this is user-selectable) and rewrites every resolved
member/folder name to that style before validation. UDT *type* names,
``parameters`` keys, and alarm names are never touched by this — only the
``name`` field of nodes in the ``tags`` tree.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ignition_toolkit.udt.conventions import (
    DEFAULT_NAMING_STYLE,
    NAMING_STYLES,
    apply_naming_style,
    find_convention_issues,
)
from ignition_toolkit.udt.models import UdtDefinition

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"

# Questionnaire field types -> the Python type(s) an answer must satisfy.
# Mirrors ParameterType in playbook/models.py, restricted to the shapes a
# device-class questionnaire actually needs.
_FIELD_TYPES = frozenset({"string", "integer", "float", "boolean"})

# Sentinel returned by ``_resolve`` for "this key/item should not appear in
# the output at all" (as opposed to ``None``, a legitimate JSON value).
_OMITTED = object()


class UdtBuilderError(ValueError):
    """Raised for an unknown template, invalid answers, or a template bug."""


@dataclass
class QuestionnaireField:
    """One entry in a template's questionnaire schema."""

    name: str
    type: str
    required: bool = False
    default: Any = None
    description: str = ""


@dataclass
class TemplateMeta:
    """Metadata + questionnaire schema for a template, without the UDT skeleton.

    This is what an API layer (Phase 3) should expose to a frontend for
    rendering a dynamic form — it deliberately excludes the ``tags``/
    ``parameters`` skeleton, which is an implementation detail of
    :func:`build`.

    ``naming_styles``/``default_naming_style`` are the same for every
    template (the option is global, not per-device-class) but are exposed
    here so a future form can render the choice alongside a template's own
    questionnaire without a second lookup.
    """

    id: str
    label: str
    description: str
    questionnaire: list[QuestionnaireField] = field(default_factory=list)
    naming_styles: list[str] = field(default_factory=lambda: list(NAMING_STYLES))
    default_naming_style: str = DEFAULT_NAMING_STYLE


def _template_path(template_id: str) -> Path:
    return TEMPLATES_DIR / f"{template_id}.json"


def _load_template(template_id: str) -> dict[str, Any]:
    """Load and JSON-parse a template file by id, raising a clear error if missing/invalid."""
    path = _template_path(template_id)
    if not path.is_file():
        available = ", ".join(sorted(p.stem for p in TEMPLATES_DIR.glob("*.json")))
        raise UdtBuilderError(f"Unknown template '{template_id}'. Available: {available}")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise UdtBuilderError(f"Template '{template_id}' is not valid JSON: {exc}") from exc


def _questionnaire_fields(raw: list[dict[str, Any]]) -> list[QuestionnaireField]:
    return [
        QuestionnaireField(
            name=item["name"],
            type=item["type"],
            required=item.get("required", False),
            default=item.get("default"),
            description=item.get("description", ""),
        )
        for item in raw
    ]


def list_templates() -> list[TemplateMeta]:
    """
    List every available template's metadata + questionnaire schema.

    Returns:
        One :class:`TemplateMeta` per ``templates/*.json`` file, sorted by
        template id. Intended for a future ``/api/udt/templates`` endpoint.
    """
    templates = []
    for path in sorted(TEMPLATES_DIR.glob("*.json")):
        data = _load_template(path.stem)
        templates.append(
            TemplateMeta(
                id=data["id"],
                label=data["label"],
                description=data["description"],
                questionnaire=_questionnaire_fields(data.get("questionnaire", [])),
            )
        )
    return templates


def _coerce_answer(name: str, value: Any, expected_type: str, errors: list[str]) -> Any:
    """Validate/coerce one answer value against its questionnaire field type."""
    if expected_type == "string":
        if not isinstance(value, str):
            errors.append(f"'{name}' must be a string")
        return value
    if expected_type == "boolean":
        if not isinstance(value, bool):
            errors.append(f"'{name}' must be a boolean")
        return value
    if expected_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"'{name}' must be an integer")
        return value
    if expected_type == "float":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(f"'{name}' must be a number")
            return value
        return float(value)
    # Unreachable while templates are only authored with _FIELD_TYPES, but
    # guards against a template typo rather than silently accepting anything.
    errors.append(f"'{name}' declares unknown questionnaire type '{expected_type}'")
    return value


def _validate_answers(fields: list[QuestionnaireField], answers: dict[str, Any]) -> dict[str, Any]:
    """
    Validate ``answers`` against a template's questionnaire schema and fill
    in defaults for anything omitted.

    Raises:
        UdtBuilderError: with every problem found (missing required fields,
            wrong types, unknown field names) joined into one message.
    """
    errors: list[str] = []
    resolved: dict[str, Any] = {}
    known_names = {f.name for f in fields}

    for qf in fields:
        if qf.type not in _FIELD_TYPES:
            errors.append(f"template field '{qf.name}' declares unknown type '{qf.type}'")
            continue
        if qf.name in answers and answers[qf.name] is not None:
            resolved[qf.name] = _coerce_answer(qf.name, answers[qf.name], qf.type, errors)
        elif qf.required:
            errors.append(f"missing required field '{qf.name}'")
        else:
            resolved[qf.name] = qf.default

    unknown = sorted(set(answers) - known_names)
    if unknown:
        errors.append(f"unknown field(s): {', '.join(unknown)}")

    if errors:
        raise UdtBuilderError("Invalid answers: " + "; ".join(errors))

    return resolved


def _apply_naming_style(tags: list[dict[str, Any]], style: str) -> list[dict[str, Any]]:
    """
    Recursively rewrite the ``name`` of every member/folder in a resolved
    ``tags`` list (and any nested folder ``tags`` lists) to ``style``.

    Deliberately shallow about *which* keys it touches: only a node's own
    ``name`` and its nested ``tags`` list are considered. This means a tag's
    ``alarms`` list (whose entries also have a ``name`` key, e.g.
    ``"HiHi"``) is left completely alone — alarm names are not members and
    are never subject to the naming-style option.
    """
    styled: list[dict[str, Any]] = []
    for tag in tags:
        new_tag = dict(tag)
        if "name" in new_tag:
            new_tag["name"] = apply_naming_style(new_tag["name"], style)
        nested = new_tag.get("tags")
        if isinstance(nested, list):
            new_tag["tags"] = _apply_naming_style(nested, style)
        styled.append(new_tag)
    return styled


def _resolve(raw: Any, answers: dict[str, Any]) -> Any:
    """
    Recursively resolve ``$ref``/``$if``/``$then`` directives in a template
    skeleton fragment against ``answers``. See the module docstring for the
    directive semantics. Returns ``_OMITTED`` if ``raw`` itself should be
    dropped from its parent container.
    """
    if isinstance(raw, dict):
        if "$if" in raw:
            if not answers.get(raw["$if"]):
                return _OMITTED
            if "$then" in raw:
                return _resolve(raw["$then"], answers)
            return _resolve({k: v for k, v in raw.items() if k != "$if"}, answers)
        if "$ref" in raw:
            if raw["$ref"] not in answers:
                raise UdtBuilderError(f"template references unknown field '{raw['$ref']}'")
            return answers[raw["$ref"]]
        resolved: dict[str, Any] = {}
        for key, value in raw.items():
            item = _resolve(value, answers)
            if item is not _OMITTED:
                resolved[key] = item
        return resolved
    if isinstance(raw, list):
        resolved_list = []
        for item in raw:
            value = _resolve(item, answers)
            if value is not _OMITTED:
                resolved_list.append(value)
        return resolved_list
    return raw


def build(
    template_id: str,
    answers: dict[str, Any],
    naming_style: str = DEFAULT_NAMING_STYLE,
) -> UdtDefinition:
    """
    Build a convention-conforming UDT type definition from a template + answers.

    Args:
        template_id: A template's ``id`` (matches its filename under
            ``templates/`` without the ``.json`` extension), e.g. ``"motor"``.
        answers: Questionnaire answers keyed by field name. Missing optional
            fields fall back to the template's declared default; missing
            required fields raise :class:`UdtBuilderError`.
        naming_style: One of ``conventions.NAMING_STYLES`` (``"camelCase"``
            or ``"PascalCase"``) — user-selectable member/folder naming
            style (Nigel-decided 2026-07-06). Applied recursively to every
            member/folder ``name`` in the emitted structure; the UDT *type*
            name, ``parameters`` keys, alarm names, and ``{ParamRef}``
            strings are never affected. Defaults to
            ``conventions.DEFAULT_NAMING_STYLE``.

    Returns:
        A :class:`~ignition_toolkit.udt.models.UdtDefinition` ready to be
        dumped via :func:`~ignition_toolkit.udt.models.to_tag_export`.

    Raises:
        UdtBuilderError: unknown template id, invalid/missing answers,
            unknown ``naming_style``, or (a template bug) generated output
            that fails the conventions self-check in
            :func:`~ignition_toolkit.udt.conventions.find_convention_issues`.
    """
    if naming_style not in NAMING_STYLES:
        raise UdtBuilderError(
            f"Unknown naming_style '{naming_style}'. Available: {', '.join(NAMING_STYLES)}"
        )

    template = _load_template(template_id)
    fields = _questionnaire_fields(template.get("questionnaire", []))
    resolved_answers = _validate_answers(fields, answers)

    resolved_parameters = _resolve(template.get("parameters", {}), resolved_answers)
    resolved_tags = _resolve(template.get("tags", []), resolved_answers)
    resolved_tags = _apply_naming_style(resolved_tags, naming_style)

    udt_data: dict[str, Any] = {"name": template["type_name"], "tagType": "UdtType"}
    if resolved_parameters:
        udt_data["parameters"] = resolved_parameters
    udt_data["tags"] = resolved_tags

    udt = UdtDefinition.model_validate(udt_data)

    issues = find_convention_issues(udt)
    if issues:
        # A non-conformant output here is a bug in this template, not bad
        # user input — surface it loudly rather than silently shipping a
        # UDT that violates the standard it exists to enforce.
        raise UdtBuilderError(
            f"Template '{template_id}' produced a UDT that violates conventions: "
            + "; ".join(issues)
        )

    return udt
