"""
Notification sender.

Channels:
  "log"              – write to stdout + notifications table (always available)
  "twilio_sms"       – send real SMS via Twilio REST (needs TWILIO_* env vars)
  "twilio_whatsapp"  – send WhatsApp via Twilio sandbox

The function send_notification_for_match() is the main entry point called by
the notifications router, the demo loop, and Celery tasks.
"""
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine
from app.notifier.templates import render_message

logger = logging.getLogger("notifier")


def _log_to_db(user_id, match_id, channel, language, body, status, provider_id=None):
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO notifications
                (user_id, match_id, channel, language, body, status, provider_id, sent_at)
                VALUES (:uid, :mid, :ch, :lang, :body, :st, :pid, :ts)
            """),
            {
                "uid": user_id, "mid": match_id, "ch": channel, "lang": language,
                "body": body, "st": status, "pid": provider_id,
                "ts": datetime.now(timezone.utc),
            },
        )


def _send_twilio(to_number: str, body: str, whatsapp: bool = False) -> str | None:
    """Send via Twilio; return message SID or None on error."""
    try:
        from twilio.rest import Client as TwilioClient  # type: ignore
    except ImportError:
        logger.warning("twilio library not installed; falling back to log channel")
        return None

    client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    prefix = "whatsapp:" if whatsapp else ""
    msg = client.messages.create(
        body=body,
        from_=f"{prefix}{settings.TWILIO_FROM_NUMBER}",
        to=f"{prefix}{to_number}",
    )
    return msg.sid


def send_notification_for_match(match_id: str) -> int:
    """
    Look up the match, find the farmer's phone, build the message in their
    language, send it via the configured channel and log it.

    Returns the number of notifications successfully queued/sent.
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
        language = row["language"] or "en"
        body = render_message(
            language=language,
            template="match_confirmed",
            buyer_name=row["buyer_name"],
            pickup_date=str(row["pickup_date"]),
            price=int(row["price_per_tonne_inr"]),
        )

        channel = settings.NOTIFIER_CHANNEL
        provider_id = None
        status = "sent"

        if channel in ("twilio_sms", "twilio_whatsapp") and row["phone"]:
            sid = _send_twilio(
                row["phone"], body, whatsapp=(channel == "twilio_whatsapp")
            )
            if sid:
                provider_id = sid
            else:
                status = "failed"
                channel = "log"   # fallback
        else:
            # log channel – just print it
            logger.info("[NOTIF][%s][%s] %s", language, row.get("phone", "no-phone"), body)

        _log_to_db(
            user_id=row["user_id"],
            match_id=match_id,
            channel=channel,
            language=language,
            body=body,
            status=status,
            provider_id=provider_id,
        )
        count += 1

    return count
