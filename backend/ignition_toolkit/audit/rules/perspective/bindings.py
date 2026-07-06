"""
Binding rules — polling faster than needed, and expression bindings that are
really just a plain tag reference in disguise.
"""

import logging
import re
from typing import Any

from ignition_toolkit.audit.engine import Finding, Rule, Severity
from ignition_toolkit.audit.project import PerspectiveProject

logger = logging.getLogger(__name__)

# Ignition history/tag-history bindings poll on a fixed interval; anything
# faster than this floor produces meaningful gateway/network load for data
# that (for a dashboard) rarely needs sub-5-second freshness.
FAST_POLL_THRESHOLD_MS = 5000

# expr/expression bindings that poll do so via a bare now(<ms>) call, e.g.
# "expression": "now(2000)".
_NOW_POLL_RE = re.compile(r"now\(\s*(\d+)\s*\)")

# An expr binding whose entire expression is just one bare tag reference in
# braces, e.g. "{[default]Path/To/Tag}" — no computation at all.
_BARE_TAG_EXPRESSION_RE = re.compile(r"^\{\s*\[[^\]]+\][^{}]*\}$")


class FastPollingRule(Rule):
    """Flags bindings polling faster than FAST_POLL_THRESHOLD_MS."""

    rule_id = "bindings-fast-polling"
    severity = Severity.HIGH
    description = "Binding polls faster than 5 seconds."

    def evaluate(self, target: Any) -> list[Finding]:
        project: PerspectiveProject = target
        findings: list[Finding] = []
        for view in project.views.values():
            for ref, prop_path, binding in view.iter_bindings():
                rate_ms = self._poll_rate_ms(binding)
                if rate_ms is None or rate_ms >= FAST_POLL_THRESHOLD_MS:
                    continue
                rate_ms_display = int(rate_ms) if rate_ms == int(rate_ms) else rate_ms
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        location=ref.location,
                        message=(
                            f'Binding on "{prop_path}" polls every {rate_ms_display} ms '
                            f'(component "{ref.node.name}").'
                        ),
                        recommendation=(
                            f'Increase the poll rate on the "{prop_path}" binding of '
                            f'"{ref.node.name}" in {ref.view_path} to at least 5 seconds, or '
                            "switch to a tag/property binding that updates on change instead "
                            "of on a timer. Sub-5-second polling multiplies gateway and "
                            "database load across every open session for data that rarely "
                            "needs that freshness."
                        ),
                    )
                )
        return findings

    @staticmethod
    def _poll_rate_ms(binding: dict[str, Any]) -> float | None:
        config = binding.get("config", {})
        if not isinstance(config, dict):
            return None

        polling = config.get("polling")
        if isinstance(polling, dict) and polling.get("enabled"):
            rate = polling.get("rate")
            try:
                return float(rate) * 1000
            except (TypeError, ValueError):
                return None

        if binding.get("type") in ("expr", "expression"):
            expression = config.get("expression", "")
            match = _NOW_POLL_RE.search(expression) if isinstance(expression, str) else None
            if match:
                return float(match.group(1))

        return None


class ExpressionShouldBeTagRule(Rule):
    """Flags expr bindings whose entire expression is one bare tag reference."""

    rule_id = "bindings-expression-should-be-tag"
    severity = Severity.MEDIUM
    description = "Expression binding is just a bare tag reference — a tag binding would do."

    def evaluate(self, target: Any) -> list[Finding]:
        project: PerspectiveProject = target
        findings: list[Finding] = []
        for view in project.views.values():
            for ref, prop_path, binding in view.iter_bindings():
                if binding.get("type") not in ("expr", "expression"):
                    continue
                expression = binding.get("config", {}).get("expression", "")
                if not isinstance(expression, str):
                    continue
                if not _BARE_TAG_EXPRESSION_RE.match(expression.strip()):
                    continue
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        location=ref.location,
                        message=(
                            f'Binding on "{prop_path}" (component "{ref.node.name}") uses an '
                            f"expression binding that only wraps one tag: {expression}."
                        ),
                        recommendation=(
                            f'Replace the expression binding on "{prop_path}" of '
                            f'"{ref.node.name}" in {ref.view_path} with a direct tag binding '
                            "on the same tag path. Expression bindings that only reference "
                            "one tag add evaluation overhead and an extra subscription for no "
                            "benefit over a plain tag binding."
                        ),
                    )
                )
        return findings
