"""Documentation-convention rule — wraps ``conventions.check_documentation``."""

import logging
from typing import Any

from ignition_toolkit.audit.engine import Finding, Rule, Severity
from ignition_toolkit.audit.rules.udt._walk import walk_members
from ignition_toolkit.udt.conventions import check_documentation
from ignition_toolkit.udt.models import UdtDefinition

logger = logging.getLogger(__name__)


class UdtMissingDocumentationRule(Rule):
    """Flags a member/folder with no (or blank) ``documentation``."""

    rule_id = "udt-missing-documentation"
    severity = Severity.MEDIUM
    description = "Member or folder has no documentation."

    def evaluate(self, target: Any) -> list[Finding]:
        udt: UdtDefinition = target
        findings: list[Finding] = []
        for element, path in walk_members(udt):
            for issue in check_documentation(element, path):
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        location=path,
                        message=issue,
                        recommendation=(
                            f"Add a short description of what '{element.name}' at {path} "
                            "represents to its documentation field, so the next person "
                            "browsing this UDT in the Designer understands it without "
                            "reading upstream PLC logic."
                        ),
                    )
                )
        return findings
