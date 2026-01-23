"""
Playbook CRUD operations router

Handles basic playbook operations: list, get, update YAML content,
update metadata (name/description), and edit steps.
"""

import logging
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator

from ignition_toolkit.api.routers.models import ParameterInfo, PlaybookInfo, StepInfo
from ignition_toolkit.core.paths import (
    get_playbooks_dir,
    get_all_playbook_dirs,
    get_builtin_playbooks_dir,
    get_user_playbooks_dir,
)
from ignition_toolkit.playbook.loader import PlaybookLoader
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================


class PlaybookUpdateRequest(BaseModel):
    """Request to update a playbook YAML file"""

    playbook_path: str  # Relative path from playbooks directory
    yaml_content: str  # New YAML content


class PlaybookMetadataUpdateRequest(BaseModel):
    """Request to update playbook name and description

    SECURITY: Includes input validation to prevent XSS, injection attacks, and DoS
    """

    playbook_path: str
    name: str | None = None
    description: str | None = None

    @validator('playbook_path')
    def validate_playbook_path_field(cls, v):
        """Validate playbook path field"""
        if not v or not v.strip():
            raise ValueError("Playbook path cannot be empty")
        if len(v) > 500:
            raise ValueError("Playbook path too long (max 500 characters)")
        return v.strip()

    @validator('name')
    def validate_name(cls, v):
        """Validate playbook name for security and sanity"""
        if v is None:
            return v

        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty or whitespace")

        if len(v) > 200:
            raise ValueError("Name too long (max 200 characters)")

        dangerous_chars = ['<', '>', '"', "'", '`', '{', '}', '$', '|', '&', ';']
        for char in dangerous_chars:
            if char in v:
                raise ValueError(f"Name contains invalid character: {char}")

        if any(ord(c) < 32 for c in v):
            raise ValueError("Name contains control characters")

        return v

    @validator('description')
    def validate_description(cls, v):
        """Validate playbook description for security"""
        if v is None:
            return v

        v = v.strip()

        if len(v) > 2000:
            raise ValueError("Description too long (max 2000 characters)")

        dangerous_patterns = ['<script', 'javascript:', 'onerror=', 'onload=', '<?php']
        v_lower = v.lower()
        for pattern in dangerous_patterns:
            if pattern in v_lower:
                raise ValueError(f"Description contains potentially dangerous pattern: {pattern}")

        for c in v:
            if ord(c) < 32 and c not in ['\n', '\r', '\t']:
                raise ValueError("Description contains invalid control characters")

        return v


class StepEditRequest(BaseModel):
    """Request to edit a step in a playbook"""

    playbook_path: str
    step_id: str
    new_parameters: dict[str, Any]


# ============================================================================
# Helper Functions
# ============================================================================


def get_metadata_store():
    """Get shared metadata store from app"""
    from ignition_toolkit.api.app import metadata_store
    return metadata_store


def validate_playbook_path(path_str: str) -> Path:
    """
    Validate playbook path to prevent directory traversal attacks

    SECURITY: This is a wrapper around PathValidator for backwards compatibility.

    Args:
        path_str: User-provided playbook path

    Returns:
        Validated absolute Path

    Raises:
        HTTPException: If path is invalid or outside playbooks directory
    """
    from ignition_toolkit.core.validation import PathValidator

    return PathValidator.validate_playbook_path(
        path_str,
        base_dir=get_playbooks_dir(),
        must_exist=True
    )


# ============================================================================
# Routes
# ============================================================================


@router.get("", response_model=list[PlaybookInfo])
async def list_playbooks():
    """
    List all available playbooks from all sources.

    Scans both built-in and user-installed playbook directories.
    User playbooks take priority over built-in playbooks with the same path.
    """
    metadata_store = get_metadata_store()

    playbook_dirs = get_all_playbook_dirs()
    builtin_dir = get_builtin_playbooks_dir()
    user_dir = get_user_playbooks_dir()

    seen_paths = set()
    playbooks = []

    for playbooks_dir in playbook_dirs:
        if not playbooks_dir.exists():
            continue

        if playbooks_dir == builtin_dir:
            source = "built-in"
        elif playbooks_dir == user_dir:
            source = "user-installed"
        else:
            source = "unknown"

        for yaml_file in playbooks_dir.rglob("*.yaml"):
            if ".backup." in yaml_file.name:
                continue

            try:
                loader = PlaybookLoader()
                playbook = loader.load_from_file(yaml_file)

                relative_path = str(yaml_file.relative_to(playbooks_dir))

                if relative_path in seen_paths:
                    logger.debug(f"Skipping {relative_path} from {source} (already loaded)")
                    continue

                seen_paths.add(relative_path)

                parameters = [
                    ParameterInfo(
                        name=p.name,
                        type=p.type.value,
                        required=p.required,
                        default=str(p.default) if p.default is not None else None,
                        description=p.description,
                    )
                    for p in playbook.parameters
                ]

                steps = [
                    StepInfo(
                        id=s.id,
                        name=s.name,
                        type=s.type.value,
                        timeout=s.timeout,
                        retry_count=s.retry_count,
                    )
                    for s in playbook.steps
                ]

                meta = metadata_store.get_metadata(relative_path)

                # Metadata store is the source of truth for verified status
                # YAML verified field is only used to initialize on first load (when origin is unknown)
                if meta.origin == "unknown":
                    # First time seeing this playbook - check YAML for initial verified state
                    yaml_verified = playbook.metadata.get("verified")
                    if yaml_verified and not meta.verified:
                        meta.verified = True
                        meta.verified_by = "yaml"
                        metadata_store.update_metadata(relative_path, meta)

                verified_status = meta.verified

                if meta.origin == "unknown":
                    meta.origin = source
                    metadata_store.update_metadata(relative_path, meta)

                playbooks.append(
                    PlaybookInfo(
                        name=playbook.name,
                        path=relative_path,
                        version=playbook.version,
                        description=playbook.description,
                        parameter_count=len(playbook.parameters),
                        step_count=len(playbook.steps),
                        parameters=parameters,
                        steps=steps,
                        domain=playbook.metadata.get("domain"),
                        group=playbook.metadata.get("group"),
                        revision=meta.revision,
                        verified=verified_status,
                        enabled=meta.enabled,
                        last_modified=meta.last_modified,
                        verified_at=meta.verified_at,
                        origin=meta.origin,
                        duplicated_from=meta.duplicated_from,
                        created_at=meta.created_at,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to load playbook {yaml_file}: {e}")
                continue

    return playbooks


@router.get("/{playbook_path:path}", response_model=PlaybookInfo)
async def get_playbook(playbook_path: str):
    """Get detailed playbook information including full parameter schema"""
    metadata_store = get_metadata_store()
    try:
        validated_path = validate_playbook_path(playbook_path)

        loader = PlaybookLoader()
        playbook = loader.load_from_file(validated_path)

        parameters = [
            ParameterInfo(
                name=p.name,
                type=p.type.value,
                required=p.required,
                default=str(p.default) if p.default is not None else None,
                description=p.description,
            )
            for p in playbook.parameters
        ]

        steps = [
            StepInfo(
                id=s.id,
                name=s.name,
                type=s.type.value,
                timeout=s.timeout,
                retry_count=s.retry_count,
            )
            for s in playbook.steps
        ]

        playbooks_dir = get_playbooks_dir()
        relative_path = str(validated_path.relative_to(playbooks_dir))
        meta = metadata_store.get_metadata(relative_path)

        return PlaybookInfo(
            name=playbook.name,
            path=relative_path,
            version=playbook.version,
            description=playbook.description,
            parameter_count=len(playbook.parameters),
            step_count=len(playbook.steps),
            parameters=parameters,
            steps=steps,
            domain=playbook.metadata.get("domain"),
            group=playbook.metadata.get("group"),
            revision=meta.revision,
            verified=meta.verified,
            enabled=meta.enabled,
            last_modified=meta.last_modified,
            verified_at=meta.verified_at,
            origin=meta.origin,
            duplicated_from=meta.duplicated_from,
            created_at=meta.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Playbook not found: {e}")


@router.put("/update")
async def update_playbook(request: PlaybookUpdateRequest):
    """
    Update a playbook YAML file with new content

    This is used when applying fixes from debug mode.
    Creates a backup before updating.
    """
    metadata_store = get_metadata_store()
    try:
        playbooks_dir = Path("playbooks")
        playbook_path = playbooks_dir / request.playbook_path

        # Security check: ensure path is within playbooks directory
        try:
            playbook_path = playbook_path.resolve()
            playbooks_dir = playbooks_dir.resolve()
            if not str(playbook_path).startswith(str(playbooks_dir)):
                raise HTTPException(status_code=400, detail="Invalid playbook path")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid playbook path")

        if not playbook_path.exists():
            raise HTTPException(status_code=404, detail="Playbook not found")

        backup_path = playbook_path.with_suffix(
            f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
        )
        backup_path.write_text(playbook_path.read_text())
        logger.info(f"Created backup: {backup_path}")

        try:
            yaml.safe_load(request.yaml_content)
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(e)}")

        playbook_path.write_text(request.yaml_content)
        logger.info(f"Updated playbook: {playbook_path}")

        metadata_store.increment_revision(request.playbook_path)
        meta = metadata_store.get_metadata(request.playbook_path)

        return {
            "status": "success",
            "playbook_path": str(request.playbook_path),
            "backup_path": str(backup_path.name),
            "revision": meta.revision,
            "message": f"Playbook updated successfully (revision {meta.revision})",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating playbook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/metadata")
async def update_playbook_metadata(request: PlaybookMetadataUpdateRequest):
    """Update playbook name and/or description in YAML file"""
    metadata_store = get_metadata_store()
    try:
        playbook_path = validate_playbook_path(request.playbook_path)

        if not playbook_path.exists():
            raise HTTPException(status_code=404, detail="Playbook not found")

        with open(playbook_path) as f:
            playbook_data = yaml.safe_load(f)

        if request.name is not None:
            playbook_data["name"] = request.name
        if request.description is not None:
            playbook_data["description"] = request.description

        backup_path = playbook_path.with_suffix(
            f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
        )
        backup_path.write_text(playbook_path.read_text())

        with open(playbook_path, "w") as f:
            yaml.safe_dump(playbook_data, f, default_flow_style=False, sort_keys=False)

        metadata_store.increment_revision(request.playbook_path)
        meta = metadata_store.get_metadata(request.playbook_path)

        logger.info(f"Updated playbook metadata: {playbook_path}")

        return {
            "status": "success",
            "playbook_path": str(request.playbook_path),
            "name": playbook_data.get("name"),
            "description": playbook_data.get("description"),
            "revision": meta.revision,
            "message": "Playbook metadata updated successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating playbook metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/edit-step")
async def edit_step(request: StepEditRequest):
    """Edit a step's parameters in a playbook during execution"""
    try:
        playbook_path = validate_playbook_path(request.playbook_path)

        with open(playbook_path) as f:
            playbook_data = yaml.safe_load(f)

        step_found = False
        for step in playbook_data.get("steps", []):
            if step.get("id") == request.step_id:
                if "parameters" not in step:
                    step["parameters"] = {}
                step["parameters"].update(request.new_parameters)
                step_found = True
                break

        if not step_found:
            raise HTTPException(status_code=404, detail=f"Step not found: {request.step_id}")

        with open(playbook_path, "w") as f:
            yaml.safe_dump(playbook_data, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Updated step '{request.step_id}' in {playbook_path}")
        return {"message": "Step updated", "step_id": request.step_id}

    except Exception as e:
        logger.exception(f"Step edit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
