"""
Perspective / UDT project audit: static analysis that produces a
customer-facing report of recommendations (consistency, layout, quality,
best practice).

See ``docs/plans/perspective-project-audit.md`` for the full design. This
package currently implements Phase 1 (project loader + inventory,
:mod:`ignition_toolkit.audit.project`) and Phase 2 (generic rule engine +
seed Perspective rules, :mod:`ignition_toolkit.audit.engine` and
:mod:`ignition_toolkit.audit.rules.perspective`). Report rendering and the
API endpoint are later phases.
"""
