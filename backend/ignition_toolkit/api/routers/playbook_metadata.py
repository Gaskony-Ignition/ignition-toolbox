"""
Playbook metadata operations router

Handles playbook metadata operations: verify/unverify, enable/disable.
"""

import logging

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# ============================================================================
# Helper Functions
# ============================================================================


def get_metadata_store():
    """Get shared metadata store from app"""
    from ignition_toolkit.api.app import metadata_store
    return metadata_store


def get_relative_playbook_path(path_str: str) -> str:
    """
    Convert a playbook path (full or relative) to a relative path from playbooks directory

    SECURITY: Validates path before conversion to prevent traversal attacks.

    Args:
        path_str: User-provided playbook path (can be full or relative)

    Returns:
        Relative path string from playbooks directory (e.g., "gateway/reset_gateway_trial.yaml")
    """
    from pathlib import Path

    from ignition_toolkit.core.paths import get_all_playbook_dirs
    from ignition_toolkit.core.validation import PathValidator

    # Search all playbook directories (user first, then built-in)
    for playbook_dir in get_all_playbook_dirs():
        try:
            validated_path = PathValidator.validate_playbook_path(
                path_str,
                base_dir=playbook_dir.resolve(),
                must_exist=False  # Metadata operations might reference deleted playbooks
            )
            relative_path = validated_path.relative_to(playbook_dir.resolve())
            return str(relative_path)
        except HTTPException:
            continue

    # Fallback: if path looks safe, return as-is (for deleted playbooks)
    if ".." not in path_str and not Path(path_str).is_absolute():
        return path_str
    raise HTTPException(
        status_code=400,
        detail="Invalid playbook path - must be relative path within playbooks directory"
    )


# ============================================================================
# Routes
# ============================================================================


@router.post("/{playbook_path:path}/verify")
async def mark_playbook_verified(playbook_path: str):
    """Mark a playbook as verified"""
    metadata_store = get_metadata_store()
    try:
        relative_path = get_relative_playbook_path(playbook_path)
        metadata_store.mark_verified(relative_path, verified_by="user")
        meta = metadata_store.get_metadata(relative_path)
        return {
            "status": "success",
            "playbook_path": playbook_path,
            "verified": meta.verified,
            "verified_at": meta.verified_at,
            "message": "Playbook marked as verified",
        }
    except Exception as e:
        logger.error(f"Error marking playbook as verified: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{playbook_path:path}/unverify")
async def unmark_playbook_verified(playbook_path: str):
    """Unmark a playbook as verified"""
    metadata_store = get_metadata_store()
    try:
        relative_path = get_relative_playbook_path(playbook_path)
        metadata_store.unmark_verified(relative_path)
        return {
            "status": "success",
            "playbook_path": playbook_path,
            "verified": False,
            "message": "Playbook verification removed",
        }
    except Exception as e:
        logger.error(f"Error unmarking playbook as verified: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{playbook_path:path}/enable")
async def enable_playbook(playbook_path: str):
    """Enable a playbook"""
    metadata_store = get_metadata_store()
    try:
        relative_path = get_relative_playbook_path(playbook_path)
        metadata_store.set_enabled(relative_path, True)
        return {
            "status": "success",
            "playbook_path": playbook_path,
            "enabled": True,
            "message": "Playbook enabled",
        }
    except Exception as e:
        logger.error(f"Error enabling playbook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{playbook_path:path}/disable")
async def disable_playbook(playbook_path: str):
    """Disable a playbook"""
    metadata_store = get_metadata_store()
    try:
        relative_path = get_relative_playbook_path(playbook_path)
        metadata_store.set_enabled(relative_path, False)
        return {
            "status": "success",
            "playbook_path": playbook_path,
            "enabled": False,
            "message": "Playbook disabled",
        }
    except Exception as e:
        logger.error(f"Error disabling playbook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-all")
async def reset_all_metadata():
    """Reset all playbook metadata (clears verification states, etc.)"""
    metadata_store = get_metadata_store()
    try:
        metadata_store.reset_all()
        return {
            "status": "success",
            "message": "All playbook metadata has been reset",
        }
    except Exception as e:
        logger.error(f"Error resetting metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))
