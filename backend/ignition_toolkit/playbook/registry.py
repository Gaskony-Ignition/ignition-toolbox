"""
Playbook Registry - Manages installed and available playbooks

The registry tracks:
- Installed playbooks (built-in + user-installed)
- Available playbooks (from GitHub Releases)
- Playbook metadata (version, checksum, source, etc.)

Registry is persisted to ~/.ignition-toolkit/registry.json
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from ignition_toolkit.core.paths import get_user_data_dir

logger = logging.getLogger(__name__)

# GitHub repository settings
DEFAULT_REPO = "Gaskony-Ignition/ignition-toolbox"
# Use GitHub API for more reliable access (raw.githubusercontent can have cache delays)
DEFAULT_INDEX_URL = f"https://api.github.com/repos/{DEFAULT_REPO}/contents/playbooks-index.json"


@dataclass
class InstalledPlaybook:
    """Metadata for an installed playbook"""
    playbook_path: str  # e.g., "gateway/module_upgrade"
    version: str  # e.g., "4.0"
    location: str  # Absolute file path
    source: str  # "built-in", "user-installed", "user-created", "imported"
    installed_at: str  # ISO 8601 timestamp
    checksum: str | None = None  # SHA256 checksum (for verification)
    verified: bool = False  # Whether playbook is verified

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "InstalledPlaybook":
        """Create from dictionary"""
        return cls(**data)


@dataclass
class AvailablePlaybook:
    """Metadata for a playbook available in the repository"""
    playbook_path: str
    version: str
    domain: str
    verified: bool
    description: str
    download_url: str
    checksum: str
    size_bytes: int
    dependencies: list[str] = field(default_factory=list)
    author: str = ""
    tags: list[str] = field(default_factory=list)
    group: str = ""
    verified_by: str | None = None
    verified_at: str | None = None
    release_notes: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AvailablePlaybook":
        """Create from dictionary"""
        return cls(**data)


class PlaybookRegistry:
    """
    Manages playbook registry

    The registry tracks installed playbooks and caches available playbooks
    from the central repository.

    Registry file location: ~/.ignition-toolkit/registry.json

    Example:
        registry = PlaybookRegistry()
        registry.load()

        # Register a new playbook
        registry.register_playbook(
            playbook_path="gateway/module_upgrade",
            version="4.0",
            location="/path/to/module_upgrade.yaml",
            source="user-installed"
        )

        # Get installed playbooks
        installed = registry.get_installed_playbooks()

        # Fetch available playbooks from GitHub
        await registry.fetch_available_playbooks()
        available = registry.get_available_playbooks()
    """

    def __init__(self, registry_path: Path | None = None):
        """
        Initialize playbook registry

        Args:
            registry_path: Path to registry JSON file (default: ~/.ignition-toolkit/registry.json)
        """
        if registry_path is None:
            registry_path = get_user_data_dir() / "registry.json"

        self.registry_path = registry_path
        self.installed: dict[str, InstalledPlaybook] = {}
        self.available: dict[str, AvailablePlaybook] = {}
        self.last_fetched: str | None = None  # Last time we fetched from GitHub

    def load(self) -> None:
        """
        Load registry from disk

        If registry file doesn't exist, starts with empty registry.
        """
        if not self.registry_path.exists():
            logger.info(f"Registry file not found, starting with empty registry: {self.registry_path}")
            return

        try:
            with open(self.registry_path, encoding='utf-8') as f:
                data = json.load(f)

            # Load installed playbooks
            self.installed = {
                path: InstalledPlaybook.from_dict(pb_data)
                for path, pb_data in data.get("installed", {}).items()
            }

            # Load available playbooks (cached)
            self.available = {
                path: AvailablePlaybook.from_dict(pb_data)
                for path, pb_data in data.get("available", {}).items()
            }

            self.last_fetched = data.get("last_fetched")

            logger.info(f"Loaded registry: {len(self.installed)} installed, {len(self.available)} available")

        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            # Start with empty registry
            self.installed = {}
            self.available = {}
            self.last_fetched = None

    def save(self) -> None:
        """Save registry to disk"""
        # Ensure directory exists
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dictionary
        data = {
            "installed": {
                path: pb.to_dict()
                for path, pb in self.installed.items()
            },
            "available": {
                path: pb.to_dict()
                for path, pb in self.available.items()
            },
            "last_fetched": self.last_fetched,
        }

        # Write to file
        with open(self.registry_path, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved registry to {self.registry_path}")

    def register_playbook(
        self,
        playbook_path: str,
        version: str,
        location: str,
        source: str,
        checksum: str | None = None,
        verified: bool = False
    ) -> None:
        """
        Register an installed playbook

        Args:
            playbook_path: Playbook path (e.g., "gateway/module_upgrade")
            version: Playbook version
            location: Absolute file path
            source: Source type ("built-in", "user-installed", "user-created", "imported")
            checksum: SHA256 checksum (optional)
            verified: Whether playbook is verified
        """
        playbook = InstalledPlaybook(
            playbook_path=playbook_path,
            version=version,
            location=location,
            source=source,
            installed_at=datetime.now(timezone.utc).isoformat(),
            checksum=checksum,
            verified=verified
        )

        self.installed[playbook_path] = playbook
        logger.info(f"Registered playbook: {playbook_path} v{version} ({source})")

    def unregister_playbook(self, playbook_path: str) -> bool:
        """
        Unregister a playbook

        Args:
            playbook_path: Playbook path to unregister

        Returns:
            True if playbook was unregistered, False if not found
        """
        if playbook_path in self.installed:
            del self.installed[playbook_path]
            logger.info(f"Unregistered playbook: {playbook_path}")
            return True
        return False

    def get_installed_playbooks(self) -> list[InstalledPlaybook]:
        """
        Get list of all installed playbooks

        Returns:
            List of installed playbook metadata
        """
        return list(self.installed.values())

    def get_installed_playbook(self, playbook_path: str) -> InstalledPlaybook | None:
        """
        Get metadata for a specific installed playbook

        Args:
            playbook_path: Playbook path

        Returns:
            Installed playbook metadata or None if not found
        """
        return self.installed.get(playbook_path)

    def is_installed(self, playbook_path: str) -> bool:
        """
        Check if a playbook is installed

        Args:
            playbook_path: Playbook path

        Returns:
            True if installed, False otherwise
        """
        return playbook_path in self.installed

    # Cache TTL: auto-refresh from GitHub after this duration
    CACHE_TTL = timedelta(hours=1)

    async def fetch_available_playbooks(
        self,
        index_url: str = DEFAULT_INDEX_URL,
        force_refresh: bool = False
    ) -> dict[str, AvailablePlaybook]:
        """
        Fetch available playbooks from GitHub

        Args:
            index_url: URL to playbooks-index.json (GitHub API or raw URL)
            force_refresh: Force refresh even if recently fetched

        Returns:
            Dictionary mapping playbook paths to metadata
        """
        if not force_refresh and self.last_fetched and self.available:
            # Check if cache is still fresh
            try:
                fetched_time = datetime.fromisoformat(self.last_fetched)
                if datetime.now(timezone.utc) - fetched_time < self.CACHE_TTL:
                    logger.info("Using cached available playbooks (cache still fresh)")
                    return self.available
                logger.info("Cache expired, refreshing from GitHub")
            except (ValueError, TypeError):
                logger.warning("Invalid last_fetched timestamp, refreshing")

        try:
            logger.info(f"Fetching playbook index from: {index_url}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Add Accept header for GitHub API
                headers = {"Accept": "application/vnd.github.v3+json"}
                response = await client.get(index_url, headers=headers)
                response.raise_for_status()
                api_response = response.json()

            # Handle GitHub API response (base64-encoded content)
            if "content" in api_response and "encoding" in api_response:
                import base64
                content = base64.b64decode(api_response["content"]).decode("utf-8")
                data = json.loads(content)
            else:
                # Direct JSON response (e.g., from raw URL)
                data = api_response

            # Parse playbooks from index
            playbooks_data = data.get("playbooks", {})
            self.available = {
                path: AvailablePlaybook(
                    playbook_path=path,
                    **pb_data
                )
                for path, pb_data in playbooks_data.items()
            }

            self.last_fetched = datetime.now(timezone.utc).isoformat()

            logger.info(f"Fetched {len(self.available)} available playbooks")

            # Save to cache
            self.save()

            return self.available

        except Exception as e:
            logger.error(f"Failed to fetch available playbooks: {e}")
            # Return cached playbooks if available
            return self.available

    def get_available_playbooks(self, include_installed: bool = False) -> list[AvailablePlaybook]:
        """
        Get list of available playbooks

        Args:
            include_installed: If False, exclude playbooks that are already installed

        Returns:
            List of available playbook metadata
        """
        if include_installed:
            return list(self.available.values())

        # Filter out installed playbooks
        return [
            pb for path, pb in self.available.items()
            if path not in self.installed
        ]

    def get_available_playbook(self, playbook_path: str) -> AvailablePlaybook | None:
        """
        Get metadata for a specific available playbook

        Args:
            playbook_path: Playbook path

        Returns:
            Available playbook metadata or None if not found
        """
        return self.available.get(playbook_path)

    def check_for_updates(self) -> dict[str, tuple[str, str]]:
        """
        Check for playbook updates

        Compares installed playbook versions against available versions.

        Returns:
            Dictionary mapping playbook paths to (current_version, latest_version) tuples
            for playbooks that have updates available
        """
        updates = {}

        for path, installed_pb in self.installed.items():
            available_pb = self.available.get(path)
            if not available_pb:
                continue

            if available_pb.version != installed_pb.version:
                try:
                    from packaging.version import Version
                    if Version(available_pb.version) > Version(installed_pb.version):
                        updates[path] = (installed_pb.version, available_pb.version)
                except Exception:
                    # Fall back to string comparison for non-standard version strings
                    if available_pb.version > installed_pb.version:
                        updates[path] = (installed_pb.version, available_pb.version)

        return updates
