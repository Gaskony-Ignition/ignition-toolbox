"""
Database migration: Convert string booleans to proper Boolean columns

Migrates:
- ai_settings.enabled: String("true"/"false") -> Boolean
- scheduled_playbooks.enabled: String("true"/"false") -> Boolean
"""

import logging
from pathlib import Path

from sqlalchemy import Boolean, Column, inspect, text

from ignition_toolkit.storage import get_database

logger = logging.getLogger(__name__)


def migrate_boolean_columns():
    """
    Migrate string boolean columns to proper Boolean type

    This migration:
    1. Adds new boolean columns (_enabled_bool)
    2. Copies data with conversion
    3. Drops old string columns
    4. Renames new columns to original names

    Note: SQLite doesn't support direct column type changes,
    so we use add/copy/drop/rename pattern.
    """
    db = get_database()

    with db.session_scope() as session:
        # Check if migration already applied
        inspector = inspect(session.bind)

        # Check ai_settings table
        if "ai_settings" in inspector.get_table_names():
            ai_columns = [col["name"] for col in inspector.get_columns("ai_settings")]

            if "enabled" in ai_columns:
                # Check column type
                for col in inspector.get_columns("ai_settings"):
                    if col["name"] == "enabled":
                        col_type = str(col["type"]).upper()
                        if "VARCHAR" in col_type or "STRING" in col_type:
                            logger.info("Migrating ai_settings.enabled column...")
                            _migrate_ai_settings_enabled(session)
                        else:
                            logger.info("ai_settings.enabled already Boolean type")
                        break

        # Check scheduled_playbooks table
        if "scheduled_playbooks" in inspector.get_table_names():
            sched_columns = [
                col["name"] for col in inspector.get_columns("scheduled_playbooks")
            ]

            if "enabled" in sched_columns:
                # Check column type
                for col in inspector.get_columns("scheduled_playbooks"):
                    if col["name"] == "enabled":
                        col_type = str(col["type"]).upper()
                        if "VARCHAR" in col_type or "STRING" in col_type:
                            logger.info("Migrating scheduled_playbooks.enabled column...")
                            _migrate_scheduled_playbooks_enabled(session)
                        else:
                            logger.info("scheduled_playbooks.enabled already Boolean type")
                        break

        session.commit()
        logger.info("✅ Boolean column migration complete")


def _migrate_ai_settings_enabled(session):
    """Migrate ai_settings.enabled from String to Boolean"""

    # Step 1: Add temporary boolean column
    session.execute(
        text("ALTER TABLE ai_settings ADD COLUMN enabled_bool INTEGER DEFAULT 0")
    )

    # Step 2: Copy data with conversion (SQLite stores Boolean as INTEGER: 0 or 1)
    session.execute(
        text(
            """
        UPDATE ai_settings
        SET enabled_bool = CASE
            WHEN enabled = 'true' THEN 1
            ELSE 0
        END
    """
        )
    )

    # Step 3: Drop old column (SQLite requires table recreation for column drops)
    # We'll use a simpler approach: rename columns directly

    # Create new table with correct schema
    session.execute(
        text(
            """
        CREATE TABLE ai_settings_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            provider TEXT NOT NULL,
            api_key TEXT,
            api_base_url TEXT,
            model_name TEXT,
            enabled INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """
        )
    )

    # Copy data
    session.execute(
        text(
            """
        INSERT INTO ai_settings_new (id, name, provider, api_key, api_base_url, model_name, enabled, created_at, updated_at)
        SELECT id, name, provider, api_key, api_base_url, model_name, enabled_bool, created_at, updated_at
        FROM ai_settings
    """
        )
    )

    # Drop old table and rename new one
    session.execute(text("DROP TABLE ai_settings"))
    session.execute(text("ALTER TABLE ai_settings_new RENAME TO ai_settings"))

    logger.info("✅ Migrated ai_settings.enabled to Boolean")


def _migrate_scheduled_playbooks_enabled(session):
    """Migrate scheduled_playbooks.enabled from String to Boolean"""

    # Create new table with correct schema
    session.execute(
        text(
            """
        CREATE TABLE scheduled_playbooks_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            playbook_path TEXT NOT NULL,
            schedule_type TEXT NOT NULL,
            schedule_config TEXT NOT NULL,
            parameters TEXT,
            gateway_url TEXT,
            credential_name TEXT,
            enabled INTEGER NOT NULL DEFAULT 1,
            last_run_at TIMESTAMP,
            next_run_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """
        )
    )

    # Copy data with conversion
    session.execute(
        text(
            """
        INSERT INTO scheduled_playbooks_new (id, name, playbook_path, schedule_type, schedule_config,
                                              parameters, gateway_url, credential_name, enabled,
                                              last_run_at, next_run_at, created_at, updated_at)
        SELECT id, name, playbook_path, schedule_type, schedule_config,
               parameters, gateway_url, credential_name,
               CASE WHEN enabled = 'true' THEN 1 ELSE 0 END,
               last_run_at, next_run_at, created_at, updated_at
        FROM scheduled_playbooks
    """
        )
    )

    # Drop old table and rename new one
    session.execute(text("DROP TABLE scheduled_playbooks"))
    session.execute(
        text("ALTER TABLE scheduled_playbooks_new RENAME TO scheduled_playbooks")
    )

    # Recreate indexes
    session.execute(
        text("CREATE INDEX idx_scheduled_playbooks_enabled ON scheduled_playbooks(enabled)")
    )
    session.execute(
        text(
            "CREATE INDEX idx_scheduled_playbooks_next_run ON scheduled_playbooks(next_run_at)"
        )
    )

    logger.info("✅ Migrated scheduled_playbooks.enabled to Boolean")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting boolean column migration...")
    migrate_boolean_columns()
