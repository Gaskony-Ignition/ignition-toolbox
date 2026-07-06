"""
Tests for ignition_toolkit.udt.composer: composition models, compose()'s
naming-style application, ISA-18.2 default alarm priority filling, every
structural-validation branch, and the preset-parity approach used by
GET /api/udt/presets (see test_api/test_udt_router.py for the HTTP-level
tests of the compose/presets endpoints themselves).
"""

from typing import Any

import pytest

from ignition_toolkit.udt.builder import build
from ignition_toolkit.udt.composer import (
    Composition,
    CompositionAlarm,
    CompositionHistory,
    UdtComposerError,
    compose,
    udt_to_composition,
)
from ignition_toolkit.udt.models import find_parameter_references, to_tag_export


def _simple_composition(**overrides: Any) -> dict[str, Any]:
    """A minimal, valid composition body — override individual keys per test."""
    base: dict[str, Any] = {
        "type_name": "ConveyorMotor",
        "description": "A conveyor motor.",
        "naming_style": "camelCase",
        "parameters": [
            {"name": "DevicePath", "data_type": "String", "default_value": ""},
            {
                "name": "OpcServer",
                "data_type": "String",
                "default_value": "Ignition OPC UA Server",
            },
        ],
        "members": [
            {
                "kind": "folder",
                "name": "status",
                "documentation": "Status folder.",
                "members": [
                    {
                        "kind": "tag",
                        "name": "speed",
                        "value_source": "opc",
                        "data_type": "Float4",
                        "opc_item_path": "{DevicePath}/Speed",
                        "opc_server": "{OpcServer}",
                        "eng_unit": "rpm",
                        "eng_low": 0,
                        "eng_high": 1500,
                        "documentation": "Motor shaft speed.",
                        "history": {
                            "enabled": True,
                            "tag_group": "Default Historical",
                            "deadband_style": "Auto",
                        },
                        "alarms": [
                            {
                                "name": "HiHi",
                                "setpoint": 1400,
                                "deadband": 25,
                                "mode": "AboveValue",
                                "priority": None,
                            }
                        ],
                    }
                ],
            }
        ],
    }
    base.update(overrides)
    return base


class TestCompositionModels:
    def test_parses_the_design_doc_example_shape(self) -> None:
        composition = Composition.model_validate(_simple_composition())
        assert composition.type_name == "ConveyorMotor"
        assert composition.members[0].kind == "folder"
        assert composition.members[0].members[0].kind == "tag"
        assert composition.members[0].members[0].value_source == "opc"

    def test_defaults(self) -> None:
        composition = Composition(type_name="Widget")
        assert composition.naming_style == "camelCase"
        assert composition.parameters == []
        assert composition.members == []

    def test_composition_alarm_priority_defaults_to_none(self) -> None:
        alarm = CompositionAlarm(name="HiHi")
        assert alarm.priority is None

    def test_composition_history_requires_enabled(self) -> None:
        history = CompositionHistory(enabled=False)
        assert history.tag_group is None
        assert history.deadband_style is None


class TestComposeBasics:
    def test_compose_returns_udt_definition_with_expected_shape(self) -> None:
        udt = compose(Composition.model_validate(_simple_composition()))
        dumped = to_tag_export(udt)

        assert dumped["name"] == "ConveyorMotor"
        assert dumped["tagType"] == "UdtType"
        assert dumped["documentation"] == "A conveyor motor."
        assert set(dumped["parameters"]) == {"DevicePath", "OpcServer"}

        status = dumped["tags"][0]
        assert status["name"] == "status"
        assert status["tagType"] == "Folder"
        speed = status["tags"][0]
        assert speed["name"] == "speed"
        assert speed["tagType"] == "AtomicTag"
        assert speed["valueSource"] == "opc"
        assert speed["opcItemPath"] == "{DevicePath}/Speed"
        assert speed["opcServer"] == "{OpcServer}"

    def test_memory_member(self) -> None:
        body = _simple_composition(
            members=[
                {
                    "kind": "tag",
                    "name": "setpoint",
                    "value_source": "memory",
                    "data_type": "Float4",
                    "value": 10.0,
                    "documentation": "doc",
                }
            ]
        )
        udt = compose(Composition.model_validate(body))
        tag = udt.tags[0]
        assert tag.value_source == "memory"
        assert tag.value == 10.0
        assert tag.opc_item_path is None

    def test_expression_member_translates_value_source_to_expr(self) -> None:
        body = _simple_composition(
            parameters=[{"name": "Factor", "data_type": "Float4", "default_value": 1.0}],
            members=[
                {
                    "kind": "tag",
                    "name": "scaled",
                    "value_source": "expression",
                    "data_type": "Float4",
                    "expression": "{Factor} * 2",
                    "documentation": "doc",
                }
            ],
        )
        udt = compose(Composition.model_validate(body))
        tag = udt.tags[0]
        # Ignition's real wire format uses "expr", never the UI-friendly
        # "expression" the composition wire format exposes.
        assert tag.value_source == "expr"
        assert tag.model_extra is not None
        assert tag.model_extra["expression"] == "{Factor} * 2"

    def test_root_description_becomes_documentation(self) -> None:
        udt = compose(Composition.model_validate(_simple_composition(description="Hello")))
        assert udt.documentation == "Hello"

    def test_alarm_deadband_and_setpoint_round_trip(self) -> None:
        udt = compose(Composition.model_validate(_simple_composition()))
        speed = udt.tags[0].tags[0]
        alarm = speed.alarms[0]
        assert alarm.setpoint_a == 1400
        assert alarm.deadband == 25


class TestNamingStyleApplication:
    def test_camel_case_default(self) -> None:
        udt = compose(Composition.model_validate(_simple_composition()))
        assert udt.tags[0].name == "status"
        assert udt.tags[0].tags[0].name == "speed"

    def test_pascal_case_applies_to_members_and_folders(self) -> None:
        udt = compose(Composition.model_validate(_simple_composition(naming_style="PascalCase")))
        assert udt.tags[0].name == "Status"
        assert udt.tags[0].tags[0].name == "Speed"

    def test_type_name_never_restyled(self) -> None:
        udt = compose(Composition.model_validate(_simple_composition(naming_style="PascalCase")))
        assert udt.name == "ConveyorMotor"

    def test_parameter_names_never_restyled(self) -> None:
        udt = compose(Composition.model_validate(_simple_composition(naming_style="PascalCase")))
        assert set(udt.parameters) == {"DevicePath", "OpcServer"}

    def test_alarm_names_never_restyled(self) -> None:
        udt = compose(Composition.model_validate(_simple_composition(naming_style="PascalCase")))
        speed = udt.tags[0].tags[0]
        assert speed.alarms[0].name == "HiHi"


class TestIsaDefaultPriorityFilling:
    def test_null_priority_fills_isa_default(self) -> None:
        # HiHi's ISA-18.2 default is "High" (conventions.STANDARD_ALARM_DEFAULTS).
        udt = compose(Composition.model_validate(_simple_composition()))
        speed = udt.tags[0].tags[0]
        assert speed.alarms[0].priority == "High"

    def test_explicit_priority_overrides_default(self) -> None:
        body = _simple_composition()
        body["members"][0]["members"][0]["alarms"][0]["priority"] = "Critical"
        udt = compose(Composition.model_validate(body))
        speed = udt.tags[0].tags[0]
        assert speed.alarms[0].priority == "Critical"

    def test_non_standard_alarm_name_has_no_default_and_stays_none(self) -> None:
        body = _simple_composition()
        body["members"][0]["members"][0]["alarms"][0]["name"] = "WeirdAlarm"
        body["members"][0]["members"][0]["alarms"][0]["priority"] = None
        udt = compose(Composition.model_validate(body))
        speed = udt.tags[0].tags[0]
        assert speed.alarms[0].priority is None

    def test_mode_also_defaults_from_standard_alarm(self) -> None:
        body = _simple_composition()
        body["members"][0]["members"][0]["alarms"][0]["mode"] = None
        udt = compose(Composition.model_validate(body))
        speed = udt.tags[0].tags[0]
        assert speed.alarms[0].mode == "AboveValue"


class TestStructuralValidation:
    def test_invalid_type_name(self) -> None:
        with pytest.raises(UdtComposerError, match="not valid PascalCase"):
            compose(Composition.model_validate(_simple_composition(type_name="conveyor motor")))

    def test_unknown_parameter_reference_in_opc_item_path(self) -> None:
        body = _simple_composition()
        body["members"][0]["members"][0]["opc_item_path"] = "{Bogus}/Speed"
        with pytest.raises(UdtComposerError, match=r"unknown parameter reference '\{Bogus\}'"):
            compose(Composition.model_validate(body))

    def test_unknown_parameter_reference_in_expression(self) -> None:
        body = _simple_composition(
            members=[
                {
                    "kind": "tag",
                    "name": "scaled",
                    "value_source": "expression",
                    "data_type": "Float4",
                    "expression": "{Bogus} * 2",
                    "documentation": "doc",
                }
            ]
        )
        with pytest.raises(UdtComposerError, match=r"unknown parameter reference '\{Bogus\}'"):
            compose(Composition.model_validate(body))

    def test_duplicate_sibling_names_after_naming_style_application(self) -> None:
        """
        "Speed" and "speed" are distinct before styling but collide once
        naming_style="camelCase" lowercases the first letter of both.
        """
        body = _simple_composition(
            members=[
                {
                    "kind": "tag",
                    "name": "Speed",
                    "value_source": "memory",
                    "data_type": "Float4",
                    "value": 1.0,
                    "documentation": "doc",
                },
                {
                    "kind": "tag",
                    "name": "speed",
                    "value_source": "memory",
                    "data_type": "Float4",
                    "value": 2.0,
                    "documentation": "doc",
                },
            ]
        )
        with pytest.raises(UdtComposerError, match="duplicate sibling member name 'speed'"):
            compose(Composition.model_validate(body))

    def test_unknown_data_type(self) -> None:
        body = _simple_composition()
        body["members"][0]["members"][0]["data_type"] = "NotARealType"
        with pytest.raises(UdtComposerError, match="unknown data type 'NotARealType'"):
            compose(Composition.model_validate(body))

    def test_alarm_on_a_folder(self) -> None:
        body = _simple_composition()
        body["members"][0]["alarms"] = [{"name": "HiHi", "setpoint": 1}]
        with pytest.raises(UdtComposerError, match="a folder cannot have alarms"):
            compose(Composition.model_validate(body))

    def test_expression_member_without_expression(self) -> None:
        body = _simple_composition(
            members=[
                {
                    "kind": "tag",
                    "name": "scaled",
                    "value_source": "expression",
                    "data_type": "Float4",
                    "documentation": "doc",
                }
            ]
        )
        with pytest.raises(UdtComposerError, match="expression member missing expression"):
            compose(Composition.model_validate(body))

    def test_memory_member_without_value(self) -> None:
        body = _simple_composition(
            members=[
                {
                    "kind": "tag",
                    "name": "setpoint",
                    "value_source": "memory",
                    "data_type": "Float4",
                    "documentation": "doc",
                }
            ]
        )
        with pytest.raises(UdtComposerError, match="memory member missing value"):
            compose(Composition.model_validate(body))

    def test_unknown_naming_style(self) -> None:
        with pytest.raises(UdtComposerError, match="unknown naming_style 'kebab-case'"):
            compose(Composition.model_validate(_simple_composition(naming_style="kebab-case")))

    def test_all_problems_are_joined_into_one_message(self) -> None:
        """
        Every structural problem is collected and raised together (same
        '; '-joined style as builder.UdtBuilderError), not just the first one
        found.
        """
        body = {
            "type_name": "bad type name",
            "naming_style": "kebab-case",
            "parameters": [],
            "members": [
                {
                    "kind": "tag",
                    "name": "a",
                    "value_source": "memory",
                    "data_type": "Bogus",
                },
                {
                    "kind": "tag",
                    "name": "a",
                    "value_source": "expression",
                    "data_type": "Float4",
                },
                {
                    "kind": "folder",
                    "name": "f",
                    "alarms": [{"name": "HiHi"}],
                    "members": [],
                },
            ],
        }
        with pytest.raises(UdtComposerError) as exc_info:
            compose(Composition.model_validate(body))

        message = str(exc_info.value)
        assert "unknown naming_style 'kebab-case'" in message
        assert "not valid PascalCase" in message
        assert "unknown data type 'Bogus'" in message
        assert "memory member missing value" in message
        assert "expression member missing expression" in message
        assert "duplicate sibling member name 'a'" in message
        assert "a folder cannot have alarms" in message


class TestPresetParity:
    """
    Preset-parity approach: build() each template with a representative
    answer set, convert the result to a Composition via
    composer.udt_to_composition(), then compose() it back and assert the
    round trip preserves member names/nesting, alarms (name/priority/mode/
    setpoint/deadband), and parameters — the exact aspects
    docs/plans/udt-composer-design.md requires. History fields are not
    compared: udt_to_composition()'s reconstruction of deadband_style is a
    best-effort approximation (documented in its docstring), and the design
    doc's parity requirement is scoped to structure/alarms/parameters only.
    """

    @pytest.mark.parametrize(
        ("template_id", "answers"),
        [
            ("motor", {"device_path": "[default]PLC1/Motors/M101"}),
            ("valve", {"device_path": "[default]PLC1/Valves/V101"}),
            (
                "analog_input",
                {
                    "device_path": "[default]PLC1/AI/LT101",
                    "eng_unit": "kPa",
                    "enable_hihi_alarm": True,
                    "enable_hi_alarm": True,
                    "enable_lo_alarm": True,
                    "enable_lolo_alarm": True,
                },
            ),
        ],
    )
    def test_preset_round_trip_matches_builder_output(
        self, template_id: str, answers: dict[str, Any]
    ) -> None:
        built = build(template_id, answers)
        composition = udt_to_composition(built)
        recomposed = compose(composition)

        assert _names_and_nesting(recomposed) == _names_and_nesting(built)
        assert _alarms_summary(recomposed) == _alarms_summary(built)
        assert _parameters_summary(recomposed) == _parameters_summary(built)

    def test_preset_composition_is_itself_structurally_valid(self) -> None:
        """A preset must not itself trip compose()'s structural validation."""
        built = build("motor", {"device_path": "[default]PLC1/Motors/M101"})
        composition = udt_to_composition(built)
        # Must not raise.
        compose(composition)

    def test_udt_to_composition_preserves_parameter_references(self) -> None:
        built = build("motor", {"device_path": "[default]PLC1/Motors/M101"})
        composition = udt_to_composition(built)
        recomposed = compose(composition)
        assert find_parameter_references(recomposed) == find_parameter_references(built)


def _names_and_nesting(udt: Any) -> list[Any]:
    def walk(element: Any) -> tuple:
        return (element.name, element.tag_type, [walk(c) for c in (element.tags or [])])

    return [walk(tag) for tag in udt.tags]


def _alarms_summary(udt: Any) -> list[tuple]:
    out: list[tuple] = []

    def walk(element: Any) -> None:
        for alarm in element.alarms or []:
            out.append(
                (
                    element.name,
                    alarm.name,
                    alarm.priority,
                    alarm.mode,
                    alarm.setpoint_a,
                    alarm.deadband,
                )
            )
        for child in element.tags or []:
            walk(child)

    for tag in udt.tags:
        walk(tag)
    return out


def _parameters_summary(udt: Any) -> dict[str, tuple]:
    return {name: (param.data_type, param.value) for name, param in (udt.parameters or {}).items()}
