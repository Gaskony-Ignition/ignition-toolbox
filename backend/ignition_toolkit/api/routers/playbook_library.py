"""
Playbook library router (v5.0 - Plugin Architecture)

Handles playbook discovery, installation, updates, and uninstallation
from the central repository.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================


class PlaybookInstallRequest(BaseModel):
    """Request to install a playbook"""
    playbook_path: str  # e.g., "gateway/module_upgrade"
    version: str = "latest"
    verify_checksum: bool = True


# ============================================================================
# Routes
# ============================================================================


@router.get("/browse")
async def browse_available_playbooks(force_refresh: bool = False):
    """
    Browse playbooks available in the central repository

    Args:
        force_refresh: Force refresh from GitHub (ignore cache)

    Returns:
        List of available playbooks with metadata
    """
    try:
        from ignition_toolkit.playbook.registry import PlaybookRegistry

        registry = PlaybookRegistry()
        registry.load()

        try:
            await registry.fetch_available_playbooks(force_refresh=force_refresh)
        except Exception as fetch_error:
            logger.warning(f"Could not fetch playbook library from remote: {fetch_error}")
            # Continue with cached/empty data - don't fail the whole request

        available = registry.get_available_playbooks(include_installed=False)

        playbooks = [
            {
                "playbook_path": pb.playbook_path,
                "version": pb.version,
                "domain": pb.domain,
                "verified": pb.verified,
                "verified_by": pb.verified_by,
                "description": pb.description,
                "author": pb.author,
                "tags": pb.tags,
                "group": pb.group,
                "size_bytes": pb.size_bytes,
                "dependencies": pb.dependencies,
                "release_notes": pb.release_notes,
            }
            for pb in available
        ]

        return {
            "status": "success",
            "count": len(playbooks),
            "playbooks": playbooks,
            "last_fetched": registry.last_fetched,
            "message": "Playbook library is not yet available. Check back later or create your own playbooks." if len(playbooks) == 0 else None,
        }

    except Exception as e:
        logger.exception(f"Error browsing available playbooks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/install")
async def install_playbook(request: PlaybookInstallRequest):
    """
    Install a playbook from the repository

    Downloads the playbook, verifies checksum, and installs to user directory.
    """
    try:
        from ignition_toolkit.playbook.installer import PlaybookInstaller, PlaybookInstallError

        installer = PlaybookInstaller()

        installed_path = await installer.install_playbook(
            playbook_path=request.playbook_path,
            version=request.version,
            verify_checksum=request.verify_checksum
        )

        return {
            "status": "success",
            "message": f"Playbook {request.playbook_path} installed successfully",
            "playbook_path": request.playbook_path,
            "installed_at": str(installed_path),
        }

    except Exception as e:
        if "PlaybookInstallError" in str(type(e).__name__):
            raise HTTPException(status_code=400, detail=str(e))
        logger.exception(f"Error installing playbook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{playbook_path:path}/uninstall")
async def uninstall_playbook(playbook_path: str, force: bool = False):
    """
    Uninstall a playbook

    Args:
        playbook_path: Playbook path (e.g., "gateway/module_upgrade")
        force: Force uninstall even if built-in (dangerous!)
    """
    try:
        from ignition_toolkit.playbook.installer import PlaybookInstaller, PlaybookInstallError

        installer = PlaybookInstaller()

        success = await installer.uninstall_playbook(
            playbook_path=playbook_path,
            force=force
        )

        if not success:
            raise HTTPException(status_code=404, detail=f"Playbook {playbook_path} not found")

        return {
            "status": "success",
            "message": f"Playbook {playbook_path} uninstalled successfully",
            "playbook_path": playbook_path,
        }

    except Exception as e:
        if "PlaybookInstallError" in str(type(e).__name__):
            raise HTTPException(status_code=400, detail=str(e))
        if isinstance(e, HTTPException):
            raise
        logger.exception(f"Error uninstalling playbook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{playbook_path:path}/update")
async def update_playbook_to_latest(playbook_path: str):
    """
    Update a playbook to the latest version

    Args:
        playbook_path: Playbook path (e.g., "gateway/module_upgrade")
    """
    try:
        from ignition_toolkit.playbook.installer import PlaybookInstaller, PlaybookInstallError

        installer = PlaybookInstaller()

        updated_path = await installer.update_playbook(playbook_path=playbook_path)

        return {
            "status": "success",
            "message": f"Playbook {playbook_path} updated successfully",
            "playbook_path": playbook_path,
            "installed_at": str(updated_path),
        }

    except Exception as e:
        if "PlaybookInstallError" in str(type(e).__name__):
            raise HTTPException(status_code=400, detail=str(e))
        logger.exception(f"Error updating playbook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/updates")
async def check_for_updates(force_refresh: bool = False):
    """
    Check for available playbook updates

    Compares installed playbooks against available versions in the repository.
    Automatically refreshes from GitHub when cache is stale (1 hour TTL).

    Args:
        force_refresh: Force refresh from GitHub (ignore cache)

    Returns:
        Update check results with detailed information for each update
    """
    try:
        from ignition_toolkit.playbook.update_checker import PlaybookUpdateChecker

        checker = PlaybookUpdateChecker()

        # Always refresh (uses cache TTL internally, so this is cheap when fresh)
        await checker.refresh(force=force_refresh)

        result = checker.check_for_updates()

        updates = [
            {
                "playbook_path": update.playbook_path,
                "current_version": update.current_version,
                "latest_version": update.latest_version,
                "description": update.description,
                "release_notes": update.release_notes,
                "domain": update.domain,
                "verified": update.verified,
                "verified_by": update.verified_by,
                "size_bytes": update.size_bytes,
                "author": update.author,
                "tags": update.tags,
                "is_major_update": update.is_major_update,
                "version_diff": update.version_diff,
                "download_url": update.download_url,
                "checksum": update.checksum,
            }
            for update in result.updates
        ]

        return {
            "status": "success",
            "checked_at": result.checked_at,
            "total_playbooks": result.total_playbooks,
            "updates_available": result.updates_available,
            "has_updates": result.has_updates,
            "last_fetched": result.last_fetched,
            "updates": updates,
            "major_updates": len(result.major_updates),
            "minor_updates": len(result.minor_updates),
        }

    except Exception as e:
        logger.exception(f"Error checking for updates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/updates/stats")
async def get_update_stats():
    """
    Get update statistics

    Returns summary statistics about available updates.
    Automatically refreshes from GitHub when cache is stale (1 hour TTL).
    """
    try:
        from ignition_toolkit.playbook.update_checker import PlaybookUpdateChecker

        checker = PlaybookUpdateChecker()

        # Auto-refresh (uses cache TTL internally, so this is cheap when fresh)
        await checker.refresh()

        result = checker.check_for_updates()

        updates_by_domain = {}
        for update in result.updates:
            domain = update.domain
            if domain not in updates_by_domain:
                updates_by_domain[domain] = []
            updates_by_domain[domain].append(update)

        verified_updates = checker.get_verified_updates()

        return {
            "status": "success",
            "checked_at": result.checked_at,
            "total_installed": result.total_playbooks,
            "total_updates_available": result.updates_available,
            "has_updates": result.has_updates,
            "major_updates": len(result.major_updates),
            "minor_updates": len(result.minor_updates),
            "verified_updates": len(verified_updates),
            "updates_by_domain": {
                domain: len(updates)
                for domain, updates in updates_by_domain.items()
            },
            "last_fetched": result.last_fetched,
        }

    except Exception as e:
        logger.exception(f"Error getting update stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/updates/{playbook_path:path}")
async def check_playbook_update(playbook_path: str):
    """
    Check for update for a specific playbook

    Args:
        playbook_path: Playbook path (e.g., "gateway/module_upgrade")

    Returns:
        Update information if available, or null if no update
    """
    try:
        from ignition_toolkit.playbook.update_checker import PlaybookUpdateChecker

        checker = PlaybookUpdateChecker()
        update = checker.get_update(playbook_path)

        if not update:
            return {
                "status": "success",
                "has_update": False,
                "playbook_path": playbook_path,
                "message": "No update available",
            }

        return {
            "status": "success",
            "has_update": True,
            "playbook_path": update.playbook_path,
            "current_version": update.current_version,
            "latest_version": update.latest_version,
            "description": update.description,
            "release_notes": update.release_notes,
            "domain": update.domain,
            "verified": update.verified,
            "verified_by": update.verified_by,
            "size_bytes": update.size_bytes,
            "author": update.author,
            "tags": update.tags,
            "is_major_update": update.is_major_update,
            "version_diff": update.version_diff,
        }

    except Exception as e:
        logger.exception(f"Error checking update for {playbook_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
