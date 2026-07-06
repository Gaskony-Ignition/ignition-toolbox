"""
Tests for the Perspective audit API router (``/api/audit``).

Uses a standalone FastAPI app with just the audit router mounted (same
pattern as test_stackbuilder/test_api_endpoints.py) since the router has no
dependency on app.py's startup lifecycle (DB, credential vault, etc.) — it
only needs the audit engine and rule pack, which are pure in-memory.
"""

import io
import zipfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ignition_toolkit.api.routers.audit import MAX_UPLOAD_BYTES, router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

FIXTURES_DIR = Path(__file__).parent.parent / "test_audit" / "fixtures" / "mini_project"


def _zip_bytes_of(project_dir: Path) -> bytes:
    """Zip a fixture project directory in-memory (never touches disk)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for file_path in project_dir.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(project_dir).as_posix())
    return buffer.getvalue()


@pytest.fixture
def mini_project_zip() -> bytes:
    return _zip_bytes_of(FIXTURES_DIR)


class TestAuditPerspectiveEndpoint:
    def test_valid_zip_returns_structured_report(self, mini_project_zip: bytes) -> None:
        response = client.post(
            "/api/audit/perspective",
            files={"file": ("mini_project.zip", mini_project_zip, "application/zip")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["project_name"] == "mini_project"
        assert data["inventory"]["component_count"] == 5
        assert "aggregated_findings" in data
        assert "findings" in data
        assert "summary" in data
        assert set(data["summary"]["by_severity"]) == {"critical", "high", "medium", "info"}

    def test_aggregated_count_reconciles_with_full_findings_list(
        self, mini_project_zip: bytes
    ) -> None:
        response = client.post(
            "/api/audit/perspective",
            files={"file": ("mini_project.zip", mini_project_zip, "application/zip")},
        )

        data = response.json()
        assert sum(row["count"] for row in data["aggregated_findings"]) == len(data["findings"])

    def test_non_zip_upload_is_rejected_with_400(self) -> None:
        response = client.post(
            "/api/audit/perspective",
            files={"file": ("project.txt", b"not a zip file", "text/plain")},
        )

        assert response.status_code == 400
        assert "not a valid zip" in response.json()["detail"]

    def test_empty_upload_is_rejected_with_400(self) -> None:
        response = client.post(
            "/api/audit/perspective",
            files={"file": ("empty.zip", b"", "application/zip")},
        )

        assert response.status_code == 400

    def test_oversize_upload_is_rejected_with_413(self) -> None:
        oversized = b"0" * (MAX_UPLOAD_BYTES + 1)

        response = client.post(
            "/api/audit/perspective",
            files={"file": ("huge.zip", oversized, "application/zip")},
        )

        assert response.status_code == 413

    def test_missing_file_is_rejected_with_422(self) -> None:
        """FastAPI's own validation for a required upload field."""
        response = client.post("/api/audit/perspective")

        assert response.status_code == 422


class TestAuditPerspectiveMarkdownEndpoint:
    def test_returns_downloadable_markdown(self, mini_project_zip: bytes) -> None:
        response = client.post(
            "/api/audit/perspective/markdown",
            files={"file": ("mini_project.zip", mini_project_zip, "application/zip")},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/markdown")
        assert "attachment" in response.headers["content-disposition"]
        assert "# Perspective Project Audit Report — mini_project" in response.text

    def test_non_zip_upload_is_rejected_with_400(self) -> None:
        response = client.post(
            "/api/audit/perspective/markdown",
            files={"file": ("project.txt", b"not a zip file", "text/plain")},
        )

        assert response.status_code == 400
