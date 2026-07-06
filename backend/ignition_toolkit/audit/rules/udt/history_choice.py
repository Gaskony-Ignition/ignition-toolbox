"""Deliberate-history-choice rule — wraps ``conventions.check_history_choice``."""

import logging
from typing import Any

from ignition_toolkit.audit.engine import Finding, Rule, Severity
from ignition_toolkit.audit.rules.udt._walk import walk_members
from ignition_toolkit.udt.conventions import check_history_choice
from ignition_toolkit.udt.models import UdtDefinition

logger = logging.getLogger(__name__)


class UdtNoDeliberateHistoryChoiceRule(Rule):
    """Flags an atomic tag that never explicitly set ``historyEnabled``."""

    rule_id = "udt-no-deliberate-history-choice"
    severity = Severity.MEDIUM
    description = "Member never made an explicit historyEnabled choice."

    def evaluate(self, target: Any) -> list[Finding]:
        udt: UdtDefinition = target
        findings: list[Finding] = []
        for element, path in walk_members(udt):
            for issue in check_history_choice(element, path):
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        location=path,
                        message=issue,
                        recommendation=(
                            f"Explicitly set historyEnabled (true or false) on '{element.name}' "
                            f"at {path} — an unset choice usually means someone forgot to "
                            "decide, rather than a deliberate opt-out."
                        ),
                    )
                )
        return findings
