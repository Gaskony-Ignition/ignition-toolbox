"""Alarm-deadband-convention rule — wraps ``conventions.check_alarm_deadbands``."""

import logging
from typing import Any

from ignition_toolkit.audit.engine import Finding, Rule, Severity
from ignition_toolkit.audit.rules.udt._walk import walk_members
from ignition_toolkit.udt.conventions import check_alarm_deadbands
from ignition_toolkit.udt.models import UdtDefinition

logger = logging.getLogger(__name__)


class UdtMissingAlarmDeadbandRule(Rule):
    """Flags an analog member's alarm with no positive deadband."""

    rule_id = "udt-missing-alarm-deadband"
    severity = Severity.HIGH
    description = "Analog member's alarm has no positive deadband, risking alarm chatter."

    def evaluate(self, target: Any) -> list[Finding]:
        udt: UdtDefinition = target
        findings: list[Finding] = []
        for element, path in walk_members(udt):
            for issue in check_alarm_deadbands(element, path):
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        location=path,
                        message=issue,
                        recommendation=(
                            f"Set a positive deadband on the alarm for '{element.name}' at "
                            f"{path} in the same engineering units as the value — without one, "
                            "a value hovering near the setpoint will chatter the alarm active/"
                            "inactive repeatedly."
                        ),
                    )
                )
        return findings
