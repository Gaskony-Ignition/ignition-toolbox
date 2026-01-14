"""
Centralized validation utilities

Provides consistent validation logic across the application,
particularly for path security and playbook validation.
"""

import logging
from pathlib import Path

from fastapi import HTTPException

logger = logging.getLogger(__name__)


class PathValidator:
    """
    Centralized path validation for security and consistency

    Prevents directory traversal attacks and ensures paths are within allowed directories.
    """

    @staticmethod
    def validate_playbook_path(
        path_str: str, base_dir: Path | None = None, must_exist: bool = True
    ) -> Path:
        """
        Validate and resolve playbook path with security checks

        Args:
            path_str: User-provided path (relative only)
            base_dir: Base directory for relative paths (defaults to playbooks_dir)
            must_exist: Whether the file must exist (default: True)

        Returns:
            Validated absolute Path

        Raises:
            HTTPException: 400 for invalid paths, 404 if not found
        """
        from ignition_toolkit.core.paths import get_playbooks_dir

        if base_dir is None:
            base_dir = get_playbooks_dir()

        # Convert to Path
        path = Path(path_str)

        # Security: Prevent directory traversal
        if ".." in str(path) or path.is_absolute():
            raise HTTPException(
                status_code=400,
                detail="Invalid playbook path - relative paths only, no directory traversal",
            )

        # Resolve to absolute
        full_path = (base_dir / path).resolve()

        # Verify within base directory
        try:
            full_path.relative_to(base_dir.resolve())
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Path must be within {base_dir}"
            )

        # Verify extension
        if full_path.suffix not in [".yaml", ".yml"]:
            raise HTTPException(
                status_code=400, detail="Playbook must be a YAML file (.yaml or .yml)"
            )

        # Verify existence
        if must_exist and not full_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Playbook file not found: {path_str}"
            )

        return full_path

    @staticmethod
    def get_relative_path(full_path: Path, base_dir: Path) -> str:
        """
        Convert absolute path to relative path from base directory

        Args:
            full_path: Absolute path to convert
            base_dir: Base directory to make relative to

        Returns:
            Relative path as string

        Raises:
            HTTPException: If path is not relative to base directory
        """
        try:
            return str(full_path.relative_to(base_dir.resolve()))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Path {full_path} is not relative to {base_dir}",
            )

    @staticmethod
    def validate_and_resolve(
        path_str: str, must_exist: bool = True
    ) -> tuple[Path, Path]:
        """
        Validate playbook path and return both base dir and full path

        Args:
            path_str: User-provided relative path
            must_exist: Whether the file must exist

        Returns:
            Tuple of (playbooks_dir, full_playbook_path)

        Raises:
            HTTPException: If path is invalid or file not found
        """
        from ignition_toolkit.core.paths import get_playbooks_dir

        playbooks_dir = get_playbooks_dir()
        full_path = PathValidator.validate_playbook_path(
            path_str, base_dir=playbooks_dir, must_exist=must_exist
        )

        return playbooks_dir, full_path

    @staticmethod
    def validate_path_safety(path: Path) -> None:
        """
        Validate that a path is safe (no directory traversal, no suspicious patterns)

        Used by filesystem router and security tests to prevent unauthorized access.

        Args:
            path: Path to validate (can be relative or absolute)

        Raises:
            ValueError: If path contains dangerous patterns

        Examples:
            >>> PathValidator.validate_path_safety(Path("data/file.txt"))  # OK
            >>> PathValidator.validate_path_safety(Path("../../../etc/passwd"))  # Raises ValueError
        """
        path_str = str(path)

        # Check for directory traversal
        if ".." in path_str:
            raise ValueError(f"Path contains directory traversal: {path_str}")

        # Check for suspicious patterns
        suspicious_patterns = [
            "/etc/passwd",
            "/etc/shadow",
            "/.ssh/",
            "/.ignition-toolkit/credentials",
            "/root/",
        ]

        path_lower = path_str.lower()
        for pattern in suspicious_patterns:
            if pattern in path_lower:
                raise ValueError(f"Path contains suspicious pattern: {pattern}")

        # Additional check: reject absolute paths to sensitive locations
        if path.is_absolute():
            sensitive_dirs = ["/etc", "/root", "/sys", "/proc"]
            for sensitive in sensitive_dirs:
                if path_str.startswith(sensitive):
                    raise ValueError(f"Access to {sensitive} is not allowed")
