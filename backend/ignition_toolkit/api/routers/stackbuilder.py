"""
Stack Builder routes

Provides endpoints for building Docker Compose stacks with
automatic service integration detection and configuration generation.
"""

import io
import logging
import re
import zipfile
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
# Helper Functions
# ============================================================================


def _convert_stack_config(
    stack_config: "StackConfig",
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


# ============================================================================
# Docker Installer Downloads
# ============================================================================


DOCKER_INSTALL_LINUX = '''#!/bin/bash
# Docker Installation Script for Linux
# Supports: Ubuntu, Debian, CentOS, RHEL, Fedora, Arch

set -e

echo "=========================================="
echo "     Docker Installation Script"
echo "=========================================="
echo ""

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    echo "Cannot detect OS. Please install Docker manually."
    exit 1
fi

echo "Detected OS: $OS $VERSION"
echo ""

install_docker_debian() {
    echo "Installing Docker on Debian/Ubuntu..."

    # Remove old versions
    sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

    # Install dependencies
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg lsb-release

    # Add Docker GPG key
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$OS/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # Set up repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

install_docker_rhel() {
    echo "Installing Docker on RHEL/CentOS/Fedora..."

    # Remove old versions
    sudo yum remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine 2>/dev/null || true

    # Install dependencies
    sudo yum install -y yum-utils

    # Set up repository
    sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

    # Install Docker
    sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

install_docker_arch() {
    echo "Installing Docker on Arch Linux..."
    sudo pacman -Sy docker docker-compose --noconfirm
}

# Install based on OS
case $OS in
    ubuntu|debian)
        install_docker_debian
        ;;
    centos|rhel|fedora)
        install_docker_rhel
        ;;
    arch)
        install_docker_arch
        ;;
    *)
        echo "Unsupported OS: $OS"
        echo "Please install Docker manually from https://docs.docker.com/engine/install/"
        exit 1
        ;;
esac

# Start Docker service
echo ""
echo "Starting Docker service..."
sudo systemctl start docker
sudo systemctl enable docker

# Add current user to docker group
echo "Adding $USER to docker group..."
sudo usermod -aG docker $USER

echo ""
echo "=========================================="
echo "     Docker Installation Complete!"
echo "=========================================="
echo ""
echo "Please log out and back in for group changes to take effect."
echo ""
echo "Verify installation:"
echo "  docker --version"
echo "  docker compose version"
echo ""
'''

DOCKER_INSTALL_WINDOWS = '''# Docker Desktop Installation Script for Windows
# Run in PowerShell as Administrator

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "     Docker Desktop Installation Script" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Check Windows version
$osInfo = Get-WmiObject -Class Win32_OperatingSystem
$osVersion = [System.Version]$osInfo.Version
if ($osVersion.Major -lt 10) {
    Write-Host "ERROR: Docker Desktop requires Windows 10 or later" -ForegroundColor Red
    exit 1
}

Write-Host "Detected: $($osInfo.Caption)" -ForegroundColor Green
Write-Host ""

# Check if Docker is already installed
$dockerPath = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerPath) {
    Write-Host "Docker is already installed at: $($dockerPath.Source)" -ForegroundColor Yellow
    docker --version
    Write-Host ""
    $continue = Read-Host "Continue with reinstallation? (y/n)"
    if ($continue -ne "y") {
        exit 0
    }
}

# Enable WSL2
Write-Host "Enabling Windows Subsystem for Linux..." -ForegroundColor Cyan
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

Write-Host "Enabling Virtual Machine Platform..." -ForegroundColor Cyan
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Download Docker Desktop installer
$installerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
$installerPath = "$env:TEMP\\DockerDesktopInstaller.exe"

Write-Host ""
Write-Host "Downloading Docker Desktop installer..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing

# Install Docker Desktop
Write-Host "Installing Docker Desktop..." -ForegroundColor Cyan
Start-Process -FilePath $installerPath -ArgumentList "install --quiet --accept-license" -Wait

# Clean up
Remove-Item $installerPath -Force

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "     Docker Desktop Installation Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANT: Please restart your computer to complete the installation." -ForegroundColor Yellow
Write-Host ""
Write-Host "After restart:" -ForegroundColor Cyan
Write-Host "  1. Launch Docker Desktop from the Start menu"
Write-Host "  2. Complete the initial setup wizard"
Write-Host "  3. Verify installation: docker --version"
Write-Host ""
'''


@router.get("/download/docker-installer/linux")
async def download_docker_installer_linux():
    """Download Docker installation script for Linux"""
    return StreamingResponse(
        iter([DOCKER_INSTALL_LINUX.encode()]),
        media_type="text/plain",
        headers={
            "Content-Disposition": 'attachment; filename="install-docker-linux.sh"'
        },
    )


@router.get("/download/docker-installer/windows")
async def download_docker_installer_windows():
    """Download Docker installation script for Windows"""
    return StreamingResponse(
        iter([DOCKER_INSTALL_WINDOWS.encode()]),
        media_type="text/plain",
        headers={
            "Content-Disposition": 'attachment; filename="install-docker-windows.ps1"'
        },
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
                version = inst.get("config", {}).get("version", app.get("default_version", "latest"))
                images.append(f"{app['image']}:{version}")

        # Generate pull script
        pull_script = f'''#!/bin/bash
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
'''

        # Generate load script
        load_script = '''#!/bin/bash
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
'''

        # Generate offline README
        stack_name = "iiot-stack"
        if global_settings:
            stack_name = global_settings.stack_name

        offline_readme = f'''# {stack_name} - Offline Deployment

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
'''

        # Create ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("docker-compose.yml", result["docker_compose"])
            zip_file.writestr(".env", result["env"])
            zip_file.writestr("README.md", offline_readme)

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

        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{stack_name}-offline.zip"'
            },
        )

    except Exception as e:
        logger.error(f"Error generating offline bundle: {e}")
        raise HTTPException(status_code=500, detail=str(e))
