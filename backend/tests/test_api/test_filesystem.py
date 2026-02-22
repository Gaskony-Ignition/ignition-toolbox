"""
Tests for filesystem API endpoints.

Tests browse_directory and list_module_files endpoints.
Uses real tmp_path directories and mocks ALLOWED_BASE_PATHS.
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_allowed_paths(paths: list[Path]):
    """Patch the module-level ALLOWED_BASE_PATHS list in the filesystem router."""
    return patch(
        "ignition_toolkit.api.routers.filesystem.ALLOWED_BASE_PATHS",
        paths,
    )


# ---------------------------------------------------------------------------
# browse_directory
# ---------------------------------------------------------------------------


class TestBrowseDirectory:
    def test_browse_valid_directory_returns_contents(self, tmp_path):
        """Browsing an allowed directory returns its subdirectories."""
        from ignition_toolkit.api.routers.filesystem import browse_directory

        # Create some subdirectories inside tmp_path
        (tmp_path / "alpha").mkdir()
        (tmp_path / "beta").mkdir()

        with _patch_allowed_paths([tmp_path]):
            result = asyncio.run(browse_directory(str(tmp_path)))

        assert str(result.current_path) == str(tmp_path.resolve())
        names = [e.name for e in result.entries]
        assert "alpha" in names
        assert "beta" in names

    def test_browse_entries_sorted_alphabetically(self, tmp_path):
        """Directory entries are sorted alphabetically by name."""
        from ignition_toolkit.api.routers.filesystem import browse_directory

        (tmp_path / "zebra").mkdir()
        (tmp_path / "apple").mkdir()
        (tmp_path / "mango").mkdir()

        with _patch_allowed_paths([tmp_path]):
            result = asyncio.run(browse_directory(str(tmp_path)))

        names = [e.name for e in result.entries]
        assert names == sorted(names, key=lambda n: n.lower())

    def test_browse_files_not_included_in_entries(self, tmp_path):
        """Regular files do not appear in directory entries (directories only)."""
        from ignition_toolkit.api.routers.filesystem import browse_directory

        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "subdir").mkdir()

        with _patch_allowed_paths([tmp_path]):
            result = asyncio.run(browse_directory(str(tmp_path)))

        names = [e.name for e in result.entries]
        assert "file.txt" not in names
        assert "subdir" in names

    def test_browse_nonexistent_path_raises_404(self, tmp_path):
        """Browsing a directory that does not exist raises 404."""
        from ignition_toolkit.api.routers.filesystem import browse_directory

        nonexistent = tmp_path / "does_not_exist"

        with _patch_allowed_paths([tmp_path]):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(browse_directory(str(nonexistent)))

        assert exc_info.value.status_code == 404

    def test_browse_file_path_raises_400(self, tmp_path):
        """Browsing a file path (not a directory) raises 400."""
        from ignition_toolkit.api.routers.filesystem import browse_directory

        file_path = tmp_path / "just_a_file.txt"
        file_path.write_text("content")

        with _patch_allowed_paths([tmp_path]):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(browse_directory(str(file_path)))

        assert exc_info.value.status_code == 400

    def test_browse_path_outside_allowed_raises_403(self, tmp_path):
        """Browsing a path that is outside allowed directories raises 403."""
        from ignition_toolkit.api.routers.filesystem import browse_directory

        allowed = tmp_path / "allowed"
        allowed.mkdir()

        outside = tmp_path / "outside"
        outside.mkdir()

        with _patch_allowed_paths([allowed]):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(browse_directory(str(outside)))

        assert exc_info.value.status_code == 403

    def test_browse_parent_path_included_when_allowed(self, tmp_path):
        """parent_path is set when the parent directory is also within allowed paths."""
        from ignition_toolkit.api.routers.filesystem import browse_directory

        child = tmp_path / "child"
        child.mkdir()

        with _patch_allowed_paths([tmp_path]):
            result = asyncio.run(browse_directory(str(child)))

        assert result.parent_path is not None
        assert str(tmp_path.resolve()) in result.parent_path

    def test_browse_nested_subdirectory_is_accessible(self, tmp_path):
        """A subdirectory within the allowed base path is marked as accessible."""
        from ignition_toolkit.api.routers.filesystem import browse_directory

        inner = tmp_path / "inner"
        inner.mkdir()

        with _patch_allowed_paths([tmp_path]):
            result = asyncio.run(browse_directory(str(tmp_path)))

        entry = next((e for e in result.entries if e.name == "inner"), None)
        assert entry is not None
        assert entry.is_accessible is True
        assert entry.is_directory is True

    def test_browse_empty_directory_returns_empty_entries(self, tmp_path):
        """Browsing an empty directory returns an empty entries list."""
        from ignition_toolkit.api.routers.filesystem import browse_directory

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with _patch_allowed_paths([tmp_path]):
            result = asyncio.run(browse_directory(str(empty_dir)))

        assert result.entries == []


# ---------------------------------------------------------------------------
# is_path_allowed  (unit test for the security helper)
# ---------------------------------------------------------------------------


class TestIsPathAllowed:
    def test_path_within_allowed_base_returns_true(self, tmp_path):
        """A path inside the allowed base directory returns True."""
        from ignition_toolkit.api.routers.filesystem import is_path_allowed

        subdir = tmp_path / "sub"
        subdir.mkdir()

        with _patch_allowed_paths([tmp_path]):
            assert is_path_allowed(subdir) is True

    def test_path_outside_allowed_base_returns_false(self, tmp_path):
        """A path outside the allowed base directory returns False."""
        from ignition_toolkit.api.routers.filesystem import is_path_allowed

        allowed = tmp_path / "allowed"
        allowed.mkdir()

        outside = tmp_path / "outside"
        outside.mkdir()

        with _patch_allowed_paths([allowed]):
            assert is_path_allowed(outside) is False

    def test_traversal_path_rejected(self, tmp_path):
        """A path containing .. that resolves outside allowed dirs returns False."""
        from ignition_toolkit.api.routers.filesystem import is_path_allowed

        allowed = tmp_path / "safe"
        allowed.mkdir()

        # This will resolve to tmp_path itself (outside allowed)
        traversal = allowed / ".."

        with _patch_allowed_paths([allowed]):
            # tmp_path itself is not in allowed; only the "safe" subdir is
            result = is_path_allowed(traversal)
            # It resolves to tmp_path, which is the *parent* of allowed — not inside it
            assert result is False

    def test_allowed_base_path_itself_is_allowed(self, tmp_path):
        """The allowed base directory itself is allowed."""
        from ignition_toolkit.api.routers.filesystem import is_path_allowed

        with _patch_allowed_paths([tmp_path]):
            assert is_path_allowed(tmp_path) is True


# ---------------------------------------------------------------------------
# list_module_files
# ---------------------------------------------------------------------------


class TestListModuleFiles:
    def test_list_modules_returns_empty_when_no_modl_files(self, tmp_path):
        """list_module_files returns empty list when no .modl files are present."""
        from ignition_toolkit.api.routers.filesystem import list_module_files

        with _patch_allowed_paths([tmp_path]), patch(
            "ignition_toolkit.api.routers.filesystem.get_data_dir",
            return_value=tmp_path,
        ):
            result = asyncio.run(list_module_files(str(tmp_path)))

        assert result.files == []

    def test_list_modules_finds_modl_files(self, tmp_path):
        """list_module_files detects .modl files in the directory."""
        from ignition_toolkit.api.routers.filesystem import list_module_files

        modl_file = tmp_path / "my_module.modl"
        modl_file.write_bytes(b"fake modl content")

        mock_metadata = MagicMock()
        mock_metadata.name = "My Module"
        mock_metadata.version = "1.0.0"
        mock_metadata.id = "com.example.module"

        # parse_module_metadata is imported lazily inside the function
        with _patch_allowed_paths([tmp_path]), patch(
            "ignition_toolkit.api.routers.filesystem.get_data_dir",
            return_value=tmp_path,
        ), patch(
            "ignition_toolkit.modules.parse_module_metadata",
            return_value=mock_metadata,
        ):
            result = asyncio.run(list_module_files(str(tmp_path)))

        assert len(result.files) == 1
        assert result.files[0].filename == "my_module.modl"
        assert result.files[0].is_unsigned is False
        assert result.files[0].module_name == "My Module"

    def test_list_modules_detects_unsigned_modl(self, tmp_path):
        """list_module_files marks .unsigned.modl files correctly."""
        from ignition_toolkit.api.routers.filesystem import list_module_files

        unsigned_file = tmp_path / "my_module.unsigned.modl"
        unsigned_file.write_bytes(b"fake unsigned content")

        # parse_module_metadata is imported lazily inside the function
        with _patch_allowed_paths([tmp_path]), patch(
            "ignition_toolkit.api.routers.filesystem.get_data_dir",
            return_value=tmp_path,
        ), patch(
            "ignition_toolkit.modules.parse_module_metadata",
            return_value=None,
        ):
            result = asyncio.run(list_module_files(str(tmp_path)))

        assert len(result.files) == 1
        assert result.files[0].is_unsigned is True

    def test_list_modules_path_outside_allowed_raises_403(self, tmp_path):
        """list_module_files raises 403 for paths outside allowed directories."""
        from ignition_toolkit.api.routers.filesystem import list_module_files

        allowed = tmp_path / "allowed"
        allowed.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        with _patch_allowed_paths([allowed]), patch(
            "ignition_toolkit.api.routers.filesystem.get_data_dir",
            return_value=allowed,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(list_module_files(str(outside)))

        assert exc_info.value.status_code == 403

    def test_list_modules_nonexistent_path_raises_404(self, tmp_path):
        """list_module_files raises 404 for a directory that doesn't exist."""
        from ignition_toolkit.api.routers.filesystem import list_module_files

        nonexistent = tmp_path / "no_such_dir"

        with _patch_allowed_paths([tmp_path]), patch(
            "ignition_toolkit.api.routers.filesystem.get_data_dir",
            return_value=tmp_path,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(list_module_files(str(nonexistent)))

        assert exc_info.value.status_code == 404

    def test_list_modules_ignores_non_modl_files(self, tmp_path):
        """list_module_files ignores files that are not .modl or .unsigned.modl."""
        from ignition_toolkit.api.routers.filesystem import list_module_files

        # Create non-modl files
        (tmp_path / "readme.txt").write_text("ignore me")
        (tmp_path / "data.yaml").write_text("ignore me")
        (tmp_path / "script.py").write_text("ignore me")

        with _patch_allowed_paths([tmp_path]), patch(
            "ignition_toolkit.api.routers.filesystem.get_data_dir",
            return_value=tmp_path,
        ):
            result = asyncio.run(list_module_files(str(tmp_path)))

        assert result.files == []

    def test_list_modules_uses_data_dir_when_no_path(self, tmp_path):
        """list_module_files defaults to get_data_dir() when path is None."""
        from ignition_toolkit.api.routers.filesystem import list_module_files

        with _patch_allowed_paths([tmp_path]), patch(
            "ignition_toolkit.api.routers.filesystem.get_data_dir",
            return_value=tmp_path,
        ):
            result = asyncio.run(list_module_files(None))

        assert result.path == str(tmp_path)
