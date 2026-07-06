"""
Unit tests for ignition_toolkit.udt.conventions.

These exercise the predicates/constants directly (naming, eng units, OPC
paths, alarms, history) so the rules are pinned independently of whatever
the templates/builder happen to produce.
"""

from ignition_toolkit.udt.conventions import (
    ALARM_PRIORITIES,
    ALARM_PRIORITY_GUIDANCE,
    STANDARD_ALARM_DEFAULTS,
    STANDARD_ALARM_NAMES,
    alarm_deadband_required,
    find_convention_issues,
    has_deliberate_history_choice,
    has_valid_deadband,
    history_config_complete,
    is_camel_case,
    is_default_name,
    is_parameterised,
    is_pascal_case,
    is_standard_alarm_name,
    is_valid_alarm_priority,
    is_valid_member_name,
    is_valid_type_name,
    opc_item_path_uses_parameters,
)
from ignition_toolkit.udt.models import AlarmConfig, TagElement, UdtDefinition


class TestNaming:
    def test_pascal_case_type_names(self) -> None:
        assert is_valid_type_name("Motor")
        assert is_valid_type_name("AnalogInput")
        assert not is_valid_type_name("motor")
        assert not is_valid_type_name("Motor Speed")
        assert not is_valid_type_name("Motor_Speed")

    def test_camel_case_member_names(self) -> None:
        assert is_valid_member_name("speed")
        assert is_valid_member_name("highSpeedSetpoint")
        assert not is_valid_member_name("Speed")
        assert not is_valid_member_name("high speed")
        assert not is_valid_member_name("high_speed")

    def test_default_names_rejected(self) -> None:
        assert is_default_name("NewTag_0")
        assert is_default_name("New_Tag1")
        assert is_default_name("Tag0")
        assert not is_default_name("speed")
        assert not is_valid_member_name("NewTag_0")
        assert not is_valid_type_name("NewUDT1")

    def test_pascal_and_camel_helpers(self) -> None:
        assert is_pascal_case("Motor")
        assert not is_pascal_case("motor")
        assert is_camel_case("motor")
        assert not is_camel_case("Motor")


class TestOpcPaths:
    def test_is_parameterised(self) -> None:
        assert is_parameterised("{OpcServer}")
        assert not is_parameterised("Ignition OPC UA Server")
        assert not is_parameterised("{OpcServer}/extra")
        assert not is_parameterised(None)

    def test_opc_item_path_uses_parameters(self) -> None:
        assert opc_item_path_uses_parameters("{DevicePath}/Speed")
        assert not opc_item_path_uses_parameters("PLC1/Motors/M101/Speed")
        assert not opc_item_path_uses_parameters(None)


class TestAlarmPriority:
    def test_five_priorities_documented(self) -> None:
        assert set(ALARM_PRIORITIES) == {"Diagnostic", "Low", "Medium", "High", "Critical"}
        assert set(ALARM_PRIORITY_GUIDANCE) == set(ALARM_PRIORITIES)
        assert all(ALARM_PRIORITY_GUIDANCE.values())

    def test_is_valid_alarm_priority(self) -> None:
        assert is_valid_alarm_priority("High")
        assert not is_valid_alarm_priority("Urgent")
        assert not is_valid_alarm_priority(None)

    def test_standard_alarm_names(self) -> None:
        assert set(STANDARD_ALARM_NAMES) == {
            "HiHi",
            "Hi",
            "Lo",
            "LoLo",
            "Fault",
            "Trip",
            "Warning",
        }
        for name, meta in STANDARD_ALARM_DEFAULTS.items():
            assert is_standard_alarm_name(name)
            assert is_valid_alarm_priority(meta["priority"])
        assert not is_standard_alarm_name("HighSpeed")

    def test_deadband_required_only_for_analog(self) -> None:
        assert alarm_deadband_required("Float4")
        assert alarm_deadband_required("Float8")
        assert not alarm_deadband_required("Boolean")
        assert not alarm_deadband_required("String")
        assert not alarm_deadband_required(None)

    def test_has_valid_deadband(self) -> None:
        assert has_valid_deadband(AlarmConfig(deadband=1.0))
        assert not has_valid_deadband(AlarmConfig(deadband=0))
        assert not has_valid_deadband(AlarmConfig(deadband=None))
        assert not has_valid_deadband(AlarmConfig(deadband="not-a-number"))


class TestHistory:
    def test_history_config_complete_does_not_itself_require_an_explicit_choice(self) -> None:
        """
        `history_config_complete` only checks "if enabled, is the rest of the
        config filled in" — it does not police whether historyEnabled was
        left unset. That's `has_deliberate_history_choice` (exercised via
        `find_convention_issues` in TestFindConventionIssues below).
        """
        tag = TagElement(tag_type="AtomicTag", history_enabled=None)
        assert history_config_complete(tag)
        assert not has_deliberate_history_choice(tag)

    def test_history_config_complete_requires_provider_and_deadband(self) -> None:
        enabled_ok = TagElement(
            tag_type="AtomicTag",
            data_type="Float4",
            history_enabled=True,
            history_provider="default",
            historical_deadband=1.0,
        )
        assert history_config_complete(enabled_ok)

        enabled_missing_provider = TagElement(
            tag_type="AtomicTag", data_type="Float4", history_enabled=True
        )
        assert not history_config_complete(enabled_missing_provider)

        enabled_missing_deadband = TagElement(
            tag_type="AtomicTag",
            data_type="Float4",
            history_enabled=True,
            history_provider="default",
        )
        assert not history_config_complete(enabled_missing_deadband)

        disabled = TagElement(tag_type="AtomicTag", history_enabled=False)
        assert history_config_complete(disabled)

        # Non-analog members enabled with just a provider are complete (no
        # historicalDeadband requirement for discrete data types).
        boolean_ok = TagElement(
            tag_type="AtomicTag",
            data_type="Boolean",
            history_enabled=True,
            history_provider="default",
        )
        assert history_config_complete(boolean_ok)


class TestFindConventionIssues:
    def test_clean_udt_has_no_issues(self) -> None:
        udt = UdtDefinition.model_validate(
            {
                "name": "Widget",
                "tagType": "UdtType",
                "parameters": {
                    "OpcServer": {"dataType": "String", "value": "Ignition OPC UA Server"},
                    "DevicePath": {"dataType": "String", "value": ""},
                },
                "tags": [
                    {
                        "name": "running",
                        "tagType": "AtomicTag",
                        "valueSource": "opc",
                        "dataType": "Boolean",
                        "opcServer": "{OpcServer}",
                        "opcItemPath": "{DevicePath}/Running",
                        "documentation": "Running status.",
                        "readOnly": True,
                        "historyEnabled": False,
                    }
                ],
            }
        )
        assert find_convention_issues(udt) == []

    def test_bad_type_name_flagged(self) -> None:
        udt = UdtDefinition.model_validate({"name": "widget", "tagType": "UdtType", "tags": []})
        issues = find_convention_issues(udt)
        assert any("PascalCase" in issue for issue in issues)

    def test_bad_member_name_flagged(self) -> None:
        udt = UdtDefinition.model_validate(
            {
                "name": "Widget",
                "tagType": "UdtType",
                "tags": [
                    {
                        "name": "Running",
                        "tagType": "AtomicTag",
                        "valueSource": "opc",
                        "dataType": "Boolean",
                        "opcServer": "{OpcServer}",
                        "opcItemPath": "{DevicePath}/Running",
                        "documentation": "doc",
                        "historyEnabled": False,
                    }
                ],
            }
        )
        issues = find_convention_issues(udt)
        assert any("camelCase" in issue for issue in issues)

    def test_missing_documentation_flagged(self) -> None:
        udt = UdtDefinition.model_validate(
            {
                "name": "Widget",
                "tagType": "UdtType",
                "tags": [
                    {
                        "name": "running",
                        "tagType": "AtomicTag",
                        "valueSource": "opc",
                        "dataType": "Boolean",
                        "opcServer": "{OpcServer}",
                        "opcItemPath": "{DevicePath}/Running",
                        "historyEnabled": False,
                    }
                ],
            }
        )
        issues = find_convention_issues(udt)
        assert any("missing documentation" in issue for issue in issues)

    def test_analog_missing_eng_unit_flagged(self) -> None:
        udt = UdtDefinition.model_validate(
            {
                "name": "Widget",
                "tagType": "UdtType",
                "tags": [
                    {
                        "name": "speed",
                        "tagType": "AtomicTag",
                        "valueSource": "opc",
                        "dataType": "Float4",
                        "opcServer": "{OpcServer}",
                        "opcItemPath": "{DevicePath}/Speed",
                        "documentation": "doc",
                        "historyEnabled": False,
                    }
                ],
            }
        )
        issues = find_convention_issues(udt)
        assert any("engUnit" in issue for issue in issues)

    def test_hardcoded_opc_server_flagged(self) -> None:
        udt = UdtDefinition.model_validate(
            {
                "name": "Widget",
                "tagType": "UdtType",
                "tags": [
                    {
                        "name": "running",
                        "tagType": "AtomicTag",
                        "valueSource": "opc",
                        "dataType": "Boolean",
                        "opcServer": "Ignition OPC UA Server",
                        "opcItemPath": "{DevicePath}/Running",
                        "documentation": "doc",
                        "historyEnabled": False,
                    }
                ],
            }
        )
        issues = find_convention_issues(udt)
        assert any("hardcoded" in issue for issue in issues)

    def test_opc_item_path_without_parameter_flagged(self) -> None:
        udt = UdtDefinition.model_validate(
            {
                "name": "Widget",
                "tagType": "UdtType",
                "tags": [
                    {
                        "name": "running",
                        "tagType": "AtomicTag",
                        "valueSource": "opc",
                        "dataType": "Boolean",
                        "opcServer": "{OpcServer}",
                        "opcItemPath": "PLC1/Widget/Running",
                        "documentation": "doc",
                        "historyEnabled": False,
                    }
                ],
            }
        )
        issues = find_convention_issues(udt)
        assert any("does not reference any" in issue for issue in issues)

    def test_unset_history_flagged(self) -> None:
        udt = UdtDefinition.model_validate(
            {
                "name": "Widget",
                "tagType": "UdtType",
                "tags": [
                    {
                        "name": "running",
                        "tagType": "AtomicTag",
                        "valueSource": "opc",
                        "dataType": "Boolean",
                        "opcServer": "{OpcServer}",
                        "opcItemPath": "{DevicePath}/Running",
                        "documentation": "doc",
                    }
                ],
            }
        )
        issues = find_convention_issues(udt)
        assert any("historyEnabled not explicitly set" in issue for issue in issues)

    def test_non_standard_alarm_name_and_missing_deadband_flagged(self) -> None:
        udt = UdtDefinition.model_validate(
            {
                "name": "Widget",
                "tagType": "UdtType",
                "tags": [
                    {
                        "name": "speed",
                        "tagType": "AtomicTag",
                        "valueSource": "opc",
                        "dataType": "Float4",
                        "opcServer": "{OpcServer}",
                        "opcItemPath": "{DevicePath}/Speed",
                        "engUnit": "RPM",
                        "documentation": "doc",
                        "historyEnabled": False,
                        "alarms": [
                            {
                                "name": "HighSpeed",
                                "mode": "AboveValue",
                                "priority": "High",
                                "enabled": True,
                            }
                        ],
                    }
                ],
            }
        )
        issues = find_convention_issues(udt)
        assert any("not one of the standardised alarm names" in issue for issue in issues)
        assert any("missing a positive deadband" in issue for issue in issues)

    def test_invalid_alarm_priority_flagged(self) -> None:
        udt = UdtDefinition.model_validate(
            {
                "name": "Widget",
                "tagType": "UdtType",
                "tags": [
                    {
                        "name": "fault",
                        "tagType": "AtomicTag",
                        "valueSource": "opc",
                        "dataType": "Boolean",
                        "opcServer": "{OpcServer}",
                        "opcItemPath": "{DevicePath}/Fault",
                        "documentation": "doc",
                        "historyEnabled": False,
                        "alarms": [{"name": "Fault", "priority": "Urgent", "enabled": True}],
                    }
                ],
            }
        )
        issues = find_convention_issues(udt)
        assert any("not a valid ISA-18.2 level" in issue for issue in issues)

    def test_folder_recursion_reaches_nested_members(self) -> None:
        udt = UdtDefinition.model_validate(
            {
                "name": "Widget",
                "tagType": "UdtType",
                "tags": [
                    {
                        "name": "status",
                        "tagType": "Folder",
                        "documentation": "Status folder.",
                        "tags": [
                            {
                                "name": "Open",  # bad casing, nested inside a folder
                                "tagType": "AtomicTag",
                                "valueSource": "opc",
                                "dataType": "Boolean",
                                "opcServer": "{OpcServer}",
                                "opcItemPath": "{DevicePath}/Open",
                                "documentation": "doc",
                                "historyEnabled": False,
                            }
                        ],
                    }
                ],
            }
        )
        issues = find_convention_issues(udt)
        assert any("Open" in issue and "camelCase" in issue for issue in issues)
