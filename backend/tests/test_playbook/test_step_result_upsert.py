"""Regression test for #5: _save_step_result must update the pre-seeded
pending step row in place, not append a duplicate.

Before the fix, _save_execution_start inserted one PENDING row per step and
_save_step_result INSERTed a fresh row each time, so get_execution returned
every step twice (all pending, then the real outcomes) and inflated
total_steps / current_step_index.
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from ignition_toolkit.playbook.engine import PlaybookEngine
from ignition_toolkit.playbook.models import (
    ExecutionState,
    ExecutionStatus,
    StepResult,
    StepStatus,
)
from ignition_toolkit.storage.database import Database
from ignition_toolkit.storage.models import ExecutionModel, StepResultModel


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.db")
        yield db
        # Close DB engine before tmpdir cleanup (prevents Windows file-locking errors)
        db.engine.dispose()


@pytest.mark.asyncio
async def test_save_step_result_updates_in_place(temp_db):
    engine = PlaybookEngine(database=temp_db)

    # Mimic _save_execution_start: one execution + two pending step rows.
    with temp_db.session_scope() as session:
        execution = ExecutionModel(
            execution_id="exec-1",
            playbook_name="demo",
            status="running",
            started_at=datetime.now(),
        )
        session.add(execution)
        session.flush()
        db_execution_id = execution.id
        for step_id, step_name in (("step1", "Step 1"), ("step2", "Step 2")):
            session.add(
                StepResultModel(
                    execution_id=db_execution_id,
                    step_id=step_id,
                    step_name=step_name,
                    status=StepStatus.PENDING.value,
                )
            )

    state = ExecutionState(
        execution_id="exec-1",
        playbook_name="demo",
        status=ExecutionStatus.RUNNING,
        started_at=datetime.now(),
        total_steps=2,
        step_results=[],
    )
    state.db_execution_id = db_execution_id

    # step1 transitions PENDING -> RUNNING -> COMPLETED (two saves, same row).
    await engine._save_step_result(
        state, StepResult(step_id="step1", step_name="Step 1", status=StepStatus.RUNNING,
                          started_at=datetime.now())
    )
    await engine._save_step_result(
        state, StepResult(step_id="step1", step_name="Step 1", status=StepStatus.COMPLETED,
                          started_at=datetime.now(), completed_at=datetime.now())
    )

    with temp_db.session_scope() as session:
        rows = (
            session.query(StepResultModel)
            .filter_by(execution_id=db_execution_id)
            .all()
        )
        # Exactly two rows total (one per step), no duplicates.
        assert len(rows) == 2
        by_id = {r.step_id: r for r in rows}
        assert by_id["step1"].status == StepStatus.COMPLETED.value
        assert by_id["step2"].status == StepStatus.PENDING.value


@pytest.mark.asyncio
async def test_save_step_result_inserts_when_not_preseeded(temp_db):
    engine = PlaybookEngine(database=temp_db)

    with temp_db.session_scope() as session:
        execution = ExecutionModel(
            execution_id="exec-2",
            playbook_name="demo",
            status="running",
            started_at=datetime.now(),
        )
        session.add(execution)
        session.flush()
        db_execution_id = execution.id

    state = ExecutionState(
        execution_id="exec-2",
        playbook_name="demo",
        status=ExecutionStatus.RUNNING,
        started_at=datetime.now(),
        total_steps=1,
        step_results=[],
    )
    state.db_execution_id = db_execution_id

    # No pre-seeded row → falls back to insert.
    await engine._save_step_result(
        state, StepResult(step_id="dyn", step_name="Dynamic", status=StepStatus.COMPLETED,
                          started_at=datetime.now(), completed_at=datetime.now())
    )

    with temp_db.session_scope() as session:
        rows = session.query(StepResultModel).filter_by(execution_id=db_execution_id).all()
        assert len(rows) == 1
        assert rows[0].step_id == "dyn"
        assert rows[0].status == StepStatus.COMPLETED.value
