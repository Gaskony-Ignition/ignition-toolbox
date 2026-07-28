"""
Stack Builder API Router

Provides endpoints for building Docker Compose stacks with
automatic service integration detection and configuration generation.
"""

import io
import logging
import re
import zipfile
from functools import lru_cache

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ignition_toolkit.api.routers.stackbuilder.installer_scripts import (
    DOCKER_INSTALL_LINUX,
    DOCKER_INSTALL_WINDOWS,
)
from ignition_toolkit.api.routers.stackbuilder.models import (
    DeploymentResult,
    DeploymentStatus,
    DeployStackRequest,
    SavedStackCreate,
    SavedStackInfo,
    StackConfig,
)
from ignition_toolkit.stackbuilder.catalog import get_service_catalog
from ignition_toolkit.stackbuilder.compose_generator import (
    ComposeGenerator,
    GlobalSettings,
    IntegrationSettings,
)
from ignition_toolkit.stackbuilder.exceptions import StackBuilderError
from ignition_toolkit.stackbuilder.integration_engine import get_integration_engine
from ignition_toolkit.stackbuilder.stack_runner import get_stack_runner
from ignition_toolkit.storage.database import get_database
from ignition_toolkit.storage.models import SavedStackModel

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/stackbuilder", tags=["stackbuilder"])


# ============================================================================
# Helper Functions
# ============================================================================


def _convert_stack_config(
    stack_config: StackConfig,
) -> tuple[list[dict], GlobalSettings | None, IntegrationSettings | None]:
    """
    Convert Pydantic StackConfig to generator-compatible format.

    Args:
        stack_config: The StackConfig from the API request

    Returns:
        Tuple of (instances list, global settings, integration settings)
    """
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

    return instances, global_settings, integration_settings


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
        instances, _, _ = _convert_stack_config(stack_config)
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
        instances, global_settings, integration_settings = _convert_stack_config(stack_config)
        generator = ComposeGenerator()
        result = generator.generate(instances, global_settings, integration_settings)

        return {
            "docker_compose": result["docker_compose"],
            "env": result["env"],
            "readme": result["readme"],
            "config_files": result["config_files"],
        }

    except StackBuilderError as e:
        # Validation problem with the requested stack (e.g. two reverse
        # proxies selected) - the client's config is at fault, not the server.
        logger.info(f"Rejected invalid stack configuration: {e}")
        raise HTTPException(status_code=422, detail=e.message)
    except Exception as e:
        logger.error(f"Error generating stack: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download")
async def download_stack(stack_config: StackConfig):
    """Download complete stack as ZIP file"""
    try:
        instances, global_settings, integration_settings = _convert_stack_config(stack_config)
        generator = ComposeGenerator()
        zip_content = generator.generate_zip(instances, global_settings, integration_settings)

        stack_name = global_settings.stack_name if global_settings else "iiot-stack"

        return StreamingResponse(
            iter([zip_content]),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{stack_name}.zip"'},
        )

    except StackBuilderError as e:
        logger.info(f"Rejected invalid stack configuration: {e}")
        raise HTTPException(status_code=422, detail=e.message)
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
            stacks = (
                session.query(SavedStackModel).order_by(SavedStackModel.updated_at.desc()).all()
            )
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
            existing = (
                session.query(SavedStackModel)
                .filter(SavedStackModel.stack_name == request.stack_name)
                .first()
            )
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
            stack = session.query(SavedStackModel).filter(SavedStackModel.id == stack_id).first()
            if not stack:
                raise HTTPException(status_code=404, detail=f"Stack with ID {stack_id} not found")
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
            stack = session.query(SavedStackModel).filter(SavedStackModel.id == stack_id).first()
            if not stack:
                raise HTTPException(status_code=404, detail=f"Stack with ID {stack_id} not found")

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
            stack = session.query(SavedStackModel).filter(SavedStackModel.id == stack_id).first()
            if not stack:
                raise HTTPException(status_code=404, detail=f"Stack with ID {stack_id} not found")

            session.delete(stack)
            return {"message": "Stack deleted successfully", "id": stack_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting stack: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Docker Installer Downloads
# ============================================================================


@router.get("/download/docker-installer/linux")
async def download_docker_installer_linux():
    """Download Docker installation script for Linux"""
    return StreamingResponse(
        iter([DOCKER_INSTALL_LINUX.encode()]),
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="install-docker-linux.sh"'},
    )


@router.get("/download/docker-installer/windows")
async def download_docker_installer_windows():
    """Download Docker installation script for Windows"""
    return StreamingResponse(
        iter([DOCKER_INSTALL_WINDOWS.encode()]),
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="install-docker-windows.ps1"'},
    )


# ============================================================================
# Offline Bundle Generation
# ============================================================================


@router.post("/generate-offline-bundle")
async def generate_offline_bundle(stack_config: StackConfig):
    """
    Generate an offline deployment bundle including:
    - Docker Compose files
    - Image pull script (for connected system)
    - Image load script (for offline system)
    - README with instructions
    """
    try:
        instances, global_settings, integration_settings = _convert_stack_config(stack_config)
        generator = ComposeGenerator()
        result = generator.generate(instances, global_settings, integration_settings)

        # Collect images from the compose output
        catalog = get_service_catalog()
        catalog_dict = catalog.get_application_as_dict()

        images = []
        for inst in instances:
            app = catalog_dict.get(inst["app_id"])
            if app and app.get("enabled", False):
                version = inst.get("config", {}).get(
                    "version", app.get("default_version", "latest")
                )
                images.append(f"{app['image']}:{version}")

        # Generate pull script
        pull_script = _generate_pull_script(images)
        load_script = _generate_load_script()
        offline_readme = _generate_offline_readme(global_settings, images)

        # Create ZIP file
        stack_name = global_settings.stack_name if global_settings else "iiot-stack"
        zip_buffer = _create_offline_zip(
            result, pull_script, load_script, offline_readme, stack_name
        )

        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{stack_name}-offline.zip"'},
        )

    except StackBuilderError as e:
        logger.info(f"Rejected invalid stack configuration: {e}")
        raise HTTPException(status_code=422, detail=e.message)
    except Exception as e:
        logger.error(f"Error generating offline bundle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _generate_pull_script(images: list[str]) -> str:
    """Generate the image pull script"""
    return f"""#!/bin/bash
# Pull all Docker images for offline deployment
# Run this on a machine with internet access

set -e

echo "Pulling Docker images..."
echo ""

IMAGES=(
{chr(10).join(f'    "{img}"' for img in images)}
)

for IMAGE in "${{IMAGES[@]}}"; do
    echo "Pulling $IMAGE..."
    docker pull "$IMAGE"
done

echo ""
echo "Saving images to archive..."
docker save ${{IMAGES[@]}} | gzip > docker-images.tar.gz

echo ""
echo "Done! Transfer docker-images.tar.gz to your offline system."
echo "File size: $(du -h docker-images.tar.gz | cut -f1)"
"""


def _generate_load_script() -> str:
    """Generate the image load script"""
    return """#!/bin/bash
# Load Docker images from archive
# Run this on your offline/airgapped system

set -e

if [ ! -f docker-images.tar.gz ]; then
    echo "ERROR: docker-images.tar.gz not found"
    echo "Please run pull-images.sh on a connected system first"
    exit 1
fi

echo "Loading Docker images..."
gunzip -c docker-images.tar.gz | docker load

echo ""
echo "Images loaded successfully!"
echo "You can now run: docker compose up -d"
"""


def _generate_offline_readme(global_settings, images: list[str]) -> str:
    """Generate the offline bundle README"""
    stack_name = global_settings.stack_name if global_settings else "iiot-stack"

    return f"""# {stack_name} - Offline Deployment

## Overview

This bundle contains everything needed for airgapped/offline deployment.

## Included Files

- `docker-compose.yml` - Docker Compose configuration
- `.env` - Environment variables
- `README.md` - This file
- `pull-images.sh` - Run on connected system to download images
- `load-images.sh` - Run on offline system to load images
- `configs/` - Service configuration files

## Deployment Steps

### On Connected System (with Internet)

1. Copy this bundle to a system with Docker and internet access
2. Make pull script executable:
   ```bash
   chmod +x pull-images.sh
   ```
3. Pull all images:
   ```bash
   ./pull-images.sh
   ```
4. This creates `docker-images.tar.gz` (~{len(images) * 300}MB estimated)

### Transfer to Offline System

5. Copy the entire bundle including `docker-images.tar.gz` to your offline system
   - USB drive
   - Network share
   - Secure file transfer

### On Offline System

6. Make load script executable:
   ```bash
   chmod +x load-images.sh
   ```
7. Load the images:
   ```bash
   ./load-images.sh
   ```
8. Start the stack:
   ```bash
   docker compose up -d
   ```

## Images Included

{chr(10).join(f"- {img}" for img in images)}

## Troubleshooting

**"docker-images.tar.gz not found"**
- Run pull-images.sh on a connected system first

**"No space left on device"**
- Images require approximately {len(images) * 500}MB disk space
- Ensure sufficient space before loading

**Permission denied**
- Ensure scripts are executable: chmod +x *.sh
- Run as user in docker group or with sudo
"""


def _create_offline_zip(
    result: dict, pull_script: str, load_script: str, readme: str, stack_name: str
) -> io.BytesIO:
    """Create the offline bundle ZIP file"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("docker-compose.yml", result["docker_compose"])
        zip_file.writestr(".env", result["env"])
        zip_file.writestr("README.md", readme)

        # Add pull/load scripts with executable permissions
        pull_info = zipfile.ZipInfo("pull-images.sh")
        pull_info.external_attr = 0o755 << 16
        zip_file.writestr(pull_info, pull_script)

        load_info = zipfile.ZipInfo("load-images.sh")
        load_info.external_attr = 0o755 << 16
        zip_file.writestr(load_info, load_script)

        for file_path, content in result.get("config_files", {}).items():
            info = zipfile.ZipInfo(file_path)
            info.external_attr = 0o644 << 16
            zip_file.writestr(info, content)

        for file_path, content in result.get("startup_scripts", {}).items():
            info = zipfile.ZipInfo(file_path)
            info.external_attr = 0o755 << 16
            zip_file.writestr(info, content)

        zip_file.writestr("configs/.gitkeep", "")

    zip_buffer.seek(0)
    return zip_buffer


# ============================================================================
# Stack Deployment Routes (Local Docker)
# ============================================================================


@router.get("/docker-status")
async def get_docker_status():
    """Check if Docker is available and running"""
    try:
        runner = get_stack_runner()
        available = runner.check_docker_available()
        return {
            "available": available,
            "message": "Docker is ready" if available else "Docker is not available",
        }
    except Exception as e:
        logger.error(f"Error checking Docker status: {e}")
        return {
            "available": False,
            "message": str(e),
        }


@router.post("/deploy", response_model=DeploymentResult)
async def deploy_stack(request: DeployStackRequest):
    """
    Deploy a stack to local Docker.

    Generates the docker-compose files and runs docker compose up.
    """
    try:
        # Generate the compose files
        instances, global_settings, integration_settings = _convert_stack_config(
            request.stack_config
        )
        generator = ComposeGenerator()
        result = generator.generate(instances, global_settings, integration_settings)

        # Deploy using the stack runner
        runner = get_stack_runner()
        deploy_result = runner.deploy_stack(
            stack_name=request.stack_name,
            compose_content=result["docker_compose"],
            env_content=result["env"],
            config_files=result.get("config_files", {}),
        )

        return DeploymentResult(
            success=deploy_result.success,
            output=deploy_result.output,
            error=deploy_result.error,
        )

    except StackBuilderError as e:
        logger.info(f"Rejected invalid stack configuration: {e}")
        raise HTTPException(status_code=422, detail=e.message)
    except Exception as e:
        logger.error(f"Error deploying stack: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop/{stack_name}", response_model=DeploymentResult)
async def stop_stack(stack_name: str, remove_volumes: bool = False):
    """
    Stop a running stack.

    Args:
        stack_name: Name of the stack to stop
        remove_volumes: If true, also remove Docker volumes
    """
    try:
        runner = get_stack_runner()
        result = runner.stop_stack(stack_name, remove_volumes=remove_volumes)

        return DeploymentResult(
            success=result.success,
            output=result.output,
            error=result.error,
        )

    except Exception as e:
        logger.error(f"Error stopping stack: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deployment-status/{stack_name}", response_model=DeploymentStatus)
async def get_deployment_status(stack_name: str):
    """Get the status of a deployed stack"""
    try:
        runner = get_stack_runner()
        status = runner.get_stack_status(stack_name)

        return DeploymentStatus(
            status=status.status,
            services=status.services,
            error=status.error,
        )

    except Exception as e:
        logger.error(f"Error getting deployment status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deployments")
async def list_deployments():
    """List all deployed stacks"""
    try:
        runner = get_stack_runner()
        stacks = runner.list_deployed_stacks()

        # Get status for each stack
        deployments = []
        for stack_name in stacks:
            status = runner.get_stack_status(stack_name)
            deployments.append(
                {
                    "name": stack_name,
                    "status": status.status,
                    "services": status.services,
                }
            )

        return {"deployments": deployments}

    except Exception as e:
        logger.error(f"Error listing deployments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/deployment/{stack_name}")
async def delete_deployment(stack_name: str):
    """Delete a deployed stack (stops and removes files)"""
    try:
        runner = get_stack_runner()
        result = runner.delete_stack(stack_name)

        if result.success:
            return {"message": f"Stack '{stack_name}' deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail=result.error)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting deployment: {e}")
        raise HTTPException(status_code=500, detail=str(e))
