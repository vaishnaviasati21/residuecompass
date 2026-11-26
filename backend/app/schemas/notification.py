"""Notification log shapes."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: int
    user_id: int | None
    match_id: str | None
    channel: str
    language: str
    body: str
    status: Literal["queued", "sent", "failed"]
    provider_id: str | None
    sent_at: datetime | None


class NotificationList(BaseModel):
    items: list[NotificationOut]
    total: int
