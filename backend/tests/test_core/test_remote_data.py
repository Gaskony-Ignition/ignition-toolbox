"""
Tests for ignition_toolkit/core/remote_data.py

Covers: RemoteDataManager load priority, cache TTL, checksum verification,
        fallback behavior, atomic writes, metadata, revert.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ignition_toolkit.core.remote_data import RemoteDataConfig, RemoteDataManager


@pytest.fixture
def tmp_user_dir(tmp_path):
    """Provide a temporary user data directory."""
    return tmp_path / "user_data"


@pytest.fixture
def bundled_dir(tmp_path):
    """Provide a bundled data directory with a sample file."""
    bundled = tmp_path / "bundled"
    bundled.mkdir()
    data = {
        "_meta": {"version": "1.0.0", "schema_version": 1},
        "items": ["a", "b", "c"],
    }
    (bundled / "test_data.json").write_text(json.dumps(data), encoding="utf-8")
    return bundled


@pytest.fixture
def config(bundled_dir):
    """Provide a RemoteDataConfig for testing."""
    return RemoteDataConfig(
        component_name="test_component",
        filename="test_data.json",
        github_path="data/test/test_data.json",
        bundled_path_fn=lambda: bundled_dir / "test_data.json",
        cache_ttl=timedelta(hours=1),
    )


@pytest.fixture
def manager(config, tmp_user_dir):
    """Provide a RemoteDataManager with patched user data dir."""
    with patch(
        "ignition_toolkit.core.remote_data.get_user_data_dir",
        return_value=tmp_user_dir,
    ):
        yield RemoteDataManager(config)


class TestLoadPriority:
    """Tests for load() method priority order."""

    def test_loads_from_bundled_when_no_user_override(self, manager):
        """Should load from bundled path when no user data exists."""
        data = manager.load()
        assert isinstance(data, dict)
        assert data["_meta"]["version"] == "1.0.0"
        assert data["items"] == ["a", "b", "c"]

    def test_loads_from_user_dir_when_override_exists(self, manager, tmp_user_dir):
        """User data dir should take priority over bundled."""
        # Create user override
        user_dir = tmp_user_dir / "remote_data" / "test_component"
        user_dir.mkdir(parents=True)
        override_data = {
            "_meta": {"version": "2.0.0", "schema_version": 1},
            "items": ["x", "y"],
        }
        (user_dir / "test_data.json").write_text(
            json.dumps(override_data), encoding="utf-8"
        )

        data = manager.load()
        assert data["_meta"]["version"] == "2.0.0"
        assert data["items"] == ["x", "y"]

    def test_falls_back_to_bundled_on_corrupt_user_file(self, manager, tmp_user_dir):
        """Should fall back to bundled if user file is corrupted."""
        user_dir = tmp_user_dir / "remote_data" / "test_component"
        user_dir.mkdir(parents=True)
        (user_dir / "test_data.json").write_text("not valid json", encoding="utf-8")

        data = manager.load()
        # Should fall back to bundled
        assert data["_meta"]["version"] == "1.0.0"

    def test_returns_empty_dict_when_nothing_exists(self, tmp_user_dir):
        """Should return empty dict when neither user nor bundled exists."""
        config = RemoteDataConfig(
            component_name="missing_component",
            filename="missing.json",
            github_path="data/missing.json",
            bundled_path_fn=lambda: Path("/nonexistent/missing.json"),
        )
        with patch(
            "ignition_toolkit.core.remote_data.get_user_data_dir",
            return_value=tmp_user_dir,
        ):
            mgr = RemoteDataManager(config)
            data = mgr.load()
            assert data == {}


class TestChecksum:
    """Tests for checksum verification."""

    def test_verify_valid_checksum(self):
        """Should return True for matching checksum."""
        content = '{"test": true}'
        sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        checksum = f"sha256:{sha256}"
        assert RemoteDataManager._verify_checksum(content, checksum) is True

    def test_verify_invalid_checksum(self):
        """Should return False for non-matching checksum."""
        assert RemoteDataManager._verify_checksum(
            "content", "sha256:0000000000000000"
        ) is False

    def test_compute_checksum_format(self):
        """Should return checksum in sha256:hexdigest format."""
        result = RemoteDataManager._compute_checksum("hello")
        assert result.startswith("sha256:")
        assert len(result) == 7 + 64  # "sha256:" + 64 hex chars


class TestUpdate:
    """Tests for update() method."""

    @pytest.mark.asyncio
    async def test_update_downloads_and_saves(self, manager, tmp_user_dir):
        """Should download content and save to user data dir."""
        content = json.dumps({
            "_meta": {"version": "2.0.0", "schema_version": 1},
            "updated": True,
        })
        sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        checksum = f"sha256:{sha256}"

        with patch.object(manager, "_download", new_callable=AsyncMock) as mock_dl:
            mock_dl.return_value = content
            result = await manager.update(
                download_url="https://example.com/test.json",
                expected_checksum=checksum,
            )

        assert result is True
        # Verify file was written
        assert manager._user_data_path.exists()
        saved = json.loads(manager._user_data_path.read_text(encoding="utf-8"))
        assert saved["updated"] is True

    @pytest.mark.asyncio
    async def test_update_rejects_bad_checksum(self, manager):
        """Should reject update when checksum doesn't match."""
        content = '{"bad": true}'

        with patch.object(manager, "_download", new_callable=AsyncMock) as mock_dl:
            mock_dl.return_value = content
            result = await manager.update(
                download_url="https://example.com/test.json",
                expected_checksum="sha256:0000000000000000",
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_update_rejects_invalid_json(self, manager):
        """Should reject update when content is not valid JSON."""
        with patch.object(manager, "_download", new_callable=AsyncMock) as mock_dl:
            mock_dl.return_value = "not json {"
            result = await manager.update(
                download_url="https://example.com/test.json",
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_update_rejects_schema_mismatch(self, manager, tmp_user_dir):
        """Should reject update when schema_version differs."""
        # Create existing data with schema_version 1
        user_dir = tmp_user_dir / "remote_data" / "test_component"
        user_dir.mkdir(parents=True)
        existing = {"_meta": {"version": "1.0.0", "schema_version": 1}}
        (user_dir / "test_data.json").write_text(
            json.dumps(existing), encoding="utf-8"
        )

        # Try to update with schema_version 2
        new_content = json.dumps({
            "_meta": {"version": "2.0.0", "schema_version": 2},
        })

        with patch.object(manager, "_download", new_callable=AsyncMock) as mock_dl:
            mock_dl.return_value = new_content
            result = await manager.update(
                download_url="https://example.com/test.json",
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_update_calls_on_update_callback(self, manager, tmp_user_dir):
        """Should call on_update callback after successful update."""
        callback = MagicMock()
        manager.config.on_update = callback

        content = json.dumps({"_meta": {"version": "2.0.0", "schema_version": 1}})
        with patch.object(manager, "_download", new_callable=AsyncMock) as mock_dl:
            mock_dl.return_value = content
            await manager.update(download_url="https://example.com/test.json")

        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_writes_metadata(self, manager, tmp_user_dir):
        """Should write metadata file alongside data file."""
        content = json.dumps({"_meta": {"version": "2.0.0", "schema_version": 1}})
        with patch.object(manager, "_download", new_callable=AsyncMock) as mock_dl:
            mock_dl.return_value = content
            await manager.update(download_url="https://example.com/test.json")

        assert manager._meta_path.exists()
        meta = json.loads(manager._meta_path.read_text(encoding="utf-8"))
        assert meta["version"] == "2.0.0"
        assert "downloaded_at" in meta
        assert meta["source"] == "https://example.com/test.json"


class TestMetadata:
    """Tests for get_metadata() method."""

    def test_metadata_bundled_source(self, manager):
        """Should report source as 'bundled' when no user override."""
        meta = manager.get_metadata()
        assert meta["source"] == "bundled"
        assert meta["component"] == "test_component"
        assert meta["version"] == "1.0.0"

    def test_metadata_downloaded_source(self, manager, tmp_user_dir):
        """Should report source as 'downloaded' when user override exists."""
        user_dir = tmp_user_dir / "remote_data" / "test_component"
        user_dir.mkdir(parents=True)
        data = {"_meta": {"version": "2.0.0", "schema_version": 1}}
        (user_dir / "test_data.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

        meta = manager.get_metadata()
        assert meta["source"] == "downloaded"


class TestRevert:
    """Tests for revert_to_bundled() method."""

    def test_revert_deletes_user_files(self, manager, tmp_user_dir):
        """Should delete user data and metadata files."""
        # Create user override
        user_dir = tmp_user_dir / "remote_data" / "test_component"
        user_dir.mkdir(parents=True)
        data_file = user_dir / "test_data.json"
        meta_file = user_dir / "test_data.json.meta.json"
        data_file.write_text('{"test": true}', encoding="utf-8")
        meta_file.write_text('{"version": "2.0.0"}', encoding="utf-8")

        result = manager.revert_to_bundled()
        assert result is True
        assert not data_file.exists()
        assert not meta_file.exists()

    def test_revert_returns_false_when_nothing_to_revert(self, manager):
        """Should return False when no user override exists."""
        result = manager.revert_to_bundled()
        assert result is False

    def test_revert_calls_on_update_callback(self, manager, tmp_user_dir):
        """Should call on_update callback after revert."""
        callback = MagicMock()
        manager.config.on_update = callback

        # Create user override
        user_dir = tmp_user_dir / "remote_data" / "test_component"
        user_dir.mkdir(parents=True)
        (user_dir / "test_data.json").write_text('{"test": true}', encoding="utf-8")

        manager.revert_to_bundled()
        callback.assert_called_once()


class TestCacheTTL:
    """Tests for cache TTL behavior in check_for_update()."""

    @pytest.mark.asyncio
    async def test_skips_check_when_cache_fresh(self, manager):
        """Should skip GitHub check when cache TTL hasn't expired."""
        manager._last_checked = datetime.now(timezone.utc)

        result = await manager.check_for_update()
        assert result is None  # Skipped, no update info

    @pytest.mark.asyncio
    async def test_checks_when_cache_expired(self, manager):
        """Should check GitHub when cache TTL has expired."""
        manager._last_checked = datetime.now(timezone.utc) - timedelta(hours=2)

        with patch.object(
            manager, "_check_github", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = None
            await manager.check_for_update()
            mock_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_check_ignores_cache(self, manager):
        """Should check GitHub when force=True regardless of cache."""
        manager._last_checked = datetime.now(timezone.utc)

        with patch.object(
            manager, "_check_github", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = None
            await manager.check_for_update(force=True)
            mock_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_manifest_info_when_provided(self, manager):
        """Should use manifest info instead of GitHub API when provided."""
        manifest_info = {
            "version": "2.0.0",
            "checksum": "sha256:different",
            "download_url": "https://example.com/test.json",
        }

        result = await manager.check_for_update(manifest_info=manifest_info, force=True)
        # Should return update info since checksum differs
        assert result is not None
        assert result["version"] == "2.0.0"
