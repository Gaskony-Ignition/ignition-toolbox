"""
Layout rules — coordinate containers used where a flex container would serve,
and flex children missing the ``minHeight:0``/``minWidth:0`` that lets them
shrink inside their parent.
"""

import logging
import re
from typing import Any

from ignition_toolkit.audit.engine import Finding, Rule, Severity
from ignition_toolkit.audit.project import PerspectiveProject

logger = logging.getLogger(__name__)

# Coordinate containers are the right tool for pixel-precise diagrams
# (process mimics, P&IDs, floor plans, maps) — anything named like one of
# these is assumed to be a deliberate, legitimate use.
_DIAGRAM_NAME_RE = re.compile(
    r"diagram|pipe|schematic|process|mimic|p&?id|floor ?plan|map|layout ?view",
    re.IGNORECASE,
)


class CoordContainerOveruseRule(Rule):
    """Flags coordinate containers that aren't obviously a pixel-precise diagram."""

    rule_id = "layout-coord-container-overuse"
    severity = Severity.MEDIUM
    description = (
        "Coordinate container used where a flex container would adapt better to screen size."
    )

    def evaluate(self, target: Any) -> list[Finding]:
        project: PerspectiveProject = target
        findings: list[Finding] = []
        for view in project.views.values():
            for ref in view.walk():
                if ref.node.type != "ia.container.coord":
                    continue
                if _DIAGRAM_NAME_RE.search(ref.node.name):
                    continue
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        location=ref.location,
                        message=(
                            f'Coordinate container "{ref.node.name}" positions its children '
                            "with fixed pixel coordinates."
                        ),
                        recommendation=(
                            f'Convert the coordinate container "{ref.node.name}" in '
                            f"{ref.view_path} to a flex container unless it is genuinely a "
                            "pixel-precise diagram (e.g. a process mimic or floor plan). Flex "
                            "containers reflow automatically across window sizes and screen "
                            "resolutions; coordinate containers keep a fixed layout and clip "
                            "or overlap content on smaller screens."
                        ),
                    )
                )
        return findings


class MissingMinSizeRule(Rule):
    """Flags nested flex containers that participate in flex sizing but never
    reset their min size, so they can't shrink below their content size."""

    rule_id = "layout-missing-min-size"
    severity = Severity.INFO
    description = "Nested flex container can grow/shrink but doesn't set minHeight/minWidth: 0."

    def evaluate(self, target: Any) -> list[Finding]:
        project: PerspectiveProject = target
        findings: list[Finding] = []
        for view in project.views.values():
            for ref in view.walk():
                node = ref.node
                if ref.depth == 0 or node.type != "ia.container.flex":
                    continue
                participates = node.position.get("grow") or node.position.get("shrink")
                if not participates:
                    continue
                style = node.props.get("style", {})
                if style.get("minHeight") == 0 and style.get("minWidth") == 0:
                    continue
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        location=ref.location,
                        message=(
                            f'Flex container "{node.name}" grows/shrinks inside its parent but '
                            "does not set style.minHeight/minWidth to 0."
                        ),
                        recommendation=(
                            f'Add "minHeight": 0 and "minWidth": 0 to the style of the flex '
                            f'container "{node.name}" in {ref.view_path}. Without this, the '
                            "browser's default flex min-size keeps the container at its "
                            "content size, so it silently refuses to shrink on smaller "
                            "screens or when siblings need the space, even though grow/shrink "
                            "is configured."
                        ),
                    )
                )
        return findings
