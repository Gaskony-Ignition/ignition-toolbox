"""
Update Installer Service

Downloads and installs updates via pip.
Handles backup, migration, and rollback.
"""

import asyncio
import logging
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


async def download_update(
    download_url: str,
    progress_callback: Callable[[int, int], None] | None = None
) -> Path:
    """
    Download update archive to temporary directory

    Args:
        download_url: URL to download from (GitHub release tarball/wheel)
        progress_callback: Optional callback(downloaded_bytes, total_bytes)

    Returns:
        Path: Path to downloaded file

    Raises:
        Exception: If download fails
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="ignition-update-"))

    # Determine filename from URL
    filename = download_url.split("/")[-1]
    if not filename.endswith(('.whl', '.tar.gz', '.zip')):
        filename = "update-package.tar.gz"

    archive_path = temp_dir / filename

    logger.info(f"Downloading update from {download_url}")

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("GET", download_url) as response:
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                logger.info(f"Download size: {total_size / 1024 / 1024:.2f} MB")

                with open(archive_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)

        logger.info(f"Download complete: {archive_path}")
        return archive_path

    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise


async def install_update(archive_path: Path) -> bool:
    """
    Install update using pip

    Args:
        archive_path: Path to downloaded package (wheel or source tarball)

    Returns:
        bool: True if installation successful, False otherwise
    """
    try:
        logger.info(f"Installing update from {archive_path}")

        # Use pip to upgrade the package
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "--force-reinstall",  # Force reinstall to ensure all files updated
                str(archive_path)
            ],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=True
        )

        logger.info("Update installation successful")
        logger.debug(f"pip output: {result.stdout}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Update installation failed: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Update installation error: {e}")
        return False


def install_update_sync(archive_path: Path) -> bool:
    """
    Synchronous version of install_update

    Args:
        archive_path: Path to downloaded package

    Returns:
        bool: True if successful
    """
    return asyncio.run(install_update(archive_path))
