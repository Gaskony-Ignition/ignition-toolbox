"""
UDT Builder — data models, conventions, templates, and builder for Ignition
User-Defined Types.

Phase 1 (see ``docs/plans/udt-builder-design.md``) built a lossless Pydantic
representation of UDT type/instance tag exports (``models.py``). Phase 2
adds the machine-checkable convention rules (``conventions.py``), the
device-class templates under ``templates/*.json``, and the questionnaire ->
UDT builder (``builder.py``). The linter (scoring arbitrary/real UDT exports
against ``conventions.py``) and the API/frontend are still out of scope —
see the design doc.
"""

from ignition_toolkit.udt.builder import (
    QuestionnaireField,
    TemplateMeta,
    UdtBuilderError,
    build,
    list_templates,
)
from ignition_toolkit.udt.conventions import find_convention_issues
from ignition_toolkit.udt.models import (
    AlarmConfig,
    ParameterDefinition,
    TagElement,
    UdtDefinition,
    find_parameter_references,
    parse_tag_export,
    to_tag_export,
)

__all__ = [
    "AlarmConfig",
    "ParameterDefinition",
    "QuestionnaireField",
    "TagElement",
    "TemplateMeta",
    "UdtBuilderError",
    "UdtDefinition",
    "build",
    "find_convention_issues",
    "find_parameter_references",
    "list_templates",
    "parse_tag_export",
    "to_tag_export",
]
