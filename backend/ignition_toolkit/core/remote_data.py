"""
Remote Data Manager - Generic manager for remotely-updatable data files.

Provides a reusable base for fetching, caching, and verifying data files
from GitHub. Reuses the proven patterns from the playbook registry:
- GitHub API fetch with base64 decode
- SHA256 checksum verification
- 1-hour cache TTL
- Bundled fallback when offline

Usage:
    config = RemoteDataConfig(
        component_name="stackbuilder_catalog",
        filename="catalog.json",
        github_path="data/stackbuilder/catalog.json",
        bundled_path_fn=lambda: Path(__file__).parent / "data" / "catalog.json",
    )
    manager = RemoteDataManager(config)
    data = manager.load()  # Sync, from disk
    update_info = await manager.check_for_update()  # Async, from GitHub
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from ignition_toolkit.core.paths import get_user_data_dir

logger = logging.getLogger(__name__)

# GitHub repository settings (matches playbook registry)
DEFAULT_REPO = "Gaskony-Ignition/ignition-toolbox"
GITHUB_API_BASE = "https://api.github.com/repos"


@dataclass
class RemoteDataConfig:
    """Configuration for a remotely-updatable data component."""

    component_name: str  # e.g., "stackbuilder_catalog"
    filename: str  # e.g., "catalog.json"
    github_path: str  # e.g., "data/stackbuilder/catalog.json"
    bundled_path_fn: Callable[[], Path]  # Returns path to bundled file
    cache_ttl: timedelta = field(default_factory=lambda: timedelta(hours=1))
    repo: str = DEFAULT_REPO
    on_update: Callable[[], None] | None = None  # Called after successful update


class RemoteDataManager:
    """
    Manages a single remotely-updatable data file.

    Load priority:
    1. User data dir (downloaded override)
    2. Bundled (frozen/dev fallback)
    3. Empty default

    Metadata is stored alongside the data file as <filename>.meta.json.
    """

    def __init__(self, config: RemoteDataConfig) -> None:
        self.config = config
        self._last_checked: datetime | None = None

    @property
    def _user_data_path(self) -> Path:
        """Path to the downloaded data file in user data dir."""
        return get_user_data_dir() / "remote_data" / self.config.component_name / self.config.filename

    @property
    def _meta_path(self) -> Path:
        """Path to the metadata file alongside the data file."""
        return self._user_data_path.with_suffix(self._user_data_path.suffix + ".meta.json")

    @property
    def _bundled_path(self) -> Path:
        """Path to the bundled data file."""
        return self.config.bundled_path_fn()

    def load(self) -> dict | list:
        """
        Load data from disk (sync).

        Priority: user data dir > bundled > empty default.

        Returns:
            Parsed JSON data (dict or list).
        """
        # Try user data dir first (downloaded override)
        if self._user_data_path.exists():
            try:
                with open(self._user_data_path, encoding="utf-8") as f:
                    data = json.load(f)
                logger.debug("Loaded %s from user data dir", self.config.component_name)
                return data
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(
                    "Failed to load %s from user data dir: %s, falling back to bundled",
                    self.config.component_name, e,
                )

        # Fall back to bundled
        bundled = self._bundled_path
        if bundled.exists():
            try:
                with open(bundled, encoding="utf-8") as f:
                    data = json.load(f)
                logger.debug("Loaded %s from bundled path", self.config.component_name)
                return data
            except (json.JSONDecodeError, OSError) as e:
                logger.error("Failed to load bundled %s: %s", self.config.component_name, e)

        # Empty default
        logger.warning("No data found for %s, returning empty dict", self.config.component_name)
        return {}

    async def check_for_update(
        self,
        manifest_info: dict | None = None,
        force: bool = False,
    ) -> dict | None:
        """
        Check if an update is available for this component.

        If manifest_info is provided, uses it directly (avoids redundant GitHub calls).
        Otherwise, fetches the file metadata from GitHub API.

        Args:
            manifest_info: Pre-fetched component info from manifest (version, checksum, download_url).
            force: Force check even if cache is still fresh.

        Returns:
            Update info dict with version, checksum, download_url if available, else None.
        """
        # Check cache TTL
        if not force and self._last_checked:
            elapsed = datetime.now(timezone.utc) - self._last_checked
            if elapsed < self.config.cache_ttl:
                logger.debug("Cache still fresh for %s, skipping check", self.config.component_name)
                return None

        self._last_checked = datetime.now(timezone.utc)

        # If manifest provides info, use it directly
        if manifest_info:
            return self._compare_with_manifest(manifest_info)

        # Otherwise, fetch from GitHub API
        try:
            return await self._check_github()
        except Exception as e:
            logger.error("Failed to check for update for %s: %s", self.config.component_name, e)
            return None

    async def update(
        self,
        download_url: str,
        expected_checksum: str | None = None,
    ) -> bool:
        """
        Download and install an update.

        Uses atomic write (temp file then rename) to prevent corruption.

        Args:
            download_url: URL to download the data file from.
            expected_checksum: Expected SHA256 checksum (format: "sha256:hexdigest").

        Returns:
            True if update succeeded, False otherwise.
        """
        try:
            # Download content
            content = await self._download(download_url)

            # Verify checksum if provided
            if expected_checksum:
                if not self._verify_checksum(content, expected_checksum):
                    logger.error(
                        "Checksum mismatch for %s, aborting update",
                        self.config.component_name,
                    )
                    return False

            # Validate JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error("Downloaded %s is not valid JSON: %s", self.config.component_name, e)
                return False

            # Check schema version compatibility
            if isinstance(data, dict) and "_meta" in data:
                remote_schema = data["_meta"].get("schema_version", 1)
                local_data = self.load()
                if isinstance(local_data, dict) and "_meta" in local_data:
                    local_schema = local_data["_meta"].get("schema_version", 1)
                    if remote_schema != local_schema:
                        logger.error(
                            "Schema version mismatch for %s: local=%s, remote=%s. Refusing update.",
                            self.config.component_name, local_schema, remote_schema,
                        )
                        return False

            # Atomic write: temp file then rename
            self._user_data_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_fd, tmp_path = tempfile.mkstemp(
                dir=self._user_data_path.parent,
                suffix=".tmp",
            )
            try:
                with open(tmp_fd, "w", encoding="utf-8") as f:
                    f.write(content)
                Path(tmp_path).replace(self._user_data_path)
            except Exception:
                Path(tmp_path).unlink(missing_ok=True)
                raise

            # Write metadata
            meta = {
                "version": data.get("_meta", {}).get("version", "unknown") if isinstance(data, dict) else "unknown",
                "checksum": expected_checksum or self._compute_checksum(content),
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "source": download_url,
            }
            with open(self._meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)

            logger.info("Updated %s successfully", self.config.component_name)

            # Invoke callback to invalidate caches
            if self.config.on_update:
                try:
                    self.config.on_update()
                except Exception as e:
                    logger.warning("on_update callback failed for %s: %s", self.config.component_name, e)

            return True

        except Exception as e:
            logger.error("Failed to update %s: %s", self.config.component_name, e)
            return False

    def get_metadata(self) -> dict[str, Any]:
        """
        Get metadata about the current data file.

        Returns:
            Dict with version, source, checksum, last_checked, etc.
        """
        meta: dict[str, Any] = {
            "component": self.config.component_name,
            "source": "bundled",
            "version": "unknown",
            "last_checked": self._last_checked.isoformat() if self._last_checked else None,
        }

        # Check if user-dir override exists
        if self._user_data_path.exists():
            meta["source"] = "downloaded"
            # Try to read meta file
            if self._meta_path.exists():
                try:
                    with open(self._meta_path, encoding="utf-8") as f:
                        saved_meta = json.load(f)
                    meta.update(saved_meta)
                except (json.JSONDecodeError, OSError):
                    pass

        # Try to extract version from the data itself
        try:
            data = self.load()
            if isinstance(data, dict) and "_meta" in data:
                meta["version"] = data["_meta"].get("version", meta.get("version", "unknown"))
        except Exception:
            pass

        return meta

    def revert_to_bundled(self) -> bool:
        """
        Delete user-dir override, reverting to the bundled version.

        Returns:
            True if reverted (files deleted), False if nothing to revert.
        """
        reverted = False

        if self._user_data_path.exists():
            self._user_data_path.unlink()
            reverted = True

        if self._meta_path.exists():
            self._meta_path.unlink()
            reverted = True

        if reverted:
            logger.info("Reverted %s to bundled version", self.config.component_name)
            # Invoke callback to invalidate caches
            if self.config.on_update:
                try:
                    self.config.on_update()
                except Exception as e:
                    logger.warning("on_update callback failed for %s: %s", self.config.component_name, e)

        return reverted

    # --- Private helpers ---

    async def _check_github(self) -> dict | None:
        """Check GitHub API for file metadata (SHA, size)."""
        url = f"{GITHUB_API_BASE}/{self.config.repo}/contents/{self.config.github_path}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Accept": "application/vnd.github.v3+json"}
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                api_data = response.json()

            # Decode content to compute checksum and extract version
            if "content" in api_data and "encoding" in api_data:
                content = base64.b64decode(api_data["content"]).decode("utf-8")
                remote_checksum = self._compute_checksum(content)

                # Compare with local
                local_meta = self.get_metadata()
                local_checksum = local_meta.get("checksum")

                if local_checksum and local_checksum == remote_checksum:
                    logger.debug("No update available for %s", self.config.component_name)
                    return None

                # Parse to get version
                try:
                    data = json.loads(content)
                    version = data.get("_meta", {}).get("version", "unknown") if isinstance(data, dict) else "unknown"
                except json.JSONDecodeError:
                    version = "unknown"

                download_url = api_data.get("download_url", "")
                return {
                    "version": version,
                    "checksum": remote_checksum,
                    "download_url": download_url,
                    "size_bytes": api_data.get("size", 0),
                }

        except httpx.HTTPStatusError as e:
            logger.error("GitHub API error checking %s: %s", self.config.component_name, e)
        except Exception as e:
            logger.error("Error checking GitHub for %s: %s", self.config.component_name, e)

        return None

    def _compare_with_manifest(self, manifest_info: dict) -> dict | None:
        """Compare local data with manifest-provided info."""
        local_meta = self.get_metadata()
        local_checksum = local_meta.get("checksum")
        remote_checksum = manifest_info.get("checksum")

        if local_checksum and remote_checksum and local_checksum == remote_checksum:
            logger.debug("No update available for %s (manifest)", self.config.component_name)
            return None

        return {
            "version": manifest_info.get("version", "unknown"),
            "checksum": remote_checksum,
            "download_url": manifest_info.get("download_url", ""),
            "schema_version": manifest_info.get("schema_version"),
        }

    async def _download(self, url: str) -> str:
        """Download content from a URL."""
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    @staticmethod
    def _verify_checksum(content: str, expected_checksum: str) -> bool:
        """
        Verify SHA256 checksum.

        Same format as PlaybookInstaller: "sha256:hexdigest"
        """
        sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        calculated = f"sha256:{sha256}"
        return calculated == expected_checksum

    @staticmethod
    def _compute_checksum(content: str) -> str:
        """Compute SHA256 checksum in standard format."""
        sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return f"sha256:{sha256}"
