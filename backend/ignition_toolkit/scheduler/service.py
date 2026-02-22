"""
Playbook Scheduler Service

Handles automated playbook execution using APScheduler
"""

import logging
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from ignition_toolkit.storage import get_database
from ignition_toolkit.storage.models import ScheduledPlaybookModel

logger = logging.getLogger(__name__)


class PlaybookScheduler:
    """
    Manages scheduled playbook executions using APScheduler

    Supports various schedule types:
    - Cron: Traditional cron expressions (e.g., "0 2 * * *" for daily at 2 AM)
    - Interval: Regular intervals (e.g., every 30 minutes)
    - Daily: Specific time each day
    - Weekly: Specific day and time each week
    - Monthly: Specific day of month and time
    """

    def __init__(self):
        """Initialize the scheduler"""
        self.scheduler = AsyncIOScheduler()
        self.db = get_database()
        self._started = False

    async def start(self):
        """Start the scheduler and load all enabled schedules"""
        if self._started:
            logger.warning("Scheduler already started")
            return

        logger.info("Starting playbook scheduler...")

        # Load all enabled schedules from database
        await self._load_schedules()

        # Start the scheduler
        self.scheduler.start()
        self._started = True

        logger.info("Playbook scheduler started successfully")

    async def stop(self):
        """Stop the scheduler"""
        if not self._started:
            return

        logger.info("Stopping playbook scheduler...")
        self.scheduler.shutdown(wait=False)
        self._started = False
        logger.info("Playbook scheduler stopped")

    async def _load_schedules(self):
        """Load all enabled schedules from database"""
        with self.db.session_scope() as session:
            result = session.execute(
                select(ScheduledPlaybookModel).where(
                    ScheduledPlaybookModel.enabled == "true"
                )
            )
            schedules = result.scalars().all()

            for schedule in schedules:
                try:
                    await self.add_schedule(schedule)
                    logger.info(f"Loaded schedule: {schedule.name} (ID: {schedule.id})")
                except Exception as e:
                    logger.error(f"Failed to load schedule {schedule.name}: {e}")

    async def add_schedule(self, schedule: ScheduledPlaybookModel):
        """
        Add a scheduled playbook to the scheduler

        Args:
            schedule: ScheduledPlaybookModel instance
        """
        job_id = f"schedule_{schedule.id}"

        # Remove existing job if it exists
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

        # Create trigger based on schedule type
        trigger = self._create_trigger(schedule)

        if not trigger:
            logger.error(f"Failed to create trigger for schedule {schedule.name}")
            return

        # Add job to scheduler
        self.scheduler.add_job(
            self._execute_scheduled_playbook,
            trigger=trigger,
            id=job_id,
            args=[schedule.id],
            name=schedule.name,
            replace_existing=True,
        )

        # Update next_run_at in database
        next_run = self.scheduler.get_job(job_id).next_run_time
        if next_run:
            await self._update_next_run(schedule.id, next_run)

        logger.info(f"Added schedule: {schedule.name} - Next run: {next_run}")

    async def remove_schedule(self, schedule_id: int):
        """
        Remove a scheduled playbook from the scheduler

        Args:
            schedule_id: ID of the schedule to remove
        """
        job_id = f"schedule_{schedule_id}"

        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed schedule ID: {schedule_id}")

    def _create_trigger(self, schedule: ScheduledPlaybookModel):
        """
        Create an APScheduler trigger based on schedule configuration

        Args:
            schedule: ScheduledPlaybookModel instance

        Returns:
            Trigger object or None if invalid
        """
        schedule_type = schedule.schedule_type
        config = schedule.schedule_config

        try:
            if schedule_type == "cron":
                # Cron expression: "0 2 * * *" (minute hour day month day_of_week)
                cron_expr = config.get("expression", "0 0 * * *")
                parts = cron_expr.split()

                if len(parts) != 5:
                    logger.error(f"Invalid cron expression: {cron_expr}")
                    return None

                return CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                    timezone="UTC",
                )

            elif schedule_type == "interval":
                # Interval in minutes
                minutes = config.get("minutes", 60)
                return IntervalTrigger(minutes=minutes, timezone="UTC")

            elif schedule_type == "daily":
                # Daily at specific time (HH:MM format)
                time_str = config.get("time", "00:00")
                hour, minute = map(int, time_str.split(":"))
                return CronTrigger(hour=hour, minute=minute, timezone="UTC")

            elif schedule_type == "weekly":
                # Weekly on specific day and time
                day_of_week = config.get("day_of_week", "mon")  # mon, tue, wed, etc.
                time_str = config.get("time", "00:00")
                hour, minute = map(int, time_str.split(":"))
                return CronTrigger(
                    day_of_week=day_of_week,
                    hour=hour,
                    minute=minute,
                    timezone="UTC",
                )

            elif schedule_type == "monthly":
                # Monthly on specific day and time
                day = config.get("day", 1)  # Day of month (1-31)
                time_str = config.get("time", "00:00")
                hour, minute = map(int, time_str.split(":"))
                return CronTrigger(day=day, hour=hour, minute=minute, timezone="UTC")

            else:
                logger.error(f"Unknown schedule type: {schedule_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to create trigger: {e}")
            return None

    async def _execute_scheduled_playbook(self, schedule_id: int):
        """
        Execute a scheduled playbook

        Args:
            schedule_id: ID of the schedule to execute
        """
        try:
            # Get schedule from database
            with self.db.session_scope() as session:
                result = session.execute(
                    select(ScheduledPlaybookModel).where(
                        ScheduledPlaybookModel.id == schedule_id
                    )
                )
                schedule = result.scalar_one_or_none()

                if not schedule:
                    logger.error(f"Schedule {schedule_id} not found")
                    return

                if schedule.enabled != "true":
                    logger.info(f"Schedule {schedule.name} is disabled, skipping")
                    return

                logger.info(f"Executing scheduled playbook: {schedule.name}")

                # Import here to avoid circular dependency
                from ignition_toolkit.api.routers.executions import execute_playbook_background

                # Execute the playbook
                await execute_playbook_background(
                    playbook_path=schedule.playbook_path,
                    parameters=schedule.parameters or {},
                    gateway_url=schedule.gateway_url,
                    credential_name=schedule.credential_name,
                    debug_mode=False,
                )

                # Update last_run_at
                schedule.last_run_at = datetime.now(UTC)
                session.commit()

                logger.info(f"Successfully triggered execution of {schedule.name}")

        except Exception as e:
            logger.error(f"Failed to execute scheduled playbook {schedule_id}: {e}", exc_info=True)

    async def _update_next_run(self, schedule_id: int, next_run: datetime):
        """
        Update the next_run_at field in database

        Args:
            schedule_id: ID of the schedule
            next_run: Next scheduled run time
        """
        try:
            with self.db.session_scope() as session:
                result = session.execute(
                    select(ScheduledPlaybookModel).where(
                        ScheduledPlaybookModel.id == schedule_id
                    )
                )
                schedule = result.scalar_one_or_none()

                if schedule:
                    schedule.next_run_at = next_run
                    session.commit()

        except Exception as e:
            logger.error(f"Failed to update next_run_at for schedule {schedule_id}: {e}")

    async def get_next_runs(self) -> list[dict]:
        """
        Get list of next scheduled runs

        Returns:
            List of dictionaries with schedule info and next run time
        """
        jobs = self.scheduler.get_jobs()

        result = []
        for job in jobs:
            if job.id.startswith("schedule_"):
                schedule_id = int(job.id.replace("schedule_", ""))
                result.append({
                    "schedule_id": schedule_id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                })

        return result


# Global scheduler instance
_scheduler: PlaybookScheduler | None = None


def get_scheduler() -> PlaybookScheduler:
    """Get the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = PlaybookScheduler()
    return _scheduler
