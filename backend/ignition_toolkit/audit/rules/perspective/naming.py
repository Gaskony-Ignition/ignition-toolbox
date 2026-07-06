"""
Naming rules — components left with a Designer-assigned default name, or
named after a file that was copy-pasted in (a real example seen in the
field: an image component named ``71oUI5FZdKL._SL1500_`` after the Amazon
product-photo filename it was dragged in from).
"""

import logging
import re
from typing import Any

from ignition_toolkit.audit.engine import Finding, Rule, Severity
from ignition_toolkit.audit.project import PerspectiveProject

logger = logging.getLogger(__name__)

# Designer auto-assigns names like "Label", "Label_1", "Flex Container 2" when
# a component is dropped and never renamed. Matches with or without a trailing
# index, case-insensitive, "_" or " " as the separator.
_DEFAULT_NAME_RE = re.compile(
    r"^(label|button|dropdown|text ?field|text ?area|flex ?container|"
    r"coordinate ?container|numeric ?entry ?field|icon|image|table|"
    r"toggle ?switch|checkbox|radio ?group|tab ?container|icon ?button|"
    r"one ?shot ?button|view)[\s_]*\d*$",
    re.IGNORECASE,
)

# A literal "." never appears in a name a person types into the Designer's
# "Name" field for a component — it's a strong signal the name is really a
# filename (image, document) that got used as-is instead of being renamed.
_FILENAME_LIKE_RE = re.compile(r"\.")


def _classify(name: str) -> str | None:
    """Return a human-readable reason the name is a smell, or None if it's fine."""
    if _DEFAULT_NAME_RE.match(name):
        return "still has the Designer-assigned default name"
    if _FILENAME_LIKE_RE.search(name):
        return "looks like a filename that was never renamed to something descriptive"
    return None


class NamingMeaninglessNameRule(Rule):
    """Flags components with a default or filename-derived name."""

    rule_id = "naming-meaningless-name"
    severity = Severity.MEDIUM
    description = (
        "Component left with a default or filename-derived name instead of a descriptive one."
    )

    def evaluate(self, target: Any) -> list[Finding]:
        project: PerspectiveProject = target
        findings: list[Finding] = []
        for view in project.views.values():
            for ref in view.walk():
                if ref.depth == 0:
                    # The view's root component is conventionally named "root"
                    # by Ignition itself — that's expected, not a smell.
                    continue
                reason = _classify(ref.node.name)
                if reason is None:
                    continue
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        location=ref.location,
                        message=f'Component "{ref.node.name}" {reason}.',
                        recommendation=(
                            f'Rename the component currently called "{ref.node.name}" in '
                            f"{ref.view_path} to a short, descriptive name that reflects what "
                            "it shows or does. Descriptive names make the view tree readable "
                            "for the next person who maintains it and make bindings/scripts "
                            "that reference the component by name self-explanatory."
                        ),
                    )
                )
        return findings
