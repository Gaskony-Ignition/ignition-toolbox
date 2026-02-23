"""
Tests for ignition_toolkit/core/remote_data_registry.py

Covers: Registration, lookup, batch operations, reset.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from ignition_toolkit.core.remote_data import RemoteDataConfig, RemoteDataManager
from ignition_toolkit.core.remote_data_registry import RemoteDataRegistry


@pytest.fixture(autouse=True)
def clean_registry():
    """Reset the registry before and after each test."""
    RemoteDataRegistry.reset()
    yield
    RemoteDataRegistry.reset()


@pytest.fixture
def tmp_user_dir(tmp_path):
    return tmp_path / "user_data"


@pytest.fixture
def bundled_dir(tmp_path):
    bundled = tmp_path / "bundled"
    bundled.mkdir()
    data = {"_meta": {"version": "1.0.0", "schema_version": 1}, "items": [1]}
    (bundled / "data.json").write_text(json.dumps(data), encoding="utf-8")
    return bundled


def make_manager(name: str, bundled_dir: Path, tmp_user_dir: Path) -> RemoteDataManager:
    config = RemoteDataConfig(
        component_name=name,
        filename="data.json",
        github_path=f"data/{name}/data.json",
        bundled_path_fn=lambda: bundled_dir / "data.json",
    )
    with patch(
        "ignition_toolkit.core.remote_data.get_user_data_dir",
        return_value=tmp_user_dir,
    ):
        return RemoteDataManager(config)


class TestRegistration:
    def test_register_and_get(self, bundled_dir, tmp_user_dir):
        mgr = make_manager("comp_a", bundled_dir, tmp_user_dir)
        RemoteDataRegistry.register(mgr)

        assert RemoteDataRegistry.get("comp_a") is mgr

    def test_get_returns_none_for_unknown(self):
        assert RemoteDataRegistry.get("nonexistent") is None

    def test_get_all_returns_registered(self, bundled_dir, tmp_user_dir):
        mgr1 = make_manager("comp_a", bundled_dir, tmp_user_dir)
        mgr2 = make_manager("comp_b", bundled_dir, tmp_user_dir)
        RemoteDataRegistry.register(mgr1)
        RemoteDataRegistry.register(mgr2)

        all_managers = RemoteDataRegistry.get_all()
        assert len(all_managers) == 2
        assert "comp_a" in all_managers
        assert "comp_b" in all_managers

    def test_unregister(self, bundled_dir, tmp_user_dir):
        mgr = make_manager("comp_a", bundled_dir, tmp_user_dir)
        RemoteDataRegistry.register(mgr)
        RemoteDataRegistry.unregister("comp_a")

        assert RemoteDataRegistry.get("comp_a") is None

    def test_reset_clears_all(self, bundled_dir, tmp_user_dir):
        mgr = make_manager("comp_a", bundled_dir, tmp_user_dir)
        RemoteDataRegistry.register(mgr)
        RemoteDataRegistry.reset()

        assert len(RemoteDataRegistry.get_all()) == 0


class TestBatchOperations:
    def test_get_all_status(self, bundled_dir, tmp_user_dir):
        mgr = make_manager("comp_a", bundled_dir, tmp_user_dir)
        RemoteDataRegistry.register(mgr)

        status = RemoteDataRegistry.get_all_status()
        assert "comp_a" in status
        assert status["comp_a"]["component"] == "comp_a"
        assert status["comp_a"]["source"] == "bundled"

    @pytest.mark.asyncio
    async def test_check_all_updates(self, bundled_dir, tmp_user_dir):
        mgr1 = make_manager("comp_a", bundled_dir, tmp_user_dir)
        mgr2 = make_manager("comp_b", bundled_dir, tmp_user_dir)
        RemoteDataRegistry.register(mgr1)
        RemoteDataRegistry.register(mgr2)

        # Mock check_for_update on both managers
        with patch.object(mgr1, "check_for_update", new_callable=AsyncMock) as m1, \
             patch.object(mgr2, "check_for_update", new_callable=AsyncMock) as m2:
            m1.return_value = {"version": "2.0.0"}
            m2.return_value = None

            results = await RemoteDataRegistry.check_all_updates(force=True)

        assert results["comp_a"] == {"version": "2.0.0"}
        assert results["comp_b"] is None

    @pytest.mark.asyncio
    async def test_check_all_with_manifest(self, bundled_dir, tmp_user_dir):
        mgr = make_manager("comp_a", bundled_dir, tmp_user_dir)
        RemoteDataRegistry.register(mgr)

        manifest = {"comp_a": {"version": "2.0.0", "checksum": "sha256:abc"}}

        with patch.object(mgr, "check_for_update", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = None
            await RemoteDataRegistry.check_all_updates(
                manifest_components=manifest, force=True
            )
            # Should pass manifest info to the manager
            mock_check.assert_called_once_with(
                manifest_info={"version": "2.0.0", "checksum": "sha256:abc"},
                force=True,
            )
