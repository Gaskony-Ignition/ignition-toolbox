"""Engineering-unit-convention rule — wraps ``conventions.check_eng_unit``."""

import logging
from typing import Any

from ignition_toolkit.audit.engine import Finding, Rule, Severity
from ignition_toolkit.audit.rules.udt._walk import walk_members
from ignition_toolkit.udt.conventions import check_eng_unit
from ignition_toolkit.udt.models import UdtDefinition

logger = logging.getLogger(__name__)


class UdtMissingEngUnitRule(Rule):
    """Flags an analog (Float4/Float8) member with no declared ``engUnit``."""

    rule_id = "udt-missing-eng-unit"
    severity = Severity.MEDIUM
    description = "Analog member has no engineering unit."

    def evaluate(self, target: Any) -> list[Finding]:
        udt: UdtDefinition = target
        findings: list[Finding] = []
        for element, path in walk_members(udt):
            for issue in check_eng_unit(element, path):
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        location=path,
                        message=issue,
                        recommendation=(
                            f"Set an engineering unit (e.g. 'RPM', 'kPa', 'degC') on "
                            f"'{element.name}' at {path} so operators and downstream "
                            "displays know how to interpret the value."
                        ),
                    )
                )
        return findings
