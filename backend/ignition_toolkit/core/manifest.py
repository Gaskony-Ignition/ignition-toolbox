"""
Toolbox Manifest Manager

Fetches and caches the toolbox-manifest.json from GitHub.
Provides component update info, notifications, and feature flags.

The manifest is the central coordination point for remote data updates.
It contains:
- Component versions and checksums (used by RemoteDataRegistry)
- Notifications (version-targeted messages to users)
- Feature flags (for gradual rollouts)
- Version constraints (minimum supported, recommended)

Follows the same GitHub API patterns as PlaybookRegistry:
- httpx.AsyncClient with Accept: application/vnd.github.v3+json
- base64 decode of content from GitHub Contents API
- 1-hour cache TTL with disk persistence
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from ignition_toolkit.core.paths import get_user_data_dir

logger = logging.getLogger(__name__)

# GitHub repository settings (matches remote_data.py and registry.py)
GITHUB_REPO = "Gaskony-Ignition/ignition-toolbox"
MANIFEST_GITHUB_URL = (
    f"https://api.github.com/repos/{GITHUB_REPO}/contents/toolbox-manifest.json"
)

# Cache settings
CACHE_TTL = timedelta(hours=1)
CACHE_FILENAME = "manifest_cache.json"
DISMISSED_FILENAME = "dismissed_notifications.json"


class ManifestManager:
    """
    Manages the toolbox-manifest.json lifecycle.

    Fetches the manifest from GitHub, caches it locally, and provides
    accessor methods for components, notifications, and feature flags.

    Cache is stored at get_user_data_dir() / "manifest_cache.json".
    Dismissed notifications at get_user_data_dir() / "dismissed_notifications.json".
    """

    def __init__(self) -> None:
        self._cache_path = get_user_data_dir() / CACHE_FILENAME
        self._dismissed_path = get_user_data_dir() / DISMISSED_FILENAME
        self._cached_data: dict[str, Any] | None = None
        self._last_fetched: datetime | None = None

        # Load cache from disk on init
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cached manifest from disk."""
        if not self._cache_path.exists():
            return

        try:
            with open(self._cache_path, encoding="utf-8") as f:
                cache = json.load(f)

            self._cached_data = cache.get("manifest")
            fetched_str = cache.get("fetched_at")
            if fetched_str:
                self._last_fetched = datetime.fromisoformat(fetched_str)

            logger.debug("Loaded manifest cache from disk")
        except (json.JSONDecodeError, OSError, ValueError) as e:
            logger.warning("Failed to load manifest cache: %s", e)
            self._cached_data = None
            self._last_fetched = None

    def _save_cache(self, data: dict[str, Any]) -> None:
        """Save manifest data to disk cache."""
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache = {
                "manifest": data,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(self._cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2)
            logger.debug("Saved manifest cache to disk")
        except OSError as e:
            logger.warning("Failed to save manifest cache: %s", e)

    def _is_cache_fresh(self) -> bool:
        """Check if the cached manifest is still within the TTL."""
        if self._last_fetched is None or self._cached_data is None:
            return False
        elapsed = datetime.now(timezone.utc) - self._last_fetched
        return elapsed < CACHE_TTL

    async def fetch(self, force: bool = False) -> dict[str, Any] | None:
        """
        Fetch the manifest, using cache if fresh.

        Args:
            force: Force a fresh fetch from GitHub, ignoring cache TTL.

        Returns:
            Parsed manifest dict, or None if fetch fails and no cache exists.
        """
        # Use cache if fresh and not forced
        if not force and self._is_cache_fresh():
            logger.debug("Using cached manifest (cache still fresh)")
            return self._cached_data

        # Fetch from GitHub
        try:
            data = await self._fetch_from_github()
            if data is not None:
                self._cached_data = data
                self._last_fetched = datetime.now(timezone.utc)
                self._save_cache(data)
                return data
        except Exception as e:
            logger.warning("Failed to fetch manifest from GitHub: %s", e)

        # Fall back to cached data
        if self._cached_data is not None:
            logger.info("Using stale manifest cache as fallback")
            return self._cached_data

        return None

    async def _fetch_from_github(self) -> dict[str, Any] | None:
        """
        Fetch toolbox-manifest.json from GitHub Contents API.

        Uses the same pattern as PlaybookRegistry.fetch_available_playbooks():
        - GitHub API with Accept: application/vnd.github.v3+json
        - base64 decode of content field
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Accept": "application/vnd.github.v3+json"}
                response = await client.get(MANIFEST_GITHUB_URL, headers=headers)
                response.raise_for_status()
                api_data = response.json()

            # Decode base64 content from GitHub API response
            if "content" in api_data and "encoding" in api_data:
                content = base64.b64decode(api_data["content"]).decode("utf-8")
                data = json.loads(content)
                logger.info(
                    "Fetched manifest v%s from GitHub",
                    data.get("manifest_version", "unknown"),
                )
                return data

            logger.warning("GitHub API response missing content/encoding fields")
            return None

        except httpx.HTTPStatusError as e:
            logger.warning("GitHub API error fetching manifest: HTTP %s", e.response.status_code)
            return None
        except httpx.TimeoutException:
            logger.warning("Manifest fetch timed out")
            return None
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse manifest JSON: %s", e)
            return None

    def get_component_info(self, name: str) -> dict[str, Any] | None:
        """
        Get info for a specific component from cached manifest.

        Args:
            name: Component name (e.g., "stackbuilder_catalog").

        Returns:
            Component info dict (version, checksum, download_url, schema_version),
            or None if not found or no cached manifest.
        """
        if self._cached_data is None:
            return None

        components = self._cached_data.get("components", {})
        return components.get(name)

    async def get_active_notifications(self) -> list[dict[str, Any]]:
        """
        Get notifications filtered by current app version, excluding dismissed ones.

        Notification filtering:
        - If notification has min_version/max_version, only show if current version is in range
        - Exclude any notifications the user has dismissed

        Returns:
            List of active notification dicts.
        """
        if self._cached_data is None:
            return []

        notifications = self._cached_data.get("notifications", [])
        if not notifications:
            return []

        # Get current app version
        try:
            from packaging.version import Version

            from ignition_toolkit import __version__
            current = Version(__version__)
        except Exception:
            # If version parsing fails, return all non-dismissed notifications
            current = None

        # Load dismissed notification IDs
        dismissed = self._load_dismissed()

        active: list[dict[str, Any]] = []
        for notification in notifications:
            notification_id = notification.get("id")
            if not notification_id:
                continue

            # Skip dismissed
            if notification_id in dismissed:
                continue

            # Filter by version range
            if current is not None:
                try:
                    min_ver = notification.get("min_version")
                    max_ver = notification.get("max_version")

                    if min_ver and current < Version(min_ver):
                        continue
                    if max_ver and current > Version(max_ver):
                        continue
                except Exception:
                    # If version comparison fails, include the notification
                    pass

            active.append(notification)

        return active

    def dismiss_notification(self, notification_id: str) -> None:
        """
        Mark a notification as dismissed.

        Persists the dismissed ID to get_user_data_dir() / "dismissed_notifications.json".

        Args:
            notification_id: The notification ID to dismiss.
        """
        dismissed = self._load_dismissed()
        if notification_id not in dismissed:
            dismissed.append(notification_id)
            self._save_dismissed(dismissed)
            logger.info("Dismissed notification: %s", notification_id)

    def get_feature_flags(self) -> dict[str, Any]:
        """
        Get feature flags from cached manifest.

        Returns:
            Dict of feature flag name -> value, or empty dict if unavailable.
        """
        if self._cached_data is None:
            return {}

        return self._cached_data.get("feature_flags", {})

    def _load_dismissed(self) -> list[str]:
        """Load dismissed notification IDs from disk."""
        if not self._dismissed_path.exists():
            return []

        try:
            with open(self._dismissed_path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load dismissed notifications: %s", e)

        return []

    def _save_dismissed(self, dismissed: list[str]) -> None:
        """Save dismissed notification IDs to disk."""
        try:
            self._dismissed_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._dismissed_path, "w", encoding="utf-8") as f:
                json.dump(dismissed, f, indent=2)
        except OSError as e:
            logger.warning("Failed to save dismissed notifications: %s", e)


# --- Singleton ---

_manifest_manager: ManifestManager | None = None


def get_manifest_manager() -> ManifestManager:
    """
    Get the singleton ManifestManager instance.

    Returns:
        The ManifestManager singleton.
    """
    global _manifest_manager
    if _manifest_manager is None:
        _manifest_manager = ManifestManager()
    return _manifest_manager
