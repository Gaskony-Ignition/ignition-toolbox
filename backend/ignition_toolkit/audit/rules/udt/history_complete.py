"""Complete-history-config rule — wraps ``conventions.check_history_completeness``."""

import logging
from typing import Any

from ignition_toolkit.audit.engine import Finding, Rule, Severity
from ignition_toolkit.audit.rules.udt._walk import walk_members
from ignition_toolkit.udt.conventions import check_history_completeness
from ignition_toolkit.udt.models import UdtDefinition

logger = logging.getLogger(__name__)


class UdtIncompleteHistoryConfigRule(Rule):
    """Flags a history-enabled tag missing its provider (or, for analogs, its deadband)."""

    rule_id = "udt-incomplete-history-config"
    severity = Severity.MEDIUM
    description = "History is enabled but historyProvider/historicalDeadband is incomplete."

    def evaluate(self, target: Any) -> list[Finding]:
        udt: UdtDefinition = target
        findings: list[Finding] = []
        for element, path in walk_members(udt):
            for issue in check_history_completeness(element, path):
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        location=path,
                        message=issue,
                        recommendation=(
                            f"Finish the history configuration on '{element.name}' at {path}: "
                            "set a historyProvider, and (for analog members) a positive "
                            "historicalDeadband, or the tag will silently fail to record."
                        ),
                    )
                )
        return findings
