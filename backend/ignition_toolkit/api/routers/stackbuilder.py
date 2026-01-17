"""
Stack Builder routes

Provides endpoints for building Docker Compose stacks with
automatic service integration detection and configuration generation.
"""

import logging
import re
from functools import lru_cache
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ignition_toolkit.stackbuilder.catalog import get_service_catalog
from ignition_toolkit.stackbuilder.compose_generator import (
    ComposeGenerator,
    GlobalSettings,
    IntegrationSettings,
)
from ignition_toolkit.stackbuilder.integration_engine import get_integration_engine
from ignition_toolkit.storage.database import get_database
from ignition_toolkit.storage.models import SavedStackModel

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/stackbuilder", tags=["stackbuilder"])


# ============================================================================
# Pydantic Models
# ============================================================================


class InstanceConfig(BaseModel):
    """Configuration for a single service instance"""

    app_id: str
    instance_name: str
    config: dict[str, Any] = Field(default_factory=dict)


class GlobalSettingsRequest(BaseModel):
    """Global settings for the entire stack"""

    stack_name: str = "iiot-stack"
    timezone: str = "UTC"
    restart_policy: str = "unless-stopped"


class IntegrationSettingsRequest(BaseModel):
    """Settings for automatic integrations"""

    reverse_proxy: dict[str, Any] | None = None
    mqtt: dict[str, Any] | None = None
    oauth: dict[str, Any] | None = None
    database: dict[str, Any] | None = None
    email: dict[str, Any] | None = None


class StackConfig(BaseModel):
    """Complete stack configuration"""

    instances: list[InstanceConfig]
    global_settings: GlobalSettingsRequest | None = None
    integration_settings: IntegrationSettingsRequest | None = None


class SavedStackCreate(BaseModel):
    """Request to save a stack configuration"""

    stack_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    config_json: dict[str, Any]
    global_settings: dict[str, Any] | None = None


class SavedStackInfo(BaseModel):
    """Saved stack information"""

    id: int
    stack_name: str
    description: str | None
    config_json: dict[str, Any]
    global_settings: dict[str, Any] | None
    created_at: str | None
    updated_at: str | None


# ============================================================================
# Docker Hub Integration
# ============================================================================


@lru_cache(maxsize=128)
def _fetch_docker_tags(repository: str, limit: int = 100) -> list[str]:
    """Fetch available tags from Docker Hub"""
    try:
        url = f"https://hub.docker.com/v2/repositories/{repository}/tags"
        params = {"page_size": limit, "ordering": "-name"}

        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()

        data = response.json()
        return [tag["name"] for tag in data.get("results", [])]
    except Exception as e:
        logger.error(f"Error fetching Docker tags for {repository}: {e}")
        return []


def _get_ignition_versions() -> list[str]:
    """Get available Ignition versions from Docker Hub"""
    all_tags = _fetch_docker_tags("inductiveautomation/ignition", limit=200)

    # Filter for version tags (8.x.x format)
    version_pattern = re.compile(r"^8\.\d+\.\d+$")
    versions = [tag for tag in all_tags if version_pattern.match(tag)]

    # Sort versions (newest first)
    def version_key(v: str) -> tuple[int, int, int]:
        parts = v.split(".")
        return (int(parts[0]), int(parts[1]), int(parts[2]))

    versions.sort(key=version_key, reverse=True)

    return ["latest"] + versions[:20]


def _get_postgres_versions() -> list[str]:
    """Get available PostgreSQL versions"""
    all_tags = _fetch_docker_tags("library/postgres", limit=100)

    version_pattern = re.compile(r"^(\d+)(-alpine)?$")
    versions = [tag for tag in all_tags if version_pattern.match(tag)]

    return ["latest"] + versions[:15]


# ============================================================================
# Catalog Routes
# ============================================================================


@router.get("/catalog")
async def get_catalog():
    """Get the service catalog"""
    catalog = get_service_catalog()
    return catalog.catalog


@router.get("/catalog/applications")
async def get_applications():
    """Get enabled applications from catalog"""
    catalog = get_service_catalog()
    return catalog.get_enabled_applications()


@router.get("/catalog/categories")
async def get_categories():
    """Get application categories"""
    catalog = get_service_catalog()
    return catalog.get_categories()


@router.get("/catalog/applications/{app_id}")
async def get_application(app_id: str):
    """Get a specific application by ID"""
    catalog = get_service_catalog()
    app = catalog.get_application_by_id(app_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' not found")
    return app


@router.get("/versions/{app_id}")
async def get_versions(app_id: str):
    """Get available Docker image versions for an application"""
    try:
        if app_id == "ignition":
            versions = _get_ignition_versions()
        elif app_id == "postgres":
            versions = _get_postgres_versions()
        else:
            catalog = get_service_catalog()
            app = catalog.get_application_by_id(app_id)
            if app and "image" in app:
                versions = _fetch_docker_tags(app["image"], limit=50)
                if not versions:
                    versions = app.get("available_versions", ["latest"])
            else:
                versions = ["latest"]

        return {"versions": versions}
    except Exception as e:
        logger.error(f"Error fetching versions for {app_id}: {e}")
        return {"versions": ["latest"]}


# ============================================================================
# Integration Detection Routes
# ============================================================================


@router.post("/detect-integrations")
async def detect_integrations(stack_config: StackConfig):
    """
    Detect possible integrations, conflicts, and recommendations
    based on selected services
    """
    try:
        instances = [
            {
                "app_id": inst.app_id,
                "instance_name": inst.instance_name,
                "config": inst.config,
            }
            for inst in stack_config.instances
        ]

        engine = get_integration_engine()
        detection_result = engine.detect_integrations(instances)
        detection_result["summary"] = engine.get_integration_summary(detection_result)

        return detection_result

    except Exception as e:
        logger.error(f"Error detecting integrations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Generation Routes
# ============================================================================


@router.post("/generate")
async def generate_stack(stack_config: StackConfig):
    """Generate docker-compose.yml and configuration files"""
    try:
        instances = [
            {
                "app_id": inst.app_id,
                "instance_name": inst.instance_name,
                "config": inst.config,
            }
            for inst in stack_config.instances
        ]

        global_settings = None
        if stack_config.global_settings:
            global_settings = GlobalSettings(
                stack_name=stack_config.global_settings.stack_name,
                timezone=stack_config.global_settings.timezone,
                restart_policy=stack_config.global_settings.restart_policy,
            )

        integration_settings = None
        if stack_config.integration_settings:
            integration_settings = IntegrationSettings(
                reverse_proxy=stack_config.integration_settings.reverse_proxy,
                mqtt=stack_config.integration_settings.mqtt,
                oauth=stack_config.integration_settings.oauth,
                database=stack_config.integration_settings.database,
                email=stack_config.integration_settings.email,
            )

        generator = ComposeGenerator()
        result = generator.generate(instances, global_settings, integration_settings)

        return {
            "docker_compose": result["docker_compose"],
            "env": result["env"],
            "readme": result["readme"],
            "config_files": result["config_files"],
        }

    except Exception as e:
        logger.error(f"Error generating stack: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download")
async def download_stack(stack_config: StackConfig):
    """Download complete stack as ZIP file"""
    try:
        instances = [
            {
                "app_id": inst.app_id,
                "instance_name": inst.instance_name,
                "config": inst.config,
            }
            for inst in stack_config.instances
        ]

        global_settings = None
        if stack_config.global_settings:
            global_settings = GlobalSettings(
                stack_name=stack_config.global_settings.stack_name,
                timezone=stack_config.global_settings.timezone,
                restart_policy=stack_config.global_settings.restart_policy,
            )

        integration_settings = None
        if stack_config.integration_settings:
            integration_settings = IntegrationSettings(
                reverse_proxy=stack_config.integration_settings.reverse_proxy,
                mqtt=stack_config.integration_settings.mqtt,
                oauth=stack_config.integration_settings.oauth,
                database=stack_config.integration_settings.database,
                email=stack_config.integration_settings.email,
            )

        generator = ComposeGenerator()
        zip_content = generator.generate_zip(instances, global_settings, integration_settings)

        stack_name = "iiot-stack"
        if global_settings:
            stack_name = global_settings.stack_name

        return StreamingResponse(
            iter([zip_content]),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{stack_name}.zip"'
            },
        )

    except Exception as e:
        logger.error(f"Error downloading stack: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Saved Stacks Routes
# ============================================================================


@router.get("/stacks", response_model=list[SavedStackInfo])
async def list_saved_stacks():
    """List all saved stack configurations"""
    try:
        db = get_database()
        with db.session_scope() as session:
            stacks = session.query(SavedStackModel).order_by(
                SavedStackModel.updated_at.desc()
            ).all()
            return [stack.to_dict() for stack in stacks]
    except Exception as e:
        logger.error(f"Error listing saved stacks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stacks", response_model=SavedStackInfo)
async def save_stack(request: SavedStackCreate):
    """Save a stack configuration"""
    try:
        db = get_database()
        with db.session_scope() as session:
            # Check if name already exists
            existing = session.query(SavedStackModel).filter(
                SavedStackModel.stack_name == request.stack_name
            ).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stack with name '{request.stack_name}' already exists",
                )

            stack = SavedStackModel(
                stack_name=request.stack_name,
                description=request.description,
                config_json=request.config_json,
                global_settings=request.global_settings,
            )
            session.add(stack)
            session.flush()
            return stack.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving stack: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stacks/{stack_id}", response_model=SavedStackInfo)
async def get_saved_stack(stack_id: int):
    """Get a saved stack by ID"""
    try:
        db = get_database()
        with db.session_scope() as session:
            stack = session.query(SavedStackModel).filter(
                SavedStackModel.id == stack_id
            ).first()
            if not stack:
                raise HTTPException(
                    status_code=404, detail=f"Stack with ID {stack_id} not found"
                )
            return stack.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stack: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/stacks/{stack_id}", response_model=SavedStackInfo)
async def update_saved_stack(stack_id: int, request: SavedStackCreate):
    """Update a saved stack configuration"""
    try:
        db = get_database()
        with db.session_scope() as session:
            stack = session.query(SavedStackModel).filter(
                SavedStackModel.id == stack_id
            ).first()
            if not stack:
                raise HTTPException(
                    status_code=404, detail=f"Stack with ID {stack_id} not found"
                )

            stack.stack_name = request.stack_name
            stack.description = request.description
            stack.config_json = request.config_json
            stack.global_settings = request.global_settings
            session.flush()
            return stack.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating stack: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/stacks/{stack_id}")
async def delete_saved_stack(stack_id: int):
    """Delete a saved stack"""
    try:
        db = get_database()
        with db.session_scope() as session:
            stack = session.query(SavedStackModel).filter(
                SavedStackModel.id == stack_id
            ).first()
            if not stack:
                raise HTTPException(
                    status_code=404, detail=f"Stack with ID {stack_id} not found"
                )

            session.delete(stack)
            return {"message": "Stack deleted successfully", "id": stack_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting stack: {e}")
        raise HTTPException(status_code=500, detail=str(e))
