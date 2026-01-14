"""
Playbook Installer - Download and install playbooks from repository

Handles:
- Downloading playbooks from GitHub Releases
- Checksum verification
- Installation to user playbooks directory
- Dependency resolution (future)
- Uninstallation
"""

import hashlib
import logging
from pathlib import Path
from typing import Any

import httpx
import yaml

from ignition_toolkit.core.paths import get_user_playbooks_dir, get_builtin_playbooks_dir
from ignition_toolkit.playbook.loader import PlaybookLoader
from ignition_toolkit.playbook.registry import PlaybookRegistry, AvailablePlaybook

logger = logging.getLogger(__name__)


class PlaybookInstallError(Exception):
    """Raised when playbook installation fails"""
    pass


class PlaybookInstaller:
    """
    Install and uninstall playbooks

    Example:
        installer = PlaybookInstaller()

        # Install a playbook
        await installer.install_playbook("gateway/module_upgrade")

        # Uninstall a playbook
        await installer.uninstall_playbook("gateway/module_upgrade")
    """

    def __init__(self, registry: PlaybookRegistry | None = None):
        """
        Initialize playbook installer

        Args:
            registry: Playbook registry (created if not provided)
        """
        self.registry = registry or PlaybookRegistry()
        self.registry.load()
        self.user_playbooks_dir = get_user_playbooks_dir()
        self.builtin_playbooks_dir = get_builtin_playbooks_dir()

    async def install_playbook(
        self,
        playbook_path: str,
        version: str = "latest",
        verify_checksum: bool = True
    ) -> Path:
        """
        Install a playbook from the repository

        Args:
            playbook_path: Playbook path (e.g., "gateway/module_upgrade")
            version: Version to install ("latest" or specific version)
            verify_checksum: Whether to verify SHA256 checksum

        Returns:
            Path to installed playbook file

        Raises:
            PlaybookInstallError: If installation fails
        """
        logger.info(f"Installing playbook: {playbook_path} (version: {version})")

        # Check if already installed
        if self.registry.is_installed(playbook_path):
            installed = self.registry.get_installed_playbook(playbook_path)
            logger.warning(f"Playbook {playbook_path} already installed (v{installed.version})")
            raise PlaybookInstallError(
                f"Playbook {playbook_path} is already installed (version {installed.version}). "
                f"Uninstall it first or use update instead."
            )

        # Get playbook metadata from registry
        available_playbook = self.registry.get_available_playbook(playbook_path)
        if not available_playbook:
            # Fetch available playbooks if not cached
            logger.info("Fetching available playbooks from repository...")
            await self.registry.fetch_available_playbooks()
            available_playbook = self.registry.get_available_playbook(playbook_path)

        if not available_playbook:
            raise PlaybookInstallError(
                f"Playbook {playbook_path} not found in repository. "
                f"Check the playbook name and try again."
            )

        # Download playbook
        logger.info(f"Downloading from: {available_playbook.download_url}")
        yaml_content = await self._download_file(available_playbook.download_url)

        # Verify checksum
        if verify_checksum:
            logger.info("Verifying checksum...")
            if not self._verify_checksum(yaml_content, available_playbook.checksum):
                raise PlaybookInstallError(
                    f"Checksum verification failed for {playbook_path}. "
                    f"The downloaded file may be corrupted."
                )
            logger.info("✓ Checksum verified")

        # Validate YAML structure
        logger.info("Validating playbook structure...")
        try:
            playbook_data = yaml.safe_load(yaml_content)
            # Basic validation
            if not all(key in playbook_data for key in ["name", "version", "steps"]):
                raise PlaybookInstallError("Invalid playbook: missing required fields (name, version, steps)")
        except yaml.YAMLError as e:
            raise PlaybookInstallError(f"Invalid YAML syntax: {e}")

        # Determine installation path
        # playbook_path is like "gateway/module_upgrade", we need to create subdirectories
        install_path = self.user_playbooks_dir / f"{playbook_path}.yaml"
        install_path.parent.mkdir(parents=True, exist_ok=True)

        # Write playbook file
        logger.info(f"Installing to: {install_path}")
        with open(install_path, "w") as f:
            f.write(yaml_content)

        # Register in registry
        self.registry.register_playbook(
            playbook_path=playbook_path,
            version=available_playbook.version,
            location=str(install_path),
            source="user-installed",
            checksum=available_playbook.checksum,
            verified=available_playbook.verified
        )
        self.registry.save()

        logger.info(f"✓ Playbook {playbook_path} installed successfully")
        return install_path

    async def uninstall_playbook(self, playbook_path: str, force: bool = False) -> bool:
        """
        Uninstall a playbook

        Args:
            playbook_path: Playbook path (e.g., "gateway/module_upgrade")
            force: Force uninstall even if playbook is built-in (dangerous!)

        Returns:
            True if uninstalled, False if not found

        Raises:
            PlaybookInstallError: If trying to uninstall built-in playbook without force
        """
        logger.info(f"Uninstalling playbook: {playbook_path}")

        # Check if installed
        installed_playbook = self.registry.get_installed_playbook(playbook_path)
        if not installed_playbook:
            logger.warning(f"Playbook {playbook_path} is not installed")
            return False

        # Prevent deletion of built-in playbooks unless forced
        if installed_playbook.source == "built-in" and not force:
            raise PlaybookInstallError(
                f"Cannot uninstall built-in playbook {playbook_path}. "
                f"Built-in playbooks are part of the toolkit installation."
            )

        # Delete playbook file
        playbook_file = Path(installed_playbook.location)
        if playbook_file.exists():
            playbook_file.unlink()
            logger.info(f"Deleted file: {playbook_file}")
        else:
            logger.warning(f"Playbook file not found: {playbook_file}")

        # Unregister from registry
        self.registry.unregister_playbook(playbook_path)
        self.registry.save()

        logger.info(f"✓ Playbook {playbook_path} uninstalled successfully")
        return True

    async def update_playbook(self, playbook_path: str) -> Path:
        """
        Update a playbook to the latest version

        Args:
            playbook_path: Playbook path

        Returns:
            Path to updated playbook file

        Raises:
            PlaybookInstallError: If update fails
        """
        logger.info(f"Updating playbook: {playbook_path}")

        # Check if installed
        if not self.registry.is_installed(playbook_path):
            raise PlaybookInstallError(
                f"Playbook {playbook_path} is not installed. "
                f"Install it first before updating."
            )

        # Uninstall current version
        await self.uninstall_playbook(playbook_path)

        # Install latest version
        return await self.install_playbook(playbook_path, version="latest")

    async def _download_file(self, url: str) -> str:
        """
        Download file from URL

        Args:
            url: URL to download from

        Returns:
            File content as string

        Raises:
            PlaybookInstallError: If download fails
        """
        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except httpx.HTTPError as e:
            raise PlaybookInstallError(f"Failed to download from {url}: {e}")

    def _verify_checksum(self, content: str, expected_checksum: str) -> bool:
        """
        Verify SHA256 checksum

        Args:
            content: File content
            expected_checksum: Expected checksum (format: "sha256:hexdigest")

        Returns:
            True if checksum matches, False otherwise
        """
        # Calculate SHA256
        sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        calculated_checksum = f"sha256:{sha256}"

        return calculated_checksum == expected_checksum
