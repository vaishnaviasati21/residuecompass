"""
Notification sender.

Channels:
  "log"              – write to stdout + notifications table (always available)
  "twilio_sms"       – send real SMS via Twilio REST (needs TWILIO_* env vars)
  "twilio_whatsapp"  – send WhatsApp via Twilio sandbox

Concurrency-safe idempotency:
  Uses a claim-first pattern backed by a partial unique index:
    uq_notifications_match_user_active ON notifications (match_id, COALESCE(user_id, -1))
    WHERE status IN ('queued', 'sent')
  Before sending, we INSERT a 'queued' claim row with ON CONFLICT DO NOTHING
  RETURNING id.  Only the winning worker receives an id and proceeds to deliver,
  then updates that row to 'sent' (or 'failed').  Failed rows do not block
  future retries.

Missing-recipient handling:
  - If user_id is None (no farmer registered for the village), or if a Twilio
    channel is active and phone is missing, we never log status='sent'.
    Instead we record status='failed' with an explicit detail and return 0.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine
from app.notifier.templates import render_message

logger = logging.getLogger("notifier")


def _claim_notification(
    conn,
    user_id: Optional[int],
    match_id: str,
    channel: str,
    language: str,
    body: str,
) -> Optional[int]:
    """
    Atomically claim a notification slot for (match_id, user_id).
    Returns the new notification id if claimed, or None if an active
    ('queued' or 'sent') notification already exists.
    """
    row = conn.execute(
        text("""
            INSERT INTO notifications
                (user_id, match_id, channel, language, body, status, sent_at)
            VALUES
                (:uid, :mid, :ch, :lang, :body, 'queued', :ts)
            ON CONFLICT (match_id, COALESCE(user_id, -1))
                WHERE status IN ('queued', 'sent')
            DO NOTHING
            RETURNING id
        """),
        {
            "uid":  user_id,
            "mid":  match_id,
            "ch":   channel,
            "lang": language,
            "body": body,
            "ts":   datetime.now(timezone.utc),
        },
    ).first()
    return int(row[0]) if row else None


def _finalize_notification(
    conn,
    notif_id: int,
    status: str,
    channel: Optional[str] = None,
    provider_id: Optional[str] = None,
) -> None:
    """Update a claimed notification row to its final status ('sent' or 'failed')."""
    conn.execute(
        text("""
            UPDATE notifications
               SET status      = :st,
                   channel     = COALESCE(:ch, channel),
                   provider_id = :pid,
                   sent_at     = :ts
             WHERE id = :id
        """),
        {
            "id":  notif_id,
            "st":  status,
            "ch":  channel,
            "pid": provider_id,
            "ts":  datetime.now(timezone.utc),
        },
    )


def _log_failed_no_claim(
    user_id: Optional[int],
    match_id: str,
    channel: str,
    language: str,
    body: str,
) -> None:
    """Persist a 'failed' record directly (e.g. missing recipient)."""
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO notifications
                    (user_id, match_id, channel, language, body, status, sent_at)
                VALUES
                    (:uid, :mid, :ch, :lang, :body, 'failed', :ts)
            """),
            {
                "uid":  user_id,
                "mid":  match_id,
                "ch":   channel,
                "lang": language,
                "body": body,
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
        logger.warning("twilio library not installed; cannot deliver via Twilio")
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


def send_notification_for_match(
    match_id: str,
    channel_override: Optional[str] = None,
) -> int:
    """
    Look up the match, find the farmer's phone, build the message in their
    language, claim an idempotent slot, send it, and finalize status.

    Returns the number of notifications successfully sent (not skipped/failed).
    """
    sql = text("""
        SELECT
            m.match_id, m.village_id, m.status AS match_status,
            m.pickup_date, m.price_per_tonne_inr, m.tonnes,
            b.name AS buyer_name,
            u.id   AS user_id, u.phone, u.language
        FROM matches m
        JOIN buyers   b ON b.id = m.buyer_id
        JOIN villages v ON v.id = m.village_id
        LEFT JOIN users u ON u.village_id = m.village_id AND u.role = 'farmer'
        WHERE m.match_id = :mid
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql, {"mid": match_id}).mappings().all()

    if not rows:
        logger.warning("send_notification: match %s not found", match_id)
        return 0

    channel = channel_override or settings.NOTIFIER_CHANNEL
    count = 0

    for row in rows:
        user_id  = row["user_id"]
        language = row["language"] or "en"
        template = (
            "match_proposed"
            if row.get("match_status") == "PROPOSED"
            else "match_confirmed"
        )
        body = render_message(
            language=language,
            template=template,
            buyer_name=row["buyer_name"],
            pickup_date=str(row["pickup_date"]),
            price=int(row["price_per_tonne_inr"]),
            tonnes=row["tonnes"],
        )

        # ── Missing-recipient guard ───────────────────────────────────────
        if user_id is None:
            logger.warning(
                "send_notification: no farmer user registered for village %s (match %s)",
                row["village_id"], match_id,
            )
            _log_failed_no_claim(None, match_id, channel, language, body)
            continue

        if channel in ("twilio_sms", "twilio_whatsapp") and not row["phone"]:
            logger.warning(
                "send_notification: farmer user=%s has no phone number (match %s)",
                user_id, match_id,
            )
            _log_failed_no_claim(user_id, match_id, channel, language, body)
            continue

        # ── Concurrency-safe claim ────────────────────────────────────────
        with engine.begin() as conn:
            notif_id = _claim_notification(
                conn, user_id, match_id, channel, language, body
            )

        if notif_id is None:
            logger.info(
                "Notification already queued/sent for match=%s user=%s – skipping",
                match_id, user_id,
            )
            continue

        # ── Delivery ──────────────────────────────────────────────────────
        provider_id: Optional[str] = None
        status = "sent"

        if channel in ("twilio_sms", "twilio_whatsapp"):
            sid = _send_twilio(
                row["phone"], body, whatsapp=(channel == "twilio_whatsapp")
            )
            if sid:
                provider_id = sid
            else:
                status = "failed"
        else:
            logger.info("[NOTIF][%s][%s] %s", language, row.get("phone", "no-phone"), body)

        with engine.begin() as conn:
            _finalize_notification(conn, notif_id, status, channel, provider_id)

        if status == "sent":
            count += 1

    return count
