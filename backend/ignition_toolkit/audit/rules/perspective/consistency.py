"""
Consistency rules — inline hardcoded styling instead of style classes / CSS
theme variables, which drifts out of sync with the rest of the project the
first time the theme changes.
"""

import logging
import re
from typing import Any

from ignition_toolkit.audit.engine import Finding, Rule, Severity
from ignition_toolkit.audit.project import PerspectiveProject

logger = logging.getLogger(__name__)

_COLOR_STYLE_KEYS = ("color", "backgroundColor", "borderColor", "fill")

# A literal hex color or rgb()/rgba() function call — as opposed to a
# stylesheet CSS variable reference like "var(--neutral-10)".
_LITERAL_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{3,8}$|^rgba?\(")


class HardcodedColorRule(Rule):
    """Flags literal hex/rgb colors set directly on a component's style."""

    rule_id = "consistency-hardcoded-color"
    severity = Severity.INFO
    description = "Component sets a literal color instead of a style class or theme variable."

    def evaluate(self, target: Any) -> list[Finding]:
        project: PerspectiveProject = target
        findings: list[Finding] = []
        for view in project.views.values():
            for ref in view.walk():
                style = ref.node.props.get("style", {})
                if not isinstance(style, dict):
                    continue
                for key in _COLOR_STYLE_KEYS:
                    value = style.get(key)
                    if not isinstance(value, str) or not _LITERAL_COLOR_RE.match(value.strip()):
                        continue
                    findings.append(
                        Finding(
                            rule_id=self.rule_id,
                            severity=self.severity,
                            location=ref.location,
                            message=(
                                f'Component "{ref.node.name}" hardcodes style.{key} to '
                                f'"{value}" instead of using a style class or theme variable.'
                            ),
                            recommendation=(
                                f'Move the {key} value on "{ref.node.name}" in {ref.view_path} '
                                "into a project style class, or reference a stylesheet theme "
                                "variable (e.g. var(--neutral-10)) instead of the literal "
                                f'"{value}". Hardcoded colors don\'t follow the project when a '
                                "theme changes and are easy to leave inconsistent with the "
                                "rest of the UI."
                            ),
                        )
                    )
        return findings
