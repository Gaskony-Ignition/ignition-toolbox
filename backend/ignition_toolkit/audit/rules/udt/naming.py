"""Naming-convention rule — wraps ``conventions.check_naming``."""

import logging
from typing import Any

from ignition_toolkit.audit.engine import Finding, Rule, Severity
from ignition_toolkit.audit.rules.udt._walk import walk_members
from ignition_toolkit.udt.conventions import check_naming
from ignition_toolkit.udt.models import UdtDefinition

logger = logging.getLogger(__name__)


class UdtNamingViolationRule(Rule):
    """Flags a member/folder name that is neither valid camelCase nor PascalCase."""

    rule_id = "udt-naming-violation"
    severity = Severity.MEDIUM
    description = (
        "Member or folder name is not valid camelCase/PascalCase, or is a Designer default."
    )

    def evaluate(self, target: Any) -> list[Finding]:
        udt: UdtDefinition = target
        findings: list[Finding] = []
        for element, path in walk_members(udt):
            for issue in check_naming(element, path):
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        location=path,
                        message=issue,
                        recommendation=(
                            f"Rename '{element.name}' at {path} to a single, consistent "
                            "camelCase or PascalCase spelling with no spaces or underscores, "
                            "matching this UDT's chosen member naming style."
                        ),
                    )
                )
        return findings
