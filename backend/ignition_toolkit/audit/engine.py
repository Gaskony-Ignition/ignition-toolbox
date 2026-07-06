"""
Generic audit rule engine.

This module is deliberately domain-agnostic: it knows nothing about
Perspective, view.json, or UDTs. A ``Rule`` inspects some ``target`` object
(a :class:`ignition_toolkit.audit.project.PerspectiveProject` today, a future
UDT type-definition model tomorrow) and returns zero or more ``Finding``
instances. ``RuleEngine`` just runs every registered rule against a target
and collects the findings.

Keeping this split (generic engine + domain-specific rules under
``audit/rules/<domain>/``) is what lets the planned UDT linter reuse this
module instead of duplicating it — see ``docs/plans/perspective-project-audit.md``
and ``docs/plans/udt-builder-design.md``.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Finding severity, ordered loosely from most to least urgent."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    INFO = "info"


@dataclass(frozen=True)
class Finding:
    """One rule violation, ready to be rendered into a customer-facing report.

    ``location`` is a rule-defined human-readable pointer into the audited
    target (for Perspective rules: ``"<view path> > <component path>"``).
    ``recommendation`` must be a full-sentence, actionable statement — it is
    read by the customer, not just a developer.
    """

    rule_id: str
    severity: Severity
    location: str
    message: str
    recommendation: str


class Rule(ABC):
    """Base class for a single audit check.

    Subclasses set the three class attributes and implement ``evaluate``.
    A rule may raise on unexpected input; :class:`RuleEngine` catches and
    logs so one broken rule can't take down an entire audit run.
    """

    rule_id: str
    severity: Severity
    description: str

    @abstractmethod
    def evaluate(self, target: Any) -> list[Finding]:
        """Inspect ``target`` and return any findings this rule detects."""
        raise NotImplementedError


class RuleEngine:
    """Runs a fixed set of rules against a target and collects findings."""

    def __init__(self, rules: list[Rule]) -> None:
        self.rules = list(rules)

    def run(self, target: Any) -> list[Finding]:
        """Evaluate every registered rule against ``target``.

        A rule that raises is logged and skipped rather than aborting the
        whole run — one bad rule shouldn't block a customer report.
        """
        findings: list[Finding] = []
        for rule in self.rules:
            try:
                findings.extend(rule.evaluate(target))
            except Exception:
                logger.exception("Rule %s raised while evaluating target; skipping", rule.rule_id)
        return findings
