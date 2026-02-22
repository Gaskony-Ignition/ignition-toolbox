"""
Tests for playbook management API endpoints.

Tests list, get, create, and delete operations.
Uses direct function import + patch pattern (same as test_health.py / test_executions.py).
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_metadata_store():
    """Return a mock metadata store that supplies default (empty) metadata."""
    meta = MagicMock()
    meta.revision = 0
    meta.verified = False
    meta.enabled = True
    meta.last_modified = None
    meta.verified_at = None
    meta.origin = "built-in"
    meta.duplicated_from = None
    meta.created_at = None

    store = MagicMock()
    store.get_metadata.return_value = meta
    store.update_metadata.return_value = None
    store.increment_revision.return_value = None
    return store


class TestListPlaybooks:
    def test_list_playbooks_returns_list_when_no_dirs_exist(self, mock_metadata_store):
        """GET /api/playbooks returns an empty list when no playbook dirs exist."""
        from ignition_toolkit.api.routers.playbook_crud import list_playbooks

        # Both dirs are non-existent tmp paths so rglob yields nothing
        nonexistent = Path("/tmp/does_not_exist_playbooks_xyz")

        with patch(
            "ignition_toolkit.api.routers.playbook_crud.get_metadata_store",
            return_value=mock_metadata_store,
        ), patch(
            "ignition_toolkit.api.routers.playbook_crud.get_all_playbook_dirs",
            return_value=[nonexistent],
        ), patch(
            "ignition_toolkit.api.routers.playbook_crud.get_builtin_playbooks_dir",
            return_value=nonexistent,
        ), patch(
            "ignition_toolkit.api.routers.playbook_crud.get_user_playbooks_dir",
            return_value=nonexistent,
        ):
            result = asyncio.run(list_playbooks())

        assert isinstance(result, list)

    def test_list_playbooks_returns_list_with_valid_yaml(self, tmp_path, mock_metadata_store):
        """GET /api/playbooks returns a list containing entries for valid YAML files."""
        from ignition_toolkit.api.routers.playbook_crud import list_playbooks

        # Write a minimal playbook
        playbook_yaml = """\
name: Test Playbook
version: "1.0"
description: A test playbook
steps:
  - id: step1
    name: Log message
    type: utility.log
    parameters:
      message: "hello"
      level: info
"""
        (tmp_path / "test_playbook.yaml").write_text(playbook_yaml, encoding="utf-8")

        with patch(
            "ignition_toolkit.api.routers.playbook_crud.get_metadata_store",
            return_value=mock_metadata_store,
        ), patch(
            "ignition_toolkit.api.routers.playbook_crud.get_all_playbook_dirs",
            return_value=[tmp_path],
        ), patch(
            "ignition_toolkit.api.routers.playbook_crud.get_builtin_playbooks_dir",
            return_value=tmp_path,
        ), patch(
            "ignition_toolkit.api.routers.playbook_crud.get_user_playbooks_dir",
            return_value=tmp_path,
        ):
            result = asyncio.run(list_playbooks())

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].name == "Test Playbook"


class TestGetPlaybook:
    def test_get_playbook_raises_404_for_unknown_name(self):
        """GET /api/playbooks/{path} returns 404 for an unknown playbook path."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.playbook_crud import get_playbook

        nonexistent = Path("/tmp/does_not_exist_xyz")

        with patch(
            "ignition_toolkit.api.routers.playbook_crud.get_all_playbook_dirs",
            return_value=[nonexistent],
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_playbook("nonexistent_playbook.yaml"))

        assert exc_info.value.status_code == 404

    def test_get_playbook_returns_info_for_known_playbook(self, tmp_path, mock_metadata_store):
        """GET /api/playbooks/{path} returns playbook info for an existing playbook."""
        from ignition_toolkit.api.routers.playbook_crud import get_playbook

        playbook_yaml = """\
name: My Playbook
version: "2.0"
description: Description here
steps:
  - id: s1
    name: Step One
    type: utility.log
    parameters:
      message: "hi"
      level: info
"""
        pb_file = tmp_path / "my_playbook.yaml"
        pb_file.write_text(playbook_yaml, encoding="utf-8")

        with patch(
            "ignition_toolkit.api.routers.playbook_crud.get_metadata_store",
            return_value=mock_metadata_store,
        ), patch(
            "ignition_toolkit.api.routers.playbook_crud.get_all_playbook_dirs",
            return_value=[tmp_path],
        ), patch(
            "ignition_toolkit.api.routers.playbook_crud.get_builtin_playbooks_dir",
            return_value=tmp_path,
        ), patch(
            "ignition_toolkit.api.routers.playbook_crud.get_user_playbooks_dir",
            return_value=tmp_path,
        ):
            result = asyncio.run(get_playbook("my_playbook.yaml"))

        assert result.name == "My Playbook"
        assert result.version == "2.0"
        assert result.step_count == 1


class TestCreatePlaybook:
    def test_create_playbook_with_invalid_domain_raises_400(self, tmp_path):
        """POST /api/playbooks/create returns 400 for an invalid domain."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.playbook_lifecycle import (
            import_playbook,
            PlaybookImportRequest,
        )

        request = PlaybookImportRequest(
            name="Test",
            domain="invalid_domain",
            yaml_content="name: Test\nversion: '1.0'\ndescription: x\nsteps: []\n",
        )

        with patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_user_playbooks_dir",
            return_value=tmp_path,
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_metadata_store",
            return_value=MagicMock(),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(import_playbook(request))

        assert exc_info.value.status_code == 400

    def test_create_playbook_succeeds_with_valid_request(self, tmp_path):
        """POST /api/playbooks/create creates a new playbook file."""
        from ignition_toolkit.api.routers.playbook_lifecycle import (
            import_playbook,
            PlaybookImportRequest,
        )

        playbook_yaml = """\
name: New Playbook
version: "1.0"
description: Created via API
steps:
  - id: s1
    name: Log
    type: utility.log
    parameters:
      message: "hello"
      level: info
"""

        mock_store = MagicMock()
        mock_meta = MagicMock()
        mock_store.get_metadata.return_value = mock_meta

        request = PlaybookImportRequest(
            name="New Playbook",
            domain="gateway",
            yaml_content=playbook_yaml,
        )

        with patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_user_playbooks_dir",
            return_value=tmp_path,
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_metadata_store",
            return_value=mock_store,
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_all_playbook_dirs",
            return_value=[tmp_path],
        ):
            result = asyncio.run(import_playbook(request))

        assert result["status"] == "success"
        assert "path" in result


class TestDeletePlaybook:
    def test_delete_playbook_raises_404_for_unknown_path(self):
        """DELETE /api/playbooks/{path} returns 404 for a nonexistent playbook."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.playbook_lifecycle import delete_playbook

        nonexistent = Path("/tmp/does_not_exist_xyz")

        with patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_all_playbook_dirs",
            return_value=[nonexistent],
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(delete_playbook("nonexistent_playbook.yaml"))

        assert exc_info.value.status_code == 404

    def test_delete_playbook_removes_file(self, tmp_path):
        """DELETE /api/playbooks/{path} deletes an existing playbook file."""
        from ignition_toolkit.api.routers.playbook_lifecycle import delete_playbook

        pb_file = tmp_path / "to_delete.yaml"
        pb_file.write_text("name: Temp\nversion: '1.0'\ndescription: x\nsteps: []\n")

        mock_store = MagicMock()
        mock_store.get_metadata.return_value = MagicMock()
        mock_store._metadata = {}

        with patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_all_playbook_dirs",
            return_value=[tmp_path],
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_metadata_store",
            return_value=mock_store,
        ):
            result = asyncio.run(delete_playbook("to_delete.yaml"))

        assert result["status"] == "success"
        assert not pb_file.exists()


class TestPlaybookMetadataUpdateRequest:
    def test_metadata_request_rejects_dangerous_name(self):
        """PlaybookMetadataUpdateRequest rejects names with dangerous characters."""
        from pydantic import ValidationError
        from ignition_toolkit.api.routers.playbook_crud import PlaybookMetadataUpdateRequest

        with pytest.raises(ValidationError):
            PlaybookMetadataUpdateRequest(
                playbook_path="some/path.yaml",
                name="<script>alert('xss')</script>",
            )

    def test_metadata_request_accepts_valid_name(self):
        """PlaybookMetadataUpdateRequest accepts a clean playbook name."""
        from ignition_toolkit.api.routers.playbook_crud import PlaybookMetadataUpdateRequest

        req = PlaybookMetadataUpdateRequest(
            playbook_path="gateway/test.yaml",
            name="My Test Playbook",
            description="A description",
        )
        assert req.name == "My Test Playbook"
        assert req.description == "A description"
