"""Initial schema baseline

Revision ID: 001
Revises: None
Create Date: 2026-02-07

Captures the existing database schema as the Alembic baseline.
Existing databases are stamped at this revision (tables already exist).
New databases get this migration applied to create all tables.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Executions
    op.create_table(
        "executions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("execution_id", sa.String(255), nullable=False),
        sa.Column("playbook_name", sa.String(255), nullable=False),
        sa.Column("playbook_version", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("config_data", sa.JSON(), nullable=True),
        sa.Column("execution_metadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_executions_execution_id", "executions", ["execution_id"], unique=True)
    op.create_index("idx_executions_status", "executions", ["status"])
    op.create_index("idx_executions_started_at", "executions", ["started_at"])
    op.create_index("idx_executions_playbook_name", "executions", ["playbook_name"])
    op.create_index("idx_executions_status_started", "executions", ["status", "started_at"])

    # Step Results
    op.create_table(
        "step_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("execution_id", sa.Integer(), nullable=False),
        sa.Column("step_id", sa.String(255), nullable=False),
        sa.Column("step_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("artifacts", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["execution_id"], ["executions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_step_results_execution_id", "step_results", ["execution_id"])
    op.create_index("idx_step_results_status", "step_results", ["status"])

    # Playbook Configs
    op.create_table(
        "playbook_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("playbook_name", sa.String(255), nullable=False),
        sa.Column("config_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_playbook_configs_playbook_name", "playbook_configs", ["playbook_name"])
    op.create_index("idx_playbook_configs_config_name", "playbook_configs", ["config_name"])

    # AI Settings
    op.create_table(
        "ai_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("api_key", sa.Text(), nullable=True),
        sa.Column("api_base_url", sa.String(500), nullable=True),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Scheduled Playbooks
    op.create_table(
        "scheduled_playbooks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("playbook_path", sa.String(500), nullable=False),
        sa.Column("schedule_type", sa.String(50), nullable=False),
        sa.Column("schedule_config", sa.JSON(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column("gateway_url", sa.String(500), nullable=True),
        sa.Column("credential_name", sa.String(255), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, default=True),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_scheduled_playbooks_enabled", "scheduled_playbooks", ["enabled"])
    op.create_index("idx_scheduled_playbooks_next_run", "scheduled_playbooks", ["next_run_at"])

    # FAT Reports
    op.create_table(
        "fat_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("execution_id", sa.Integer(), nullable=True),
        sa.Column("report_name", sa.String(255), nullable=False),
        sa.Column("page_url", sa.String(500), nullable=True),
        sa.Column("total_components", sa.Integer(), nullable=False, default=0),
        sa.Column("passed_tests", sa.Integer(), nullable=False, default=0),
        sa.Column("failed_tests", sa.Integer(), nullable=False, default=0),
        sa.Column("skipped_tests", sa.Integer(), nullable=False, default=0),
        sa.Column("visual_issues", sa.Integer(), nullable=False, default=0),
        sa.Column("report_html", sa.Text(), nullable=True),
        sa.Column("report_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["executions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_fat_reports_execution_id", "fat_reports", ["execution_id"])
    op.create_index("idx_fat_reports_created_at", "fat_reports", ["created_at"])

    # FAT Component Tests
    op.create_table(
        "fat_component_tests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("component_id", sa.String(255), nullable=False),
        sa.Column("component_type", sa.String(100), nullable=True),
        sa.Column("component_label", sa.String(500), nullable=True),
        sa.Column("test_action", sa.String(100), nullable=False),
        sa.Column("expected_behavior", sa.Text(), nullable=True),
        sa.Column("actual_behavior", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("screenshot_path", sa.String(500), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("tested_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["fat_reports.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_fat_component_tests_report_id", "fat_component_tests", ["report_id"])
    op.create_index("idx_fat_component_tests_status", "fat_component_tests", ["status"])

    # Test Suites
    op.create_table(
        "test_suites",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("suite_name", sa.String(255), nullable=False),
        sa.Column("page_url", sa.String(500), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("total_playbooks", sa.Integer(), nullable=False, default=0),
        sa.Column("completed_playbooks", sa.Integer(), nullable=False, default=0),
        sa.Column("passed_playbooks", sa.Integer(), nullable=False, default=0),
        sa.Column("failed_playbooks", sa.Integer(), nullable=False, default=0),
        sa.Column("total_components_tested", sa.Integer(), nullable=False, default=0),
        sa.Column("passed_tests", sa.Integer(), nullable=False, default=0),
        sa.Column("failed_tests", sa.Integer(), nullable=False, default=0),
        sa.Column("skipped_tests", sa.Integer(), nullable=False, default=0),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("suite_metadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_test_suites_status", "test_suites", ["status"])
    op.create_index("idx_test_suites_started_at", "test_suites", ["started_at"])
    op.create_index("idx_test_suites_suite_name", "test_suites", ["suite_name"])

    # Test Suite Executions
    op.create_table(
        "test_suite_executions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("suite_id", sa.Integer(), nullable=False),
        sa.Column("execution_id", sa.Integer(), nullable=False),
        sa.Column("playbook_name", sa.String(255), nullable=False),
        sa.Column("playbook_type", sa.String(100), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("passed_tests", sa.Integer(), nullable=False, default=0),
        sa.Column("failed_tests", sa.Integer(), nullable=False, default=0),
        sa.Column("skipped_tests", sa.Integer(), nullable=False, default=0),
        sa.Column("execution_order", sa.Integer(), nullable=False, default=0),
        sa.Column("failed_component_ids", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["suite_id"], ["test_suites.id"]),
        sa.ForeignKeyConstraint(["execution_id"], ["executions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_test_suite_executions_suite_id", "test_suite_executions", ["suite_id"]
    )
    op.create_index(
        "idx_test_suite_executions_execution_id", "test_suite_executions", ["execution_id"]
    )
    op.create_index(
        "idx_test_suite_executions_status", "test_suite_executions", ["status"]
    )

    # Saved Stacks
    op.create_table(
        "saved_stacks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("stack_name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("global_settings", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_saved_stacks_stack_name", "saved_stacks", ["stack_name"])

    # API Keys
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("gateway_url", sa.String(500), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_api_keys_name", "api_keys", ["name"])
    op.create_index("idx_api_keys_gateway_url", "api_keys", ["gateway_url"])


def downgrade() -> None:
    op.drop_table("api_keys")
    op.drop_table("saved_stacks")
    op.drop_table("test_suite_executions")
    op.drop_table("test_suites")
    op.drop_table("fat_component_tests")
    op.drop_table("fat_reports")
    op.drop_table("scheduled_playbooks")
    op.drop_table("ai_settings")
    op.drop_table("playbook_configs")
    op.drop_table("step_results")
    op.drop_table("executions")
