"""
SQLite database connection and session management
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ignition_toolkit.config import get_toolkit_data_dir
from ignition_toolkit.storage.models import Base

logger = logging.getLogger(__name__)


# Enable foreign key constraints for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign key constraints on SQLite connections"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Database:
    """
    Database connection manager

    Handles SQLite connection, session management, and table creation.
    """

    def __init__(self, database_path: Path | None = None):
        """
        Initialize database connection

        Args:
            database_path: Path to SQLite database file. If None, uses consistent data directory
        """
        if database_path is None:
            # Use consistent data directory instead of relative path
            data_dir = get_toolkit_data_dir()
            database_path = data_dir / "ignition_toolkit.db"

        self.database_path = database_path

        # Ensure data directory exists
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        # Create SQLAlchemy engine
        self.engine = create_engine(
            f"sqlite:///{self.database_path}",
            echo=False,  # Set to True for SQL query logging
            pool_pre_ping=True,  # Verify connections before using
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )

        # Create tables
        self.create_tables()

        logger.info(f"Database initialized: {self.database_path}")

    def create_tables(self) -> None:
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created/verified")

    def verify_schema(self) -> bool:
        """
        Verify database schema is valid

        Returns:
            True if schema is valid, False otherwise

        Raises:
            Exception: If database query fails
        """
        try:
            with self.session_scope() as session:
                # Test basic query
                result = session.execute(text("SELECT 1")).fetchone()
                if result[0] != 1:
                    return False

                # Verify key tables exist
                tables_query = text(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name IN ('executions', 'step_results')"
                )
                tables = session.execute(tables_query).fetchall()
                expected_tables = {"executions", "step_results"}
                found_tables = {row[0] for row in tables}

                return expected_tables.issubset(found_tables)

        except Exception as e:
            logger.error(f"Schema verification failed: {e}")
            return False

    def get_session(self) -> Session:
        """
        Get a new database session

        Returns:
            SQLAlchemy Session object

        Usage:
            session = db.get_session()
            try:
                # Use session
                pass
            finally:
                session.close()
        """
        return self.SessionLocal()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope for database operations

        Yields:
            SQLAlchemy Session object

        Usage:
            with db.session_scope() as session:
                # Use session
                pass
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Global database instance (singleton)
_database: Database | None = None


def get_database(database_path: Path | None = None) -> Database:
    """
    Get the global database instance (singleton pattern)

    Args:
        database_path: Path to database file (only used on first call)

    Returns:
        Database instance
    """
    global _database
    if _database is None:
        _database = Database(database_path)
    return _database


def get_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions

    Yields:
        SQLAlchemy Session object

    Usage in FastAPI:
        @app.get("/items")
        def get_items(session: Session = Depends(get_session)):
            return session.query(Item).all()
    """
    db = get_database()
    with db.session_scope() as session:
        yield session
