"""
Tests for the UDT Builder API router (``/api/udt``).

Uses a standalone FastAPI app with just the udt router mounted (same pattern
as test_audit_router.py) since the router has no dependency on app.py's
startup lifecycle — it only calls the pure in-memory
``ignition_toolkit.udt.builder`` module.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ignition_toolkit.api.routers.udt import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

TYPICAL_ANSWERS = {
    "motor": {"device_path": "[default]PLC1/Motors/M101"},
    "valve": {"device_path": "[default]PLC1/Valves/V101"},
    "analog_input": {"device_path": "[default]PLC1/AI/LT101", "eng_unit": "kPa"},
}


class TestGetTemplates:
    def test_returns_three_templates(self) -> None:
        response = client.get("/api/udt/templates")

        assert response.status_code == 200
        data = response.json()
        assert {t["id"] for t in data} == {"motor", "valve", "analog_input"}

    def test_template_shape_includes_questionnaire_and_naming_styles(self) -> None:
        response = client.get("/api/udt/templates")

        motor = next(t for t in response.json() if t["id"] == "motor")
        assert motor["label"] == "Motor"
        assert motor["description"]
        assert len(motor["questionnaire"]) > 0
        for field in motor["questionnaire"]:
            assert set(field) == {"name", "type", "required", "default", "description"}
        assert set(motor["naming_styles"]) == {"camelCase", "PascalCase"}
        assert motor["default_naming_style"] == "camelCase"


class TestBuildUdt:
    def test_builds_each_template_with_typical_answers(self) -> None:
        for template_id, answers in TYPICAL_ANSWERS.items():
            response = client.post(
                "/api/udt/build",
                json={"template_id": template_id, "answers": answers},
            )

            assert response.status_code == 200, response.text
            data = response.json()
            assert "udt" in data
            assert data["udt"]["tagType"] == "UdtType"
            assert data["filename"] == f"{data['udt']['name']}.json"

    def test_motor_build_response_is_wire_format_camel_case(self) -> None:
        response = client.post(
            "/api/udt/build",
            json={"template_id": "motor", "answers": TYPICAL_ANSWERS["motor"]},
        )

        data = response.json()
        assert data["udt"]["name"] == "Motor"
        assert data["filename"] == "Motor.json"
        member_names = [tag["name"] for tag in data["udt"]["tags"]]
        assert member_names == ["running", "start", "speed", "fault"]
        # Wire format uses camelCase keys, not snake_case.
        speed = next(tag for tag in data["udt"]["tags"] if tag["name"] == "speed")
        assert "engUnit" in speed
        assert "eng_unit" not in speed

    def test_pascal_case_naming_style_applied(self) -> None:
        response = client.post(
            "/api/udt/build",
            json={
                "template_id": "motor",
                "answers": TYPICAL_ANSWERS["motor"],
                "naming_style": "PascalCase",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["udt"]["name"] == "Motor"
        member_names = [tag["name"] for tag in data["udt"]["tags"]]
        assert member_names == ["Running", "Start", "Speed", "Fault"]

    def test_missing_required_answer_returns_422(self) -> None:
        response = client.post(
            "/api/udt/build",
            json={"template_id": "motor", "answers": {}},
        )

        assert response.status_code == 422
        assert "device_path" in response.json()["detail"]

    def test_bad_naming_style_returns_422(self) -> None:
        response = client.post(
            "/api/udt/build",
            json={
                "template_id": "motor",
                "answers": TYPICAL_ANSWERS["motor"],
                "naming_style": "snake_case",
            },
        )

        assert response.status_code == 422
        assert "naming_style" in response.json()["detail"]

    def test_wrong_type_answer_returns_422(self) -> None:
        response = client.post(
            "/api/udt/build",
            json={
                "template_id": "motor",
                "answers": {**TYPICAL_ANSWERS["motor"], "has_speed_feedback": "yes"},
            },
        )

        assert response.status_code == 422
        assert "must be a boolean" in response.json()["detail"]

    def test_unknown_template_returns_404(self) -> None:
        response = client.post(
            "/api/udt/build",
            json={"template_id": "not_a_real_template", "answers": {}},
        )

        assert response.status_code == 404
        assert "Unknown template" in response.json()["detail"]

    def test_no_endpoint_writes_to_disk(self, tmp_path, monkeypatch) -> None:
        """Sanity check: building a UDT never touches the filesystem outside templates/."""
        monkeypatch.chdir(tmp_path)
        response = client.post(
            "/api/udt/build",
            json={"template_id": "valve", "answers": TYPICAL_ANSWERS["valve"]},
        )

        assert response.status_code == 200
        assert list(tmp_path.iterdir()) == []


SIMPLE_COMPOSITION = {
    "type_name": "ConveyorMotor",
    "description": "A conveyor motor.",
    "naming_style": "camelCase",
    "parameters": [
        {"name": "DevicePath", "data_type": "String", "default_value": ""},
        {"name": "OpcServer", "data_type": "String", "default_value": "Ignition OPC UA Server"},
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
                    "alarms": [
                        {"name": "HiHi", "setpoint": 1400, "deadband": 25, "mode": "AboveValue"}
                    ],
                }
            ],
        }
    ],
}


class TestComposeUdt:
    def test_compose_returns_200_with_udt_filename_and_findings(self) -> None:
        response = client.post("/api/udt/compose", json=SIMPLE_COMPOSITION)

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["udt"]["name"] == "ConveyorMotor"
        assert data["udt"]["tagType"] == "UdtType"
        assert data["filename"] == "ConveyorMotor_udt.json"
        assert isinstance(data["findings"], list)
        for finding in data["findings"]:
            assert set(finding) == {
                "rule_id",
                "severity",
                "location",
                "message",
                "recommendation",
            }

    def test_isa_default_priority_is_filled_in_response(self) -> None:
        response = client.post("/api/udt/compose", json=SIMPLE_COMPOSITION)

        speed = response.json()["udt"]["tags"][0]["tags"][0]
        assert speed["alarms"][0]["priority"] == "High"

    def test_lint_dirty_composition_still_composes(self) -> None:
        """A UDT with lint findings (e.g. missing documentation) still gets a 200 + udt."""
        body = {
            "type_name": "Widget",
            "members": [
                {
                    "kind": "tag",
                    "name": "value",
                    "value_source": "memory",
                    "data_type": "Boolean",
                    "value": True,
                }
            ],
        }
        response = client.post("/api/udt/compose", json=body)

        assert response.status_code == 200
        assert response.json()["udt"]["name"] == "Widget"
        assert len(response.json()["findings"]) > 0

    def test_structural_error_returns_422(self) -> None:
        body = {**SIMPLE_COMPOSITION, "type_name": "bad type name"}
        response = client.post("/api/udt/compose", json=body)

        assert response.status_code == 422
        assert "not valid PascalCase" in response.json()["detail"]

    def test_all_structural_errors_joined_in_422_detail(self) -> None:
        body = {
            "type_name": "bad type name",
            "naming_style": "kebab-case",
            "members": [
                {"kind": "tag", "name": "a", "value_source": "memory", "data_type": "Bogus"},
                {"kind": "folder", "name": "f", "alarms": [{"name": "HiHi"}], "members": []},
            ],
        }
        response = client.post("/api/udt/compose", json=body)

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert "not valid PascalCase" in detail
        assert "unknown naming_style" in detail
        assert "unknown data type" in detail
        assert "a folder cannot have alarms" in detail

    def test_malformed_body_missing_type_name_returns_422(self) -> None:
        response = client.post("/api/udt/compose", json={"members": []})

        assert response.status_code == 422

    def test_malformed_body_bad_member_kind_returns_422(self) -> None:
        body = {
            "type_name": "Widget",
            "members": [{"kind": "not_a_real_kind", "name": "x"}],
        }
        response = client.post("/api/udt/compose", json=body)

        assert response.status_code == 422

    def test_malformed_body_not_json_object_returns_422(self) -> None:
        response = client.post("/api/udt/compose", json=["not", "an", "object"])

        assert response.status_code == 422


class TestGetPresets:
    def test_returns_three_presets(self) -> None:
        response = client.get("/api/udt/presets")

        assert response.status_code == 200
        data = response.json()
        assert {p["id"] for p in data} == {"motor", "valve", "analog_input"}

    def test_preset_shape(self) -> None:
        response = client.get("/api/udt/presets")

        motor = next(p for p in response.json() if p["id"] == "motor")
        assert motor["label"] == "Motor"
        assert motor["description"]
        assert motor["composition"]["type_name"] == "Motor"
        assert len(motor["composition"]["members"]) > 0

    def test_every_preset_composes_cleanly(self) -> None:
        """Every preset's composition must itself pass compose()'s structural validation."""
        presets = client.get("/api/udt/presets").json()
        for preset in presets:
            response = client.post("/api/udt/compose", json=preset["composition"])
            assert response.status_code == 200, (preset["id"], response.text)
            assert response.json()["udt"]["name"] == preset["composition"]["type_name"]

    def test_motor_preset_matches_builder_output_in_structure(self) -> None:
        """
        Preset-parity check at the API layer: running the motor preset's
        composition through /compose must reproduce the same member names/
        nesting and alarms (with ISA priorities) as /build with the
        equivalent typical answers.
        """
        preset = next(p for p in client.get("/api/udt/presets").json() if p["id"] == "motor")
        composed = client.post("/api/udt/compose", json=preset["composition"]).json()["udt"]
        built = client.post(
            "/api/udt/build",
            json={"template_id": "motor", "answers": TYPICAL_ANSWERS["motor"]},
        ).json()["udt"]

        composed_names = [t["name"] for t in composed["tags"]]
        built_names = [t["name"] for t in built["tags"]]
        assert composed_names == built_names

        composed_speed = next(t for t in composed["tags"] if t["name"] == "speed")
        built_speed = next(t for t in built["tags"] if t["name"] == "speed")
        assert [a["name"] for a in composed_speed["alarms"]] == [
            a["name"] for a in built_speed["alarms"]
        ]
        assert [a["priority"] for a in composed_speed["alarms"]] == [
            a["priority"] for a in built_speed["alarms"]
        ]
