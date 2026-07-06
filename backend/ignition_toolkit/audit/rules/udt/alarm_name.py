"""Alarm-name-convention rule — wraps ``conventions.check_alarm_names``."""

import logging
from typing import Any

from ignition_toolkit.audit.engine import Finding, Rule, Severity
from ignition_toolkit.audit.rules.udt._walk import walk_members
from ignition_toolkit.udt.conventions import STANDARD_ALARM_NAMES, check_alarm_names
from ignition_toolkit.udt.models import UdtDefinition

logger = logging.getLogger(__name__)


class UdtNonStandardAlarmNameRule(Rule):
    """Flags an alarm whose name isn't one of the standardised set (HiHi/Hi/Lo/LoLo/...)."""

    rule_id = "udt-nonstandard-alarm-name"
    severity = Severity.MEDIUM
    description = "Alarm name is not one of the standardised alarm names."

    def evaluate(self, target: Any) -> list[Finding]:
        udt: UdtDefinition = target
        findings: list[Finding] = []
        for element, path in walk_members(udt):
            for issue in check_alarm_names(element, path):
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        location=path,
                        message=issue,
                        recommendation=(
                            f"Rename the alarm on '{element.name}' at {path} to one of the "
                            f"standardised names ({', '.join(STANDARD_ALARM_NAMES)}) so alarm "
                            "summaries and journals are consistent across every UDT in the "
                            "project."
                        ),
                    )
                )
        return findings
