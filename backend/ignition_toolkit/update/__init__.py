"""
Update Management Package

Provides auto-update functionality for Ignition Automation Toolkit.

Features:
- Check for updates from GitHub Releases
- Download and install updates via pip
- Backup user data before updates
- Database migrations
- Rollback capability

Version: 4.1.0
"""

from ignition_toolkit.update.checker import check_for_updates, get_current_version
from ignition_toolkit.update.installer import download_update, install_update

__all__ = [
    "check_for_updates",
    "get_current_version",
    "download_update",
    "install_update",
]
