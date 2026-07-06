"""
Tests for ignition_toolkit.udt.builder: template loading, questionnaire
validation, conditional sections, and the emitted UDT's conformance to
ignition_toolkit.udt.conventions plus lossless round-tripping through
ignition_toolkit.udt.models.

The Motor build with typical answers is also pinned as a golden regression
fixture (golden/motor_built_golden.json, kept out of fixtures/ so it doesn't
trip test_models.py's "every fixture file is covered" guard) — if this test
fails because the template intentionally changed, regenerate the fixture
deliberately rather than papering over an unreviewed diff.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from ignition_toolkit.udt.builder import UdtBuilderError, build, list_templates
from ignition_toolkit.udt.conventions import find_convention_issues
from ignition_toolkit.udt.models import UdtDefinition, find_parameter_references, to_tag_export

GOLDEN_MOTOR_PATH = Path(__file__).parent / "golden" / "motor_built_golden.json"


def _iter_atomic_tags(element):
    """Yield every AtomicTag node in the tree rooted at element (incl. nested folders)."""
    if element.tag_type == "AtomicTag":
        yield element
    for child in element.tags or []:
        yield from _iter_atomic_tags(child)


def _assert_lossless_round_trip(udt: UdtDefinition) -> None:
    """A builder-produced UDT must survive dump -> parse -> dump unchanged."""
    dumped = to_tag_export(udt)
    reparsed = UdtDefinition.model_validate(dumped)
    assert to_tag_export(reparsed) == dumped


class TestListTemplates:
    def test_three_templates_present(self) -> None:
        templates = list_templates()
        assert {t.id for t in templates} == {"motor", "valve", "analog_input"}

    def test_metadata_and_questionnaire_shape(self) -> None:
        templates = {t.id: t for t in list_templates()}
        motor = templates["motor"]
        assert motor.label == "Motor"
        assert motor.description
        assert len(motor.questionnaire) > 0
        for qf in motor.questionnaire:
            assert qf.name
            assert qf.type in {"string", "integer", "float", "boolean"}
            assert isinstance(qf.required, bool)
            assert isinstance(qf.description, str) and qf.description


class TestMotorTemplate:
    @pytest.fixture
    def typical_answers(self) -> dict[str, Any]:
        return {"device_path": "[default]PLC1/Motors/M101"}

    def test_builds_with_typical_answers(self, typical_answers: dict[str, Any]) -> None:
        udt = build("motor", typical_answers)
        assert udt.name == "Motor"
        assert udt.tag_type == "UdtType"
        names = [t.name for t in udt.tags]
        assert names == ["running", "start", "speed", "fault"]

    def test_round_trips_losslessly(self, typical_answers: dict[str, Any]) -> None:
        udt = build("motor", typical_answers)
        _assert_lossless_round_trip(udt)

    def test_every_member_has_documentation(self, typical_answers: dict[str, Any]) -> None:
        udt = build("motor", typical_answers)
        for tag in _iter_atomic_tags(udt):
            assert tag.documentation and tag.documentation.strip(), tag.name

    def test_analog_members_have_eng_unit(self, typical_answers: dict[str, Any]) -> None:
        udt = build("motor", typical_answers)
        speed = next(t for t in udt.tags if t.name == "speed")
        assert speed.data_type == "Float4"
        assert speed.eng_unit == "RPM"

    def test_alarms_have_deadband_name_and_priority(self, typical_answers: dict[str, Any]) -> None:
        udt = build("motor", typical_answers)
        speed = next(t for t in udt.tags if t.name == "speed")
        assert len(speed.alarms) == 1
        alarm = speed.alarms[0]
        assert alarm.name == "HiHi"
        assert alarm.priority == "High"
        assert alarm.deadband and alarm.deadband > 0

    def test_opc_paths_reference_parameters_not_hardcoded_servers(
        self, typical_answers: dict[str, Any]
    ) -> None:
        """
        Every member's own opcServer/opcItemPath must be a {Parameter}
        reference, never a literal connection/device name. The literal
        server name legitimately appears exactly once, as the *default
        value* of the OpcServer parameter itself — that's the one place a
        concrete name belongs, since it's what makes the parameter useful.
        """
        udt = build("motor", typical_answers)
        for tag in _iter_atomic_tags(udt):
            if tag.value_source != "opc":
                continue
            assert tag.opc_server == "{OpcServer}"
            assert tag.opc_item_path.startswith("{DevicePath}")
        assert udt.parameters["OpcServer"].value == "Ignition OPC UA Server"

    def test_conditional_speed_feedback_toggle(self, typical_answers: dict[str, Any]) -> None:
        without_speed = {**typical_answers, "has_speed_feedback": False}
        udt = build("motor", without_speed)
        names = [t.name for t in udt.tags]
        assert "speed" not in names
        # The parameter that only exists to feed the speed alarm should also disappear.
        assert "HighSpeedSetpoint" not in (udt.parameters or {})

    def test_conditional_fault_input_toggle(self, typical_answers: dict[str, Any]) -> None:
        without_fault = {**typical_answers, "has_fault_input": False}
        udt = build("motor", without_fault)
        assert "fault" not in [t.name for t in udt.tags]

    def test_history_opt_in_fills_in_provider_and_deadband(
        self, typical_answers: dict[str, Any]
    ) -> None:
        with_history = {**typical_answers, "enable_speed_history": True}
        udt = build("motor", with_history)
        speed = next(t for t in udt.tags if t.name == "speed")
        assert speed.history_enabled is True
        assert speed.history_provider == "default"
        assert speed.historical_deadband == 1.0

    def test_history_disabled_by_default_and_no_leftover_fields(
        self, typical_answers: dict[str, Any]
    ) -> None:
        udt = build("motor", typical_answers)
        speed = next(t for t in udt.tags if t.name == "speed")
        assert speed.history_enabled is False
        assert speed.history_provider is None
        assert speed.historical_deadband is None

    def test_missing_required_field_raises_clean_error(self) -> None:
        with pytest.raises(UdtBuilderError, match="device_path"):
            build("motor", {})

    def test_wrong_type_answer_raises_clean_error(self) -> None:
        with pytest.raises(UdtBuilderError, match="must be a"):
            build("motor", {"device_path": "x", "has_speed_feedback": "yes"})

    def test_unknown_answer_field_raises_clean_error(self) -> None:
        with pytest.raises(UdtBuilderError, match="unknown field"):
            build("motor", {"device_path": "x", "not_a_real_field": 1})

    def test_no_convention_violations(self, typical_answers: dict[str, Any]) -> None:
        udt = build("motor", typical_answers)
        assert find_convention_issues(udt) == []


class TestValveTemplate:
    @pytest.fixture
    def typical_answers(self) -> dict[str, Any]:
        return {"device_path": "[default]PLC1/Valves/V101"}

    def test_builds_with_typical_answers(self, typical_answers: dict[str, Any]) -> None:
        udt = build("valve", typical_answers)
        assert udt.name == "Valve"
        assert [t.name for t in udt.tags] == ["status", "command", "config"]

    def test_status_command_config_folder_structure(self, typical_answers: dict[str, Any]) -> None:
        udt = build("valve", typical_answers)
        status, command, config = udt.tags
        assert status.tag_type == "Folder"
        assert command.tag_type == "Folder"
        assert config.tag_type == "Folder"
        assert [t.name for t in status.tags] == ["open", "closed", "position", "fault"]
        assert [t.name for t in command.tags] == ["openCmd", "closeCmd"]
        assert [t.name for t in config.tags] == ["travelTimeSetpoint"]

    def test_round_trips_losslessly(self, typical_answers: dict[str, Any]) -> None:
        udt = build("valve", typical_answers)
        _assert_lossless_round_trip(udt)

    def test_every_member_has_documentation_including_folders(
        self, typical_answers: dict[str, Any]
    ) -> None:
        udt = build("valve", typical_answers)

        def _walk(element):
            if element.tag_type in {"AtomicTag", "Folder"}:
                assert element.documentation and element.documentation.strip(), element.name
            for child in element.tags or []:
                _walk(child)

        for tag in udt.tags:
            _walk(tag)

    def test_conditional_position_feedback_toggle(self, typical_answers: dict[str, Any]) -> None:
        no_position = {**typical_answers, "has_position_feedback": False}
        udt = build("valve", no_position)
        status = next(t for t in udt.tags if t.name == "status")
        assert "position" not in [t.name for t in status.tags]

    def test_conditional_fault_detection_toggle(self, typical_answers: dict[str, Any]) -> None:
        no_fault = {**typical_answers, "has_fault_detection": False}
        udt = build("valve", no_fault)
        status = next(t for t in udt.tags if t.name == "status")
        assert "fault" not in [t.name for t in status.tags]

    def test_config_memory_tag_is_not_opc(self, typical_answers: dict[str, Any]) -> None:
        udt = build("valve", typical_answers)
        config = next(t for t in udt.tags if t.name == "config")
        travel_time = config.tags[0]
        assert travel_time.value_source == "memory"
        assert travel_time.opc_item_path is None

    def test_opc_paths_reference_parameters(self, typical_answers: dict[str, Any]) -> None:
        udt = build("valve", typical_answers)
        for tag in _iter_atomic_tags(udt):
            if tag.value_source != "opc":
                continue
            assert tag.opc_server == "{OpcServer}"
            assert tag.opc_item_path.startswith("{DevicePath}")

    def test_no_convention_violations(self, typical_answers: dict[str, Any]) -> None:
        udt = build("valve", typical_answers)
        assert find_convention_issues(udt) == []


class TestAnalogInputTemplate:
    @pytest.fixture
    def typical_answers(self) -> dict[str, Any]:
        return {
            "device_path": "[default]PLC1/AI/LT101",
            "eng_unit": "kPa",
            "enable_hihi_alarm": True,
            "enable_hi_alarm": True,
            "enable_lo_alarm": True,
            "enable_lolo_alarm": True,
        }

    def test_builds_with_typical_answers(self, typical_answers: dict[str, Any]) -> None:
        udt = build("analog_input", typical_answers)
        assert udt.name == "AnalogInput"
        value = udt.tags[0]
        assert value.name == "value"
        assert value.eng_unit == "kPa"

    def test_round_trips_losslessly(self, typical_answers: dict[str, Any]) -> None:
        udt = build("analog_input", typical_answers)
        _assert_lossless_round_trip(udt)

    def test_full_alarm_ladder_present_with_standard_names_and_priorities(
        self, typical_answers: dict[str, Any]
    ) -> None:
        udt = build("analog_input", typical_answers)
        value = udt.tags[0]
        alarms_by_name = {a.name: a for a in value.alarms}
        assert set(alarms_by_name) == {"HiHi", "Hi", "Lo", "LoLo"}
        assert alarms_by_name["HiHi"].priority == "High"
        assert alarms_by_name["Hi"].priority == "Medium"
        assert alarms_by_name["Lo"].priority == "Medium"
        assert alarms_by_name["LoLo"].priority == "High"
        for alarm in value.alarms:
            assert alarm.deadband and alarm.deadband > 0

    def test_disabled_alarms_are_absent_and_their_parameters_too(self) -> None:
        udt = build(
            "analog_input",
            {"device_path": "[default]PLC1/AI/LT102", "eng_unit": "degC"},
        )
        value = udt.tags[0]
        assert value.alarms == []
        assert udt.parameters is not None
        for name in ("HiHiSetpoint", "HiSetpoint", "LoSetpoint", "LoLoSetpoint"):
            assert name not in udt.parameters

    def test_partial_alarm_ladder_only_enabled_ones_appear(self) -> None:
        udt = build(
            "analog_input",
            {
                "device_path": "[default]PLC1/AI/LT103",
                "eng_unit": "m3/h",
                "enable_hihi_alarm": True,
            },
        )
        value = udt.tags[0]
        assert [a.name for a in value.alarms] == ["HiHi"]
        assert "HiHiSetpoint" in udt.parameters
        assert "LoSetpoint" not in udt.parameters

    def test_missing_required_eng_unit_raises_clean_error(self) -> None:
        with pytest.raises(UdtBuilderError, match="eng_unit"):
            build("analog_input", {"device_path": "x"})

    def test_no_convention_violations(self, typical_answers: dict[str, Any]) -> None:
        udt = build("analog_input", typical_answers)
        assert find_convention_issues(udt) == []


class TestParameterReferencesUsedByAllTemplates:
    """Every template's OPC-backed members must depend on OpcServer/DevicePath, never a literal."""

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
                },
            ),
        ],
    )
    def test_parameter_refs_include_opc_server_and_device_path(
        self, template_id: str, answers: dict[str, Any]
    ) -> None:
        udt = build(template_id, answers)
        refs = find_parameter_references(udt)
        assert "OpcServer" in refs
        assert "DevicePath" in refs


class TestMotorGoldenFixture:
    """
    Regression fixture: pins the exact JSON emitted for a typical Motor build.
    If the template changes deliberately, regenerate this file (see the
    module docstring) rather than hand-editing it to match.
    """

    def test_matches_golden_fixture(self) -> None:
        udt = build("motor", {"device_path": "[default]PLC1/Motors/M101"})
        dumped = to_tag_export(udt)

        with open(GOLDEN_MOTOR_PATH, encoding="utf-8") as f:
            golden = json.load(f)

        assert dumped == golden, (
            "Motor build output no longer matches the golden fixture. If this "
            "change to templates/motor.json was deliberate, regenerate "
            f"{GOLDEN_MOTOR_PATH} from the new output.\n"
            f"Got: {json.dumps(dumped, indent=2)}"
        )
