"""
Database verification: Confirm test suite tables exist

Verifies that the test_suites and test_suite_executions tables
were created successfully.
"""

import logging

from sqlalchemy import inspect

from ignition_toolkit.storage import get_database

logger = logging.getLogger(__name__)


def verify_test_suite_tables():
    """
    Verify test suite tables exist and have correct schema

    Returns:
        bool: True if all tables and columns exist, False otherwise
    """
    db = get_database()

    with db.session_scope() as session:
        inspector = inspect(session.bind)
        table_names = inspector.get_table_names()

        # Check for test_suites table
        if "test_suites" not in table_names:
            logger.error("❌ test_suites table does not exist")
            return False

        logger.info("✅ test_suites table exists")

        # Verify test_suites columns
        test_suites_columns = {col["name"] for col in inspector.get_columns("test_suites")}
        required_suite_columns = {
            "id",
            "suite_name",
            "page_url",
            "status",
            "total_playbooks",
            "completed_playbooks",
            "passed_playbooks",
            "failed_playbooks",
            "total_components_tested",
            "passed_tests",
            "failed_tests",
            "skipped_tests",
            "started_at",
            "completed_at",
            "suite_metadata",
        }

        missing_suite_cols = required_suite_columns - test_suites_columns
        if missing_suite_cols:
            logger.error(f"❌ test_suites missing columns: {missing_suite_cols}")
            return False

        logger.info(f"✅ test_suites has all required columns ({len(test_suites_columns)} columns)")

        # Check for test_suite_executions table
        if "test_suite_executions" not in table_names:
            logger.error("❌ test_suite_executions table does not exist")
            return False

        logger.info("✅ test_suite_executions table exists")

        # Verify test_suite_executions columns
        test_suite_exec_columns = {
            col["name"] for col in inspector.get_columns("test_suite_executions")
        }
        required_exec_columns = {
            "id",
            "suite_id",
            "execution_id",
            "playbook_name",
            "playbook_type",
            "status",
            "passed_tests",
            "failed_tests",
            "skipped_tests",
            "execution_order",
            "failed_component_ids",
        }

        missing_exec_cols = required_exec_columns - test_suite_exec_columns
        if missing_exec_cols:
            logger.error(f"❌ test_suite_executions missing columns: {missing_exec_cols}")
            return False

        logger.info(
            f"✅ test_suite_executions has all required columns ({len(test_suite_exec_columns)} columns)"
        )

        # Verify indexes exist
        test_suite_indexes = {idx["name"] for idx in inspector.get_indexes("test_suites")}
        required_suite_indexes = {
            "idx_test_suites_status",
            "idx_test_suites_started_at",
            "idx_test_suites_suite_name",
        }

        if not required_suite_indexes.issubset(test_suite_indexes):
            missing_indexes = required_suite_indexes - test_suite_indexes
            logger.warning(f"⚠️  test_suites missing indexes: {missing_indexes}")
        else:
            logger.info(f"✅ test_suites has all required indexes ({len(test_suite_indexes)} indexes)")

        test_suite_exec_indexes = {
            idx["name"] for idx in inspector.get_indexes("test_suite_executions")
        }
        required_exec_indexes = {
            "idx_test_suite_executions_suite_id",
            "idx_test_suite_executions_execution_id",
            "idx_test_suite_executions_status",
        }

        if not required_exec_indexes.issubset(test_suite_exec_indexes):
            missing_indexes = required_exec_indexes - test_suite_exec_indexes
            logger.warning(f"⚠️  test_suite_executions missing indexes: {missing_indexes}")
        else:
            logger.info(
                f"✅ test_suite_executions has all required indexes ({len(test_suite_exec_indexes)} indexes)"
            )

        logger.info("✅ All test suite tables verified successfully!")
        return True


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger.info("Verifying test suite tables...")
    success = verify_test_suite_tables()
    if success:
        logger.info("✅ Verification complete - all tables ready!")
    else:
        logger.error("❌ Verification failed - please check database schema")
