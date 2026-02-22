"""
Exchange API Router

Provides endpoints for the Ignition Exchange scraper.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ignition_toolkit.exchange import get_exchange_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/exchange", tags=["exchange"])


# ============================================================================
# Pydantic Models
# ============================================================================


class ExchangeRunRequest(BaseModel):
    """Request body for starting a scrape run."""

    max_resources: int | None = Field(
        None,
        ge=0,
        description="Override max resources (0 = all, None = use config)",
    )


class ExchangeStatusResponse(BaseModel):
    """Current service status."""

    status: str
    is_running: bool
    last_run: str | None
    last_error: str | None
    item_count: int
    progress_current: int
    progress_total: int


class ExchangeConfig(BaseModel):
    """Service configuration."""

    headless: bool = True
    max_resources: int = Field(0, ge=0)
    schedule: dict[str, Any] = Field(
        default_factory=lambda: {"enabled": False, "cron": "0 6 * * 1"}
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/status", response_model=ExchangeStatusResponse)
async def get_status() -> dict[str, Any]:
    """Get current scraper status and progress."""
    return get_exchange_service().get_status()


@router.post("/run")
async def run_scrape(request: ExchangeRunRequest | None = None) -> dict[str, Any]:
    """Start a scrape run."""
    max_resources = request.max_resources if request else None
    result = await get_exchange_service().run(max_resources_override=max_resources)
    if not result.get("started"):
        raise HTTPException(status_code=409, detail=result.get("reason", "already_running"))
    return result


@router.post("/stop")
async def stop_scrape() -> dict[str, Any]:
    """Stop the running scrape."""
    return await get_exchange_service().stop()


@router.get("/results")
async def get_results(search: str = "", category: str = "") -> dict[str, Any]:
    """Get scraped results with optional search/category filter."""
    results = get_exchange_service().get_results(search=search, category=category)
    return {"items": results, "count": len(results)}


@router.get("/changes")
async def get_changes() -> dict[str, Any]:
    """Get changes detected in the last scrape run."""
    return get_exchange_service().get_changes()


@router.get("/history")
async def get_history() -> list[dict[str, Any]]:
    """Get history of scrape runs (most recent first)."""
    return get_exchange_service().get_history()


@router.get("/logs")
async def get_logs(lines: int = 200) -> list[str]:
    """Get the last N lines from the activity log."""
    return get_exchange_service().get_logs(lines=lines)


@router.get("/config", response_model=ExchangeConfig)
async def get_config() -> dict[str, Any]:
    """Get current configuration."""
    return get_exchange_service().get_config()


@router.put("/config", response_model=ExchangeConfig)
async def save_config(config: ExchangeConfig) -> dict[str, Any]:
    """Save configuration."""
    return get_exchange_service().save_config(config.model_dump())
