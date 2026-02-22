"""
Exchange Service - manages scraping, scheduling, state and config.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ignition_toolkit.core.paths import get_data_dir
from ignition_toolkit.exchange.comparison import compare_items
from ignition_toolkit.exchange.scraper import scrape_all

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: dict[str, Any] = {
    "headless": True,
    "max_resources": 0,
    "schedule": {
        "enabled": False,
        "cron": "0 6 * * 1",  # Every Monday at 6am
    },
}

MAX_HISTORY_ENTRIES = 100
MAX_LOG_LINES = 500


class ExchangeService:
    """
    Manages the Ignition Exchange scraper lifecycle.

    Handles:
    - Running/stopping the scraper
    - Persisting state, config, results to JSON files
    - APScheduler cron scheduling
    - Progress tracking and log capture
    """

    def __init__(self) -> None:
        self._data_dir: Path = get_data_dir() / "exchange"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._current_task: asyncio.Task[Any] | None = None
        self._stop_event: threading.Event = threading.Event()
        self._progress: dict[str, int] = {"current": 0, "total": 0}
        self._scheduler: AsyncIOScheduler = AsyncIOScheduler()
        self._scheduler_started: bool = False

        # Scheduler is started lazily on first async call (requires event loop)

    # =========================================================================
    # Public API
    # =========================================================================

    async def run(self, max_resources_override: int | None = None) -> dict[str, Any]:
        """Start a scrape run. Raises if already running."""
        # Ensure scheduler is started now that we have an event loop
        self._ensure_scheduler_started()
        self._update_scheduler()

        if self._current_task and not self._current_task.done():
            return {"started": False, "reason": "already_running"}

        self._stop_event.clear()
        self._progress = {"current": 0, "total": 0}

        config = self.get_config()
        max_resources = (
            max_resources_override
            if max_resources_override is not None
            else config.get("max_resources", 0)
        )
        headless = config.get("headless", True)

        self._append_log(f"Starting scrape (max_resources={max_resources}, headless={headless})")
        self._save_file(
            "state.json",
            {
                "status": "running",
                "is_running": True,
                "last_run": None,
                "last_error": None,
            },
        )

        start_time = datetime.now(timezone.utc)

        self._current_task = asyncio.create_task(
            self._run_scrape(max_resources, headless, start_time)
        )

        return {"started": True}

    async def stop(self) -> dict[str, Any]:
        """Request the running scrape to stop."""
        self._stop_event.set()
        if self._current_task and not self._current_task.done():
            self._append_log("Stop requested by user")
            return {"stopped": True}
        return {"stopped": False, "reason": "not_running"}

    def get_status(self) -> dict[str, Any]:
        """Return current service status."""
        state = self._load_file("state.json") or {}
        is_running = bool(self._current_task and not self._current_task.done())

        results = self._load_file("latest_results.json") or []

        return {
            "status": "running" if is_running else state.get("status", "idle"),
            "is_running": is_running,
            "last_run": state.get("last_run"),
            "last_error": state.get("last_error"),
            "item_count": len(results),
            "progress_current": self._progress["current"],
            "progress_total": self._progress["total"],
        }

    def get_results(self, search: str = "", category: str = "") -> list[dict[str, Any]]:
        """Return scraped results with optional filtering."""
        results: list[dict[str, Any]] = self._load_file("latest_results.json") or []

        if search:
            search_lower = search.lower()
            results = [
                r for r in results
                if search_lower in r.get("title", "").lower()
                or search_lower in r.get("contributor", "").lower()
                or search_lower in r.get("tagline", "").lower()
            ]

        if category:
            results = [r for r in results if r.get("category", "") == category]

        return results

    def get_changes(self) -> dict[str, list[dict[str, Any]]]:
        """Return the changes detected in the last run."""
        changes = self._load_file("latest_changes.json")
        if not changes:
            return {"new": [], "updated": [], "removed": []}
        return changes

    def get_history(self) -> list[dict[str, Any]]:
        """Return history of scrape runs (most recent first)."""
        history: list[dict[str, Any]] = self._load_file("history.json") or []
        return list(reversed(history))

    def get_logs(self, lines: int = 200) -> list[str]:
        """Return the last N log lines."""
        log_file = self._data_dir / "activity.log"
        if not log_file.exists():
            return []
        all_lines = log_file.read_text(encoding="utf-8").splitlines()
        return all_lines[-lines:]

    def get_config(self) -> dict[str, Any]:
        """Return current config, merged with defaults."""
        stored = self._load_file("config.json") or {}
        config = {**DEFAULT_CONFIG}
        config.update(stored)
        # Ensure schedule key exists
        if "schedule" not in config:
            config["schedule"] = dict(DEFAULT_CONFIG["schedule"])
        else:
            sched_defaults = dict(DEFAULT_CONFIG["schedule"])
            sched_defaults.update(config["schedule"])
            config["schedule"] = sched_defaults
        return config

    def save_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Persist config and update scheduler."""
        self._save_file("config.json", config)
        self._update_scheduler()
        self._append_log(f"Config saved: {config}")
        return config

    # =========================================================================
    # Private helpers
    # =========================================================================

    async def _run_scrape(
        self,
        max_resources: int,
        headless: bool,
        start_time: datetime,
    ) -> None:
        """Internal coroutine that runs the scrape and persists results."""
        error: str | None = None
        results: list[dict[str, Any]] = []

        def progress_cb(current: int, total: int) -> None:
            self._progress["current"] = current
            self._progress["total"] = total

        try:
            results = await scrape_all(
                max_resources=max_resources,
                headless=headless,
                stop_event=self._stop_event,
                progress_callback=progress_cb,
            )
        except Exception as exc:
            error = str(exc)
            logger.exception("Scrape failed: %s", exc)

        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        # Load previous results for comparison
        previous_results: list[dict[str, Any]] = self._load_file("latest_results.json") or []

        changes: dict[str, list[dict[str, Any]]] = {"new": [], "updated": [], "removed": []}
        if results:
            changes = compare_items(results, previous_results)
            self._save_file("latest_results.json", results)
            self._save_file("latest_changes.json", changes)

        # Update history
        history: list[dict[str, Any]] = self._load_file("history.json") or []
        history_entry: dict[str, Any] = {
            "timestamp": end_time.isoformat(),
            "success": error is None,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": round(duration, 1),
            "items_scraped": len(results),
            "changes": {
                "new": len(changes["new"]),
                "updated": len(changes["updated"]),
                "removed": len(changes["removed"]),
            },
            "error": error,
        }
        history.append(history_entry)
        if len(history) > MAX_HISTORY_ENTRIES:
            history = history[-MAX_HISTORY_ENTRIES:]
        self._save_file("history.json", history)

        # Update state
        self._save_file(
            "state.json",
            {
                "status": "error" if error else "completed",
                "is_running": False,
                "last_run": end_time.isoformat(),
                "last_error": error,
            },
        )

        if error:
            self._append_log(f"Scrape failed after {duration:.1f}s: {error}", level="ERROR")
        else:
            n = len(changes["new"])
            u = len(changes["updated"])
            r = len(changes["removed"])
            self._append_log(
                f"Scrape completed in {duration:.1f}s: "
                f"{len(results)} items, {n} new, {u} updated, {r} removed"
            )

    def _ensure_scheduler_started(self) -> None:
        """Start the APScheduler lazily (requires a running event loop)."""
        if not self._scheduler_started:
            try:
                self._scheduler.start()
                self._scheduler_started = True
            except RuntimeError:
                # No event loop yet — scheduler will start on next call
                pass

    def _update_scheduler(self) -> None:
        """Add or remove the cron job based on current config."""
        self._ensure_scheduler_started()
        if not self._scheduler_started:
            # Can't configure jobs without a running scheduler
            return

        job_id = "exchange_scrape"
        # Remove existing job if any
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

        config = self.get_config()
        schedule = config.get("schedule", {})

        if schedule.get("enabled") and schedule.get("cron"):
            try:
                trigger = CronTrigger.from_crontab(schedule["cron"])
                self._scheduler.add_job(
                    self._scheduled_run,
                    trigger=trigger,
                    id=job_id,
                    replace_existing=True,
                )
                self._append_log(f"Scheduler enabled: cron={schedule['cron']}")
            except Exception as exc:
                logger.error("Failed to set up scheduler: %s", exc)
                self._append_log(f"Scheduler setup failed: {exc}", level="ERROR")
        else:
            self._append_log("Scheduler disabled")

    async def _scheduled_run(self) -> None:
        """Called by APScheduler."""
        self._append_log("Scheduled scrape triggered")
        await self.run()

    def _load_file(self, name: str) -> Any:
        """Load a JSON file from the data directory. Returns None if not found."""
        path = self._data_dir / name
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load %s: %s", name, exc)
            return None

    def _save_file(self, name: str, data: Any) -> None:
        """Save data as JSON to the data directory."""
        path = self._data_dir / name
        try:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            logger.error("Failed to save %s: %s", name, exc)

    def _append_log(self, msg: str, level: str = "INFO") -> None:
        """Append a timestamped line to activity.log."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"[{ts}] [{level}] {msg}"
        log_file = self._data_dir / "activity.log"
        try:
            with log_file.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
            # Trim log if too long
            all_lines = log_file.read_text(encoding="utf-8").splitlines()
            if len(all_lines) > MAX_LOG_LINES:
                log_file.write_text(
                    "\n".join(all_lines[-MAX_LOG_LINES:]) + "\n", encoding="utf-8"
                )
        except OSError as exc:
            logger.error("Failed to write activity log: %s", exc)
