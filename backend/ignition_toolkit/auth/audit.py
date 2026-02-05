"""
Audit Logging

Records security-relevant events for compliance and debugging.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from pathlib import Path

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events"""
    # Authentication events
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_FAILED = "auth.failed"
    AUTH_KEY_CREATED = "auth.key_created"
    AUTH_KEY_REVOKED = "auth.key_revoked"

    # Playbook events
    PLAYBOOK_CREATED = "playbook.created"
    PLAYBOOK_UPDATED = "playbook.updated"
    PLAYBOOK_DELETED = "playbook.deleted"
    PLAYBOOK_EXECUTED = "playbook.executed"

    # Credential events
    CREDENTIAL_CREATED = "credential.created"
    CREDENTIAL_UPDATED = "credential.updated"
    CREDENTIAL_DELETED = "credential.deleted"
    CREDENTIAL_ACCESSED = "credential.accessed"

    # System events
    SYSTEM_CONFIG_CHANGED = "system.config_changed"
    SYSTEM_STARTED = "system.started"
    SYSTEM_STOPPED = "system.stopped"

    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    ROLE_ASSIGNED = "role.assigned"

    # Access events
    ACCESS_DENIED = "access.denied"
    ACCESS_GRANTED = "access.granted"


@dataclass
class AuditEvent:
    """Represents an audit log entry"""
    event_type: AuditEventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    user_id: str | None = None
    api_key_id: str | None = None
    ip_address: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    action: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "api_key_id": self.api_key_id,
            "ip_address": self.ip_address,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "details": self.details,
            "success": self.success,
            "error_message": self.error_message,
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


class AuditLogger:
    """
    Audit Logger

    Records security-relevant events to:
    - In-memory buffer (for API access)
    - Log file (for persistence)
    - Standard logger (for integration)

    Example:
        audit = AuditLogger()

        audit.log(
            event_type=AuditEventType.PLAYBOOK_EXECUTED,
            user_id="user123",
            resource_type="playbook",
            resource_id="my_playbook.yaml",
            details={"parameters": {...}}
        )

        # Get recent events
        events = audit.get_events(limit=100)
    """

    def __init__(
        self,
        max_buffer_size: int = 10000,
        log_file: Path | None = None,
    ):
        """
        Initialize audit logger

        Args:
            max_buffer_size: Maximum events to keep in memory
            log_file: Optional file path for persistent logging
        """
        self._buffer: list[AuditEvent] = []
        self._max_buffer_size = max_buffer_size
        self._log_file = log_file

        # Create audit file logger if path provided
        self._file_logger = None
        if log_file:
            self._setup_file_logger(log_file)

        logger.info(f"AuditLogger initialized (buffer_size={max_buffer_size})")

    def _setup_file_logger(self, log_file: Path) -> None:
        """Setup file logger for persistent audit logs"""
        log_file.parent.mkdir(parents=True, exist_ok=True)

        self._file_logger = logging.getLogger("audit_file")
        self._file_logger.setLevel(logging.INFO)

        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self._file_logger.addHandler(handler)
        self._file_logger.propagate = False

    def log(
        self,
        event_type: AuditEventType,
        user_id: str | None = None,
        api_key_id: str | None = None,
        ip_address: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        action: str | None = None,
        details: dict[str, Any] | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> AuditEvent:
        """
        Log an audit event

        Args:
            event_type: Type of event
            user_id: User ID (if known)
            api_key_id: API key ID (if used)
            ip_address: Client IP address
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            action: Action performed
            details: Additional details
            success: Whether action succeeded
            error_message: Error message if failed

        Returns:
            Created AuditEvent
        """
        event = AuditEvent(
            event_type=event_type,
            user_id=user_id,
            api_key_id=api_key_id,
            ip_address=ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details or {},
            success=success,
            error_message=error_message,
        )

        # Add to buffer
        self._buffer.append(event)
        if len(self._buffer) > self._max_buffer_size:
            self._buffer = self._buffer[-self._max_buffer_size:]

        # Log to file if configured
        if self._file_logger:
            self._file_logger.info(event.to_json())

        # Log to standard logger (info for success, warning for failure)
        log_msg = f"[AUDIT] {event_type.value}: user={user_id}, resource={resource_type}/{resource_id}"
        if success:
            logger.info(log_msg)
        else:
            logger.warning(f"{log_msg}, error={error_message}")

        return event

    def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        event_type: AuditEventType | None = None,
        user_id: str | None = None,
        resource_type: str | None = None,
        success: bool | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[AuditEvent]:
        """
        Get audit events with filtering

        Args:
            limit: Maximum events to return
            offset: Number of events to skip
            event_type: Filter by event type
            user_id: Filter by user
            resource_type: Filter by resource type
            success: Filter by success status
            start_time: Filter events after this time
            end_time: Filter events before this time

        Returns:
            List of matching AuditEvent objects
        """
        events = self._buffer.copy()

        # Apply filters
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if user_id:
            events = [e for e in events if e.user_id == user_id]

        if resource_type:
            events = [e for e in events if e.resource_type == resource_type]

        if success is not None:
            events = [e for e in events if e.success == success]

        if start_time:
            events = [e for e in events if e.timestamp >= start_time]

        if end_time:
            events = [e for e in events if e.timestamp <= end_time]

        # Sort by timestamp descending (newest first)
        events.sort(key=lambda e: e.timestamp, reverse=True)

        # Apply pagination
        return events[offset:offset + limit]

    def get_stats(self) -> dict:
        """Get audit statistics"""
        events = self._buffer

        # Count by event type
        type_counts: dict[str, int] = {}
        for event in events:
            type_name = event.event_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        # Count successes and failures
        success_count = sum(1 for e in events if e.success)
        failure_count = len(events) - success_count

        return {
            "total_events": len(events),
            "success_count": success_count,
            "failure_count": failure_count,
            "events_by_type": type_counts,
            "buffer_capacity": self._max_buffer_size,
        }

    def clear(self) -> int:
        """
        Clear the audit buffer

        Returns:
            Number of events cleared
        """
        count = len(self._buffer)
        self._buffer = []
        logger.info(f"Cleared {count} audit events from buffer")
        return count


# Global instance
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
