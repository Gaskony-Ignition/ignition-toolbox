"""
Startup validators

Validates system components during startup in phases:
1. Environment (Python version, directories, permissions)
2. Database (schema, connectivity)
3. Credential vault (encryption, file access)
4. Playbook library (directory, YAML validity)
5. Frontend build (production only)
"""

import logging
import os
import sys

from sqlalchemy import text

from ignition_toolkit.core.config import get_settings
from ignition_toolkit.core.paths import get_playbooks_dir
from ignition_toolkit.credentials.vault import get_credential_vault
from ignition_toolkit.startup.exceptions import (
    DatabaseInitError,
    EnvironmentError,
    VaultInitError,
)
from ignition_toolkit.storage.database import get_database

logger = logging.getLogger(__name__)


async def validate_environment() -> None:
    """
    Phase 1: Validate environment requirements

    Checks:
    - Python version >= 3.10
    - Data directory exists and is writable
    - Toolkit directory exists

    Raises:
        EnvironmentError: If environment validation fails
    """
    # Check Python version
    if sys.version_info < (3, 10):
        raise EnvironmentError(
            f"Python 3.10+ required, found {sys.version}",
            recovery_hint="Upgrade Python: https://www.python.org/downloads/",
        )
    logger.info(f"✓ Python version: {sys.version_info.major}.{sys.version_info.minor}")

    # Check/create data directory
    settings = get_settings()
    data_dir = settings.database_path.parent

    if not data_dir.exists():
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"✓ Created data directory: {data_dir.absolute()}")
        except Exception as e:
            raise EnvironmentError(
                f"Cannot create data directory: {e}", recovery_hint="Check filesystem permissions"
            )

    if not os.access(data_dir, os.W_OK):
        raise EnvironmentError(
            f"Data directory not writable: {data_dir.absolute()}",
            recovery_hint=f"Fix permissions: chmod u+w {data_dir}",
        )
    logger.info(f"✓ Data directory writable: {data_dir.absolute()}")

    # Check/create toolkit directory
    toolkit_dir = settings.vault_path.parent
    if not toolkit_dir.exists():
        try:
            toolkit_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"✓ Created toolkit directory: {toolkit_dir}")
        except Exception as e:
            raise EnvironmentError(
                f"Cannot create toolkit directory: {e}",
                recovery_hint="Check home directory permissions",
            )
    logger.info(f"✓ Toolkit directory: {toolkit_dir}")


async def initialize_database() -> None:
    """
    Phase 2: Initialize database and verify schema

    Checks:
    - Database file can be created/accessed
    - Tables can be created
    - Test query works

    Raises:
        DatabaseInitError: If database initialization fails
    """
    try:
        db = get_database()

        # Create all tables (idempotent)
        db.create_tables()
        logger.info("✓ Database tables created/verified")

        # Test query
        with db.session_scope() as session:
            result = session.execute(text("SELECT 1")).fetchone()
            if result[0] != 1:
                raise DatabaseInitError("Database test query failed")

        logger.info(f"✓ Database operational: {db.database_path}")

    except Exception as e:
        if isinstance(e, DatabaseInitError):
            raise
        raise DatabaseInitError(
            f"Database initialization failed: {e}",
            recovery_hint="Delete data/toolkit.db and restart",
        )


async def initialize_vault() -> None:
    """
    Phase 3: Initialize credential vault

    Checks:
    - Vault file can be created/accessed
    - Encryption/decryption works

    Raises:
        VaultInitError: If vault initialization fails
    """
    try:
        vault = get_credential_vault()

        # Initialize vault (creates file if needed)
        vault.initialize()

        # Test encryption/decryption
        if not vault.test_encryption():
            raise VaultInitError("Vault encryption test failed")

        logger.info(f"✓ Credential vault operational: {vault.vault_path}")

    except Exception as e:
        if isinstance(e, VaultInitError):
            raise
        raise VaultInitError(
            f"Vault initialization failed: {e}",
            recovery_hint="Run 'ignition-toolkit init' to reset vault",
        )


async def validate_playbooks() -> dict:
    """
    Phase 4: Validate playbook library (non-fatal)

    Checks:
    - Playbooks directory exists
    - Counts available playbooks

    Returns:
        dict: Playbook statistics (total, gateway, perspective counts)

    Raises:
        Exception: If validation fails (caught by lifecycle manager as warning)
    """
    playbooks_dir = get_playbooks_dir()
    if not playbooks_dir.exists():
        raise Exception(f"Playbooks directory not found: {playbooks_dir}")

    # Count playbooks by domain
    gateway_playbooks = (
        list((playbooks_dir / "gateway").glob("*.yaml"))
        if (playbooks_dir / "gateway").exists()
        else []
    )
    perspective_playbooks = (
        list((playbooks_dir / "perspective").glob("*.yaml"))
        if (playbooks_dir / "perspective").exists()
        else []
    )
    example_playbooks = (
        list((playbooks_dir / "examples").glob("*.yaml"))
        if (playbooks_dir / "examples").exists()
        else []
    )

    total = len(gateway_playbooks) + len(perspective_playbooks) + len(example_playbooks)

    logger.info(
        f"✓ Found {total} playbooks "
        f"({len(gateway_playbooks)} gateway, {len(perspective_playbooks)} perspective, "
        f"{len(example_playbooks)} examples)"
    )

    # PORTABILITY v4: Auto-detect and mark built-in playbooks
    try:
        from ignition_toolkit.playbook.metadata import PlaybookMetadataStore

        metadata_store = PlaybookMetadataStore()
        metadata_store.auto_detect_built_ins(playbooks_dir)
        logger.info("✓ Auto-detected built-in playbooks")
    except Exception as e:
        logger.warning(f"⚠️  Failed to auto-detect built-in playbooks: {e}")

    return {
        "total": total,
        "gateway": len(gateway_playbooks),
        "perspective": len(perspective_playbooks),
        "examples": len(example_playbooks),
    }


async def validate_frontend() -> None:
    """
    Phase 5: Validate frontend build (production only, non-fatal)

    Checks:
    - frontend/dist/ exists
    - index.html exists

    Raises:
        Exception: If frontend validation fails
    """
    settings = get_settings()
    frontend_dir = settings.frontend_dir

    if not frontend_dir.exists():
        raise Exception(f"Frontend build not found: {frontend_dir.absolute()}")

    index_file = frontend_dir / "index.html"
    if not index_file.exists():
        raise Exception(f"Frontend index.html not found: {index_file.absolute()}")

    logger.info(f"✓ Frontend build verified: {frontend_dir.absolute()}")
