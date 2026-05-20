"""Centralized telemetry for SecureMLOps security events."""

from telemetry.events import emit_event, EventSeverity, EventSource, EventType
from telemetry.event_store import init_event_store
from telemetry.queries import query_events, get_event_by_id, export_events
from telemetry.aggregator import (
    get_dashboard_summary,
    get_recent_activity,
    get_system_status,
    get_security_event_summary,
)

__all__ = [
    "emit_event",
    "EventSeverity",
    "EventSource",
    "EventType",
    "init_event_store",
    "query_events",
    "get_event_by_id",
    "export_events",
    "get_dashboard_summary",
    "get_recent_activity",
    "get_system_status",
    "get_security_event_summary",
]
