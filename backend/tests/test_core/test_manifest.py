"""
Tests for ignition_toolkit/core/manifest.py

Covers: ManifestManager fetch, cache, notifications, dismiss, feature flags.
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from ignition_toolkit.core.manifest import ManifestManager


@pytest.fixture
def tmp_user_dir(tmp_path):
    return tmp_path / "user_data"


@pytest.fixture
def manifest_manager(tmp_user_dir):
    """Create a ManifestManager with patched user data dir."""
    with patch(
        "ignition_toolkit.core.manifest.get_user_data_dir",
        return_value=tmp_user_dir,
    ):
        tmp_user_dir.mkdir(parents=True, exist_ok=True)
        yield ManifestManager()


SAMPLE_MANIFEST = {
    "manifest_version": "1.0.0",
    "published_at": "2026-02-23T00:00:00Z",
    "components": {
        "stackbuilder_catalog": {
            "version": "1.0.0",
            "checksum": "sha256:abc123",
            "download_url": "https://example.com/catalog.json",
            "schema_version": 1,
        },
    },
    "notifications": [
        {
            "id": "test-notification",
            "severity": "info",
            "title": "Test",
            "message": "Test notification",
            "min_version": "3.0.0",
            "max_version": "4.0.0",
            "dismissible": True,
        },
        {
            "id": "old-notification",
            "severity": "warning",
            "title": "Old",
            "message": "For old versions only",
            "min_version": "1.0.0",
            "max_version": "2.0.0",
        },
    ],
    "feature_flags": {"new_ui": True, "beta_feature": False},
    "minimum_supported_version": "3.0.0",
    "recommended_version": "3.0.15",
}


class TestFetch:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_cache_and_fetch_fails(self, manifest_manager):
        with patch.object(
            manifest_manager, "_fetch_from_github", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = None
            result = await manifest_manager.fetch()
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_cached_data_when_fresh(self, manifest_manager):
        manifest_manager._cached_data = SAMPLE_MANIFEST
        manifest_manager._last_fetched = datetime.now(timezone.utc)

        result = await manifest_manager.fetch()
        assert result == SAMPLE_MANIFEST

    @pytest.mark.asyncio
    async def test_fetches_when_cache_expired(self, manifest_manager):
        manifest_manager._cached_data = SAMPLE_MANIFEST
        manifest_manager._last_fetched = datetime.now(timezone.utc) - timedelta(hours=2)

        with patch.object(
            manifest_manager, "_fetch_from_github", new_callable=AsyncMock
        ) as mock_fetch:
            updated = {**SAMPLE_MANIFEST, "manifest_version": "1.1.0"}
            mock_fetch.return_value = updated
            result = await manifest_manager.fetch()
            assert result["manifest_version"] == "1.1.0"

    @pytest.mark.asyncio
    async def test_force_ignores_cache(self, manifest_manager):
        manifest_manager._cached_data = SAMPLE_MANIFEST
        manifest_manager._last_fetched = datetime.now(timezone.utc)

        with patch.object(
            manifest_manager, "_fetch_from_github", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = SAMPLE_MANIFEST
            await manifest_manager.fetch(force=True)
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_falls_back_to_stale_cache_on_failure(self, manifest_manager):
        manifest_manager._cached_data = SAMPLE_MANIFEST
        manifest_manager._last_fetched = datetime.now(timezone.utc) - timedelta(hours=2)

        with patch.object(
            manifest_manager, "_fetch_from_github", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = None
            result = await manifest_manager.fetch()
            assert result == SAMPLE_MANIFEST


class TestCachePersistence:
    @pytest.mark.asyncio
    async def test_saves_cache_to_disk(self, manifest_manager, tmp_user_dir):
        with patch.object(
            manifest_manager, "_fetch_from_github", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = SAMPLE_MANIFEST
            await manifest_manager.fetch()

        cache_path = tmp_user_dir / "manifest_cache.json"
        assert cache_path.exists()
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        assert cache["manifest"]["manifest_version"] == "1.0.0"

    def test_loads_cache_from_disk(self, tmp_user_dir):
        # Pre-populate cache file
        cache = {
            "manifest": SAMPLE_MANIFEST,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        tmp_user_dir.mkdir(parents=True, exist_ok=True)
        (tmp_user_dir / "manifest_cache.json").write_text(
            json.dumps(cache), encoding="utf-8"
        )

        with patch(
            "ignition_toolkit.core.manifest.get_user_data_dir",
            return_value=tmp_user_dir,
        ):
            mgr = ManifestManager()
            assert mgr._cached_data == SAMPLE_MANIFEST


class TestComponentInfo:
    def test_returns_component_info(self, manifest_manager):
        manifest_manager._cached_data = SAMPLE_MANIFEST
        info = manifest_manager.get_component_info("stackbuilder_catalog")
        assert info["version"] == "1.0.0"
        assert info["checksum"] == "sha256:abc123"

    def test_returns_none_for_unknown_component(self, manifest_manager):
        manifest_manager._cached_data = SAMPLE_MANIFEST
        assert manifest_manager.get_component_info("nonexistent") is None

    def test_returns_none_when_no_manifest(self, manifest_manager):
        assert manifest_manager.get_component_info("stackbuilder_catalog") is None


class TestNotifications:
    @pytest.mark.asyncio
    async def test_filters_by_version(self, manifest_manager):
        manifest_manager._cached_data = SAMPLE_MANIFEST

        with patch("ignition_toolkit.__version__", "3.0.15"):
            notifications = await manifest_manager.get_active_notifications()

        # "test-notification" should match (3.0.0 <= 3.0.15 <= 4.0.0)
        # "old-notification" should NOT match (3.0.15 > 2.0.0 max)
        ids = [n["id"] for n in notifications]
        assert "test-notification" in ids
        assert "old-notification" not in ids

    @pytest.mark.asyncio
    async def test_excludes_dismissed(self, manifest_manager, tmp_user_dir):
        manifest_manager._cached_data = SAMPLE_MANIFEST

        # Pre-dismiss test-notification
        tmp_user_dir.mkdir(parents=True, exist_ok=True)
        (tmp_user_dir / "dismissed_notifications.json").write_text(
            json.dumps(["test-notification"]), encoding="utf-8"
        )

        with patch("ignition_toolkit.__version__", "3.0.15"):
            notifications = await manifest_manager.get_active_notifications()

        ids = [n["id"] for n in notifications]
        assert "test-notification" not in ids

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_manifest(self, manifest_manager):
        result = await manifest_manager.get_active_notifications()
        assert result == []


class TestDismissNotification:
    def test_dismiss_persists_to_disk(self, manifest_manager, tmp_user_dir):
        manifest_manager.dismiss_notification("test-123")

        dismissed_path = tmp_user_dir / "dismissed_notifications.json"
        assert dismissed_path.exists()
        dismissed = json.loads(dismissed_path.read_text(encoding="utf-8"))
        assert "test-123" in dismissed

    def test_dismiss_does_not_duplicate(self, manifest_manager, tmp_user_dir):
        manifest_manager.dismiss_notification("test-123")
        manifest_manager.dismiss_notification("test-123")

        dismissed_path = tmp_user_dir / "dismissed_notifications.json"
        dismissed = json.loads(dismissed_path.read_text(encoding="utf-8"))
        assert dismissed.count("test-123") == 1


class TestFeatureFlags:
    def test_returns_flags(self, manifest_manager):
        manifest_manager._cached_data = SAMPLE_MANIFEST
        flags = manifest_manager.get_feature_flags()
        assert flags == {"new_ui": True, "beta_feature": False}

    def test_returns_empty_when_no_manifest(self, manifest_manager):
        assert manifest_manager.get_feature_flags() == {}
