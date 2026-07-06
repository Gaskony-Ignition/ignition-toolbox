"""Alarm-priority-convention rule — wraps ``conventions.check_alarm_priorities``."""

import logging
from typing import Any

from ignition_toolkit.audit.engine import Finding, Rule, Severity
from ignition_toolkit.audit.rules.udt._walk import walk_members
from ignition_toolkit.udt.conventions import ALARM_PRIORITIES, check_alarm_priorities
from ignition_toolkit.udt.models import UdtDefinition

logger = logging.getLogger(__name__)


class UdtInvalidAlarmPriorityRule(Rule):
    """Flags an alarm whose priority isn't one of Ignition's five ISA-18.2-mapped levels."""

    rule_id = "udt-invalid-alarm-priority"
    severity = Severity.HIGH
    description = "Alarm priority is missing or not a valid ISA-18.2-mapped level."

    def evaluate(self, target: Any) -> list[Finding]:
        udt: UdtDefinition = target
        findings: list[Finding] = []
        for element, path in walk_members(udt):
            for issue in check_alarm_priorities(element, path):
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        location=path,
                        message=issue,
                        recommendation=(
                            f"Set the alarm priority on '{element.name}' at {path} to one of "
                            f"{', '.join(ALARM_PRIORITIES)}, chosen per the ISA-18.2 "
                            "consequence/response-time guidance — a missing or invalid "
                            "priority leaves the alarm miscategorised in every operator "
                            "alarm-rate/shelving view."
                        ),
                    )
                )
        return findings
