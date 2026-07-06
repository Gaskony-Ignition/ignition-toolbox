"""
Shared tree-walk helper for the UDT lint rule pack.

Builds ``location`` strings as a slash-joined member path (folder/tag names
only — the UDT type name itself is never part of the path), matching the
example in ``docs/plans/udt-composer-design.md`` (``"location": "status/speed"``).
This is deliberately different from ``conventions.find_convention_issues``'s
own path-building (which prefixes every path with the UDT type name) since
that function serves a different caller (``builder.py``'s self-check
messages) than the lint pack's ``Finding.location``.
"""

from collections.abc import Iterator

from ignition_toolkit.udt.models import TagElement, UdtDefinition


def walk_members(udt: UdtDefinition) -> Iterator[tuple[TagElement, str]]:
    """Yield every member node (any depth) under ``udt`` with its slash-joined path."""
    yield from _walk(udt.tags or [], "")


def _walk(elements: list[TagElement], prefix: str) -> Iterator[tuple[TagElement, str]]:
    for element in elements:
        path = f"{prefix}/{element.name}" if prefix else (element.name or "")
        yield element, path
        if element.tags:
            yield from _walk(element.tags, path)
