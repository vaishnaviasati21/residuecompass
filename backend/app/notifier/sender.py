"""
Notification sender.

Channels:
  "log"              – write to stdout + notifications table (always available)
  "twilio_sms"       – send real SMS via Twilio REST (needs TWILIO_* env vars)
  "twilio_whatsapp"  – send WhatsApp via Twilio sandbox

The function send_notification_for_match() is the main entry point called by
the notifications router, the demo loop, and Celery tasks.

Idempotency: before inserting a new notification row, we check whether one
already exists for the same (match_id, user_id, status='sent') pair.  If it
does, we skip the send entirely.  This prevents duplicate messages on retries.

Failure logging: Twilio errors are caught with logger.exception(), and the row
is still persisted with status='failed' so operations teams can audit and retry.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine
from app.notifier.templates import render_message

logger = logging.getLogger("notifier")


def _already_sent(conn, match_id: str, user_id: Optional[int]) -> bool:
    """Return True if a 'sent' notification already exists for this pair."""
    row = conn.execute(
        text("""
            SELECT 1 FROM notifications
             WHERE match_id = :mid
               AND user_id  IS NOT DISTINCT FROM :uid
               AND status   = 'sent'
             LIMIT 1
        """),
        {"mid": match_id, "uid": user_id},
    ).first()
    return row is not None


def _log_to_db(
    user_id: Optional[int],
    match_id: str,
    channel: str,
    language: str,
    body: str,
    status: str,
    provider_id: Optional[str] = None,
) -> None:
    """Persist the notification record (regardless of success/failure)."""
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO notifications
                    (user_id, match_id, channel, language, body, status, provider_id, sent_at)
                VALUES
                    (:uid, :mid, :ch, :lang, :body, :st, :pid, :ts)
            """),
            {
                "uid":  user_id,
                "mid":  match_id,
                "ch":   channel,
                "lang": language,
                "body": body,
                "st":   status,
                "pid":  provider_id,
                "ts":   datetime.now(timezone.utc),
            },
        )


def _send_twilio(to_number: str, body: str, whatsapp: bool = False) -> Optional[str]:
    """
    Send via Twilio; return message SID on success, None on error.
    Logs the full exception so provider failures are always traceable.
    """
    try:
        from twilio.rest import Client as TwilioClient  # type: ignore
    except ImportError:
        logger.warning("twilio library not installed; falling back to log channel")
        return None

    try:
        client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        prefix = "whatsapp:" if whatsapp else ""
        msg = client.messages.create(
            body=body,
            from_=f"{prefix}{settings.TWILIO_FROM_NUMBER}",
            to=f"{prefix}{to_number}",
        )
        return msg.sid
    except Exception:
        logger.exception(
            "Twilio send failed (to=%s, whatsapp=%s)", to_number, whatsapp
        )
        return None


def send_notification_for_match(match_id: str) -> int:
    """
    Look up the match, find the farmer's phone, build the message in their
    language, send it via the configured channel, and log it.

    - Idempotency: skips if a 'sent' record already exists for this pair.
    - Failure safety: Twilio errors are logged and persisted as 'failed'.
    - Demo persistence: always writes a row even on the log channel.

    Returns the number of notifications successfully sent (not skipped).
    """
    sql = text("""
        SELECT
            m.match_id, m.village_id, m.pickup_date, m.price_per_tonne_inr, m.tonnes,
            b.name AS buyer_name,
            u.id  AS user_id, u.phone, u.language
        FROM matches m
        JOIN buyers  b ON b.id = m.buyer_id
        JOIN villages v ON v.id = m.village_id
        -- find the farmer linked to this village
        LEFT JOIN users u ON u.village_id = m.village_id AND u.role = 'farmer'
        WHERE m.match_id = :mid
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql, {"mid": match_id}).mappings().all()

    if not rows:
        logger.warning("send_notification: match %s not found", match_id)
        return 0

    count = 0
    for row in rows:
        user_id  = row["user_id"]
        language = row["language"] or "en"

        # ── Idempotency guard ──────────────────────────────────────────────
        with engine.connect() as conn:
            if _already_sent(conn, match_id, user_id):
                logger.info(
                    "Notification already sent for match=%s user=%s – skipping",
                    match_id, user_id,
                )
                continue

        body = render_message(
            language=language,
            template="match_confirmed",
            buyer_name=row["buyer_name"],
            pickup_date=str(row["pickup_date"]),
            price=int(row["price_per_tonne_inr"]),
        )

        channel     = settings.NOTIFIER_CHANNEL
        provider_id: Optional[str] = None
        status      = "sent"

        if channel in ("twilio_sms", "twilio_whatsapp") and row["phone"]:
            sid = _send_twilio(
                row["phone"], body, whatsapp=(channel == "twilio_whatsapp")
            )
            if sid:
                provider_id = sid
            else:
                # Twilio failed: persist as 'failed', do NOT fall back to 'log'
                # channel silently – the failed status is the audit trail.
                status  = "failed"
                channel = "log"
        else:
            # Log channel – always print for observability
            logger.info("[NOTIF][%s][%s] %s", language, row.get("phone", "no-phone"), body)

        # Always persist (even log-channel rows and failures)
        _log_to_db(
            user_id=user_id,
            match_id=match_id,
            channel=channel,
            language=language,
            body=body,
            status=status,
            provider_id=provider_id,
        )

        if status == "sent":
            count += 1

    return count
