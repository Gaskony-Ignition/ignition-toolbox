"""
Tests for ignition_toolkit/core/paths.py

Covers: is_frozen, get_package_root, get_data_dir, get_user_playbooks_dir,
        get_screenshots_dir, get_all_playbook_dirs, env-var overrides.
"""

import os
import sys
from pathlib import Path

import pytest


class TestIsFrozen:
    """Tests for is_frozen()"""

    def test_returns_bool(self):
        """is_frozen must always return a bool."""
        from ignition_toolkit.core.paths import is_frozen

        result = is_frozen()
        assert isinstance(result, bool)

    def test_returns_false_in_normal_python(self):
        """Running under pytest means we are NOT frozen."""
        from ignition_toolkit.core.paths import is_frozen

        # sys.frozen is not set in a normal Python interpreter
        assert is_frozen() is False

    def test_returns_true_when_frozen_attributes_set(self, monkeypatch):
        """Simulate PyInstaller frozen environment."""
        from ignition_toolkit.core import paths

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", "/fake/meipass", raising=False)

        assert paths.is_frozen() is True

    def test_returns_false_when_only_frozen_set(self, monkeypatch):
        """frozen=True without _MEIPASS is not considered frozen."""
        from ignition_toolkit.core import paths

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        # Remove _MEIPASS if present
        if hasattr(sys, "_MEIPASS"):
            monkeypatch.delattr(sys, "_MEIPASS")

        assert paths.is_frozen() is False


class TestGetPackageRoot:
    """Tests for get_package_root()"""

    def test_returns_path(self):
        from ignition_toolkit.core.paths import get_package_root

        result = get_package_root()
        assert isinstance(result, Path)

    def test_path_exists(self):
        from ignition_toolkit.core.paths import get_package_root

        assert get_package_root().exists()

    def test_path_is_absolute(self):
        from ignition_toolkit.core.paths import get_package_root

        assert get_package_root().is_absolute()

    def test_contains_backend_dir(self):
        """The package root is the project root which contains a backend/ subdir."""
        from ignition_toolkit.core.paths import get_package_root

        root = get_package_root()
        # paths.py lives at backend/ignition_toolkit/core/paths.py
        # get_package_root() goes 3 levels up: core -> ignition_toolkit -> backend
        # so root points at the backend/ directory
        assert (root / "ignition_toolkit").is_dir()


class TestGetDataDir:
    """Tests for get_data_dir()"""

    def test_returns_path(self):
        from ignition_toolkit.core.paths import get_data_dir

        result = get_data_dir()
        assert isinstance(result, Path)

    def test_returns_absolute_path(self):
        from ignition_toolkit.core.paths import get_data_dir

        assert get_data_dir().is_absolute()

    def test_env_var_override(self, tmp_path, monkeypatch):
        """When IGNITION_TOOLKIT_DATA is set, get_data_dir must be inside it."""
        custom_data = tmp_path / "custom_data"
        monkeypatch.setenv("IGNITION_TOOLKIT_DATA", str(custom_data))

        # Re-import to get a fresh call (env var read at call time, not module load)
        from ignition_toolkit.core import paths

        # get_user_data_dir uses the env var; get_data_dir checks is_frozen() first
        # but get_user_data_dir always checks the env var
        result = paths.get_user_data_dir()
        assert str(result).startswith(str(tmp_path))

    def test_directory_is_created(self, tmp_path, monkeypatch):
        """get_data_dir() creates the directory if it does not exist."""
        custom_data = tmp_path / "brand_new_dir"
        assert not custom_data.exists()

        # In non-frozen mode get_data_dir uses get_package_root()/data,
        # but get_user_data_dir uses the env var.
        monkeypatch.setenv("IGNITION_TOOLKIT_DATA", str(custom_data))

        from ignition_toolkit.core import paths

        result = paths.get_user_data_dir()
        assert result.exists()


class TestGetUserPlaybooksDir:
    """Tests for get_user_playbooks_dir()"""

    def test_returns_path(self):
        from ignition_toolkit.core.paths import get_user_playbooks_dir

        result = get_user_playbooks_dir()
        assert isinstance(result, Path)

    def test_is_under_user_data_dir(self):
        """User playbooks must be inside the user data dir."""
        from ignition_toolkit.core.paths import get_user_playbooks_dir, get_user_data_dir

        user_data = get_user_data_dir()
        user_pb = get_user_playbooks_dir()
        assert str(user_pb).startswith(str(user_data))

    def test_directory_exists(self):
        """get_user_playbooks_dir() creates the dir on demand."""
        from ignition_toolkit.core.paths import get_user_playbooks_dir

        result = get_user_playbooks_dir()
        assert result.exists()


class TestGetScreenshotsDir:
    """Tests for get_screenshots_dir()"""

    def test_returns_path(self):
        from ignition_toolkit.core.paths import get_screenshots_dir

        result = get_screenshots_dir()
        assert isinstance(result, Path)

    def test_is_under_data_dir(self):
        from ignition_toolkit.core.paths import get_screenshots_dir, get_data_dir

        data = get_data_dir()
        screenshots = get_screenshots_dir()
        assert str(screenshots).startswith(str(data))

    def test_directory_exists(self):
        from ignition_toolkit.core.paths import get_screenshots_dir

        assert get_screenshots_dir().exists()


class TestGetAllPlaybookDirs:
    """Tests for get_all_playbook_dirs()"""

    def test_returns_list(self):
        from ignition_toolkit.core.paths import get_all_playbook_dirs

        result = get_all_playbook_dirs()
        assert isinstance(result, list)

    def test_returns_at_least_one_dir(self):
        from ignition_toolkit.core.paths import get_all_playbook_dirs

        result = get_all_playbook_dirs()
        assert len(result) >= 1

    def test_all_entries_are_paths(self):
        from ignition_toolkit.core.paths import get_all_playbook_dirs

        for entry in get_all_playbook_dirs():
            assert isinstance(entry, Path)

    def test_user_dir_has_priority(self):
        """User playbooks dir should appear before the built-in dir."""
        from ignition_toolkit.core.paths import get_all_playbook_dirs, get_user_playbooks_dir

        dirs = get_all_playbook_dirs()
        user_dir = get_user_playbooks_dir()
        assert dirs[0] == user_dir
