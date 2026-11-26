"""
Audit log helper.

Writes a row to the audit_log table for sensitive actions (login, register,
match confirm/cancel, notification send).  Failures are logged but never
propagate – audit logging must never break the main request.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text

logger = logging.getLogger("audit")


def log_action(
    *,
    user_id: Optional[int],
    action: str,
    entity: str,
    entity_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """
    Insert a row into audit_log.

    Args:
        user_id:   ID of the authenticated user performing the action.
        action:    Short snake_case verb, e.g. 'login', 'match_confirmed'.
        entity:    Table/resource name, e.g. 'match', 'user'.
        entity_id: Primary key of the affected row (may be None for list ops).
        details:   Arbitrary JSON-serialisable dict for extra context.
    """
    try:
        from app.core.db import engine  # local import to avoid circular deps
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO audit_log
                        (user_id, action, entity, entity_id, details, created_at)
                    VALUES
                        (:uid, :action, :entity, :eid, CAST(:details AS jsonb), :ts)
                """),
                {
                    "uid":    user_id,
                    "action": action,
                    "entity": entity,
                    "eid":    entity_id,
                    "details": json.dumps(details or {}),
                    "ts":     datetime.now(timezone.utc),
                },
            )
    except Exception:
        # Never let audit failures break the main request.
        logger.exception(
            "audit_log write failed: action=%s entity=%s entity_id=%s",
            action, entity, entity_id,
        )
