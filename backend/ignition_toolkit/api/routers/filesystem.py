"""
Filesystem router - Browse server filesystem for path selection

SECURITY: Restricted filesystem browsing for selecting download locations.
Access is limited to the data/ directory by default. Additional directories
can be configured via FILESYSTEM_ALLOWED_PATHS environment variable.

PORTABILITY v4: Uses dynamic path resolution instead of hardcoded paths.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ignition_toolkit.core.paths import get_data_dir
from ignition_toolkit.core.validation import PathValidator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/filesystem", tags=["filesystem"])


class DirectoryEntry(BaseModel):
    """Represents a file or directory entry"""

    name: str
    path: str
    is_directory: bool
    is_accessible: bool


class DirectoryContents(BaseModel):
    """Directory listing response"""

    current_path: str
    parent_path: str | None
    entries: list[DirectoryEntry]


def _get_allowed_base_paths() -> list[Path]:
    """
    Get list of allowed base paths for filesystem browsing.

    By default, only allows access to data/ directory for security.
    Additional paths can be configured via FILESYSTEM_ALLOWED_PATHS env var.

    SECURITY: Restricting filesystem access prevents:
    - Access to credentials (~/.ignition-toolkit/)
    - Access to SSH keys (~/.ssh/)
    - Access to system directories (/etc/, /usr/, etc.)
    - Path traversal attacks

    Returns:
        List of allowed base paths

    Example:
        # Allow additional directory for module storage
        export FILESYSTEM_ALLOWED_PATHS="/opt/ignition-modules"
    """
    # Always allow data/ directory
    allowed_paths = [get_data_dir()]

    # Get additional paths from settings (loaded from .env)
    from ignition_toolkit.core.config import get_settings
    settings = get_settings()
    extra_paths = settings.filesystem_allowed_paths.strip()

    if extra_paths:
        for path_str in extra_paths.split(":"):
            path_str = path_str.strip()
            if path_str:
                try:
                    path = Path(path_str).resolve()
                    if path.exists() and path.is_dir():
                        allowed_paths.append(path)
                        logger.info(f"Added allowed filesystem path: {path}")
                    else:
                        logger.warning(f"Skipping non-existent path from FILESYSTEM_ALLOWED_PATHS: {path_str}")
                except Exception as e:
                    logger.warning(f"Invalid path in FILESYSTEM_ALLOWED_PATHS: {path_str} - {e}")

    return allowed_paths


# SECURITY: Get allowed base paths (restricted by default)
ALLOWED_BASE_PATHS = _get_allowed_base_paths()

logger.info(f"Filesystem API restricted to {len(ALLOWED_BASE_PATHS)} base paths: {[str(p) for p in ALLOWED_BASE_PATHS]}")


def is_path_allowed(path: Path) -> bool:
    """
    Check if path is within allowed base paths

    SECURITY: Prevents directory traversal and unauthorized file access.
    Uses PathValidator for consistent path validation across the application.

    Args:
        path: Path to validate

    Returns:
        True if path is allowed, False otherwise
    """
    try:
        resolved_path = path.resolve()

        # Check against each allowed base path
        for base_path in ALLOWED_BASE_PATHS:
            resolved_base = base_path.resolve()
            if resolved_path == resolved_base or resolved_path.is_relative_to(
                resolved_base
            ):
                # Additional validation using PathValidator
                try:
                    PathValidator.validate_path_safety(resolved_path)
                    return True
                except ValueError:
                    # PathValidator rejected the path (suspicious patterns)
                    logger.warning(f"PathValidator rejected path: {resolved_path}")
                    return False

        return False
    except (ValueError, RuntimeError, OSError) as e:
        logger.warning(f"Path validation error for {path}: {e}")
        return False


@router.get("/browse", response_model=DirectoryContents)
async def browse_directory(path: str = "./data/downloads") -> DirectoryContents:
    """
    Browse server filesystem directory

    SECURITY: Access restricted to data/ directory by default.
    Additional directories can be configured via FILESYSTEM_ALLOWED_PATHS environment variable.

    Args:
        path: Directory path to browse (default: ./data/downloads)

    Returns:
        Directory contents with subdirectories and parent path

    Raises:
        HTTPException: If path is invalid or not accessible
    """
    try:
        target_path = Path(path).resolve()

        # Security check: Verify path is within allowed base paths
        if not is_path_allowed(target_path):
            allowed_paths_str = ", ".join(str(p) for p in ALLOWED_BASE_PATHS)
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: Path must be within allowed directories. Allowed: {allowed_paths_str}. Configure FILESYSTEM_ALLOWED_PATHS to add more directories.",
            )

        # Verify path exists and is a directory
        if not target_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Directory not found: {path}",
            )

        if not target_path.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"Path is not a directory: {path}",
            )

        # Get parent directory path (if not at root of allowed paths)
        parent_path = None
        if target_path.parent != target_path:
            if is_path_allowed(target_path.parent):
                parent_path = str(target_path.parent)

        # List directory contents (directories only, sorted)
        entries: list[DirectoryEntry] = []

        try:
            for entry in sorted(target_path.iterdir(), key=lambda x: x.name.lower()):
                if entry.is_dir():
                    is_accessible = is_path_allowed(entry)
                    entries.append(
                        DirectoryEntry(
                            name=entry.name,
                            path=str(entry),
                            is_directory=True,
                            is_accessible=is_accessible,
                        )
                    )
        except PermissionError:
            # If we can't list the directory, return empty list
            logger.warning(f"Permission denied listing directory: {target_path}")

        return DirectoryContents(
            current_path=str(target_path),
            parent_path=parent_path,
            entries=entries,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error browsing directory {path}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to browse directory: {str(e)}",
        )


class ModuleFileInfo(BaseModel):
    """Information about a module file"""

    filename: str
    filepath: str
    is_unsigned: bool
    module_name: str | None = None
    module_version: str | None = None
    module_id: str | None = None


class ModuleFilesResponse(BaseModel):
    """Response containing detected module files"""

    path: str
    files: list[ModuleFileInfo]


@router.get("/list-modules")
async def list_module_files(path: str | None = None) -> ModuleFilesResponse:
    """
    List .modl and .unsigned.modl files in a directory and extract metadata

    SECURITY: Access restricted to data/ directory by default.
    Additional directories can be configured via FILESYSTEM_ALLOWED_PATHS environment variable.

    Args:
        path: Directory path to search for module files (default: data/)

    Returns:
        ModuleFilesResponse with detected module files and their metadata
    """
    try:
        from ignition_toolkit.modules import parse_module_metadata

        # Default to data/ directory if no path provided
        if path is None:
            target_path = get_data_dir()
        else:
            target_path = Path(path).resolve()

        # Security check
        if not is_path_allowed(target_path):
            allowed_paths_str = ", ".join(str(p) for p in ALLOWED_BASE_PATHS)
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: Path must be within allowed directories. Allowed: {allowed_paths_str}. Configure FILESYSTEM_ALLOWED_PATHS to add more directories.",
            )

        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"Directory not found: {path}")

        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")

        # Find all .modl and .unsigned.modl files
        module_files = []

        for file_path in target_path.iterdir():
            if file_path.is_file() and (
                file_path.suffix == ".modl" or str(file_path).endswith(".unsigned.modl")
            ):
                is_unsigned = str(file_path).endswith(".unsigned.modl")

                # Try to extract metadata
                metadata = parse_module_metadata(str(file_path))

                module_files.append(
                    ModuleFileInfo(
                        filename=file_path.name,
                        filepath=str(file_path.absolute()),
                        is_unsigned=is_unsigned,
                        module_name=metadata.name if metadata else None,
                        module_version=metadata.version if metadata else None,
                        module_id=metadata.id if metadata else None,
                    )
                )

        logger.info(f"Found {len(module_files)} module files in {path}")

        return ModuleFilesResponse(path=str(target_path), files=module_files)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing module files in {path}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list module files: {str(e)}",
        )
