"""OPC-path-parameterisation rule — wraps ``conventions.check_opc_path``."""

import logging
from typing import Any

from ignition_toolkit.audit.engine import Finding, Rule, Severity
from ignition_toolkit.audit.rules.udt._walk import walk_members
from ignition_toolkit.udt.conventions import check_opc_path
from ignition_toolkit.udt.models import UdtDefinition

logger = logging.getLogger(__name__)


class UdtUnparameterisedOpcPathRule(Rule):
    """Flags an OPC-sourced member whose ``opcItemPath``/``opcServer`` isn't ``{Parameter}``-driven."""

    rule_id = "udt-unparameterised-opc-path"
    severity = Severity.HIGH
    description = (
        "OPC-sourced member's item path or server connection is hardcoded instead of "
        "referencing a UDT parameter."
    )

    def evaluate(self, target: Any) -> list[Finding]:
        udt: UdtDefinition = target
        findings: list[Finding] = []
        for element, path in walk_members(udt):
            for issue in check_opc_path(element, path):
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        location=path,
                        message=issue,
                        recommendation=(
                            f"Rewrite '{element.name}' at {path} so its opcItemPath/opcServer "
                            "reference a UDT parameter (e.g. '{DevicePath}/...' / "
                            "'{OpcServer}') instead of a hardcoded path or connection name — "
                            "hardcoding breaks every instance of this UDT from being "
                            "independently retargetable."
                        ),
                    )
                )
        return findings
