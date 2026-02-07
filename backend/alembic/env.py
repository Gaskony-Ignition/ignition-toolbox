"""
Alembic environment configuration.

Resolves the SQLite database path from IGNITION_TOOLKIT_DATA
(same logic as ignition_toolkit.storage.database).
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ignition_toolkit.storage.models import Base  # noqa: E402

# Alembic Config object
config = context.config

# Set up logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLAlchemy MetaData for autogenerate
target_metadata = Base.metadata


def _get_database_url() -> str:
    """Resolve SQLite database URL using the same logic as the app."""
    import os

    data_dir = os.environ.get("IGNITION_TOOLKIT_DATA")
    if data_dir:
        db_path = Path(data_dir) / "ignition_toolkit.db"
    else:
        # Fallback: same default as core.config.get_toolkit_data_dir()
        db_path = Path.home() / ".ignition-toolkit" / "ignition_toolkit.db"

    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def _resolve_url() -> str:
    """Get the database URL, preferring config (set programmatically) over default."""
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url
    return _get_database_url()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without connecting)."""
    url = _resolve_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Required for SQLite ALTER TABLE support
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to database)."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _resolve_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Required for SQLite ALTER TABLE support
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
