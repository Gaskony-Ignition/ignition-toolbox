"""
API endpoints for schedule management
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ignition_toolkit.scheduler import get_scheduler
from ignition_toolkit.storage import get_database
from ignition_toolkit.storage.models import ScheduledPlaybookModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


class ScheduleConfig(BaseModel):
    """Schedule configuration"""

    expression: str | None = None  # For cron type
    minutes: int | None = None  # For interval type
    time: str | None = None  # For daily/weekly/monthly (HH:MM format)
    day_of_week: str | None = None  # For weekly (mon, tue, etc.)
    day: int | None = None  # For monthly (1-31)


class CreateScheduleRequest(BaseModel):
    """Request to create a new schedule"""

    name: str
    playbook_path: str
    schedule_type: str  # "cron", "interval", "daily", "weekly", "monthly"
    schedule_config: ScheduleConfig
    parameters: dict | None = None
    gateway_url: str | None = None
    credential_name: str | None = None
    enabled: bool = True


class UpdateScheduleRequest(BaseModel):
    """Request to update an existing schedule"""

    name: str | None = None
    schedule_type: str | None = None
    schedule_config: ScheduleConfig | None = None
    parameters: dict | None = None
    gateway_url: str | None = None
    credential_name: str | None = None
    enabled: bool | None = None


@router.get("")
async def list_schedules():
    """List all scheduled playbooks"""
    try:
        db = get_database()
        with db.session_scope() as session:
            result = session.execute(select(ScheduledPlaybookModel))
            schedules = result.scalars().all()
            return {"schedules": [schedule.to_dict() for schedule in schedules]}

    except Exception as e:
        logger.error(f"Failed to list schedules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{schedule_id}")
async def get_schedule(schedule_id: int):
    """Get a specific schedule by ID"""
    try:
        db = get_database()
        with db.session_scope() as session:
            result = session.execute(
                select(ScheduledPlaybookModel).where(ScheduledPlaybookModel.id == schedule_id)
            )
            schedule = result.scalar_one_or_none()

            if not schedule:
                raise HTTPException(status_code=404, detail="Schedule not found")

            return schedule.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_schedule(request: CreateScheduleRequest):
    """Create a new scheduled playbook"""
    try:
        db = get_database()

        # Create schedule in database
        schedule = None
        with db.session_scope() as session:
            schedule = ScheduledPlaybookModel(
                name=request.name,
                playbook_path=request.playbook_path,
                schedule_type=request.schedule_type,
                schedule_config=request.schedule_config.model_dump(exclude_none=True),
                parameters=request.parameters,
                gateway_url=request.gateway_url,
                credential_name=request.credential_name,
                enabled="true" if request.enabled else "false",
            )

            session.add(schedule)
            session.flush()  # Flush to get the ID
            session.refresh(schedule)
            schedule_dict = schedule.to_dict()

        # Add to scheduler if enabled
        if request.enabled and schedule:
            scheduler = get_scheduler()
            await scheduler.add_schedule(schedule)

        logger.info(f"Created schedule: {request.name} (ID: {schedule.id if schedule else 'N/A'})")

        return {"message": "Schedule created successfully", "schedule": schedule_dict}

    except Exception as e:
        logger.error(f"Failed to create schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{schedule_id}")
async def update_schedule(schedule_id: int, request: UpdateScheduleRequest):
    """Update an existing schedule"""
    try:
        db = get_database()

        schedule_dict = None
        with db.session_scope() as session:
            result = session.execute(
                select(ScheduledPlaybookModel).where(ScheduledPlaybookModel.id == schedule_id)
            )
            schedule = result.scalar_one_or_none()

            if not schedule:
                raise HTTPException(status_code=404, detail="Schedule not found")

            # Update fields
            if request.name is not None:
                schedule.name = request.name

            if request.schedule_type is not None:
                schedule.schedule_type = request.schedule_type

            if request.schedule_config is not None:
                schedule.schedule_config = request.schedule_config.model_dump(exclude_none=True)

            if request.parameters is not None:
                schedule.parameters = request.parameters

            if request.gateway_url is not None:
                schedule.gateway_url = request.gateway_url

            if request.credential_name is not None:
                schedule.credential_name = request.credential_name

            if request.enabled is not None:
                schedule.enabled = "true" if request.enabled else "false"

            session.flush()
            session.refresh(schedule)
            schedule_dict = schedule.to_dict()

        # Update scheduler
        scheduler = get_scheduler()
        # Re-fetch to get the updated schedule
        with db.session_scope() as session:
            result = session.execute(
                select(ScheduledPlaybookModel).where(ScheduledPlaybookModel.id == schedule_id)
            )
            updated_schedule = result.scalar_one_or_none()

            if updated_schedule and updated_schedule.enabled == "true":
                await scheduler.add_schedule(updated_schedule)
            else:
                await scheduler.remove_schedule(schedule_id)

        logger.info(f"Updated schedule ID: {schedule_id}")

        return {"message": "Schedule updated successfully", "schedule": schedule_dict}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int):
    """Delete a schedule"""
    try:
        db = get_database()

        with db.session_scope() as session:
            result = session.execute(
                select(ScheduledPlaybookModel).where(ScheduledPlaybookModel.id == schedule_id)
            )
            schedule = result.scalar_one_or_none()

            if not schedule:
                raise HTTPException(status_code=404, detail="Schedule not found")

            session.delete(schedule)

        # Remove from scheduler
        scheduler = get_scheduler()
        await scheduler.remove_schedule(schedule_id)

        logger.info(f"Deleted schedule ID: {schedule_id}")

        return {"message": "Schedule deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: int):
    """Toggle a schedule on/off"""
    try:
        db = get_database()

        schedule_dict = None
        with db.session_scope() as session:
            result = session.execute(
                select(ScheduledPlaybookModel).where(ScheduledPlaybookModel.id == schedule_id)
            )
            schedule = result.scalar_one_or_none()

            if not schedule:
                raise HTTPException(status_code=404, detail="Schedule not found")

            # Toggle enabled status
            schedule.enabled = "false" if schedule.enabled == "true" else "true"

            session.flush()
            session.refresh(schedule)
            schedule_dict = schedule.to_dict()

        # Update scheduler
        scheduler = get_scheduler()
        # Re-fetch to get the updated schedule
        with db.session_scope() as session:
            result = session.execute(
                select(ScheduledPlaybookModel).where(ScheduledPlaybookModel.id == schedule_id)
            )
            updated_schedule = result.scalar_one_or_none()

            if updated_schedule and updated_schedule.enabled == "true":
                await scheduler.add_schedule(updated_schedule)
            else:
                await scheduler.remove_schedule(schedule_id)

        logger.info(f"Toggled schedule ID: {schedule_id}")

        return {"message": "Schedule toggled successfully", "schedule": schedule_dict}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/next-runs")
async def get_next_runs():
    """Get list of next scheduled runs"""
    try:
        scheduler = get_scheduler()
        next_runs = await scheduler.get_next_runs()

        return {"next_runs": next_runs}

    except Exception as e:
        logger.error(f"Failed to get next runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
