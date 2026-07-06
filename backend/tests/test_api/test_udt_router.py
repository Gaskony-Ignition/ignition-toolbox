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
