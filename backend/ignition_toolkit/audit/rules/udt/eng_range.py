"""
Engineering-range-convention rule — wraps ``conventions.check_eng_range``.

Deliberately not part of ``conventions.find_convention_issues`` (see that
function's neighbouring ``check_eng_range`` docstring) — this rule is the
only place it runs, so the pre-existing ``valve`` template's
``config/travelTimeSetpoint`` memory tag (analog, no declared range) is
free to keep passing ``builder.py``'s own self-check while still being
surfaced here as a lint finding.
"""

import logging
from typing import Any

from ignition_toolkit.audit.engine import Finding, Rule, Severity
from ignition_toolkit.audit.rules.udt._walk import walk_members
from ignition_toolkit.udt.conventions import check_eng_range
from ignition_toolkit.udt.models import UdtDefinition

logger = logging.getLogger(__name__)


class UdtMissingEngRangeRule(Rule):
    """Flags an analog (Float4/Float8) member with no declared ``engLow``/``engHigh``."""

    rule_id = "udt-missing-eng-range"
    severity = Severity.MEDIUM
    description = "Analog member has no engineering range (engLow/engHigh)."

    def evaluate(self, target: Any) -> list[Finding]:
        udt: UdtDefinition = target
        findings: list[Finding] = []
        for element, path in walk_members(udt):
            for issue in check_eng_range(element, path):
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        location=path,
                        message=issue,
                        recommendation=(
                            f"Set an engineering range (engLow/engHigh) on '{element.name}' "
                            f"at {path} so scaled displays, trends, and alarm setpoint pickers "
                            "have a sensible bound to work against."
                        ),
                    )
                )
        return findings
