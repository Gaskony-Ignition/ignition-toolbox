"""
Tests for health check API endpoints

Tests database, storage, and cleanup endpoints.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class TestDatabaseHealth:
    """Test database health endpoint"""

    def test_database_health_returns_stats(self):
        """Test that database health returns statistics"""
        from ignition_toolkit.api.routers.health import database_health
        from contextlib import contextmanager
        import asyncio

        # Mock the database
        mock_db = MagicMock()
        mock_session = MagicMock()

        # Setup mock query results for func.count and func.min/max
        mock_session.query.return_value.scalar.side_effect = [10, 50, None, None]  # exec count, step count, oldest, newest
        mock_session.query.return_value.group_by.return_value.all.return_value = [
            ("completed", 8),
            ("failed", 2),
        ]

        # Create a proper context manager mock
        @contextmanager
        def mock_session_scope():
            yield mock_session

        mock_db.session_scope = mock_session_scope
        mock_db.db_path = "/tmp/test.db"

        with patch('ignition_toolkit.api.routers.health.get_database', return_value=mock_db):
            with patch('pathlib.Path.exists', return_value=False):
                result = asyncio.run(database_health())

        assert result["status"] == "healthy"
        assert result["type"] == "sqlite"

    def test_database_health_handles_errors(self):
        """Test that database health handles errors gracefully"""
        from ignition_toolkit.api.routers.health import database_health
        import asyncio

        mock_db = MagicMock()
        mock_db.session_scope.side_effect = Exception("Database error")

        with patch('ignition_toolkit.api.routers.health.get_database', return_value=mock_db):
            result = asyncio.run(database_health())

        assert result["status"] == "error"
        assert "error" in result


class TestStorageHealth:
    """Test storage health endpoint"""

    def test_storage_health_returns_stats(self, tmp_path):
        """Test that storage health returns file statistics"""
        from ignition_toolkit.api.routers.health import storage_health
        import asyncio

        # Create test screenshot files
        screenshots_dir = tmp_path / "screenshots"
        screenshots_dir.mkdir()

        (screenshots_dir / "test1.png").write_bytes(b"x" * 1000)
        (screenshots_dir / "test2.png").write_bytes(b"x" * 2000)

        with patch('ignition_toolkit.core.paths.get_screenshots_dir', return_value=screenshots_dir):
            result = asyncio.run(storage_health())

        assert result["status"] == "healthy"
        assert result["file_count"] == 2
        assert result["total_size_bytes"] == 3000

    def test_storage_health_empty_directory(self, tmp_path):
        """Test storage health with empty directory"""
        from ignition_toolkit.api.routers.health import storage_health
        import asyncio

        screenshots_dir = tmp_path / "screenshots"
        screenshots_dir.mkdir()

        with patch('ignition_toolkit.core.paths.get_screenshots_dir', return_value=screenshots_dir):
            result = asyncio.run(storage_health())

        assert result["status"] == "healthy"
        assert result["file_count"] == 0
        assert result["total_size_bytes"] == 0

    def test_storage_health_nonexistent_directory(self, tmp_path):
        """Test storage health when directory doesn't exist"""
        from ignition_toolkit.api.routers.health import storage_health
        import asyncio

        screenshots_dir = tmp_path / "nonexistent"

        with patch('ignition_toolkit.core.paths.get_screenshots_dir', return_value=screenshots_dir):
            result = asyncio.run(storage_health())

        assert result["status"] == "healthy"
        assert result["file_count"] == 0
        assert "note" in result


class TestCleanupEndpoint:
    """Test cleanup endpoint"""

    def test_cleanup_dry_run(self):
        """Test cleanup in dry run mode"""
        from ignition_toolkit.api.routers.health import cleanup_old_data, CleanupRequest
        import asyncio

        mock_db = MagicMock()
        mock_session = MagicMock()

        # Mock no old executions found
        mock_session.query.return_value.filter.return_value.all.return_value = []

        mock_db.session_scope.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.session_scope.return_value.__exit__ = MagicMock(return_value=False)

        request = CleanupRequest(older_than_days=30, dry_run=True)

        with patch('ignition_toolkit.api.routers.health.get_database', return_value=mock_db):
            result = asyncio.run(cleanup_old_data(request))

        assert result["dry_run"] is True
        assert result["executions_found"] == 0
        assert result["executions_deleted"] == 0

    def test_cleanup_request_validation(self):
        """Test cleanup request validation"""
        from ignition_toolkit.api.routers.health import CleanupRequest

        # Default values
        request = CleanupRequest()
        assert request.older_than_days == 30
        assert request.dry_run is True

        # Custom values
        request = CleanupRequest(older_than_days=7, dry_run=False)
        assert request.older_than_days == 7
        assert request.dry_run is False


class TestHealthEndpoints:
    """Test basic health endpoints"""

    def test_liveness_probe(self):
        """Test liveness probe always returns alive"""
        from ignition_toolkit.api.routers.health import liveness_probe
        import asyncio

        result = asyncio.run(liveness_probe())
        assert result["status"] == "alive"

    def test_readiness_probe_healthy(self):
        """Test readiness probe when healthy"""
        from ignition_toolkit.api.routers.health import readiness_probe
        from ignition_toolkit.startup.health import HealthStatus
        import asyncio

        mock_health = MagicMock()
        mock_health.ready = True
        mock_health.overall = HealthStatus.HEALTHY

        mock_response = MagicMock()

        with patch('ignition_toolkit.api.routers.health.get_health_state', return_value=mock_health):
            result = asyncio.run(readiness_probe(mock_response))

        assert result["ready"] is True
        assert result["status"] == "healthy"

    def test_readiness_probe_not_ready(self):
        """Test readiness probe when not ready"""
        from ignition_toolkit.api.routers.health import readiness_probe
        from ignition_toolkit.startup.health import HealthStatus
        import asyncio

        mock_health = MagicMock()
        mock_health.ready = False
        mock_health.overall = HealthStatus.UNHEALTHY

        mock_response = MagicMock()

        with patch('ignition_toolkit.api.routers.health.get_health_state', return_value=mock_health):
            result = asyncio.run(readiness_probe(mock_response))

        assert result["ready"] is False
        # Response should have 503 status
        assert mock_response.status_code == 503
