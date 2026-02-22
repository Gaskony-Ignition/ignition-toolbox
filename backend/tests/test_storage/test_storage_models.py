"""
Tests for SQLAlchemy storage models.

Verifies model classes can be instantiated, required columns exist,
defaults are correct, and to_dict() produces the expected structure.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from ignition_toolkit.storage.models import (
    Base,
    ExecutionModel,
    StepResultModel,
    PlaybookConfigModel,
    AISettingsModel,
    ScheduledPlaybookModel,
    FATReportModel,
    FATComponentTestModel,
    TestSuiteModel as TestSuiteDBModel,
    SavedStackModel,
    APIKeyModel,
    utcnow,
)


@pytest.fixture(scope="module")
def engine():
    """Create an in-memory SQLite engine for the whole test module."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Return a SQLAlchemy session that rolls back after each test."""
    with Session(engine) as sess:
        yield sess
        sess.rollback()


# ==============================================================================
# utcnow helper
# ==============================================================================

class TestUtcnow:
    def test_utcnow_returns_datetime(self):
        """utcnow() returns a timezone-aware datetime."""
        result = utcnow()
        assert isinstance(result, datetime)
        assert result.tzinfo is not None


# ==============================================================================
# ExecutionModel
# ==============================================================================

class TestExecutionModel:
    def test_execution_model_table_name(self):
        """ExecutionModel maps to the 'executions' table."""
        assert ExecutionModel.__tablename__ == "executions"

    def test_execution_model_can_be_instantiated(self):
        """ExecutionModel can be created with required fields."""
        model = ExecutionModel(
            execution_id="exec-uuid-001",
            playbook_name="My Playbook",
            status="running",
        )
        assert model.execution_id == "exec-uuid-001"
        assert model.playbook_name == "My Playbook"
        assert model.status == "running"

    def test_execution_model_optional_fields_default_to_none(self):
        """ExecutionModel optional fields are None by default."""
        model = ExecutionModel(
            execution_id="exec-uuid-002",
            playbook_name="Playbook",
            status="pending",
        )
        assert model.error_message is None
        assert model.config_data is None
        assert model.execution_metadata is None
        assert model.completed_at is None

    def test_execution_model_to_dict_has_expected_keys(self, session):
        """ExecutionModel.to_dict() contains all required keys."""
        model = ExecutionModel(
            execution_id="exec-uuid-003",
            playbook_name="Test",
            status="completed",
        )
        session.add(model)
        session.flush()

        d = model.to_dict()
        for key in ("id", "execution_id", "playbook_name", "status",
                    "started_at", "completed_at", "error_message",
                    "config_data", "step_results"):
            assert key in d, f"Missing key: {key}"

    def test_execution_model_step_results_defaults_to_empty_list(self, session):
        """ExecutionModel.to_dict() has an empty step_results list initially."""
        model = ExecutionModel(
            execution_id="exec-uuid-004",
            playbook_name="Test",
            status="pending",
        )
        session.add(model)
        session.flush()

        d = model.to_dict()
        assert d["step_results"] == []

    def test_execution_model_persisted_and_retrieved(self, session):
        """ExecutionModel is correctly stored and retrieved from the database."""
        model = ExecutionModel(
            execution_id="exec-uuid-persist",
            playbook_name="Persist Test",
            status="completed",
            playbook_version="1.0",
        )
        session.add(model)
        session.flush()

        retrieved = session.query(ExecutionModel).filter_by(
            execution_id="exec-uuid-persist"
        ).first()
        assert retrieved is not None
        assert retrieved.playbook_name == "Persist Test"
        assert retrieved.playbook_version == "1.0"


# ==============================================================================
# StepResultModel
# ==============================================================================

class TestStepResultModel:
    def test_step_result_model_table_name(self):
        """StepResultModel maps to the 'step_results' table."""
        assert StepResultModel.__tablename__ == "step_results"

    def test_step_result_can_be_linked_to_execution(self, session):
        """StepResultModel is linked to an ExecutionModel via FK."""
        execution = ExecutionModel(
            execution_id="exec-for-steps",
            playbook_name="Steps Test",
            status="running",
        )
        session.add(execution)
        session.flush()

        step = StepResultModel(
            execution_id=execution.id,
            step_id="step-1",
            step_name="Click Button",
            status="completed",
        )
        session.add(step)
        session.flush()

        assert step.id is not None
        assert step.execution_id == execution.id

    def test_step_result_to_dict_keys(self, session):
        """StepResultModel.to_dict() has all required keys."""
        execution = ExecutionModel(
            execution_id="exec-step-dict",
            playbook_name="Dict Test",
            status="running",
        )
        session.add(execution)
        session.flush()

        step = StepResultModel(
            execution_id=execution.id,
            step_id="step-x",
            step_name="My Step",
            status="failed",
        )
        session.add(step)
        session.flush()

        d = step.to_dict()
        for key in ("id", "execution_id", "step_id", "step_name", "status",
                    "started_at", "completed_at", "output", "error_message", "artifacts"):
            assert key in d, f"Missing key: {key}"


# ==============================================================================
# PlaybookConfigModel
# ==============================================================================

class TestPlaybookConfigModel:
    def test_playbook_config_table_name(self):
        """PlaybookConfigModel maps to the 'playbook_configs' table."""
        assert PlaybookConfigModel.__tablename__ == "playbook_configs"

    def test_playbook_config_can_be_instantiated(self):
        """PlaybookConfigModel can be created with required fields."""
        model = PlaybookConfigModel(
            playbook_name="My Playbook",
            config_name="Production",
            parameters={"gateway_url": "http://prod:8088"},
        )
        assert model.playbook_name == "My Playbook"
        assert model.config_name == "Production"
        assert model.parameters == {"gateway_url": "http://prod:8088"}

    def test_playbook_config_to_dict_keys(self, session):
        """PlaybookConfigModel.to_dict() has all required keys."""
        model = PlaybookConfigModel(
            playbook_name="PB",
            config_name="CFG",
            parameters={},
        )
        session.add(model)
        session.flush()

        d = model.to_dict()
        for key in ("id", "playbook_name", "config_name", "description",
                    "parameters", "created_at", "updated_at"):
            assert key in d


# ==============================================================================
# AISettingsModel
# ==============================================================================

class TestAISettingsModel:
    def test_ai_settings_table_name(self):
        """AISettingsModel maps to the 'ai_settings' table."""
        assert AISettingsModel.__tablename__ == "ai_settings"

    def test_ai_settings_can_be_instantiated(self):
        """AISettingsModel can be created with required fields."""
        model = AISettingsModel(
            name="anthropic-claude",
            provider="anthropic",
            api_key="encrypted-key",
            enabled=True,
        )
        assert model.name == "anthropic-claude"
        assert model.provider == "anthropic"
        assert model.enabled is True

    def test_ai_settings_to_dict_excludes_api_key(self, session):
        """AISettingsModel.to_dict() exposes has_api_key bool, not the raw key."""
        model = AISettingsModel(
            name="test-ai",
            provider="openai",
            api_key="super-secret",
            enabled=False,
        )
        session.add(model)
        session.flush()

        d = model.to_dict()
        assert "api_key" not in d
        assert d["has_api_key"] is True
        assert d["provider"] == "openai"


# ==============================================================================
# ScheduledPlaybookModel
# ==============================================================================

class TestScheduledPlaybookModel:
    def test_scheduled_playbook_table_name(self):
        """ScheduledPlaybookModel maps to the 'scheduled_playbooks' table."""
        assert ScheduledPlaybookModel.__tablename__ == "scheduled_playbooks"

    def test_scheduled_playbook_can_be_instantiated(self, session):
        """ScheduledPlaybookModel can be created with required fields and enabled defaults True."""
        model = ScheduledPlaybookModel(
            name="Daily Backup",
            playbook_path="gateway/backup.yaml",
            schedule_type="cron",
            schedule_config={"cron": "0 2 * * *"},
        )
        session.add(model)
        session.flush()
        assert model.name == "Daily Backup"
        assert model.schedule_type == "cron"
        assert model.enabled is True  # default applied after flush

    def test_scheduled_playbook_to_dict_keys(self, session):
        """ScheduledPlaybookModel.to_dict() contains all required keys."""
        model = ScheduledPlaybookModel(
            name="Test Schedule",
            playbook_path="test.yaml",
            schedule_type="interval",
            schedule_config={"minutes": 30},
        )
        session.add(model)
        session.flush()

        d = model.to_dict()
        for key in ("id", "name", "playbook_path", "schedule_type",
                    "schedule_config", "enabled", "created_at"):
            assert key in d


# ==============================================================================
# FATReportModel
# ==============================================================================

class TestFATReportModel:
    def test_fat_report_table_name(self):
        """FATReportModel maps to the 'fat_reports' table."""
        assert FATReportModel.__tablename__ == "fat_reports"

    def test_fat_report_default_counters(self, session):
        """FATReportModel numeric counters default to 0 after flush."""
        model = FATReportModel(report_name="FAT Report 1")
        session.add(model)
        session.flush()
        assert model.total_components == 0
        assert model.passed_tests == 0
        assert model.failed_tests == 0
        assert model.skipped_tests == 0
        assert model.visual_issues == 0

    def test_fat_report_to_dict_keys(self, session):
        """FATReportModel.to_dict() contains all expected keys."""
        model = FATReportModel(
            report_name="Test FAT",
            total_components=5,
            passed_tests=4,
            failed_tests=1,
        )
        session.add(model)
        session.flush()

        d = model.to_dict()
        for key in ("id", "report_name", "total_components", "passed_tests",
                    "failed_tests", "skipped_tests", "created_at", "component_tests"):
            assert key in d
        assert d["component_tests"] == []


# ==============================================================================
# SavedStackModel
# ==============================================================================

class TestSavedStackModel:
    def test_saved_stack_table_name(self):
        """SavedStackModel maps to the 'saved_stacks' table."""
        assert SavedStackModel.__tablename__ == "saved_stacks"

    def test_saved_stack_can_be_instantiated(self):
        """SavedStackModel can be created with required fields."""
        model = SavedStackModel(
            stack_name="my-stack",
            config_json={"services": []},
        )
        assert model.stack_name == "my-stack"
        assert model.config_json == {"services": []}

    def test_saved_stack_to_dict_keys(self, session):
        """SavedStackModel.to_dict() contains all required keys."""
        model = SavedStackModel(
            stack_name="test-stack",
            config_json={"services": ["ignition"]},
            description="A test stack",
        )
        session.add(model)
        session.flush()

        d = model.to_dict()
        for key in ("id", "stack_name", "description", "config_json",
                    "global_settings", "created_at", "updated_at"):
            assert key in d


# ==============================================================================
# APIKeyModel
# ==============================================================================

class TestAPIKeyModel:
    def test_api_key_table_name(self):
        """APIKeyModel maps to the 'api_keys' table."""
        assert APIKeyModel.__tablename__ == "api_keys"

    def test_api_key_can_be_instantiated(self):
        """APIKeyModel can be created with required fields."""
        model = APIKeyModel(
            name="prod-key",
            gateway_url="https://gw.example.com",
            api_key_encrypted="encrypted-token",
        )
        assert model.name == "prod-key"
        assert model.gateway_url == "https://gw.example.com"

    def test_api_key_to_dict_hides_encrypted_key(self, session):
        """APIKeyModel.to_dict() shows has_api_key bool, not the encrypted value."""
        model = APIKeyModel(
            name="hidden-key",
            gateway_url="http://gw:8088",
            api_key_encrypted="very-secret",
        )
        session.add(model)
        session.flush()

        d = model.to_dict()
        assert "api_key_encrypted" not in d
        assert d["has_api_key"] is True
        assert d["gateway_url"] == "http://gw:8088"

    def test_api_key_to_dict_keys(self, session):
        """APIKeyModel.to_dict() contains all expected keys."""
        model = APIKeyModel(
            name="key-dict-test",
            gateway_url="http://example.com",
            api_key_encrypted="enc",
        )
        session.add(model)
        session.flush()

        d = model.to_dict()
        for key in ("id", "name", "gateway_url", "has_api_key",
                    "description", "created_at", "last_used"):
            assert key in d


# ==============================================================================
# TestSuiteModel
# ==============================================================================

class TestTestSuiteModel:
    def test_test_suite_table_name(self):
        """TestSuiteModel maps to the 'test_suites' table."""
        assert TestSuiteDBModel.__tablename__ == "test_suites"

    def test_test_suite_default_counters(self, session):
        """TestSuiteModel numeric counters default to 0 after flush."""
        model = TestSuiteDBModel(suite_name="Suite A", status="pending")
        session.add(model)
        session.flush()
        assert model.total_playbooks == 0
        assert model.completed_playbooks == 0
        assert model.passed_playbooks == 0
        assert model.failed_playbooks == 0

    def test_test_suite_to_dict_keys(self, session):
        """TestSuiteModel.to_dict() contains all required keys."""
        model = TestSuiteDBModel(suite_name="My Suite", status="running")
        session.add(model)
        session.flush()

        d = model.to_dict()
        for key in ("id", "suite_name", "status", "total_playbooks",
                    "started_at", "suite_executions"):
            assert key in d
        assert d["suite_executions"] == []


# ==============================================================================
# FATComponentTestModel
# ==============================================================================

class TestFATComponentTestModel:
    def test_fat_component_test_table_name(self):
        """FATComponentTestModel maps to the 'fat_component_tests' table."""
        assert FATComponentTestModel.__tablename__ == "fat_component_tests"

    def test_fat_component_test_to_dict_keys(self, session):
        """FATComponentTestModel.to_dict() contains all required keys."""
        report = FATReportModel(report_name="Parent Report")
        session.add(report)
        session.flush()

        component = FATComponentTestModel(
            report_id=report.id,
            component_id="btn-submit",
            test_action="click",
            status="passed",
        )
        session.add(component)
        session.flush()

        d = component.to_dict()
        for key in ("id", "report_id", "component_id", "test_action",
                    "status", "error_message", "tested_at"):
            assert key in d
