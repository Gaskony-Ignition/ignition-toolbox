"""
Remote Data Updates API Router

Provides generic endpoints for checking and applying updates to
remotely-updatable data components (stack builder catalog, exchange
selectors, etc.).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ignition_toolkit.core.remote_data_registry import RemoteDataRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data-updates", tags=["data-updates"])


class UpdateRequest(BaseModel):
    """Request body for triggering a component update."""
    download_url: str
    checksum: str | None = None


class DismissRequest(BaseModel):
    """Request body for dismissing a notification."""
    pass


# --- Status & Check endpoints ---


@router.get("/status")
async def get_all_status() -> dict[str, Any]:
    """Get status of all registered remote data components."""
    return {
        "components": RemoteDataRegistry.get_all_status(),
    }


@router.get("/check")
async def check_all_updates(force: bool = False) -> dict[str, Any]:
    """
    Check all components for available updates.

    Query params:
        force: Force check even if cache is still fresh.
    """
    # Try to use manifest if available
    manifest_components = None
    try:
        from ignition_toolkit.core.manifest import get_manifest_manager
        manifest = get_manifest_manager()
        manifest_data = await manifest.fetch()
        if manifest_data:
            manifest_components = manifest_data.get("components")
    except ImportError:
        pass
    except Exception as e:
        logger.warning("Failed to fetch manifest for batch check: %s", e)

    results = await RemoteDataRegistry.check_all_updates(
        manifest_components=manifest_components,
        force=force,
    )

    # Format response: only include components with available updates
    updates = {}
    for name, info in results.items():
        if info is not None:
            updates[name] = info

    return {
        "updates_available": len(updates),
        "updates": updates,
    }


# --- Per-component endpoints ---


@router.post("/{component}/update")
async def update_component(component: str, request: UpdateRequest) -> dict[str, Any]:
    """
    Update a specific component by downloading from the provided URL.

    Path params:
        component: Component name (e.g., "stackbuilder_catalog").
    """
    manager = RemoteDataRegistry.get(component)
    if not manager:
        raise HTTPException(status_code=404, detail=f"Unknown component: {component}")

    success = await manager.update(
        download_url=request.download_url,
        expected_checksum=request.checksum,
    )

    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to update {component}")

    return {
        "success": True,
        "component": component,
        "metadata": manager.get_metadata(),
    }


@router.post("/{component}/revert")
async def revert_component(component: str) -> dict[str, Any]:
    """
    Revert a component to its bundled version.

    Path params:
        component: Component name.
    """
    manager = RemoteDataRegistry.get(component)
    if not manager:
        raise HTTPException(status_code=404, detail=f"Unknown component: {component}")

    reverted = manager.revert_to_bundled()

    return {
        "success": True,
        "reverted": reverted,
        "component": component,
        "metadata": manager.get_metadata(),
    }


# --- Notification endpoints (Phase 3) ---


@router.get("/notifications")
async def get_notifications() -> dict[str, Any]:
    """Get active notifications for the current app version."""
    try:
        from ignition_toolkit.core.manifest import get_manifest_manager
        manifest = get_manifest_manager()
        notifications = await manifest.get_active_notifications()
        return {"notifications": notifications}
    except ImportError:
        return {"notifications": []}
    except Exception as e:
        logger.warning("Failed to get notifications: %s", e)
        return {"notifications": []}


@router.post("/notifications/{notification_id}/dismiss")
async def dismiss_notification(notification_id: str) -> dict[str, Any]:
    """Dismiss a notification by ID."""
    try:
        from ignition_toolkit.core.manifest import get_manifest_manager
        manifest = get_manifest_manager()
        manifest.dismiss_notification(notification_id)
        return {"success": True, "notification_id": notification_id}
    except ImportError:
        raise HTTPException(status_code=501, detail="Manifest system not available")
    except Exception as e:
        logger.error("Failed to dismiss notification: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
