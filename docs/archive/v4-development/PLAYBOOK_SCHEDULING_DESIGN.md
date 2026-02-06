# Playbook Scheduling Design

## Overview
Add ability to schedule playbook executions to run automatically at specified times or intervals.

## Requirements
1. Schedule playbooks to run at specific times (one-time or recurring)
2. Support cron-style scheduling (e.g., "every day at 2 AM", "every Monday")
3. Store scheduled job configurations in SQLite database
4. View and manage scheduled playbooks from UI
5. Enable/disable schedules without deleting them
6. View execution history for scheduled runs
7. Send notifications on schedule execution success/failure (future enhancement)

## Architecture

### Database Schema
New table: `scheduled_playbooks`
```sql
CREATE TABLE scheduled_playbooks (
    id TEXT PRIMARY KEY,
    playbook_path TEXT NOT NULL,
    schedule_type TEXT NOT NULL,  -- 'cron', 'interval', 'one_time'
    schedule_expression TEXT NOT NULL,  -- cron expression or interval seconds
    parameters TEXT,  -- JSON-encoded playbook parameters
    enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_run_at TIMESTAMP,
    last_run_status TEXT,  -- 'success', 'failed', null
    next_run_at TIMESTAMP,
    name TEXT,
    description TEXT
);
```

### Components

#### 1. Scheduler Service (`ignition_toolkit/scheduler/`)
- **`scheduler.py`** - Main scheduler using APScheduler library
  - Initialize APScheduler on application startup
  - Load schedules from database
  - Add/remove/update jobs
  - Execute playbooks via PlaybookEngine

- **`models.py`** - Schedule data models
  - ScheduledPlaybook (id, playbook_path, schedule, parameters, enabled, etc.)
  - ScheduleType enum (CRON, INTERVAL, ONE_TIME)

- **`crud.py`** - Database operations
  - create_schedule()
  - get_schedule()
  - list_schedules()
  - update_schedule()
  - delete_schedule()
  - toggle_schedule()

#### 2. API Endpoints (`ignition_toolkit/api/routers/schedules.py`)
```python
POST   /api/schedules              # Create new schedule
GET    /api/schedules              # List all schedules
GET    /api/schedules/{id}         # Get schedule details
PUT    /api/schedules/{id}         # Update schedule
DELETE /api/schedules/{id}         # Delete schedule
POST   /api/schedules/{id}/toggle  # Enable/disable schedule
GET    /api/schedules/{id}/history # Get execution history
```

#### 3. Frontend (`frontend/src/pages/Schedules.tsx`)
- Schedule list view with filters (enabled/disabled, playbook)
- Create/edit schedule form with:
  - Playbook selection dropdown
  - Schedule type selector (Cron, Interval, One-time)
  - Cron expression builder or interval input
  - Parameter editor (pre-filled with playbook defaults)
  - Enable/disable toggle
- Execution history view per schedule
- Next run time display

### Technology Stack
- **APScheduler** - Python job scheduling library
  - Supports cron, interval, and date-based triggers
  - Thread-safe, persistent job store
  - Integrates with SQLite

### Implementation Plan

#### Phase 1: Backend Core (2-3 hours)
1. Add APScheduler dependency to `pyproject.toml`
2. Create database schema and models
3. Implement scheduler service
4. Add API endpoints
5. Wire scheduler into FastAPI app lifecycle

#### Phase 2: Frontend UI (2-3 hours)
1. Create Schedules page with list view
2. Build schedule creation form
3. Add cron expression helper/validator
4. Implement enable/disable toggle
5. Add execution history view

#### Phase 3: Testing & Polish (1-2 hours)
1. Test schedule creation and execution
2. Verify timezone handling
3. Test schedule persistence across server restarts
4. Add error handling and validation
5. Update documentation

### Example Usage

#### Create Cron Schedule (API)
```json
POST /api/schedules
{
  "name": "Daily Gateway Backup",
  "playbook_path": "gateway/backup_gateway.yaml",
  "schedule_type": "cron",
  "schedule_expression": "0 2 * * *",  // Every day at 2 AM
  "parameters": {
    "gateway_url": "http://localhost:8088",
    "username": "admin",
    "password": "{{ credential.gateway_admin }}"
  },
  "enabled": true
}
```

#### Create Interval Schedule
```json
{
  "name": "Hourly Health Check",
  "playbook_path": "gateway/health_check.yaml",
  "schedule_type": "interval",
  "schedule_expression": "3600",  // Every 3600 seconds (1 hour)
  "parameters": {...},
  "enabled": true
}
```

### Cron Expression Examples
- `0 2 * * *` - Every day at 2:00 AM
- `0 */4 * * *` - Every 4 hours
- `0 0 * * 0` - Every Sunday at midnight
- `*/30 * * * *` - Every 30 minutes
- `0 9 * * 1-5` - Weekdays at 9:00 AM

### Security Considerations
1. Credentials in parameters should use `{{ credential.xxx }}` references
2. Validate schedule expressions to prevent malicious input
3. Limit maximum number of concurrent scheduled executions
4. Add audit logging for schedule changes

### Future Enhancements
1. Email/Slack notifications on execution completion
2. Retry logic for failed scheduled executions
3. Schedule dependencies (run B after A completes)
4. Execution windows (only run between 2 AM - 6 AM)
5. Conditional execution based on previous run status
6. Schedule templates/presets
7. Bulk schedule operations (enable/disable multiple)
8. Export/import schedules as JSON

### Dependencies
```toml
[project.dependencies]
apscheduler = "^3.10.4"
```

### Migration Notes
- Existing playbooks work without changes
- Schedules are optional - manual execution still available
- Server restart loads all enabled schedules automatically
- SQLite database stores all schedule configurations

## Open Questions
1. Should we support timezone configuration per schedule or use server timezone?
   - **Decision**: Start with server timezone, add per-schedule timezone in v2
2. How to handle long-running playbooks that overlap with next scheduled run?
   - **Decision**: Skip next run if previous execution still running (log warning)
3. Should scheduled executions appear in main execution history?
   - **Decision**: Yes, with a "scheduled: true" flag and schedule_id reference

## Next Steps
1. Review and approve this design
2. Add APScheduler dependency
3. Create database migration for scheduled_playbooks table
4. Implement Phase 1 (Backend Core)
5. Implement Phase 2 (Frontend UI)
6. Test and document
