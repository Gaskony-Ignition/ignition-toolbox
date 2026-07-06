"""
UDT lint rule pack — 10 checks wrapping ``ignition_toolkit.udt.conventions``
(naming, documentation, engineering units/range, OPC path parameterisation,
alarms, history), on the same generic ``Rule``/``Finding`` shape as the
Perspective rule pack (``audit/rules/perspective/``).

``default_rules()`` returns fresh rule instances ready to hand to
:class:`ignition_toolkit.audit.engine.RuleEngine`; :func:`lint_udt` is the
one-call convenience entry point ``docs/plans/udt-composer-design.md``
specifies for the compose endpoint to use.
"""

from ignition_toolkit.audit.engine import Finding, Rule, RuleEngine
from ignition_toolkit.audit.rules.udt.alarm_deadband import UdtMissingAlarmDeadbandRule
from ignition_toolkit.audit.rules.udt.alarm_name import UdtNonStandardAlarmNameRule
from ignition_toolkit.audit.rules.udt.alarm_priority import UdtInvalidAlarmPriorityRule
from ignition_toolkit.audit.rules.udt.documentation import UdtMissingDocumentationRule
from ignition_toolkit.audit.rules.udt.eng_range import UdtMissingEngRangeRule
from ignition_toolkit.audit.rules.udt.eng_unit import UdtMissingEngUnitRule
from ignition_toolkit.audit.rules.udt.history_choice import UdtNoDeliberateHistoryChoiceRule
from ignition_toolkit.audit.rules.udt.history_complete import UdtIncompleteHistoryConfigRule
from ignition_toolkit.audit.rules.udt.naming import UdtNamingViolationRule
from ignition_toolkit.audit.rules.udt.opc_path import UdtUnparameterisedOpcPathRule
from ignition_toolkit.udt.models import UdtDefinition

__all__ = [
    "UdtNamingViolationRule",
    "UdtMissingDocumentationRule",
    "UdtMissingEngUnitRule",
    "UdtMissingEngRangeRule",
    "UdtUnparameterisedOpcPathRule",
    "UdtNonStandardAlarmNameRule",
    "UdtInvalidAlarmPriorityRule",
    "UdtMissingAlarmDeadbandRule",
    "UdtNoDeliberateHistoryChoiceRule",
    "UdtIncompleteHistoryConfigRule",
    "default_rules",
    "lint_udt",
]


def default_rules() -> list[Rule]:
    """Return one fresh instance of every UDT lint rule."""
    return [
        UdtNamingViolationRule(),
        UdtMissingDocumentationRule(),
        UdtMissingEngUnitRule(),
        UdtMissingEngRangeRule(),
        UdtUnparameterisedOpcPathRule(),
        UdtNonStandardAlarmNameRule(),
        UdtInvalidAlarmPriorityRule(),
        UdtMissingAlarmDeadbandRule(),
        UdtNoDeliberateHistoryChoiceRule(),
        UdtIncompleteHistoryConfigRule(),
    ]


def lint_udt(udt: UdtDefinition) -> list[Finding]:
    """Run every UDT lint rule against ``udt`` and return the combined findings."""
    return RuleEngine(default_rules()).run(udt)
