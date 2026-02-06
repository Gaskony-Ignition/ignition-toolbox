"""
CloudDesigner API Router

Provides endpoints for managing the browser-accessible Ignition Designer
Docker stack.
"""

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ignition_toolkit.clouddesigner.manager import (
    CloudDesignerManager,
    get_clouddesigner_manager,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/clouddesigner", tags=["clouddesigner"])


# ============================================================================
# Pydantic Models
# ============================================================================


class DockerStatusResponse(BaseModel):
    """Docker daemon status response"""

    installed: bool
    running: bool
    version: str | None = None
    docker_path: str | None = None


class CloudDesignerStatusResponse(BaseModel):
    """CloudDesigner container status response"""

    status: str  # running, exited, paused, not_created, unknown
    port: int | None = None
    error: str | None = None


class StartRequest(BaseModel):
    """Request to start CloudDesigner"""

    gateway_url: str = Field(..., min_length=1, description="Ignition Gateway URL")
    credential_name: str | None = Field(
        None, description="Optional credential name for auto-login"
    )
    force_rebuild: bool = Field(
        False, description="Force a full image rebuild even if cached"
    )


class StartResponse(BaseModel):
    """Response from start operation"""

    success: bool
    output: str | None = None
    error: str | None = None


class StopResponse(BaseModel):
    """Response from stop operation"""

    success: bool
    output: str | None = None
    error: str | None = None


class CleanupResponse(BaseModel):
    """Response from cleanup operation"""

    success: bool
    output: str | None = None
    error: str | None = None


class ConfigResponse(BaseModel):
    """CloudDesigner configuration response"""

    compose_dir: str
    compose_dir_exists: bool
    container_name: str
    default_port: int


class ImageInfo(BaseModel):
    """Status of a single Docker image"""

    exists: bool
    source: str  # "pull" or "build"


class ImageStatusResponse(BaseModel):
    """Status of all required Docker images"""

    images: dict[str, ImageInfo]
    all_ready: bool


class PrepareRequest(BaseModel):
    """Request to prepare (pull/build) images"""

    force_rebuild: bool = Field(
        False, description="Force rebuild of designer-desktop image"
    )


class PrepareResponse(BaseModel):
    """Response from prepare operation"""

    success: bool
    output: str | None = None
    error: str | None = None


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/docker-status", response_model=DockerStatusResponse)
async def get_docker_status():
    """
    Check if Docker is installed and running.

    Returns:
        DockerStatusResponse with installed, running, and version info
    """
    try:
        manager = get_clouddesigner_manager()
        # Run in thread to avoid blocking the event loop during subprocess calls
        status = await asyncio.to_thread(manager.get_docker_status)

        return DockerStatusResponse(
            installed=status.installed,
            running=status.running,
            version=status.version,
            docker_path=status.docker_path,
        )
    except Exception as e:
        logger.exception("Error checking Docker status")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=CloudDesignerStatusResponse)
async def get_status():
    """
    Get CloudDesigner container status.

    Returns:
        CloudDesignerStatusResponse with container status and port
    """
    try:
        manager = get_clouddesigner_manager()
        # Run in thread to avoid blocking the event loop during subprocess calls
        status = await asyncio.to_thread(manager.get_container_status)

        return CloudDesignerStatusResponse(
            status=status.status,
            port=status.port,
            error=status.error,
        )
    except Exception as e:
        logger.exception("Error getting CloudDesigner status")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start", response_model=StartResponse)
async def start_clouddesigner(request: StartRequest):
    """
    Start the CloudDesigner Docker stack.

    Args:
        request: StartRequest with gateway_url and optional credential_name

    Returns:
        StartResponse with success status and output/error
    """
    logger.info("[CloudDesigner API] ===== START REQUEST RECEIVED =====")
    logger.info(f"[CloudDesigner API] Gateway URL: {request.gateway_url}")
    logger.info(f"[CloudDesigner API] Credential: {request.credential_name}")
    try:
        manager = get_clouddesigner_manager()

        # Check Docker first (run in thread to avoid blocking event loop)
        docker_status = await asyncio.to_thread(manager.get_docker_status)
        if not docker_status.installed:
            return StartResponse(
                success=False,
                error="Docker is not installed. Please install Docker Desktop.",
            )
        if not docker_status.running:
            return StartResponse(
                success=False,
                error="Docker is not running. Please start Docker Desktop.",
            )

        # Start the stack in a thread to avoid blocking the event loop
        # This allows health checks to continue responding during long Docker operations
        result = await asyncio.to_thread(
            manager.start,
            gateway_url=request.gateway_url,
            credential_name=request.credential_name,
            force_rebuild=request.force_rebuild,
        )

        return StartResponse(
            success=result["success"],
            output=result.get("output"),
            error=result.get("error"),
        )
    except Exception as e:
        logger.exception(f"[CloudDesigner API] EXCEPTION during start: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=StopResponse)
async def stop_clouddesigner():
    """
    Stop the CloudDesigner Docker stack.

    Returns:
        StopResponse with success status and output/error
    """
    try:
        manager = get_clouddesigner_manager()
        # Run in thread to avoid blocking the event loop
        result = await asyncio.to_thread(manager.stop)

        return StopResponse(
            success=result["success"],
            output=result.get("output"),
            error=result.get("error"),
        )
    except Exception as e:
        logger.exception("Error stopping CloudDesigner")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_clouddesigner():
    """
    Forcefully clean up all CloudDesigner containers, volumes, and images.

    Use this when containers are in a bad state or there are conflicts.

    Returns:
        CleanupResponse with success status and cleanup details
    """
    try:
        logger.info("[CloudDesigner API] Cleanup request received")
        manager = get_clouddesigner_manager()
        # Run in thread to avoid blocking the event loop
        result = await asyncio.to_thread(manager.cleanup)

        return CleanupResponse(
            success=result["success"],
            output=result.get("output"),
            error=result.get("error"),
        )
    except Exception as e:
        logger.exception("Error cleaning up CloudDesigner")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/images", response_model=ImageStatusResponse)
async def get_image_status():
    """
    Check which required Docker images are available locally.

    Returns:
        ImageStatusResponse with per-image status and overall readiness
    """
    try:
        manager = get_clouddesigner_manager()
        status = await asyncio.to_thread(manager.get_image_status)

        return ImageStatusResponse(
            images={
                name: ImageInfo(**info)
                for name, info in status["images"].items()
            },
            all_ready=status["all_ready"],
        )
    except Exception as e:
        logger.exception("Error checking image status")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prepare", response_model=PrepareResponse)
async def prepare_images(request: PrepareRequest):
    """
    Pull base images and build the designer-desktop image.

    This is the long-running step that downloads/builds Docker images.
    Call /images first to check if this is needed.

    Returns:
        PrepareResponse with success status and output
    """
    try:
        manager = get_clouddesigner_manager()

        # Check Docker first
        docker_status = await asyncio.to_thread(manager.get_docker_status)
        if not docker_status.installed:
            return PrepareResponse(
                success=False,
                error="Docker is not installed. Please install Docker Desktop.",
            )
        if not docker_status.running:
            return PrepareResponse(
                success=False,
                error="Docker is not running. Please start Docker Desktop.",
            )

        # Step 1: Pull base images
        logger.info("[CloudDesigner API] Pulling base images...")
        pull_result = await asyncio.to_thread(manager.pull_images)
        if not pull_result["success"]:
            return PrepareResponse(
                success=False,
                error=pull_result.get("error"),
                output=pull_result.get("output"),
            )

        # Step 2: Build designer-desktop image
        logger.info("[CloudDesigner API] Building designer-desktop image...")
        build_result = await asyncio.to_thread(
            manager.build_desktop_image,
            force=request.force_rebuild,
        )

        output_parts = []
        if pull_result.get("output"):
            output_parts.append(pull_result["output"])
        if build_result.get("output"):
            output_parts.append(build_result["output"])

        return PrepareResponse(
            success=build_result["success"],
            output="\n".join(output_parts) if output_parts else None,
            error=build_result.get("error"),
        )
    except Exception as e:
        logger.exception("Error preparing CloudDesigner images")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """
    Get CloudDesigner configuration.

    Returns:
        ConfigResponse with compose directory and container info
    """
    try:
        manager = get_clouddesigner_manager()
        config = manager.get_config()

        return ConfigResponse(
            compose_dir=config["compose_dir"],
            compose_dir_exists=config["compose_dir_exists"],
            container_name=config["container_name"],
            default_port=config["default_port"],
        )
    except Exception as e:
        logger.exception("Error getting CloudDesigner config")
        raise HTTPException(status_code=500, detail=str(e))
