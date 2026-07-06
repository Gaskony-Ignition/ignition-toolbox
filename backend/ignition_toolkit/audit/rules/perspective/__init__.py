"""
Seed rule pack for Perspective projects — 10 checks derived from
battle-tested conventions in ``/home/nigel/claude/ignition/CLAUDE.md``
(naming, layout, bindings, scripts, consistency, hygiene).

``default_rules()`` returns fresh rule instances ready to hand to
:class:`ignition_toolkit.audit.engine.RuleEngine`.
"""

from ignition_toolkit.audit.engine import Rule
from ignition_toolkit.audit.rules.perspective.bindings import (
    ExpressionShouldBeTagRule,
    FastPollingRule,
)
from ignition_toolkit.audit.rules.perspective.consistency import HardcodedColorRule
from ignition_toolkit.audit.rules.perspective.hygiene import (
    OversizedEmbeddedImageRule,
    UnreachableViewRule,
)
from ignition_toolkit.audit.rules.perspective.layout import (
    CoordContainerOveruseRule,
    MissingMinSizeRule,
)
from ignition_toolkit.audit.rules.perspective.naming import NamingMeaninglessNameRule
from ignition_toolkit.audit.rules.perspective.scripts import (
    ClickHandlerVsNativeNavRule,
    InvokeAsynchronousDaemonRule,
)

__all__ = [
    "NamingMeaninglessNameRule",
    "CoordContainerOveruseRule",
    "MissingMinSizeRule",
    "FastPollingRule",
    "ExpressionShouldBeTagRule",
    "InvokeAsynchronousDaemonRule",
    "ClickHandlerVsNativeNavRule",
    "HardcodedColorRule",
    "OversizedEmbeddedImageRule",
    "UnreachableViewRule",
    "default_rules",
]


def default_rules() -> list[Rule]:
    """Return one fresh instance of every seed Perspective rule."""
    return [
        NamingMeaninglessNameRule(),
        CoordContainerOveruseRule(),
        MissingMinSizeRule(),
        FastPollingRule(),
        ExpressionShouldBeTagRule(),
        InvokeAsynchronousDaemonRule(),
        ClickHandlerVsNativeNavRule(),
        HardcodedColorRule(),
        OversizedEmbeddedImageRule(),
        UnreachableViewRule(),
    ]
