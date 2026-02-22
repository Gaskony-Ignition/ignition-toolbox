"""
Backup Service

Preserves user data during updates.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def backup_user_data() -> Path:
    """
    Backup credentials, database, and custom playbooks

    Returns:
        Path: Path to backup directory

    Raises:
        Exception: If backup fails
    """
    from ignition_toolkit.core.paths import get_user_data_dir

    user_data_dir = get_user_data_dir()
    backup_dir = user_data_dir / "backups" / f"pre-update-{datetime.now():%Y%m%d-%H%M%S}"

    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Creating backup at {backup_dir}")

        # Backup credential vault
        vault_file = user_data_dir / "credentials.json"
        if vault_file.exists():
            shutil.copy2(vault_file, backup_dir / "credentials.json")
            logger.info("Backed up credential vault")

        # Backup encryption key
        key_file = user_data_dir / "encryption.key"
        if key_file.exists():
            shutil.copy2(key_file, backup_dir / "encryption.key")
            logger.info("Backed up encryption key")

        # Backup database (actual filename is ignition_toolkit.db)
        db_file = user_data_dir / "ignition_toolkit.db"
        if db_file.exists():
            shutil.copy2(db_file, backup_dir / "ignition_toolkit.db")
            logger.info("Backed up database")

        # Backup custom playbooks (if outside package)
        package_root = Path(__file__).parent.parent.parent
        playbooks_dir = package_root / "playbooks"

        if playbooks_dir.exists():
            # Only backup custom playbooks (user-created)
            custom_playbooks = []
            for playbook in playbooks_dir.rglob("*.yaml"):
                # Check if it's a custom playbook (not built-in)
                # Built-in playbooks are in gateway/, perspective/, designer/, examples/
                # Normalize to forward slashes for cross-platform compatibility
                relative_path_str = str(playbook.relative_to(playbooks_dir)).replace("\\", "/")
                if not relative_path_str.startswith(("gateway/", "perspective/", "designer/", "examples/")):
                    custom_playbooks.append(playbook)

            if custom_playbooks:
                custom_backup_dir = backup_dir / "playbooks"
                custom_backup_dir.mkdir(exist_ok=True)

                for playbook in custom_playbooks:
                    shutil.copy2(playbook, custom_backup_dir / playbook.name)

                logger.info(f"Backed up {len(custom_playbooks)} custom playbooks")

        # Create backup manifest
        manifest_path = backup_dir / "MANIFEST.txt"
        with open(manifest_path, "w", encoding='utf-8') as f:
            f.write(f"Backup created: {datetime.now().isoformat()}\n")
            f.write("Files backed up:\n")
            for file in backup_dir.glob("*"):
                if file.is_file():
                    f.write(f"  - {file.name} ({file.stat().st_size} bytes)\n")

        logger.info(f"Backup complete: {backup_dir}")
        return backup_dir

    except Exception as e:
        logger.error(f"Backup failed: {e}")
        raise


def restore_backup(backup_dir: Path) -> bool:
    """
    Restore user data from backup (rollback)

    Args:
        backup_dir: Path to backup directory

    Returns:
        bool: True if restore successful
    """
    from ignition_toolkit.core.paths import get_user_data_dir

    try:
        user_data_dir = get_user_data_dir()
        logger.info(f"Restoring backup from {backup_dir}")

        # Restore credential vault
        vault_backup = backup_dir / "credentials.json"
        if vault_backup.exists():
            shutil.copy2(vault_backup, user_data_dir / "credentials.json")
            logger.info("Restored credential vault")

        # Restore encryption key
        key_backup = backup_dir / "encryption.key"
        if key_backup.exists():
            shutil.copy2(key_backup, user_data_dir / "encryption.key")
            logger.info("Restored encryption key")

        # Restore database
        db_backup = backup_dir / "ignition_toolkit.db"
        if db_backup.exists():
            shutil.copy2(db_backup, user_data_dir / "ignition_toolkit.db")
            logger.info("Restored database")

        # Restore custom playbooks
        playbooks_backup = backup_dir / "playbooks"
        if playbooks_backup.exists():
            package_root = Path(__file__).parent.parent.parent
            playbooks_dir = package_root / "playbooks"
            playbooks_dir.mkdir(exist_ok=True)

            for playbook in playbooks_backup.glob("*.yaml"):
                shutil.copy2(playbook, playbooks_dir / playbook.name)

            logger.info("Restored custom playbooks")

        logger.info("Restore complete")
        return True

    except Exception as e:
        logger.error(f"Restore failed: {e}")
        return False


def list_backups() -> list[Path]:
    """
    List all available backups

    Returns:
        list[Path]: List of backup directories (newest first)
    """
    from ignition_toolkit.core.paths import get_user_data_dir

    user_data_dir = get_user_data_dir()
    backups_dir = user_data_dir / "backups"

    if not backups_dir.exists():
        return []

    backups = [d for d in backups_dir.iterdir() if d.is_dir()]
    backups.sort(key=lambda d: d.stat().st_mtime, reverse=True)

    return backups
