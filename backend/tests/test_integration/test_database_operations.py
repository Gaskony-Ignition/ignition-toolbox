"""
Integration tests for database operations.

Tests the full lifecycle of executions and step results using a real SQLite database.
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime, UTC
import uuid

from ignition_toolkit.storage.database import Database
from ignition_toolkit.storage.models import ExecutionModel, StepResultModel


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)  # Pass Path object, not string
        yield db
        # Close DB engine before tmpdir cleanup (prevents Windows file-locking errors)
        db.engine.dispose()


class TestExecutionLifecycle:
    """Test complete execution lifecycle in database."""

    def test_create_execution(self, temp_db):
        """Test creating a new execution."""
        execution_id = str(uuid.uuid4())

        with temp_db.session_scope() as session:
            execution = ExecutionModel(
                execution_id=execution_id,
                playbook_name="Test Playbook",
                playbook_version="1.0.0",
                status="pending",
                config_data={"param1": "value1"},
            )
            session.add(execution)
            session.flush()

            # Verify execution was created
            assert execution.id is not None
            assert execution.execution_id == execution_id
            assert execution.status == "pending"

    def test_update_execution_status(self, temp_db):
        """Test updating execution status through lifecycle."""
        execution_id = str(uuid.uuid4())

        # Create execution
        with temp_db.session_scope() as session:
            execution = ExecutionModel(
                execution_id=execution_id,
                playbook_name="Test Playbook",
                status="pending",
            )
            session.add(execution)

        # Update to running
        with temp_db.session_scope() as session:
            execution = session.query(ExecutionModel).filter_by(
                execution_id=execution_id
            ).first()
            execution.status = "running"

        # Update to completed
        with temp_db.session_scope() as session:
            execution = session.query(ExecutionModel).filter_by(
                execution_id=execution_id
            ).first()
            execution.status = "completed"
            execution.completed_at = datetime.now(UTC)

        # Verify final state
        with temp_db.session_scope() as session:
            execution = session.query(ExecutionModel).filter_by(
                execution_id=execution_id
            ).first()
            assert execution.status == "completed"
            assert execution.completed_at is not None

    def test_add_step_results(self, temp_db):
        """Test adding step results to an execution."""
        execution_id = str(uuid.uuid4())

        # Create execution with step results
        with temp_db.session_scope() as session:
            execution = ExecutionModel(
                execution_id=execution_id,
                playbook_name="Test Playbook",
                status="running",
            )
            session.add(execution)
            session.flush()

            # Add step results
            for i in range(3):
                step = StepResultModel(
                    execution_id=execution.id,
                    step_id=f"step_{i}",
                    step_name=f"Step {i}",
                    status="completed" if i < 2 else "running",
                    started_at=datetime.now(UTC),
                    output={"result": f"output_{i}"},
                )
                session.add(step)

        # Verify step results
        with temp_db.session_scope() as session:
            execution = session.query(ExecutionModel).filter_by(
                execution_id=execution_id
            ).first()
            assert len(execution.step_results) == 3
            assert execution.step_results[0].status == "completed"
            assert execution.step_results[2].status == "running"

    def test_cascade_delete(self, temp_db):
        """Test that deleting execution cascades to step results."""
        execution_id = str(uuid.uuid4())

        # Create execution with step results
        with temp_db.session_scope() as session:
            execution = ExecutionModel(
                execution_id=execution_id,
                playbook_name="Test Playbook",
                status="completed",
            )
            session.add(execution)
            session.flush()

            for i in range(3):
                step = StepResultModel(
                    execution_id=execution.id,
                    step_id=f"step_{i}",
                    step_name=f"Step {i}",
                    status="completed",
                )
                session.add(step)

        # Count step results before delete
        with temp_db.session_scope() as session:
            step_count = session.query(StepResultModel).count()
            assert step_count == 3

        # Delete execution
        with temp_db.session_scope() as session:
            execution = session.query(ExecutionModel).filter_by(
                execution_id=execution_id
            ).first()
            session.delete(execution)

        # Verify step results were deleted
        with temp_db.session_scope() as session:
            step_count = session.query(StepResultModel).count()
            assert step_count == 0


class TestExecutionQueries:
    """Test querying executions."""

    def test_query_by_status(self, temp_db):
        """Test querying executions by status."""
        # Create multiple executions with different statuses
        with temp_db.session_scope() as session:
            for status in ["pending", "running", "completed", "completed", "failed"]:
                execution = ExecutionModel(
                    execution_id=str(uuid.uuid4()),
                    playbook_name="Test Playbook",
                    status=status,
                )
                session.add(execution)

        # Query by status
        with temp_db.session_scope() as session:
            completed = session.query(ExecutionModel).filter_by(status="completed").all()
            assert len(completed) == 2

            failed = session.query(ExecutionModel).filter_by(status="failed").all()
            assert len(failed) == 1

    def test_query_with_ordering(self, temp_db):
        """Test querying with order by."""
        # Create executions
        with temp_db.session_scope() as session:
            for i in range(5):
                execution = ExecutionModel(
                    execution_id=str(uuid.uuid4()),
                    playbook_name=f"Playbook {i}",
                    status="completed",
                )
                session.add(execution)

        # Query with order by
        with temp_db.session_scope() as session:
            executions = (
                session.query(ExecutionModel)
                .order_by(ExecutionModel.started_at.desc())
                .limit(3)
                .all()
            )
            assert len(executions) == 3

    def test_query_by_playbook_name(self, temp_db):
        """Test querying executions by playbook name."""
        # Create executions for different playbooks
        with temp_db.session_scope() as session:
            for name in ["Playbook A", "Playbook A", "Playbook B"]:
                execution = ExecutionModel(
                    execution_id=str(uuid.uuid4()),
                    playbook_name=name,
                    status="completed",
                )
                session.add(execution)

        # Query by playbook name
        with temp_db.session_scope() as session:
            playbook_a = session.query(ExecutionModel).filter_by(
                playbook_name="Playbook A"
            ).all()
            assert len(playbook_a) == 2


class TestStepResultOperations:
    """Test step result specific operations."""

    def test_step_result_with_output(self, temp_db):
        """Test storing complex output in step result."""
        execution_id = str(uuid.uuid4())

        complex_output = {
            "tables": [
                {"name": "users", "rows": 100},
                {"name": "orders", "rows": 500},
            ],
            "metrics": {
                "duration_ms": 1234,
                "memory_mb": 256,
            },
            "nested": {
                "level1": {
                    "level2": {
                        "value": "deep"
                    }
                }
            }
        }

        # Create execution with complex output
        with temp_db.session_scope() as session:
            execution = ExecutionModel(
                execution_id=execution_id,
                playbook_name="Test Playbook",
                status="completed",
            )
            session.add(execution)
            session.flush()

            step = StepResultModel(
                execution_id=execution.id,
                step_id="step_1",
                step_name="Complex Step",
                status="completed",
                output=complex_output,
            )
            session.add(step)

        # Verify complex output was stored and retrieved
        with temp_db.session_scope() as session:
            execution = session.query(ExecutionModel).filter_by(
                execution_id=execution_id
            ).first()
            step = execution.step_results[0]
            assert step.output["tables"][0]["name"] == "users"
            assert step.output["metrics"]["duration_ms"] == 1234
            assert step.output["nested"]["level1"]["level2"]["value"] == "deep"

    def test_step_result_with_error(self, temp_db):
        """Test storing error messages in step result."""
        execution_id = str(uuid.uuid4())

        # Create execution with failed step
        with temp_db.session_scope() as session:
            execution = ExecutionModel(
                execution_id=execution_id,
                playbook_name="Test Playbook",
                status="failed",
            )
            session.add(execution)
            session.flush()

            step = StepResultModel(
                execution_id=execution.id,
                step_id="step_1",
                step_name="Failing Step",
                status="failed",
                error_message="Connection timeout after 30 seconds",
            )
            session.add(step)

        # Verify error was stored
        with temp_db.session_scope() as session:
            execution = session.query(ExecutionModel).filter_by(
                execution_id=execution_id
            ).first()
            step = execution.step_results[0]
            assert step.status == "failed"
            assert "timeout" in step.error_message.lower()

    def test_step_result_artifacts(self, temp_db):
        """Test storing artifacts (screenshot paths, etc.) in step result."""
        execution_id = str(uuid.uuid4())

        artifacts = {
            "screenshots": [
                "/screenshots/exec123/step1_before.png",
                "/screenshots/exec123/step1_after.png",
            ],
            "logs": "/logs/exec123/step1.log",
            "dom_snapshot": "/snapshots/exec123/step1.html",
        }

        # Create execution with artifacts
        with temp_db.session_scope() as session:
            execution = ExecutionModel(
                execution_id=execution_id,
                playbook_name="Test Playbook",
                status="completed",
            )
            session.add(execution)
            session.flush()

            step = StepResultModel(
                execution_id=execution.id,
                step_id="step_1",
                step_name="Visual Step",
                status="completed",
                artifacts=artifacts,
            )
            session.add(step)

        # Verify artifacts were stored
        with temp_db.session_scope() as session:
            execution = session.query(ExecutionModel).filter_by(
                execution_id=execution_id
            ).first()
            step = execution.step_results[0]
            assert len(step.artifacts["screenshots"]) == 2
            assert step.artifacts["logs"] == "/logs/exec123/step1.log"


class TestDatabaseConcurrency:
    """Test database operations under concurrent access patterns."""

    def test_multiple_sessions(self, temp_db):
        """Test that multiple sessions can work independently."""
        execution_id_1 = str(uuid.uuid4())
        execution_id_2 = str(uuid.uuid4())

        # Create two executions in separate sessions
        with temp_db.session_scope() as session1:
            exec1 = ExecutionModel(
                execution_id=execution_id_1,
                playbook_name="Playbook 1",
                status="running",
            )
            session1.add(exec1)

        with temp_db.session_scope() as session2:
            exec2 = ExecutionModel(
                execution_id=execution_id_2,
                playbook_name="Playbook 2",
                status="running",
            )
            session2.add(exec2)

        # Verify both exist
        with temp_db.session_scope() as session:
            count = session.query(ExecutionModel).count()
            assert count == 2

    def test_rollback_on_error(self, temp_db):
        """Test that failed transactions rollback properly."""
        execution_id = str(uuid.uuid4())

        # Create initial execution
        with temp_db.session_scope() as session:
            execution = ExecutionModel(
                execution_id=execution_id,
                playbook_name="Test Playbook",
                status="pending",
            )
            session.add(execution)

        # Try to create duplicate (should fail due to unique constraint)
        try:
            with temp_db.session_scope() as session:
                duplicate = ExecutionModel(
                    execution_id=execution_id,  # Same ID
                    playbook_name="Duplicate Playbook",
                    status="pending",
                )
                session.add(duplicate)
        except Exception:
            pass  # Expected to fail

        # Verify only one execution exists
        with temp_db.session_scope() as session:
            count = session.query(ExecutionModel).count()
            assert count == 1


class TestModelSerialization:
    """Test model to_dict serialization."""

    def test_execution_to_dict(self, temp_db):
        """Test ExecutionModel.to_dict() serialization."""
        execution_id = str(uuid.uuid4())

        # Create execution with step results
        with temp_db.session_scope() as session:
            execution = ExecutionModel(
                execution_id=execution_id,
                playbook_name="Test Playbook",
                playbook_version="1.2.3",
                status="completed",
                config_data={"gateway": "http://localhost:8088"},
                execution_metadata={"source": "ui"},
            )
            session.add(execution)
            session.flush()

            step = StepResultModel(
                execution_id=execution.id,
                step_id="step_1",
                step_name="First Step",
                status="completed",
                output={"result": "success"},
            )
            session.add(step)

        # Serialize and verify
        with temp_db.session_scope() as session:
            execution = session.query(ExecutionModel).filter_by(
                execution_id=execution_id
            ).first()
            data = execution.to_dict()

            assert data["execution_id"] == execution_id
            assert data["playbook_name"] == "Test Playbook"
            assert data["playbook_version"] == "1.2.3"
            assert data["status"] == "completed"
            assert data["config_data"]["gateway"] == "http://localhost:8088"
            assert len(data["step_results"]) == 1
            assert data["step_results"][0]["step_name"] == "First Step"
