# Implementation Guide: Modular Architecture & Startup System

**Status:** Phase 1 Partially Complete
**Created:** 2025-10-24
**Estimated Remaining Time:** 6-8 hours

---

## Table of Contents

1. [Overview](#overview)
2. [What's Been Completed](#whats-been-completed)
3. [Implementation Roadmap](#implementation-roadmap)
4. [Detailed Implementation Steps](#detailed-implementation-steps)
5. [Testing Strategy](#testing-strategy)
6. [Verification Checklist](#verification-checklist)

---

## Overview

This guide documents the implementation of a robust startup system and modular architecture for the Ignition Automation Toolkit. The goals are:

- **Robust Startup**: Fail-fast validation, health checks, clear error messages
- **Modular Design**: Loose coupling via dependency injection
- **Scalability**: Plugin architecture for extensibility
- **Sustainability**: Clear interfaces, testable components

---

## What's Been Completed

### ✅ Core Module (`ignition_toolkit/core/`)

**Files Created:**
- `__init__.py` - Module exports
- `config.py` - Centralized configuration with Pydantic
- `interfaces.py` - Protocol definitions for DI
- `exceptions.py` - Base exception hierarchy

**Key Components:**

1. **Settings (config.py)**
   - Environment-based configuration
   - Type-safe with Pydantic
   - Supports .env files
   - Singleton pattern

2. **Interfaces (interfaces.py)**
   - `IDatabase` - Database protocol
   - `ICredentialVault` - Vault protocol
   - `IGatewayClient` - Gateway client protocol
   - `IBrowserManager` - Browser manager protocol
   - `IPlaybookEngine` - Playbook engine protocol
   - `IExecutionRepository` - Repository protocol

3. **Exception Hierarchy (exceptions.py)**
   - `ToolkitError` - Base exception with recovery hints
   - `ConfigurationError` - Config-related errors
   - `ValidationError` - Input validation errors
   - `AuthenticationError` - Auth errors
   - `ResourceNotFoundError` - 404-style errors

### ✅ Startup Module Structure (`ignition_toolkit/startup/`)

**Files Created:**
- `__init__.py` - Module exports

### ✅ Critical Bug Fixes

**Fixed in `ignition_toolkit/playbook/engine.py`:**
- Browser manager scope issue (variable defined inside try block)
- Now initializes `browser_manager = None` before try block (line 136)

---

## Implementation Roadmap

### Phase 1: Startup System (PRIORITY: CRITICAL)
- [ ] 1.1 Health State Management
- [ ] 1.2 Startup Exceptions
- [ ] 1.3 Startup Validators
- [ ] 1.4 Lifespan Manager
- [ ] 1.5 Health Check Endpoints

### Phase 2: Component Updates (PRIORITY: HIGH)
- [ ] 2.1 Update Database Module
- [ ] 2.2 Update Credential Vault
- [ ] 2.3 Update FastAPI App

### Phase 3: Testing (PRIORITY: HIGH)
- [ ] 3.1 Unit Tests for Startup Components
- [ ] 3.2 Integration Tests
- [ ] 3.3 End-to-End Startup Test

### Phase 4: Documentation (PRIORITY: MEDIUM)
- [ ] 4.1 Update README
- [ ] 4.2 Add Architecture Documentation
- [ ] 4.3 Update CHANGELOG

---

## Detailed Implementation Steps

### Step 1.1: Health State Management

**File:** `ignition_toolkit/startup/health.py`

**Purpose:** Track system health status for observability

**Implementation:**

```python
"""
Health state management

Tracks component health and overall system readiness for monitoring
and debugging.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class HealthStatus(str, Enum):
    """Health status for system components"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """
    Health information for a single component

    Attributes:
        status: Health status (healthy/degraded/unhealthy/unknown)
        message: Human-readable status message
        last_checked: When health was last checked
        error: Error message if unhealthy
    """
    status: HealthStatus
    message: str = ""
    last_checked: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict"""
        return {
            "status": self.status.value,
            "message": self.message,
            "last_checked": self.last_checked.isoformat(),
            "error": self.error,
        }


@dataclass
class SystemHealth:
    """
    Global system health state

    Tracks overall system health and individual component health.
    Used for startup validation and health check endpoints.
    """
    overall: HealthStatus = HealthStatus.UNKNOWN
    ready: bool = False
    startup_time: Optional[datetime] = None

    # Component health
    database: ComponentHealth = field(default_factory=lambda: ComponentHealth(HealthStatus.UNKNOWN))
    vault: ComponentHealth = field(default_factory=lambda: ComponentHealth(HealthStatus.UNKNOWN))
    playbooks: ComponentHealth = field(default_factory=lambda: ComponentHealth(HealthStatus.UNKNOWN))
    frontend: ComponentHealth = field(default_factory=lambda: ComponentHealth(HealthStatus.UNKNOWN))

    # Startup issues
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for API responses"""
        return {
            "overall": self.overall.value,
            "ready": self.ready,
            "startup_time": self.startup_time.isoformat() if self.startup_time else None,
            "components": {
                "database": self.database.to_dict(),
                "vault": self.vault.to_dict(),
                "playbooks": self.playbooks.to_dict(),
                "frontend": self.frontend.to_dict(),
            },
            "errors": self.errors,
            "warnings": self.warnings,
        }


# Global health state (singleton)
_health_state = SystemHealth()


def get_health_state() -> SystemHealth:
    """
    Get current system health state

    Returns:
        SystemHealth instance
    """
    return _health_state


def set_component_healthy(component: str, message: str = "") -> None:
    """
    Mark a component as healthy

    Args:
        component: Component name (database, vault, playbooks, frontend)
        message: Optional status message
    """
    comp_health = ComponentHealth(HealthStatus.HEALTHY, message)
    setattr(_health_state, component, comp_health)


def set_component_unhealthy(component: str, error: str) -> None:
    """
    Mark a component as unhealthy

    Args:
        component: Component name
        error: Error message
    """
    comp_health = ComponentHealth(HealthStatus.UNHEALTHY, error=error)
    setattr(_health_state, component, comp_health)
    _health_state.errors.append(f"{component}: {error}")


def set_component_degraded(component: str, warning: str) -> None:
    """
    Mark a component as degraded

    Args:
        component: Component name
        warning: Warning message
    """
    comp_health = ComponentHealth(HealthStatus.DEGRADED, error=warning)
    setattr(_health_state, component, comp_health)
    _health_state.warnings.append(f"{component}: {warning}")


def reset_health_state() -> None:
    """Reset health state to initial values (for testing)"""
    global _health_state
    _health_state = SystemHealth()
```

**Testing:**
```python
# tests/test_startup/test_health.py
import pytest
from ignition_toolkit.startup.health import (
    get_health_state,
    set_component_healthy,
    set_component_unhealthy,
    HealthStatus,
)

def test_health_state_singleton():
    """Test health state is singleton"""
    state1 = get_health_state()
    state2 = get_health_state()
    assert state1 is state2

def test_set_component_healthy():
    """Test marking component as healthy"""
    set_component_healthy("database", "Test message")
    state = get_health_state()
    assert state.database.status == HealthStatus.HEALTHY
    assert state.database.message == "Test message"

def test_set_component_unhealthy():
    """Test marking component as unhealthy"""
    set_component_unhealthy("database", "Connection failed")
    state = get_health_state()
    assert state.database.status == HealthStatus.UNHEALTHY
    assert state.database.error == "Connection failed"
    assert "database: Connection failed" in state.errors
```

---

### Step 1.2: Startup Exceptions

**File:** `ignition_toolkit/startup/exceptions.py`

**Purpose:** Define startup-specific exceptions with recovery hints

**Implementation:**

```python
"""
Startup-specific exceptions

Provides clear error messages with recovery instructions for startup failures.
"""

from ignition_toolkit.core.exceptions import ToolkitError


class StartupError(ToolkitError):
    """Base exception for startup failures"""

    def __init__(self, message: str, component: str, recovery_hint: str = ""):
        super().__init__(message, component=component, recovery_hint=recovery_hint)


class EnvironmentError(StartupError):
    """Environment validation failed"""

    def __init__(self, message: str, recovery_hint: str = ""):
        super().__init__(
            message,
            component="Environment",
            recovery_hint=recovery_hint
        )


class DatabaseInitError(StartupError):
    """Database initialization failed"""

    def __init__(self, message: str, recovery_hint: str = ""):
        super().__init__(
            message,
            component="Database",
            recovery_hint=recovery_hint or "Check database file permissions and disk space"
        )


class VaultInitError(StartupError):
    """Credential vault initialization failed"""

    def __init__(self, message: str, recovery_hint: str = ""):
        super().__init__(
            message,
            component="Vault",
            recovery_hint=recovery_hint or "Run 'ignition-toolkit init' to create vault"
        )
```

---

### Step 1.3: Startup Validators

**File:** `ignition_toolkit/startup/validators.py`

**Purpose:** Phase-by-phase validation of system components

**Implementation:**

```python
"""
Startup validators

Validates system components during startup in phases:
1. Environment (Python version, directories, permissions)
2. Database (schema, connectivity)
3. Credential vault (encryption, file access)
4. Playbook library (directory, YAML validity)
5. Frontend build (production only)
"""

import sys
import os
from pathlib import Path
import logging
from sqlalchemy import text

from ignition_toolkit.core.config import get_settings
from ignition_toolkit.storage.database import get_database
from ignition_toolkit.credentials.vault import get_credential_vault
from ignition_toolkit.startup.exceptions import (
    DatabaseInitError,
    VaultInitError,
    EnvironmentError,
)

logger = logging.getLogger(__name__)


async def validate_environment() -> None:
    """
    Phase 1: Validate environment requirements

    Checks:
    - Python version >= 3.10
    - Data directory exists and is writable
    - Toolkit directory exists

    Raises:
        EnvironmentError: If environment validation fails
    """
    # Check Python version
    if sys.version_info < (3, 10):
        raise EnvironmentError(
            f"Python 3.10+ required, found {sys.version}",
            recovery_hint="Upgrade Python: https://www.python.org/downloads/"
        )
    logger.info(f"✓ Python version: {sys.version_info.major}.{sys.version_info.minor}")

    # Check/create data directory
    settings = get_settings()
    data_dir = settings.database_path.parent

    if not data_dir.exists():
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"✓ Created data directory: {data_dir.absolute()}")
        except Exception as e:
            raise EnvironmentError(
                f"Cannot create data directory: {e}",
                recovery_hint="Check filesystem permissions"
            )

    if not os.access(data_dir, os.W_OK):
        raise EnvironmentError(
            f"Data directory not writable: {data_dir.absolute()}",
            recovery_hint=f"Fix permissions: chmod u+w {data_dir}"
        )
    logger.info(f"✓ Data directory writable: {data_dir.absolute()}")

    # Check/create toolkit directory
    toolkit_dir = settings.vault_path.parent
    if not toolkit_dir.exists():
        try:
            toolkit_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"✓ Created toolkit directory: {toolkit_dir}")
        except Exception as e:
            raise EnvironmentError(
                f"Cannot create toolkit directory: {e}",
                recovery_hint="Check home directory permissions"
            )
    logger.info(f"✓ Toolkit directory: {toolkit_dir}")


async def initialize_database() -> None:
    """
    Phase 2: Initialize database and verify schema

    Checks:
    - Database file can be created/accessed
    - Tables can be created
    - Test query works

    Raises:
        DatabaseInitError: If database initialization fails
    """
    try:
        db = get_database()

        # Create all tables (idempotent)
        db.create_tables()
        logger.info("✓ Database tables created/verified")

        # Test query
        with db.session_scope() as session:
            result = session.execute(text("SELECT 1")).fetchone()
            if result[0] != 1:
                raise DatabaseInitError("Database test query failed")

        logger.info(f"✓ Database operational: {db.database_path}")

    except Exception as e:
        if isinstance(e, DatabaseInitError):
            raise
        raise DatabaseInitError(
            f"Database initialization failed: {e}",
            recovery_hint="Delete data/toolkit.db and restart"
        )


async def initialize_vault() -> None:
    """
    Phase 3: Initialize credential vault

    Checks:
    - Vault file can be created/accessed
    - Encryption/decryption works

    Raises:
        VaultInitError: If vault initialization fails
    """
    try:
        vault = get_credential_vault()

        # Initialize vault (creates file if needed)
        vault.initialize()

        # Test encryption/decryption
        if not vault.test_encryption():
            raise VaultInitError("Vault encryption test failed")

        logger.info(f"✓ Credential vault operational: {vault.vault_path}")

    except Exception as e:
        if isinstance(e, VaultInitError):
            raise
        raise VaultInitError(
            f"Vault initialization failed: {e}",
            recovery_hint="Run 'ignition-toolkit init' to reset vault"
        )


async def validate_playbooks() -> dict:
    """
    Phase 4: Validate playbook library (non-fatal)

    Checks:
    - Playbooks directory exists
    - Counts available playbooks

    Returns:
        dict: Playbook statistics (total, gateway, perspective counts)

    Raises:
        Exception: If validation fails (caught by lifecycle manager as warning)
    """
    playbooks_dir = Path("playbooks")
    if not playbooks_dir.exists():
        raise Exception(f"Playbooks directory not found: {playbooks_dir.absolute()}")

    # Count playbooks by domain
    gateway_playbooks = list((playbooks_dir / "gateway").glob("*.yaml")) if (playbooks_dir / "gateway").exists() else []
    perspective_playbooks = list((playbooks_dir / "perspective").glob("*.yaml")) if (playbooks_dir / "perspective").exists() else []
    example_playbooks = list((playbooks_dir / "examples").glob("*.yaml")) if (playbooks_dir / "examples").exists() else []

    total = len(gateway_playbooks) + len(perspective_playbooks) + len(example_playbooks)

    logger.info(
        f"✓ Found {total} playbooks "
        f"({len(gateway_playbooks)} gateway, {len(perspective_playbooks)} perspective, "
        f"{len(example_playbooks)} examples)"
    )

    return {
        "total": total,
        "gateway": len(gateway_playbooks),
        "perspective": len(perspective_playbooks),
        "examples": len(example_playbooks),
    }


async def validate_frontend() -> None:
    """
    Phase 5: Validate frontend build (production only, non-fatal)

    Checks:
    - frontend/dist/ exists
    - index.html exists

    Raises:
        Exception: If frontend validation fails
    """
    settings = get_settings()
    frontend_dir = settings.frontend_dir

    if not frontend_dir.exists():
        raise Exception(f"Frontend build not found: {frontend_dir.absolute()}")

    index_file = frontend_dir / "index.html"
    if not index_file.exists():
        raise Exception(f"Frontend index.html not found: {index_file.absolute()}")

    logger.info(f"✓ Frontend build verified: {frontend_dir.absolute()}")
```

---

### Step 1.4: Lifespan Manager

**File:** `ignition_toolkit/startup/lifecycle.py`

**Purpose:** FastAPI lifespan context manager for orchestrating startup

**Implementation:**

```python
"""
Lifecycle management

Orchestrates application startup and shutdown using FastAPI's lifespan
context manager pattern.
"""

from contextlib import asynccontextmanager
from datetime import datetime
import logging

from fastapi import FastAPI

from ignition_toolkit.startup.validators import (
    validate_environment,
    initialize_database,
    initialize_vault,
    validate_playbooks,
    validate_frontend,
)
from ignition_toolkit.startup.health import (
    get_health_state,
    set_component_healthy,
    set_component_unhealthy,
    set_component_degraded,
    HealthStatus,
)
from ignition_toolkit.startup.exceptions import StartupError
from ignition_toolkit.core.config import get_settings, is_dev_mode

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
    start_time = datetime.utcnow()

    logger.info("=" * 60)
    logger.info("🚀 Ignition Automation Toolkit - Startup")
    logger.info("=" * 60)

    try:
        # Phase 1: Environment Validation (CRITICAL)
        logger.info("Phase 1/5: Environment Validation")
        try:
            await validate_environment()
            logger.info("✅ Environment validated")
        except StartupError as e:
            logger.error(f"❌ {e}")
            set_component_unhealthy("environment", str(e))
            raise

        # Phase 2: Database Initialization (CRITICAL)
        logger.info("Phase 2/5: Database Initialization")
        try:
            await initialize_database()
            set_component_healthy("database", "Database operational")
            logger.info("✅ Database initialized")
        except StartupError as e:
            logger.error(f"❌ {e}")
            set_component_unhealthy("database", str(e))
            raise

        # Phase 3: Credential Vault (CRITICAL)
        logger.info("Phase 3/5: Credential Vault Initialization")
        try:
            await initialize_vault()
            set_component_healthy("vault", "Vault operational")
            logger.info("✅ Credential vault initialized")
        except StartupError as e:
            logger.error(f"❌ {e}")
            set_component_unhealthy("vault", str(e))
            raise

        # Phase 4: Playbook Library (NON-FATAL)
        logger.info("Phase 4/5: Playbook Library Validation")
        try:
            stats = await validate_playbooks()
            set_component_healthy("playbooks", f"Found {stats['total']} playbooks")
            logger.info("✅ Playbook library validated")
        except Exception as e:
            logger.warning(f"⚠️  Playbook validation failed: {e}")
            set_component_degraded("playbooks", str(e))

        # Phase 5: Frontend Build (NON-FATAL, production only)
        if not is_dev_mode():
            logger.info("Phase 5/5: Frontend Validation")
            try:
                await validate_frontend()
                set_component_healthy("frontend", "Frontend build verified")
                logger.info("✅ Frontend validated")
            except Exception as e:
                logger.warning(f"⚠️  Frontend validation failed: {e}")
                set_component_degraded("frontend", str(e))
        else:
            logger.info("Phase 5/5: Frontend Validation (SKIPPED - dev mode)")
            set_component_healthy("frontend", "Dev mode - frontend served separately")

        # Mark system ready
        health.ready = True
        health.startup_time = datetime.utcnow()

        # Determine overall health
        if health.errors:
            health.overall = HealthStatus.UNHEALTHY
        elif health.warnings:
            health.overall = HealthStatus.DEGRADED
        else:
            health.overall = HealthStatus.HEALTHY

        # Startup summary
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info(f"✅ System Ready (Startup time: {elapsed:.2f}s)")
        logger.info(f"   Overall Status: {health.overall.value.upper()}")
        logger.info(f"   Database: {health.database.status.value}")
        logger.info(f"   Vault: {health.vault.status.value}")
        logger.info(f"   Playbooks: {health.playbooks.status.value}")
        logger.info(f"   Frontend: {health.frontend.status.value}")

        if health.warnings:
            logger.warning(f"   Warnings: {len(health.warnings)}")
            for warning in health.warnings:
                logger.warning(f"     - {warning}")

        logger.info("=" * 60)

        yield  # Application runs here

    except StartupError as e:
        logger.error("=" * 60)
        logger.error(f"❌ Startup failed: {e}")
        logger.error("=" * 60)
        health.overall = HealthStatus.UNHEALTHY
        health.ready = False
        raise

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ Unexpected startup error: {e}", exc_info=True)
        logger.error("=" * 60)
        health.overall = HealthStatus.UNHEALTHY
        health.ready = False
        raise

    finally:
        # Shutdown cleanup
        logger.info("🛑 Shutting down...")
        # Add any cleanup logic here (close connections, etc.)
        logger.info("✅ Shutdown complete")
```

---

### Step 1.5: Health Check Endpoints

**File:** `ignition_toolkit/api/routers/health.py`

**Purpose:** Expose health status via REST API

**Implementation:**

```python
"""
Health check endpoints

Provides health check endpoints for monitoring and debugging:
- GET /health - Overall health (200 if healthy/degraded, 503 if unhealthy)
- GET /health/live - Liveness probe (always 200 if running)
- GET /health/ready - Readiness probe (200 if ready, 503 if not)
- GET /health/detailed - Component-level health details
"""

from fastapi import APIRouter, Response, status
from datetime import datetime

from ignition_toolkit.startup.health import get_health_state, HealthStatus

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check(response: Response):
    """
    Overall health check

    Returns 200 if system is healthy/degraded and ready.
    Returns 503 if system is unhealthy or not ready.

    Used by load balancers and monitoring systems to determine
    if the application should receive traffic.
    """
    health = get_health_state()

    if not health.ready or health.overall == HealthStatus.UNHEALTHY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": health.overall.value,
        "ready": health.ready,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/live")
async def liveness_probe():
    """
    Liveness probe (Kubernetes-style)

    Always returns 200 if process is running.
    Used to detect if application should be restarted.

    This endpoint should ALWAYS return 200 unless the process
    has crashed or is in a completely unrecoverable state.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/ready")
async def readiness_probe(response: Response):
    """
    Readiness probe (Kubernetes-style)

    Returns 200 if system is ready to accept traffic.
    Returns 503 if system is not ready (still starting up or degraded).

    Used by load balancers to determine if this instance should
    receive traffic.
    """
    health = get_health_state()

    if not health.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "message": "System still initializing",
            "timestamp": datetime.utcnow().isoformat(),
        }

    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/detailed")
async def detailed_health(response: Response):
    """
    Detailed health check with component-level information

    Returns full health state including:
    - Overall status
    - Individual component health (database, vault, playbooks, frontend)
    - Startup time
    - Errors and warnings

    Use this for debugging and detailed monitoring.
    """
    health = get_health_state()

    if not health.ready or health.overall == HealthStatus.UNHEALTHY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return health.to_dict()
```

**Create Router Directory:**
```bash
mkdir -p ignition_toolkit/api/routers
touch ignition_toolkit/api/routers/__init__.py
```

---

### Step 2.1: Update Database Module

**File:** `ignition_toolkit/storage/database.py`

**Changes Needed:**

Add these methods to the `Database` class:

```python
# Add this method to Database class
def create_tables(self) -> None:
    """
    Explicitly create all database tables

    Should be called during startup initialization.
    Idempotent - safe to call multiple times.
    """
    Base.metadata.create_all(bind=self.engine)
    logger.info("Database tables created/verified")

def verify_schema(self) -> bool:
    """
    Verify database schema is valid

    Returns:
        bool: True if schema is valid
    """
    try:
        with self.session_scope() as session:
            # Test query on each table
            session.execute(text("SELECT COUNT(*) FROM executions")).fetchone()
            session.execute(text("SELECT COUNT(*) FROM step_results")).fetchone()
            session.execute(text("SELECT COUNT(*) FROM playbook_configs")).fetchone()
            return True
    except Exception as e:
        logger.error(f"Schema verification failed: {e}")
        return False
```

**Import Addition:**
```python
from sqlalchemy import text  # Add to imports at top
```

---

### Step 2.2: Update Credential Vault

**File:** `ignition_toolkit/credentials/vault.py`

**Changes Needed:**

Add these methods to the `CredentialVault` class:

```python
# Add these methods to CredentialVault class
def initialize(self) -> None:
    """
    Explicitly initialize vault (create file if needed)

    Should be called during startup initialization.
    Creates vault file with empty credentials if it doesn't exist.
    """
    if not self.vault_path.exists():
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        self._save_credentials({})
        logger.info(f"Created new credential vault: {self.vault_path}")
    else:
        # Verify we can read existing vault
        try:
            self._load_credentials()
            logger.info(f"Using existing credential vault: {self.vault_path}")
        except Exception as e:
            logger.error(f"Failed to read vault: {e}")
            raise

def test_encryption(self) -> bool:
    """
    Test vault encryption/decryption

    Returns:
        bool: True if encryption works correctly
    """
    try:
        test_data = "test_credential_12345"
        encrypted = self._cipher.encrypt(test_data.encode())
        decrypted = self._cipher.decrypt(encrypted).decode()
        return decrypted == test_data
    except Exception as e:
        logger.error(f"Encryption test failed: {e}")
        return False
```

---

### Step 2.3: Update FastAPI App

**File:** `ignition_toolkit/api/app.py`

**Changes Needed:**

1. **Import the lifespan manager:**
```python
# Add to imports
from ignition_toolkit.startup.lifecycle import lifespan
from ignition_toolkit.api.routers import health
```

2. **Update FastAPI app initialization:**
```python
# Change from:
app = FastAPI(
    title="Ignition Automation Toolkit",
    description="Visual acceptance testing platform for Ignition SCADA",
    version="1.0.6",
)

# To:
app = FastAPI(
    title="Ignition Automation Toolkit",
    description="Visual acceptance testing platform for Ignition SCADA",
    version="1.0.7",  # Bump version
    lifespan=lifespan,  # ← ADD THIS
)
```

3. **Register health router FIRST (before other routers):**
```python
# Add this right after app creation, before other routers
app.include_router(health.router)
```

**Complete app.py structure should look like:**
```python
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Import startup system
from ignition_toolkit.startup.lifecycle import lifespan
from ignition_toolkit.api.routers import health

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s - %(message)s",
)

# Create FastAPI app with lifespan
app = FastAPI(
    title="Ignition Automation Toolkit",
    description="Visual acceptance testing platform for Ignition SCADA",
    version="1.0.7",
    lifespan=lifespan,  # ← Startup/shutdown lifecycle
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register health check router FIRST (high priority)
app.include_router(health.router)

# ... rest of existing routers ...
```

---

## Testing Strategy

### Unit Tests

**Create:** `tests/test_startup/`

```bash
mkdir -p tests/test_startup
touch tests/test_startup/__init__.py
```

**Files to create:**
1. `test_health.py` - Test health state management
2. `test_validators.py` - Test each validator function
3. `test_lifecycle.py` - Test lifespan manager

### Integration Tests

**Test end-to-end startup:**

```python
# tests/test_startup/test_integration.py
import pytest
from fastapi.testclient import TestClient

from ignition_toolkit.api.app import app

def test_startup_success():
    """Test successful startup sequence"""
    with TestClient(app) as client:
        # Health check should work
        response = client.get("/health")
        assert response.status_code in (200, 503)

        # Liveness should always work
        response = client.get("/health/live")
        assert response.status_code == 200

        # Detailed health should have all components
        response = client.get("/health/detailed")
        data = response.json()
        assert "components" in data
        assert "database" in data["components"]
        assert "vault" in data["components"]
```

---

## Verification Checklist

After implementation, verify:

### ✅ Startup Sequence
- [ ] Server starts without errors
- [ ] All 5 phases complete successfully
- [ ] Startup time logged (should be < 2 seconds)
- [ ] Health status shows "healthy" or "degraded"

### ✅ Health Check Endpoints
- [ ] `GET /health` returns 200 or 503
- [ ] `GET /health/live` always returns 200
- [ ] `GET /health/ready` returns 200 when ready
- [ ] `GET /health/detailed` shows all components

### ✅ Error Handling
- [ ] Missing database shows clear error with recovery hint
- [ ] Invalid vault shows clear error with recovery hint
- [ ] Missing playbooks directory shows warning (not fatal)
- [ ] Server exits cleanly on fatal errors

### ✅ Development Mode
- [ ] `ENVIRONMENT=development` skips frontend validation
- [ ] Dev mode clearly indicated in logs

### ✅ Database
- [ ] Tables created on first run
- [ ] Schema validation works
- [ ] Test queries succeed

### ✅ Credential Vault
- [ ] Vault created on first run
- [ ] Encryption test passes
- [ ] Existing vault loads correctly

---

## Next Steps After Implementation

1. **Test thoroughly** - Run all tests, manual verification
2. **Update documentation** - README, ARCHITECTURE.md
3. **Version bump** - Update to 1.0.7 in pyproject.toml
4. **Create migration guide** - For existing deployments
5. **Add CLI `init` command** - For first-time setup
6. **Create development script** - `scripts/dev_startup.sh`

---

## Estimated Time Breakdown

| Task | Estimated Time |
|------|----------------|
| Health State Management | 30 min |
| Startup Exceptions | 15 min |
| Startup Validators | 1 hour |
| Lifespan Manager | 30 min |
| Health Check Endpoints | 30 min |
| Update Database Module | 15 min |
| Update Vault Module | 15 min |
| Update FastAPI App | 15 min |
| Testing | 1-2 hours |
| Documentation | 30 min |
| **TOTAL** | **5-6 hours** |

---

## Common Issues & Solutions

### Issue: "ModuleNotFoundError: No module named 'pydantic_settings'"

**Solution:**
```bash
pip install pydantic-settings
```

### Issue: Database errors on startup

**Solution:**
```bash
# Delete existing database and let startup recreate it
rm data/toolkit.db
# Restart server
```

### Issue: Vault encryption test fails

**Solution:**
```bash
# Reset vault
rm ~/.ignition-toolkit/credentials.vault
# Restart server
```

### Issue: Server won't start, shows "already in use"

**Solution:**
```bash
# Kill existing process
pkill -f "uvicorn.*ignition_toolkit"
# Restart
```

---

**END OF IMPLEMENTATION GUIDE**

*This guide will be updated as implementation progresses.*
