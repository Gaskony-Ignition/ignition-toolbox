"""
Tests for the UDT lint rule pack (ignition_toolkit.audit.rules.udt): one
positive + one negative case per rule, plus a sanity check on
default_rules()/lint_udt(). Each rule wraps a specific conventions.py check
function (see composer.py's imports) — these tests exercise the Rule layer
(Finding shape, rule_id, severity, location) rather than re-testing the
underlying predicate logic already covered by test_conventions.py.
"""

from typing import Any

from ignition_toolkit.audit.engine import Finding, Severity
from ignition_toolkit.audit.rules.udt import default_rules, lint_udt
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


def _udt(tags: list[dict[str, Any]], **root_overrides: Any) -> UdtDefinition:
    data: dict[str, Any] = {"name": "Widget", "tagType": "UdtType", "tags": tags}
    data.update(root_overrides)
    return UdtDefinition.model_validate(data)


_CLEAN_TAG: dict[str, Any] = {
    "name": "running",
    "tagType": "AtomicTag",
    "valueSource": "opc",
    "dataType": "Boolean",
    "opcServer": "{OpcServer}",
    "opcItemPath": "{DevicePath}/Running",
    "documentation": "Running status.",
    "historyEnabled": False,
}


class TestUdtNamingViolationRule:
    def test_positive_bad_member_name(self) -> None:
        udt = _udt([{**_CLEAN_TAG, "name": "running_status"}])
        findings = UdtNamingViolationRule().evaluate(udt)
        assert len(findings) == 1
        assert findings[0].rule_id == "udt-naming-violation"
        assert findings[0].location == "running_status"

    def test_negative_clean_name(self) -> None:
        udt = _udt([_CLEAN_TAG])
        assert UdtNamingViolationRule().evaluate(udt) == []


class TestUdtMissingDocumentationRule:
    def test_positive_missing_documentation(self) -> None:
        tag = {k: v for k, v in _CLEAN_TAG.items() if k != "documentation"}
        udt = _udt([tag])
        findings = UdtMissingDocumentationRule().evaluate(udt)
        assert len(findings) == 1
        assert findings[0].rule_id == "udt-missing-documentation"
        assert findings[0].severity == Severity.MEDIUM

    def test_negative_has_documentation(self) -> None:
        udt = _udt([_CLEAN_TAG])
        assert UdtMissingDocumentationRule().evaluate(udt) == []


class TestUdtMissingEngUnitRule:
    def test_positive_analog_missing_eng_unit(self) -> None:
        tag = {
            **_CLEAN_TAG,
            "name": "speed",
            "dataType": "Float4",
            "opcItemPath": "{DevicePath}/Speed",
        }
        udt = _udt([tag])
        findings = UdtMissingEngUnitRule().evaluate(udt)
        assert len(findings) == 1
        assert findings[0].rule_id == "udt-missing-eng-unit"
        assert findings[0].location == "speed"

    def test_negative_analog_with_eng_unit(self) -> None:
        tag = {
            **_CLEAN_TAG,
            "name": "speed",
            "dataType": "Float4",
            "opcItemPath": "{DevicePath}/Speed",
            "engUnit": "RPM",
        }
        udt = _udt([tag])
        assert UdtMissingEngUnitRule().evaluate(udt) == []


class TestUdtMissingEngRangeRule:
    def test_positive_analog_missing_eng_range(self) -> None:
        tag = {
            **_CLEAN_TAG,
            "name": "speed",
            "dataType": "Float4",
            "opcItemPath": "{DevicePath}/Speed",
            "engUnit": "RPM",
        }
        udt = _udt([tag])
        findings = UdtMissingEngRangeRule().evaluate(udt)
        assert len(findings) == 1
        assert findings[0].rule_id == "udt-missing-eng-range"

    def test_negative_analog_with_eng_range(self) -> None:
        tag = {
            **_CLEAN_TAG,
            "name": "speed",
            "dataType": "Float4",
            "opcItemPath": "{DevicePath}/Speed",
            "engUnit": "RPM",
            "engLow": 0,
            "engHigh": 1500,
        }
        udt = _udt([tag])
        assert UdtMissingEngRangeRule().evaluate(udt) == []

    def test_boolean_member_never_flagged(self) -> None:
        """A discrete (Boolean) member has no engineering range concept at all."""
        udt = _udt([_CLEAN_TAG])
        assert UdtMissingEngRangeRule().evaluate(udt) == []


class TestUdtUnparameterisedOpcPathRule:
    def test_positive_hardcoded_opc_server(self) -> None:
        tag = {**_CLEAN_TAG, "opcServer": "Ignition OPC UA Server"}
        udt = _udt([tag])
        findings = UdtUnparameterisedOpcPathRule().evaluate(udt)
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH

    def test_negative_parameterised_opc_path(self) -> None:
        udt = _udt([_CLEAN_TAG])
        assert UdtUnparameterisedOpcPathRule().evaluate(udt) == []


class TestUdtNonStandardAlarmNameRule:
    def test_positive_non_standard_name(self) -> None:
        tag = {
            **_CLEAN_TAG,
            "name": "speed",
            "dataType": "Float4",
            "opcItemPath": "{DevicePath}/Speed",
            "engUnit": "RPM",
            "alarms": [{"name": "HighSpeed", "priority": "High", "deadband": 5}],
        }
        udt = _udt([tag])
        findings = UdtNonStandardAlarmNameRule().evaluate(udt)
        assert len(findings) == 1
        assert findings[0].rule_id == "udt-nonstandard-alarm-name"

    def test_negative_standard_name(self) -> None:
        tag = {
            **_CLEAN_TAG,
            "name": "speed",
            "dataType": "Float4",
            "opcItemPath": "{DevicePath}/Speed",
            "engUnit": "RPM",
            "alarms": [{"name": "HiHi", "priority": "High", "deadband": 5}],
        }
        udt = _udt([tag])
        assert UdtNonStandardAlarmNameRule().evaluate(udt) == []


class TestUdtInvalidAlarmPriorityRule:
    def test_positive_invalid_priority(self) -> None:
        tag = {
            **_CLEAN_TAG,
            "name": "fault",
            "alarms": [{"name": "Fault", "priority": "Urgent"}],
        }
        udt = _udt([tag])
        findings = UdtInvalidAlarmPriorityRule().evaluate(udt)
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH

    def test_negative_valid_priority(self) -> None:
        tag = {
            **_CLEAN_TAG,
            "name": "fault",
            "alarms": [{"name": "Fault", "priority": "High"}],
        }
        udt = _udt([tag])
        assert UdtInvalidAlarmPriorityRule().evaluate(udt) == []


class TestUdtMissingAlarmDeadbandRule:
    def test_positive_analog_alarm_missing_deadband(self) -> None:
        tag = {
            **_CLEAN_TAG,
            "name": "speed",
            "dataType": "Float4",
            "opcItemPath": "{DevicePath}/Speed",
            "engUnit": "RPM",
            "alarms": [{"name": "HiHi", "priority": "High"}],
        }
        udt = _udt([tag])
        findings = UdtMissingAlarmDeadbandRule().evaluate(udt)
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH

    def test_negative_analog_alarm_with_deadband(self) -> None:
        tag = {
            **_CLEAN_TAG,
            "name": "speed",
            "dataType": "Float4",
            "opcItemPath": "{DevicePath}/Speed",
            "engUnit": "RPM",
            "alarms": [{"name": "HiHi", "priority": "High", "deadband": 25}],
        }
        udt = _udt([tag])
        assert UdtMissingAlarmDeadbandRule().evaluate(udt) == []

    def test_boolean_alarm_never_needs_deadband(self) -> None:
        tag = {**_CLEAN_TAG, "name": "fault", "alarms": [{"name": "Fault", "priority": "High"}]}
        udt = _udt([tag])
        assert UdtMissingAlarmDeadbandRule().evaluate(udt) == []


class TestUdtNoDeliberateHistoryChoiceRule:
    def test_positive_history_enabled_unset(self) -> None:
        tag = {k: v for k, v in _CLEAN_TAG.items() if k != "historyEnabled"}
        udt = _udt([tag])
        findings = UdtNoDeliberateHistoryChoiceRule().evaluate(udt)
        assert len(findings) == 1
        assert findings[0].rule_id == "udt-no-deliberate-history-choice"

    def test_negative_history_explicitly_disabled(self) -> None:
        udt = _udt([_CLEAN_TAG])
        assert UdtNoDeliberateHistoryChoiceRule().evaluate(udt) == []


class TestUdtIncompleteHistoryConfigRule:
    def test_positive_enabled_without_provider(self) -> None:
        tag = {**_CLEAN_TAG, "historyEnabled": True}
        udt = _udt([tag])
        findings = UdtIncompleteHistoryConfigRule().evaluate(udt)
        assert len(findings) == 1
        assert findings[0].rule_id == "udt-incomplete-history-config"

    def test_negative_enabled_with_full_config(self) -> None:
        tag = {**_CLEAN_TAG, "historyEnabled": True, "historyProvider": "default"}
        udt = _udt([tag])
        assert UdtIncompleteHistoryConfigRule().evaluate(udt) == []

    def test_negative_no_deliberate_choice_not_double_reported(self) -> None:
        """
        An unset historyEnabled is UdtNoDeliberateHistoryChoiceRule's concern,
        not this rule's — avoid double-reporting the same member.
        """
        tag = {k: v for k, v in _CLEAN_TAG.items() if k != "historyEnabled"}
        udt = _udt([tag])
        assert UdtIncompleteHistoryConfigRule().evaluate(udt) == []


class TestDefaultRulesAndLintUdt:
    def test_default_rules_returns_ten_fresh_rules(self) -> None:
        rules = default_rules()
        assert len(rules) == 10
        assert len({rule.rule_id for rule in rules}) == 10

    def test_lint_udt_runs_every_rule_and_returns_findings(self) -> None:
        tag = {k: v for k, v in _CLEAN_TAG.items() if k != "documentation"}
        udt = _udt([tag])
        findings = lint_udt(udt)
        assert any(isinstance(f, Finding) for f in findings)
        assert any(f.rule_id == "udt-missing-documentation" for f in findings)

    def test_lint_udt_clean_udt_has_no_findings(self) -> None:
        udt = _udt([_CLEAN_TAG])
        assert lint_udt(udt) == []

    def test_location_is_slash_joined_member_path_without_type_name(self) -> None:
        """Matches the design doc's example: {"location": "status/speed"}."""
        udt = _udt(
            [
                {
                    "name": "status",
                    "tagType": "Folder",
                    "documentation": "Status folder.",
                    "tags": [
                        {
                            **_CLEAN_TAG,
                            "name": "speed",
                            "dataType": "Float4",
                            "opcItemPath": "{DevicePath}/Speed",
                            "documentation": None,
                        }
                    ],
                }
            ]
        )
        findings = lint_udt(udt)
        locations = {f.location for f in findings}
        assert "status/speed" in locations
        assert not any(loc.startswith("Widget") or loc.startswith("/") for loc in locations)
