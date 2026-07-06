"""
Round-trip and parsing tests for ignition_toolkit.udt.models.

Fixtures under fixtures/ are synthetic (hand-authored to match the documented
shape of Ignition 8.x tag-export JSON) — the real reference project is not on
this machine yet (see docs/plans/udt-builder-design.md prerequisite). These
tests must be re-run against real Designer exports once
docs/reference/udt-examples/ exists, to confirm no assumption here was wrong.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from ignition_toolkit.udt.models import (
    UdtDefinition,
    find_parameter_references,
    parse_tag_export,
    to_tag_export,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict[str, Any]:
    """Load a fixture JSON file by filename from fixtures/."""
    with open(FIXTURES_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def assert_round_trips_losslessly(data: dict[str, Any]) -> UdtDefinition:
    """
    Parse ``data`` into a UdtDefinition, dump it back out, and assert the
    result is deeply equal to the original (same keys/values; dict key order
    may differ, list order must match).

    Returns the parsed model so callers can run further assertions on it.
    """
    model = parse_tag_export(data)
    dumped = to_tag_export(model)
    assert dumped == data, (
        f"Round-trip mismatch.\nOriginal: {json.dumps(data, indent=2)}\n"
        f"Dumped:   {json.dumps(dumped, indent=2)}"
    )
    return model


@pytest.fixture
def motor_simple() -> dict[str, Any]:
    return _load_fixture("motor_simple.json")


@pytest.fixture
def valve_nested_inheritance() -> dict[str, Any]:
    return _load_fixture("valve_nested_inheritance.json")


@pytest.fixture
def extras_lossless() -> dict[str, Any]:
    return _load_fixture("extras_lossless.json")


class TestParsing:
    """Basic structural assertions after parsing each fixture."""

    def test_motor_simple_parses(self, motor_simple: dict[str, Any]) -> None:
        model = parse_tag_export(motor_simple)
        assert model.name == "Motor"
        assert model.tag_type == "UdtType"
        assert model.parameters is not None
        assert set(model.parameters.keys()) == {"OpcServer", "DevicePath", "HighSpeedSetpoint"}
        assert model.tags is not None
        assert [t.name for t in model.tags] == ["Speed", "Running", "Start"]

    def test_motor_simple_alarm_parsed(self, motor_simple: dict[str, Any]) -> None:
        model = parse_tag_export(motor_simple)
        speed = next(t for t in model.tags if t.name == "Speed")
        assert speed.alarms is not None
        assert len(speed.alarms) == 1
        alarm = speed.alarms[0]
        assert alarm.name == "HighSpeed"
        assert alarm.priority == "High"
        assert alarm.setpoint_a == "{HighSpeedSetpoint}"

    def test_valve_nested_folder_and_instance(
        self, valve_nested_inheritance: dict[str, Any]
    ) -> None:
        model = parse_tag_export(valve_nested_inheritance)
        assert model.type_id == "BaseDevice"  # UDT type inheritance
        names = [t.name for t in model.tags]
        assert names == ["Status", "Command", "Actuator"]

        status_folder = model.tags[0]
        assert status_folder.tag_type == "Folder"
        assert [t.name for t in status_folder.tags] == ["Open", "Closed"]

        actuator = model.tags[2]
        assert actuator.tag_type == "UdtInstance"
        assert actuator.type_id == "Motor"
        assert actuator.parameters is not None
        assert actuator.parameters["DevicePath"].value == "{DevicePath}/Actuator"

    def test_extras_unknown_fields_are_accessible(self, extras_lossless: dict[str, Any]) -> None:
        model = parse_tag_export(extras_lossless)
        # Unknown top-level field captured via extra="allow"
        assert model.model_extra is not None
        assert model.model_extra["customTypeFlag"] is True
        assert model.model_extra["exportedBy"] == "Designer-8.1.37"
        assert model.model_extra["trailingUnknownBlock"]["nested"]["deep"]["deeper"] is None


class TestRoundTrip:
    """Every fixture must survive a parse -> dump cycle unchanged."""

    def test_motor_simple_round_trips(self, motor_simple: dict[str, Any]) -> None:
        assert_round_trips_losslessly(motor_simple)

    def test_valve_nested_inheritance_round_trips(
        self, valve_nested_inheritance: dict[str, Any]
    ) -> None:
        assert_round_trips_losslessly(valve_nested_inheritance)

    def test_extras_lossless_round_trips(self, extras_lossless: dict[str, Any]) -> None:
        assert_round_trips_losslessly(extras_lossless)

    def test_no_default_pollution(self, motor_simple: dict[str, Any]) -> None:
        """
        A field never set in the input (e.g. 'readOnly' on a tag that omits
        it) must not appear in the output — proves exclude_unset is doing its
        job rather than emitting every Optional field's None/False default.
        """
        model = parse_tag_export(motor_simple)
        dumped = to_tag_export(model)
        speed_dump = dumped["tags"][0]
        # Speed never set historyEnabled's sibling 'scaleMode' in the fixture
        assert "scaleMode" not in speed_dump
        # Running never sets 'engUnit' or 'alarms' in the fixture
        running_dump = dumped["tags"][1]
        assert "engUnit" not in running_dump
        assert "alarms" not in running_dump

    def test_all_fixture_files_covered(self) -> None:
        """Guard against a fixture being added but forgotten in these tests."""
        fixture_files = {p.name for p in FIXTURES_DIR.glob("*.json")}
        assert fixture_files == {
            "motor_simple.json",
            "valve_nested_inheritance.json",
            "extras_lossless.json",
        }


class TestParameterReferenceDiscovery:
    """find_parameter_references walks the whole subtree for {Param} usages."""

    def test_motor_simple_references(self, motor_simple: dict[str, Any]) -> None:
        model = parse_tag_export(motor_simple)
        refs = find_parameter_references(model)
        assert refs == {"OpcServer", "DevicePath", "HighSpeedSetpoint"}

    def test_valve_nested_references_include_instance_params(
        self, valve_nested_inheritance: dict[str, Any]
    ) -> None:
        model = parse_tag_export(valve_nested_inheritance)
        refs = find_parameter_references(model)
        # Referenced in opcItemPath/opcServer of the valve's own members, plus
        # the nested UdtInstance's own parameter *values* (which point back at
        # the parent's parameters, e.g. "{DevicePath}/Actuator").
        assert refs == {"OpcServer", "DevicePath"}

    def test_no_references_returns_empty_set(self) -> None:
        model = UdtDefinition.model_validate(
            {
                "name": "NoParams",
                "tagType": "UdtType",
                "tags": [
                    {
                        "name": "Constant",
                        "tagType": "AtomicTag",
                        "valueSource": "memory",
                        "dataType": "Boolean",
                        "value": True,
                    }
                ],
            }
        )
        assert find_parameter_references(model) == set()


class TestModelConfig:
    """Sanity checks on the extra='allow' behaviour itself."""

    def test_unknown_field_round_trips_even_if_never_declared(self) -> None:
        data = {
            "name": "Foo",
            "tagType": "UdtType",
            "somethingIgnitionAddedInAFutureVersion": {"a": 1, "b": [1, 2, None]},
        }
        model = parse_tag_export(data)
        assert to_tag_export(model) == data

    def test_empty_udt_round_trips(self) -> None:
        """A minimal UDT with only name/tagType/tags=[] round-trips cleanly."""
        data = {"name": "Empty", "tagType": "UdtType", "tags": []}
        assert_round_trips_losslessly(data)

    def test_snake_case_input_key_is_rewritten_to_camel_case(self) -> None:
        """Pins the known populate_by_name limitation (see models.py docstring).

        A snake_case twin of a modelled key in the *input* is consumed by the
        field and re-emitted as camelCase. Genuine Ignition exports are always
        camelCase, so this only affects hand-edited files. If this test starts
        failing because the output became lossless, the limitation was fixed —
        update the models.py docstring accordingly.
        """
        model = parse_tag_export({"name": "T", "tag_type": "AtomicTag"})
        assert to_tag_export(model) == {"name": "T", "tagType": "AtomicTag"}
