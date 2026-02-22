"""
Tests for playbook lifecycle API endpoints.

Tests delete, duplicate, import, export, and create operations.
Uses direct function calls with asyncio.run() and mocking.
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_PLAYBOOK_YAML = """\
name: Test Playbook
version: "1.0"
description: A test playbook
domain: gateway
steps:
  - id: step1
    name: Log a message
    type: utility.log
    parameters:
      message: "hello"
      level: info
"""

INVALID_YAML = "{{ not: valid: yaml: :"


def _make_metadata_store():
    """Return a MagicMock that behaves like the metadata store."""
    store = MagicMock()
    store.get_metadata.return_value = MagicMock(
        revision=0,
        verified=False,
        verified_at=None,
        verified_by=None,
        origin=None,
        created_at=None,
    )
    return store


# ---------------------------------------------------------------------------
# delete_playbook
# ---------------------------------------------------------------------------


class TestDeletePlaybook:
    def test_delete_nonexistent_raises_404(self):
        """DELETE a playbook that does not exist → 404."""
        from ignition_toolkit.api.routers.playbook_lifecycle import delete_playbook

        # validate_playbook_path raises 404 when file not found
        with patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.validate_playbook_path",
            side_effect=HTTPException(status_code=404, detail="Playbook file not found"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(delete_playbook("gateway/nonexistent.yaml"))

        assert exc_info.value.status_code == 404

    def test_delete_existing_playbook(self, tmp_path):
        """DELETE an existing playbook succeeds and returns success status."""
        from ignition_toolkit.api.routers.playbook_lifecycle import delete_playbook

        # Create a real file so os.remove works
        playbook_file = tmp_path / "test.yaml"
        playbook_file.write_text(VALID_PLAYBOOK_YAML)

        mock_store = _make_metadata_store()
        mock_store._metadata = {}

        with patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.validate_playbook_path",
            return_value=playbook_file,
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_relative_playbook_path",
            return_value="gateway/test.yaml",
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_metadata_store",
            return_value=mock_store,
        ):
            result = asyncio.run(delete_playbook("gateway/test.yaml"))

        assert result["status"] == "success"
        assert not playbook_file.exists()


# ---------------------------------------------------------------------------
# duplicate_playbook
# ---------------------------------------------------------------------------


class TestDuplicatePlaybook:
    def test_duplicate_nonexistent_raises_404(self):
        """Duplicating a playbook that does not exist → 404."""
        from ignition_toolkit.api.routers.playbook_lifecycle import duplicate_playbook

        with patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.validate_playbook_path",
            side_effect=HTTPException(status_code=404, detail="Playbook file not found"),
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_metadata_store",
            return_value=_make_metadata_store(),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(duplicate_playbook("gateway/nonexistent.yaml"))

        assert exc_info.value.status_code == 404

    def test_duplicate_creates_copy(self, tmp_path):
        """Duplicating an existing playbook creates a new file."""
        from ignition_toolkit.api.routers.playbook_lifecycle import duplicate_playbook
        from ignition_toolkit.playbook.loader import PlaybookLoader

        # Set up source file
        source_dir = tmp_path / "gateway"
        source_dir.mkdir(parents=True)
        source_file = source_dir / "test_playbook.yaml"
        source_file.write_text(VALID_PLAYBOOK_YAML)

        user_dir = tmp_path / "user_playbooks"
        user_dir.mkdir(parents=True)
        user_gateway = user_dir / "gateway"
        user_gateway.mkdir(parents=True)

        mock_store = _make_metadata_store()

        with patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.validate_playbook_path",
            return_value=source_file,
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle._get_relative_to_any_playbook_dir",
            return_value="gateway/test_playbook.yaml",
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_user_playbooks_dir",
            return_value=user_dir,
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_metadata_store",
            return_value=mock_store,
        ):
            result = asyncio.run(duplicate_playbook("gateway/test_playbook.yaml"))

        assert result["status"] == "success"
        assert "new_path" in result
        assert "playbook" in result

    def test_duplicate_with_custom_name(self, tmp_path):
        """Duplicating with a custom name uses that name for the copy."""
        from ignition_toolkit.api.routers.playbook_lifecycle import duplicate_playbook

        source_dir = tmp_path / "gateway"
        source_dir.mkdir(parents=True)
        source_file = source_dir / "original.yaml"
        source_file.write_text(VALID_PLAYBOOK_YAML)

        user_dir = tmp_path / "user"
        user_dir.mkdir(parents=True)
        user_gateway = user_dir / "gateway"
        user_gateway.mkdir(parents=True)

        mock_store = _make_metadata_store()

        def _relative_side_effect(path: Path) -> str:
            # Return the relative path based on what file is being asked about
            name = Path(path).name
            return f"gateway/{name}"

        with patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.validate_playbook_path",
            return_value=source_file,
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle._get_relative_to_any_playbook_dir",
            side_effect=_relative_side_effect,
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_user_playbooks_dir",
            return_value=user_dir,
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_metadata_store",
            return_value=mock_store,
        ):
            result = asyncio.run(duplicate_playbook("gateway/original.yaml", new_name="my_copy"))

        assert result["status"] == "success"
        assert "my_copy" in result["new_path"]


# ---------------------------------------------------------------------------
# export_playbook
# ---------------------------------------------------------------------------


class TestExportPlaybook:
    def test_export_nonexistent_raises_404(self):
        """Exporting a playbook that does not exist → 404."""
        from ignition_toolkit.api.routers.playbook_lifecycle import export_playbook

        with patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.validate_playbook_path",
            side_effect=HTTPException(status_code=404, detail="Playbook file not found"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(export_playbook("gateway/missing.yaml"))

        assert exc_info.value.status_code == 404

    def test_export_returns_yaml_content(self, tmp_path):
        """Exporting an existing playbook returns YAML content and metadata."""
        from ignition_toolkit.api.routers.playbook_lifecycle import export_playbook

        playbook_file = tmp_path / "test_playbook.yaml"
        playbook_file.write_text(VALID_PLAYBOOK_YAML)

        mock_store = _make_metadata_store()

        with patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.validate_playbook_path",
            return_value=playbook_file,
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle._get_relative_to_any_playbook_dir",
            return_value="gateway/test_playbook.yaml",
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_metadata_store",
            return_value=mock_store,
        ):
            result = asyncio.run(export_playbook("gateway/test_playbook.yaml"))

        assert result.name == "Test Playbook"
        assert result.domain == "gateway"
        assert "steps:" in result.yaml_content
        assert result.metadata is not None


# ---------------------------------------------------------------------------
# import_playbook / create_playbook
# ---------------------------------------------------------------------------


class TestImportPlaybook:
    def test_import_invalid_domain_raises_400(self, tmp_path):
        """Importing with an invalid domain raises 400."""
        from ignition_toolkit.api.routers.playbook_lifecycle import import_playbook, PlaybookImportRequest

        user_dir = tmp_path / "user_playbooks"
        user_dir.mkdir()

        mock_store = _make_metadata_store()

        request = PlaybookImportRequest(
            name="bad_domain_playbook",
            domain="invalid_domain",
            yaml_content=VALID_PLAYBOOK_YAML,
        )

        with patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_metadata_store",
            return_value=mock_store,
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_user_playbooks_dir",
            return_value=user_dir,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(import_playbook(request))

        assert exc_info.value.status_code == 400
        assert "Invalid domain" in exc_info.value.detail

    def test_import_invalid_yaml_raises_400(self, tmp_path):
        """Importing malformed YAML raises 400."""
        from ignition_toolkit.api.routers.playbook_lifecycle import import_playbook, PlaybookImportRequest

        user_dir = tmp_path / "user_playbooks"
        user_dir.mkdir()

        mock_store = _make_metadata_store()

        request = PlaybookImportRequest(
            name="bad_yaml_playbook",
            domain="gateway",
            yaml_content=INVALID_YAML,
        )

        with patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_metadata_store",
            return_value=mock_store,
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_user_playbooks_dir",
            return_value=user_dir,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(import_playbook(request))

        assert exc_info.value.status_code == 400
        assert "Invalid YAML" in exc_info.value.detail

    def test_import_valid_playbook_succeeds(self, tmp_path):
        """Importing a valid playbook creates the file and returns success."""
        from ignition_toolkit.api.routers.playbook_lifecycle import import_playbook, PlaybookImportRequest

        user_dir = tmp_path / "user_playbooks"
        user_dir.mkdir()

        mock_store = _make_metadata_store()

        request = PlaybookImportRequest(
            name="My New Playbook",
            domain="gateway",
            yaml_content=VALID_PLAYBOOK_YAML,
        )

        with patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_metadata_store",
            return_value=mock_store,
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_user_playbooks_dir",
            return_value=user_dir,
        ):
            result = asyncio.run(import_playbook(request))

        assert result["status"] == "success"
        assert "playbook" in result
        # File should have been written to the user dir
        expected_file = user_dir / "gateway" / "my_new_playbook.yaml"
        assert expected_file.exists()

    def test_import_overwrite_false_renames_on_conflict(self, tmp_path):
        """When overwrite=False and name conflicts, a counter suffix is added."""
        from ignition_toolkit.api.routers.playbook_lifecycle import import_playbook, PlaybookImportRequest

        user_dir = tmp_path / "user_playbooks"
        gateway_dir = user_dir / "gateway"
        gateway_dir.mkdir(parents=True)

        # Pre-create the target file to trigger the conflict
        (gateway_dir / "my_playbook.yaml").write_text(VALID_PLAYBOOK_YAML)

        mock_store = _make_metadata_store()

        request = PlaybookImportRequest(
            name="my_playbook",
            domain="gateway",
            yaml_content=VALID_PLAYBOOK_YAML,
            overwrite=False,
        )

        with patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_metadata_store",
            return_value=mock_store,
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_user_playbooks_dir",
            return_value=user_dir,
        ):
            result = asyncio.run(import_playbook(request))

        assert result["status"] == "success"
        # Should have created my_playbook_1.yaml
        assert (gateway_dir / "my_playbook_1.yaml").exists()

    def test_create_playbook_delegates_to_import(self, tmp_path):
        """create_playbook is an alias for import_playbook and accepts same inputs."""
        from ignition_toolkit.api.routers.playbook_lifecycle import create_playbook, PlaybookImportRequest

        user_dir = tmp_path / "user_playbooks"
        user_dir.mkdir()

        mock_store = _make_metadata_store()

        request = PlaybookImportRequest(
            name="Created Playbook",
            domain="perspective",
            yaml_content=VALID_PLAYBOOK_YAML,
        )

        with patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_metadata_store",
            return_value=mock_store,
        ), patch(
            "ignition_toolkit.api.routers.playbook_lifecycle.get_user_playbooks_dir",
            return_value=user_dir,
        ):
            result = asyncio.run(create_playbook(request))

        assert result["status"] == "success"
        assert result["playbook"]["domain"] == "perspective"

    def test_import_pydantic_model_requires_name(self):
        """PlaybookImportRequest requires name field."""
        from ignition_toolkit.api.routers.playbook_lifecycle import PlaybookImportRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PlaybookImportRequest(domain="gateway", yaml_content=VALID_PLAYBOOK_YAML)

    def test_import_pydantic_model_requires_domain(self):
        """PlaybookImportRequest requires domain field."""
        from ignition_toolkit.api.routers.playbook_lifecycle import PlaybookImportRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PlaybookImportRequest(name="test", yaml_content=VALID_PLAYBOOK_YAML)
