"""
Lifecycle management

Orchestrates application startup and shutdown using FastAPI's lifespan
context manager pattern.
"""

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI

from ignition_toolkit.core.config import is_dev_mode
from ignition_toolkit.startup.exceptions import StartupError
from ignition_toolkit.startup.health import (
    HealthStatus,
    get_health_state,
    set_component_degraded,
    set_component_healthy,
    set_component_unhealthy,
)
from ignition_toolkit.startup.validators import (
    initialize_database,
    initialize_vault,
    validate_environment,
    validate_frontend,
    validate_playbooks,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager

    Handles startup initialization and shutdown cleanup.
    Runs validation in phases:
    1. Environment (CRITICAL - must pass)
    2. Database (CRITICAL - must pass)
    3. Credential Vault (CRITICAL - must pass)
    4. Playbook Library (NON-FATAL - warns if fails)
    5. Frontend Build (NON-FATAL - production only)

    Yields control to FastAPI to handle requests, then cleans up on shutdown.
    """
    health = get_health_state()
    start_time = datetime.now(UTC)

    logger.info("=" * 60)
    logger.info("Ignition Automation Toolkit - Startup")
    logger.info("=" * 60)

    try:
        # Phase 1: Environment Validation (CRITICAL)
        logger.info("Phase 1/8: Environment Validation")
        try:
            await validate_environment()
            logger.info("[OK] Environment validated")
        except StartupError as e:
            logger.error(f"[ERROR] {e}")
            set_component_unhealthy("environment", str(e))
            raise

        # Phase 2: Database Initialization (CRITICAL)
        logger.info("Phase 2/8: Database Initialization")
        try:
            await initialize_database()
            set_component_healthy("database", "Database operational")
            logger.info("[OK] Database initialized")
        except StartupError as e:
            logger.error(f"[ERROR] {e}")
            set_component_unhealthy("database", str(e))
            raise

        # Phase 3: Credential Vault (CRITICAL)
        logger.info("Phase 3/8: Credential Vault Initialization")
        try:
            await initialize_vault()
            set_component_healthy("vault", "Vault operational")
            logger.info("[OK] Credential vault initialized")
        except StartupError as e:
            logger.error(f"[ERROR] {e}")
            set_component_unhealthy("vault", str(e))
            raise

        # Phase 4: Playbook Library (NON-FATAL)
        logger.info("Phase 4/8: Playbook Library Validation")
        try:
            stats = await validate_playbooks()
            set_component_healthy("playbooks", f"Found {stats['total']} playbooks")
            logger.info("[OK] Playbook library validated")
        except Exception as e:
            logger.warning(f"[WARN]  Playbook validation failed: {e}")
            set_component_degraded("playbooks", str(e))

        # Step type registry completeness check (NON-FATAL)
        try:
            from ignition_toolkit.playbook.step_type_registry import validate_registry_completeness

            missing = validate_registry_completeness()
            if missing:
                logger.warning(
                    f"[WARN]  Step type registry is incomplete. "
                    f"Missing entries for: {missing}"
                )
            else:
                logger.info("[OK] Step type registry complete")
        except Exception as e:
            logger.warning(f"[WARN]  Step type registry check failed: {e}")

        # Phase 5: Playwright Browser (NON-FATAL but required for playbook execution)
        # Browsers should be bundled with the installer - just verify they exist
        logger.info("Phase 5/8: Playwright Browser Check")
        try:
            from ignition_toolkit.startup.playwright_installer import (
                get_playwright_browsers_path,
                is_browser_installed,
            )

            browsers_path = get_playwright_browsers_path()
            logger.info(f"Checking for browsers at: {browsers_path}")
            logger.info(f"  Path exists: {browsers_path.exists()}")
            if browsers_path.exists():
                contents = list(browsers_path.iterdir())
                logger.info(f"  Contents: {[p.name for p in contents]}")

            if is_browser_installed():
                set_component_healthy("browser", "Chromium browser ready")
                logger.info("[OK] Playwright browser ready")
            else:
                # Browser not found - provide diagnostic detail
                if browsers_path.exists():
                    contents = [p.name for p in browsers_path.iterdir()]
                    detail = f"Browser directory exists at {browsers_path} but no Chromium executable found. Contents: {contents}"
                else:
                    detail = f"Browser directory not found at {browsers_path}"
                set_component_degraded("browser", detail)
                logger.warning(f"[WARN]  {detail}")
                logger.warning("   Playbooks requiring a browser will fail.")
        except Exception as e:
            logger.warning(f"[WARN]  Browser check failed: {e}")
            set_component_degraded("browser", str(e))

        # Phase 6: Frontend Build (NON-FATAL, production only)
        # In frozen mode (PyInstaller), Electron serves the frontend - skip validation
        from ignition_toolkit.core.paths import is_frozen
        if is_frozen():
            logger.info("Phase 6/8: Frontend Validation (SKIPPED - Electron serves frontend)")
            set_component_healthy("frontend", "Electron serves frontend")
        elif not is_dev_mode():
            logger.info("Phase 6/8: Frontend Validation")
            try:
                await validate_frontend()
                set_component_healthy("frontend", "Frontend build verified")
                logger.info("[OK] Frontend validated")
            except Exception as e:
                logger.warning(f"[WARN]  Frontend validation failed: {e}")
                set_component_degraded("frontend", str(e))
        else:
            logger.info("Phase 6/8: Frontend Validation (SKIPPED - dev mode)")
            set_component_healthy("frontend", "Dev mode - frontend served separately")

        # Phase 7: Start Scheduler (NON-FATAL)
        logger.info("Phase 7/8: Starting Playbook Scheduler")
        try:
            from ignition_toolkit.scheduler import get_scheduler

            scheduler = get_scheduler()
            await scheduler.start()
            set_component_healthy("scheduler", "Scheduler running")
            logger.info("[OK] Playbook scheduler started")
        except Exception as e:
            logger.warning(f"[WARN]  Scheduler startup failed: {e}")
            set_component_degraded("scheduler", str(e))

        # Phase 8: Initialize Application Services
        logger.info("Phase 8/8: Initializing Application Services")
        try:
            from ignition_toolkit.api.services import AppServices

            services = AppServices.create(ttl_minutes=30)
            app.state.services = services
            set_component_healthy("services", "Application services initialized")
            logger.info("[OK] Application services initialized")
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize services: {e}")
            set_component_unhealthy("services", str(e))
            raise

        # Mark system ready
        health.ready = True
        health.startup_time = datetime.now(UTC)

        # Determine overall health
        if health.errors:
            health.overall = HealthStatus.UNHEALTHY
        elif health.warnings:
            health.overall = HealthStatus.DEGRADED
        else:
            health.overall = HealthStatus.HEALTHY

        # Startup summary
        elapsed = (datetime.now(UTC) - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info(f"[OK] System Ready (Startup time: {elapsed:.2f}s)")
        logger.info(f"   Overall Status: {health.overall.value.upper()}")
        logger.info(f"   Database: {health.database.status.value}")
        logger.info(f"   Vault: {health.vault.status.value}")
        logger.info(f"   Playbooks: {health.playbooks.status.value}")
        logger.info(f"   Browser: {health.browser.status.value}")
        logger.info(f"   Frontend: {health.frontend.status.value}")
        logger.info(f"   Scheduler: {health.scheduler.status.value if hasattr(health, 'scheduler') else 'N/A'}")

        if health.warnings:
            logger.warning(f"   Warnings: {len(health.warnings)}")
            for warning in health.warnings:
                logger.warning(f"     - {warning}")

        logger.info("=" * 60)

        yield  # Application runs here

    except StartupError as e:
        logger.error("=" * 60)
        logger.error(f"[ERROR] Startup failed: {e}")
        logger.error("=" * 60)
        health.overall = HealthStatus.UNHEALTHY
        health.ready = False
        raise

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"[ERROR] Unexpected startup error: {e}", exc_info=True)
        logger.error("=" * 60)
        health.overall = HealthStatus.UNHEALTHY
        health.ready = False
        raise

    finally:
        # Shutdown cleanup
        logger.info("[STOP] Shutting down...")

        # Cleanup application services
        try:
            if hasattr(app.state, "services"):
                await app.state.services.cleanup()
                logger.info("[OK] Application services cleaned up")
        except Exception as e:
            logger.warning(f"[WARN]  Service cleanup warning: {e}")

        # Stop scheduler
        try:
            from ignition_toolkit.scheduler import get_scheduler

            scheduler = get_scheduler()
            await scheduler.stop()
            logger.info("[OK] Scheduler stopped")
        except Exception as e:
            logger.warning(f"[WARN]  Scheduler shutdown warning: {e}")

        logger.info("[OK] Shutdown complete")
