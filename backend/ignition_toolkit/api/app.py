"""
FastAPI application - Main API server

Provides REST endpoints for playbook management and execution control.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from fastapi import (
    FastAPI,
    Response,
    WebSocket,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ignition_toolkit import __version__
from ignition_toolkit.api.middleware import RateLimitMiddleware
from ignition_toolkit.api.routers import health_router
from ignition_toolkit.api.routers.api_explorer import router as api_explorer_router
from ignition_toolkit.api.routers.auth import router as auth_router
from ignition_toolkit.api.routers.clouddesigner import router as clouddesigner_router
from ignition_toolkit.api.routers.config import router as config_router
from ignition_toolkit.api.routers.context import router as context_router
from ignition_toolkit.api.routers.credentials import router as credentials_router
from ignition_toolkit.api.routers.exchange import router as exchange_router
from ignition_toolkit.api.routers.execution_queue import router as execution_queue_router
from ignition_toolkit.api.routers.executions import router as executions_router
from ignition_toolkit.api.routers.filesystem import router as filesystem_router
from ignition_toolkit.api.routers.logs import router as logs_router
from ignition_toolkit.api.routers.playbooks import router as playbooks_router
from ignition_toolkit.api.routers.remote_data import router as remote_data_router
from ignition_toolkit.api.routers.reports import router as reports_router
from ignition_toolkit.api.routers.schedules import router as schedules_router
from ignition_toolkit.api.routers.stackbuilder import router as stackbuilder_router
from ignition_toolkit.api.routers.step_types import router as step_types_router
from ignition_toolkit.api.routers.updates import router as updates_router
from ignition_toolkit.api.routers.websockets import router as websockets_router
from ignition_toolkit.api.services.log_capture import setup_log_capture
from ignition_toolkit.playbook.engine import PlaybookEngine
from ignition_toolkit.playbook.metadata import PlaybookMetadataStore
from ignition_toolkit.startup.lifecycle import lifespan

logger = logging.getLogger(__name__)

# Create FastAPI app with lifespan manager
app = FastAPI(
    title="Ignition Automation Toolkit API",
    description="REST API for Ignition Gateway automation",
    version=__version__,
    lifespan=lifespan,
)

# Register health check router FIRST (before other routes)
app.include_router(health_router)

# Register config router (for portability)
app.include_router(config_router)

# Register Step Types router BEFORE playbooks (to avoid catch-all path conflict)
app.include_router(step_types_router)

# Register playbooks router
app.include_router(playbooks_router)

# Register executions router
app.include_router(executions_router)

# Register credentials router
app.include_router(credentials_router)

# Register schedules router
app.include_router(schedules_router)

# Register filesystem router
app.include_router(filesystem_router)

# Register updates router (v4.1.0)
app.include_router(updates_router)

# Register API Explorer router
app.include_router(api_explorer_router)

# Register Stack Builder router
app.include_router(stackbuilder_router)

# Register Exchange router
app.include_router(exchange_router)

# Register Remote Data Updates router
app.include_router(remote_data_router)

# Register CloudDesigner router
app.include_router(clouddesigner_router)

# Register Context router (used by MCP server)
app.include_router(context_router)

# Register WebSocket router
app.include_router(websockets_router)

# Register Logs router (for UI log access)
app.include_router(logs_router)

# Note: Step Types router registered earlier (before playbooks) to avoid path conflict

# Execution queue and parallel execution
app.include_router(execution_queue_router)

# Authentication and authorization
app.include_router(auth_router)

# Reporting and analytics
app.include_router(reports_router)

# Initialize log capture for UI access
setup_log_capture(max_entries=2000)
logger.info("Log capture initialized for UI access")

# ============================================================================
# Middleware (order matters - applied in reverse order)
# ============================================================================

# SECURITY: Rate limiting middleware (PORTABILITY v4)
# Prevents DoS attacks and API abuse
# No external dependencies - uses token bucket algorithm
app.add_middleware(RateLimitMiddleware)

# CORS middleware - Allow all origins for local desktop app
# This is safe because:
# 1. Backend only binds to 127.0.0.1 (localhost)
# 2. This is a single-user desktop application
# 3. The Electron app uses file:// or app:// protocol which doesn't match fixed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Electron app compatibility
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
active_engines: dict[str, PlaybookEngine] = {}
active_tasks: dict[str, "asyncio.Task"] = {}  # Track asyncio Tasks for proper cancellation
engine_completion_times: dict[str, datetime] = {}  # Track when engines completed for TTL cleanup
websocket_connections: list[WebSocket] = []

# Configuration
EXECUTION_TTL_MINUTES = 30  # Keep completed executions for 30 minutes

# Initialize playbook metadata store
metadata_store = PlaybookMetadataStore()


# Custom StaticFiles class with cache-busting headers
class NoCacheStaticFiles(StaticFiles):
    """StaticFiles subclass that adds no-cache headers to prevent browser caching"""

    async def get_response(self, path: str, scope) -> Response:
        response = await super().get_response(path, scope)
        # Add no-cache headers to all static files
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


# Pydantic models imported from shared models module

# Frontend static files will be mounted AFTER all API routes to avoid conflicts
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"


# Execution endpoints


# Credential routes moved to routers/credentials.py


# Playbook Metadata Endpoints


# WebSocket endpoints moved to routers/websockets.py

# AI routes moved to routers/ai.py


# ============================================================================
# NOTE: AI Credentials endpoints are defined earlier in this file (line ~1362-1440)
# This section intentionally left empty to avoid duplicate endpoint definitions
# ============================================================================


# ============================================================================
# Frontend Serving
# ============================================================================

# Serve frontend (React build) - MUST be at the END to avoid catching API routes
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    # Mount static assets directory with no-cache headers
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", NoCacheStaticFiles(directory=str(assets_dir)), name="assets")

    # Serve index.html for all routes (SPA routing) with cache-busting headers
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve React SPA - returns index.html for all non-API routes with no-cache headers"""
        # Check if this is a static file that exists in frontend_dist
        if full_path:
            static_file = frontend_dist / full_path
            if static_file.exists() and static_file.is_file():
                return FileResponse(str(static_file))

        # Serve index.html for all other routes (React Router handles routing)
        index_path = frontend_dist / "index.html"
        response = FileResponse(str(index_path))
        # Add cache-busting headers to prevent browser caching of index.html
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

else:
    logger.warning(
        "Frontend build not found at frontend/dist - run 'npm run build' in frontend/ directory"
    )


# Note: Shutdown logic moved to startup/lifecycle.py lifespan manager
