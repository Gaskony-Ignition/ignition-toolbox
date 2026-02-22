"""
Update Checker Service

Checks GitHub Releases API for new versions of Ignition Automation Toolkit.
"""

import logging

import httpx
from packaging.version import parse as parse_version

logger = logging.getLogger(__name__)

# GitHub repository information
GITHUB_REPO = "nigelgwork/ignition-toolbox"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
TIMEOUT_SECONDS = 10.0


def get_current_version() -> str:
    """
    Get the current installed version

    Returns:
        str: Version string (e.g., "4.0.9")
    """
    from ignition_toolkit import __version__
    return __version__


async def check_for_updates() -> dict | None:
    """
    Check GitHub Releases for newer version

    Returns:
        dict or None: Update information if available, None otherwise

        Update dict format:
        {
            "current_version": "4.0.9",
            "latest_version": "4.1.0",
            "release_url": "https://github.com/nigelgwork/ignition-toolbox/releases/tag/v4.1.0",
            "release_notes": "Markdown changelog...",
            "download_url": "https://github.com/nigelgwork/ignition-toolbox/archive/refs/tags/v4.1.0.tar.gz",
            "published_at": "2025-11-02T10:00:00Z",
            "assets": [...],  # List of release assets
        }
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            logger.info(f"Checking for updates at {RELEASES_API}")
            response = await client.get(RELEASES_API)
            response.raise_for_status()

            release = response.json()
            latest_version = release["tag_name"].lstrip("v")
            current_version = get_current_version()

            logger.info(f"Current version: {current_version}, Latest version: {latest_version}")

            # Compare versions using semantic versioning
            if parse_version(latest_version) > parse_version(current_version):
                logger.info(f"Update available: {latest_version}")

                # Get download URL (prefer wheel, fallback to source tarball)
                download_url = release["tarball_url"]  # Default to source tarball

                # Check for wheel or sdist in assets
                for asset in release.get("assets", []):
                    if asset["name"].endswith(".whl"):
                        download_url = asset["browser_download_url"]
                        break
                    elif asset["name"].endswith(".tar.gz") and "ignition-toolkit" in asset["name"]:
                        download_url = asset["browser_download_url"]

                return {
                    "current_version": current_version,
                    "latest_version": latest_version,
                    "release_url": release["html_url"],
                    "release_notes": release.get("body", "No release notes available"),
                    "download_url": download_url,
                    "published_at": release["published_at"],
                    "assets": release.get("assets", []),
                    "is_prerelease": release.get("prerelease", False),
                    "is_draft": release.get("draft", False),
                }

            logger.info("No update available (already on latest version)")
            return None

    except httpx.TimeoutException:
        logger.warning("Update check timed out (network slow or unavailable)")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"Update check failed: HTTP {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Failed to check for updates: {e}")
        return None


def check_for_updates_sync() -> dict | None:
    """
    Synchronous version of check_for_updates (for CLI use)

    Returns:
        dict or None: Update information if available
    """
    import asyncio

    try:
        return asyncio.run(check_for_updates())
    except Exception as e:
        logger.error(f"Failed to check for updates: {e}")
        return None
