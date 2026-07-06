"""
UDT Builder — data models for Ignition tag-export JSON.

Phase 1 of the UDT Builder (see ``docs/plans/udt-builder-design.md``): a
lossless Pydantic representation of UDT type/instance tag exports, so later
phases (templates, builder, linter, API) can generate and inspect UDT JSON
without hand-rolling dict manipulation.

Templates, ``builder.py``, ``conventions.py``, and the linter are explicitly
out of scope for this phase — see the design doc before adding to this
package.
"""

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
    "TagElement",
    "UdtDefinition",
    "find_parameter_references",
    "parse_tag_export",
    "to_tag_export",
]
