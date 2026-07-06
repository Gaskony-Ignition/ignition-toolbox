"""
Hygiene rules — embedded images bloating the project export, and views that
are dead weight because nothing routes to or embeds them.
"""

import logging
from typing import Any

from ignition_toolkit.audit.engine import Finding, Rule, Severity
from ignition_toolkit.audit.project import PerspectiveProject

logger = logging.getLogger(__name__)

# Base64-encoded image data embedded directly in view.json bloats the project
# export and gets re-downloaded by every session on every view load, unlike a
# real image resource which the browser can cache. 50 KB is comfortably above
# a reasonable icon/thumbnail but well below a typical unoptimised photo.
OVERSIZED_IMAGE_THRESHOLD_BYTES = 50_000


class OversizedEmbeddedImageRule(Rule):
    """Flags ia.display.image components with a large base64 data-URI source."""

    rule_id = "hygiene-oversized-embedded-image"
    severity = Severity.MEDIUM
    description = "Image component embeds a large base64 image directly in the view."

    def evaluate(self, target: Any) -> list[Finding]:
        project: PerspectiveProject = target
        findings: list[Finding] = []
        for view in project.views.values():
            for ref in view.walk():
                if ref.node.type != "ia.display.image":
                    continue
                source = ref.node.props.get("source")
                if not isinstance(source, str) or not source.startswith("data:"):
                    continue
                if "base64," not in source:
                    continue
                b64_payload = source.split("base64,", 1)[1]
                approx_bytes = len(b64_payload) * 3 // 4
                if approx_bytes <= OVERSIZED_IMAGE_THRESHOLD_BYTES:
                    continue
                approx_kb = approx_bytes // 1000
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        location=ref.location,
                        message=(
                            f'Image component "{ref.node.name}" embeds a ~{approx_kb} KB '
                            "base64 image directly in the view."
                        ),
                        recommendation=(
                            f'Replace the embedded base64 image on "{ref.node.name}" in '
                            f"{ref.view_path} with a reference to an image resource (or an "
                            "external URL) instead of inlining the bytes in view.json. "
                            "Embedded images this size bloat the project export and are "
                            "re-sent to the browser on every view load instead of being "
                            "cached like a normal image resource."
                        ),
                    )
                )
        return findings


class UnreachableViewRule(Rule):
    """Flags views nothing in the project routes to or embeds."""

    rule_id = "hygiene-unreachable-view"
    severity = Severity.INFO
    description = "View is not reachable from page-config routes, docks, or an embedding."

    def evaluate(self, target: Any) -> list[Finding]:
        project: PerspectiveProject = target
        findings: list[Finding] = []
        for view_path in project.unreachable_views():
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    severity=self.severity,
                    location=view_path,
                    message=f'View "{view_path}" is not reachable from any page route, dock, or embedded view.',
                    recommendation=(
                        f'Confirm whether "{view_path}" is still in use. If it is opened only '
                        "via a popup or a script-driven navigate call this may be a false "
                        "positive worth noting in the report, but if it's simply left over "
                        "from earlier work, remove it to keep the project easy to navigate "
                        "and reduce what has to be reviewed in future audits."
                    ),
                )
            )
        return findings
