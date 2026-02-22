"""
Playbook Update Checker - Check for playbook updates

Provides rich update information including:
- Available updates with version comparison
- Release notes and changelogs
- Update statistics (count, categories)
- Recommendations for which updates to apply

Example:
    checker = PlaybookUpdateChecker()
    await checker.refresh()

    updates = checker.get_available_updates()
    for update in updates:
        print(f"{update.playbook_path}: {update.current_version} -> {update.latest_version}")
        print(f"  Release notes: {update.release_notes}")
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ignition_toolkit.playbook.registry import (
    PlaybookRegistry,
)

logger = logging.getLogger(__name__)


@dataclass
class PlaybookUpdate:
    """
    Information about an available playbook update
    """
    playbook_path: str
    current_version: str
    latest_version: str
    description: str
    release_notes: str | None = None
    domain: str = ""
    verified: bool = False
    verified_by: str | None = None
    size_bytes: int = 0
    author: str = ""
    tags: list[str] = field(default_factory=list)
    download_url: str = ""
    checksum: str = ""

    @property
    def is_major_update(self) -> bool:
        """
        Check if this is a major version update

        Returns:
            True if major version number increased
        """
        try:
            current_major = int(float(self.current_version))
            latest_major = int(float(self.latest_version))
            return latest_major > current_major
        except ValueError:
            # Can't determine, assume minor
            return False

    @property
    def version_diff(self) -> float:
        """
        Calculate version difference

        Returns:
            Numeric difference between versions (0.0 if can't calculate)
        """
        try:
            return float(self.latest_version) - float(self.current_version)
        except ValueError:
            return 0.0


@dataclass
class UpdateCheckResult:
    """
    Results of checking for playbook updates
    """
    updates: list[PlaybookUpdate]
    checked_at: str
    total_playbooks: int
    updates_available: int
    last_fetched: str | None = None

    @property
    def has_updates(self) -> bool:
        """Check if any updates are available"""
        return self.updates_available > 0

    @property
    def major_updates(self) -> list[PlaybookUpdate]:
        """Get list of major updates"""
        return [u for u in self.updates if u.is_major_update]

    @property
    def minor_updates(self) -> list[PlaybookUpdate]:
        """Get list of minor updates"""
        return [u for u in self.updates if not u.is_major_update]


class PlaybookUpdateChecker:
    """
    Check for playbook updates and provide rich update information

    Example:
        checker = PlaybookUpdateChecker()

        # Refresh available playbooks from repository
        await checker.refresh()

        # Get update check results
        result = checker.check_for_updates()

        if result.has_updates:
            print(f"Found {result.updates_available} updates")
            for update in result.updates:
                print(f"  - {update.playbook_path}: {update.current_version} -> {update.latest_version}")
    """

    def __init__(self, registry: PlaybookRegistry | None = None):
        """
        Initialize update checker

        Args:
            registry: Playbook registry (created if not provided)
        """
        self.registry = registry or PlaybookRegistry()
        self.registry.load()

    async def refresh(self, force: bool = False) -> None:
        """
        Refresh available playbooks from repository

        Args:
            force: Force refresh even if recently fetched
        """
        logger.info("Refreshing available playbooks from repository")
        await self.registry.fetch_available_playbooks(force_refresh=force)

    def check_for_updates(self) -> UpdateCheckResult:
        """
        Check for available updates

        Returns:
            Update check results with detailed information
        """
        logger.info("Checking for playbook updates")

        # Get updates from registry
        updates_dict = self.registry.check_for_updates()

        # Build rich update objects
        updates = []
        for playbook_path, (current_ver, latest_ver) in updates_dict.items():
            installed_pb = self.registry.get_installed_playbook(playbook_path)
            available_pb = self.registry.get_available_playbook(playbook_path)

            if not installed_pb or not available_pb:
                logger.warning(f"Skipping {playbook_path}: missing metadata")
                continue

            update = PlaybookUpdate(
                playbook_path=playbook_path,
                current_version=current_ver,
                latest_version=latest_ver,
                description=available_pb.description,
                release_notes=available_pb.release_notes,
                domain=available_pb.domain,
                verified=available_pb.verified,
                verified_by=available_pb.verified_by,
                size_bytes=available_pb.size_bytes,
                author=available_pb.author,
                tags=available_pb.tags,
                download_url=available_pb.download_url,
                checksum=available_pb.checksum
            )
            updates.append(update)

        # Sort by version difference (largest updates first)
        updates.sort(key=lambda u: u.version_diff, reverse=True)

        result = UpdateCheckResult(
            updates=updates,
            checked_at=datetime.now(timezone.utc).isoformat(),
            total_playbooks=len(self.registry.installed),
            updates_available=len(updates),
            last_fetched=self.registry.last_fetched
        )

        logger.info(
            f"Update check complete: {result.updates_available} updates available "
            f"out of {result.total_playbooks} installed playbooks"
        )

        return result

    def get_update(self, playbook_path: str) -> PlaybookUpdate | None:
        """
        Get update information for a specific playbook

        Args:
            playbook_path: Playbook path to check

        Returns:
            Update information or None if no update available
        """
        result = self.check_for_updates()
        for update in result.updates:
            if update.playbook_path == playbook_path:
                return update
        return None

    def get_updates_by_domain(self, domain: str) -> list[PlaybookUpdate]:
        """
        Get updates filtered by domain

        Args:
            domain: Domain to filter by ("gateway", "perspective", "designer")

        Returns:
            List of updates for specified domain
        """
        result = self.check_for_updates()
        return [u for u in result.updates if u.domain == domain]

    def get_verified_updates(self) -> list[PlaybookUpdate]:
        """
        Get only verified updates

        Returns:
            List of updates for verified playbooks only
        """
        result = self.check_for_updates()
        return [u for u in result.updates if u.verified]
