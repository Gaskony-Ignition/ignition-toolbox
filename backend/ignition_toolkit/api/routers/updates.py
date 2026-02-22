"""
Update Management API Endpoints

Provides endpoints for checking and installing updates.

Version: 4.1.0
"""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from ignition_toolkit.update.backup import backup_user_data, list_backups, restore_backup
from ignition_toolkit.update.checker import check_for_updates, get_current_version
from ignition_toolkit.update.installer import download_update, install_update

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/updates", tags=["updates"])


# ==============================================================================
# Request/Response Models
# ==============================================================================

class UpdateCheckResponse(BaseModel):
    """Response for update check"""
    update_available: bool
    current_version: str
    latest_version: Optional[str] = None
    release_url: Optional[str] = None
    release_notes: Optional[str] = None
    download_url: Optional[str] = None
    published_at: Optional[str] = None


class UpdateInstallRequest(BaseModel):
    """Request to install update"""
    version: str  # Version to install


class UpdateStatusResponse(BaseModel):
    """Response for update status"""
    status: str  # 'idle', 'downloading', 'installing', 'migrating', 'complete', 'failed'
    progress: int  # 0-100
    message: str
    version: Optional[str] = None
    error: Optional[str] = None


class BackupResponse(BaseModel):
    """Response for backup operations"""
    backup_path: str
    created_at: str
    files_count: int


# ==============================================================================
# Update Status Tracking (simple in-memory for now)
# ==============================================================================

update_status = {
    "status": "idle",
    "progress": 0,
    "message": "No update in progress",
    "version": None,
    "error": None,
}


def update_progress(status: str, progress: int, message: str, version: Optional[str] = None, error: Optional[str] = None):
    """Update the global update status"""
    update_status["status"] = status
    update_status["progress"] = progress
    update_status["message"] = message
    update_status["version"] = version
    update_status["error"] = error
    logger.info(f"Update status: {status} ({progress}%) - {message}")


# ==============================================================================
# API Endpoints
# ==============================================================================

@router.get("/check", response_model=UpdateCheckResponse)
async def check_updates():
    """
    Check for available updates from GitHub Releases

    Returns:
        UpdateCheckResponse: Update information
    """
    logger.info("Checking for updates...")

    update_info = await check_for_updates()

    if update_info:
        return UpdateCheckResponse(
            update_available=True,
            current_version=update_info["current_version"],
            latest_version=update_info["latest_version"],
            release_url=update_info["release_url"],
            release_notes=update_info["release_notes"],
            download_url=update_info["download_url"],
            published_at=update_info["published_at"],
        )

    return UpdateCheckResponse(
        update_available=False,
        current_version=get_current_version()
    )


@router.post("/install")
async def install_update_endpoint(background_tasks: BackgroundTasks):
    """
    Start update installation in background

    This endpoint initiates the update process which includes:
    1. Checking for updates
    2. Backing up user data
    3. Downloading the update
    4. Installing via pip
    5. Running database migrations
    6. Scheduling server restart

    Returns:
        dict: Status indicating update has started
    """
    # Check if update already in progress
    if update_status["status"] not in ["idle", "complete", "failed"]:
        raise HTTPException(
            status_code=409,
            detail=f"Update already in progress: {update_status['status']}"
        )

    # Check if update is available
    update_info = await check_for_updates()

    if not update_info:
        raise HTTPException(status_code=400, detail="No update available")

    # Start update in background
    background_tasks.add_task(
        perform_update,
        update_info["download_url"],
        update_info["latest_version"]
    )

    return {
        "status": "update_started",
        "version": update_info["latest_version"],
        "message": "Update installation started in background"
    }


@router.get("/status", response_model=UpdateStatusResponse)
async def get_update_status():
    """
    Get current update status

    Returns:
        UpdateStatusResponse: Current update progress
    """
    return UpdateStatusResponse(**update_status)


@router.get("/backups")
async def list_available_backups():
    """
    List available backups

    Returns:
        list: List of backup directories
    """
    backups = list_backups()

    return {
        "backups": [
            {
                "path": str(backup),
                "name": backup.name,
                "created_at": backup.stat().st_mtime,
            }
            for backup in backups
        ]
    }


@router.post("/rollback")
async def rollback_update():
    """
    Rollback to previous version using latest backup

    Returns:
        dict: Status of rollback operation
    """
    backups = list_backups()

    if not backups:
        raise HTTPException(status_code=404, detail="No backups found")

    latest_backup = backups[0]

    logger.info(f"Rolling back to backup: {latest_backup}")

    if restore_backup(latest_backup):
        return {
            "status": "rollback_complete",
            "backup_used": str(latest_backup),
            "message": "Successfully rolled back to previous version. Please restart the server."
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Rollback failed. Check logs for details."
        )


# ==============================================================================
# Background Task
# ==============================================================================

async def perform_update(download_url: str, version: str):
    """
    Background task to perform the actual update

    Args:
        download_url: URL to download update from
        version: Version being installed
    """
    try:
        update_progress("backing_up", 10, "Backing up user data...", version)

        # Step 1: Backup user data
        backup_dir = backup_user_data()
        logger.info(f"Backup created at {backup_dir}")

        update_progress("downloading", 30, "Downloading update...", version)

        # Step 2: Download update
        def progress_callback(downloaded, total):
            if total > 0:
                progress = 30 + int((downloaded / total) * 40)  # 30-70%
                update_progress("downloading", progress, f"Downloading... {downloaded}/{total} bytes", version)

        archive_path = await download_update(download_url, progress_callback)

        update_progress("installing", 70, "Installing update...", version)

        # Step 3: Install update
        success = await install_update(archive_path)

        if not success:
            update_progress("failed", 0, "Update installation failed", version, "pip install failed")
            logger.error("Update installation failed")
            return

        # Step 4: Database migrations are additive and handled by SQLAlchemy
        # on next startup — no explicit migration step needed at this time.
        update_progress("complete", 100, f"Update to v{version} complete! Restart the app to apply.", version)

        logger.info(f"Update to v{version} complete — restart required")

    except Exception as e:
        logger.error(f"Update failed: {e}", exc_info=True)
        update_progress("failed", 0, f"Update failed: {str(e)}", version, str(e))

        # Try to restore backup
        try:
            backups = list_backups()
            if backups:
                logger.info("Attempting automatic rollback...")
                restore_backup(backups[0])
                update_progress("failed", 0, "Update failed, backup restored", version, str(e))
        except Exception as rollback_error:
            logger.error(f"Rollback also failed: {rollback_error}")
