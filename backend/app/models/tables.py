"""
SQLAlchemy 2.x + GeoAlchemy2 table definitions mirroring migrations/001_init.sql
and 003_extra_columns.sql.

Provides ORM types for Alembic/services while keeping raw-SQL compatibility.
"""
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

try:
    from geoalchemy2 import Geometry
except ImportError:
    # Fallback type when geoalchemy2 is not installed in a minimal local venv
    def Geometry(*_args, **_kwargs):  # type: ignore
        return Text


class District(Base):
    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    geom: Mapped[Any] = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)


class Village(Base):
    __tablename__ = "villages"
    __table_args__ = (
        Index("idx_villages_geom", "geom", postgresql_using="gist"),
        Index("idx_villages_centroid", "centroid", postgresql_using="gist"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id"))
    geom: Mapped[Any] = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)
    centroid: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    paddy_area_ha: Mapped[float | None] = mapped_column(Numeric)


class NdviObservation(Base):
    __tablename__ = "ndvi_observations"
    __table_args__ = (UniqueConstraint("village_id", "obs_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    village_id: Mapped[str] = mapped_column(ForeignKey("villages.id"), nullable=False)
    obs_date: Mapped[date] = mapped_column(Date, nullable=False)
    ndvi_mean: Mapped[float | None] = mapped_column(Numeric)
    ndvi_median: Mapped[float | None] = mapped_column(Numeric)
    cloud_pct: Mapped[float | None] = mapped_column(Numeric)
    quality_flag: Mapped[str | None] = mapped_column(Text)


class WeatherObservation(Base):
    __tablename__ = "weather_observations"
    __table_args__ = (UniqueConstraint("village_id", "obs_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    village_id: Mapped[str] = mapped_column(ForeignKey("villages.id"), nullable=False)
    obs_date: Mapped[date] = mapped_column(Date, nullable=False)
    rain_mm: Mapped[float | None] = mapped_column(Numeric)
    temp_max_c: Mapped[float | None] = mapped_column(Numeric)
    temp_min_c: Mapped[float | None] = mapped_column(Numeric)
    source: Mapped[str | None] = mapped_column(Text)


class FireDetection(Base):
    __tablename__ = "fire_detections"
    __table_args__ = (
        Index("idx_fire_geom", "geom", postgresql_using="gist"),
        Index("idx_fire_time", "acq_datetime"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    geom: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    acq_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    brightness: Mapped[float | None] = mapped_column(Numeric)
    frp: Mapped[float | None] = mapped_column(Numeric)
    sat_confidence: Mapped[str | None] = mapped_column(Text)
    village_id: Mapped[str | None] = mapped_column(ForeignKey("villages.id"))


class BurnScar(Base):
    __tablename__ = "burn_scars"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    village_id: Mapped[str] = mapped_column(ForeignKey("villages.id"), nullable=False)
    detected_on: Mapped[date] = mapped_column(Date, nullable=False)
    area_ha: Mapped[float | None] = mapped_column(Numeric)
    geom: Mapped[Any] = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)


class Forecast(Base):
    __tablename__ = "forecasts"
    __table_args__ = (
        CheckConstraint("confidence_tag IN ('LOW','MEDIUM','HIGH')"),
        CheckConstraint("harvest_status IN ('GROWING','READY_SOON','HARVESTED')"),
        Index("idx_forecasts_village", "village_id", "generated_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    village_id: Mapped[str] = mapped_column(ForeignKey("villages.id"), nullable=False)
    season: Mapped[str] = mapped_column(Text, nullable=False)
    harvest_expected: Mapped[date] = mapped_column(Date, nullable=False)
    harvest_earliest: Mapped[date | None] = mapped_column(Date)
    harvest_latest: Mapped[date | None] = mapped_column(Date)
    paddy_area_ha: Mapped[float | None] = mapped_column(Numeric)
    straw_expected: Mapped[float] = mapped_column(Numeric, nullable=False)
    straw_low: Mapped[float | None] = mapped_column(Numeric)
    straw_high: Mapped[float | None] = mapped_column(Numeric)
    confidence_tag: Mapped[str] = mapped_column(Text, nullable=False)
    reasons: Mapped[Any] = mapped_column(JSONB, default=list)
    model_version: Mapped[str | None] = mapped_column(Text)
    harvest_status: Mapped[str] = mapped_column(Text, nullable=False, default="GROWING")
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Decision(Base):
    __tablename__ = "decisions"
    __table_args__ = (
        CheckConstraint("best_option IN ('keep','sell','feed')"),
        CheckConstraint("confidence_tag IN ('LOW','MEDIUM','HIGH')"),
        Index("idx_decisions_village", "village_id", "generated_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    village_id: Mapped[str] = mapped_column(ForeignKey("villages.id"), nullable=False)
    forecast_id: Mapped[int | None] = mapped_column(ForeignKey("forecasts.id"))
    per_tonne: Mapped[Any] = mapped_column(JSONB, nullable=False)
    best_option: Mapped[str] = mapped_column(Text, nullable=False)
    break_even_price: Mapped[float] = mapped_column(Numeric, nullable=False)
    price_low: Mapped[float | None] = mapped_column(Numeric)
    price_high: Mapped[float | None] = mapped_column(Numeric)
    assumptions: Mapped[Any] = mapped_column(JSONB, nullable=False)
    confidence_tag: Mapped[str | None] = mapped_column(Text)
    confidence_reasons: Mapped[Any] = mapped_column(JSONB, default=list)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BurnEvent(Base):
    __tablename__ = "burn_events"
    __table_args__ = (
        CheckConstraint("confidence_tag IN ('LOW','MEDIUM','HIGH')"),
        Index("idx_burn_geom", "geom", postgresql_using="gist"),
        Index("idx_burn_date", "detected_on"),
    )

    event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    village_id: Mapped[str] = mapped_column(ForeignKey("villages.id"), nullable=False)
    geom: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    detected_on: Mapped[date] = mapped_column(Date, nullable=False)
    confidence_tag: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Any] = mapped_column(JSONB)
    source: Mapped[str | None] = mapped_column(Text)


class Buyer(Base):
    __tablename__ = "buyers"
    __table_args__ = (
        CheckConstraint("type IN ('POWER','PELLET','BIOGAS','OTHER')"),
        Index("idx_buyers_geom", "geom", postgresql_using="gist"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    geom: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    capacity_t_per_day: Mapped[float | None] = mapped_column(Numeric)
    price_per_tonne_inr: Mapped[float | None] = mapped_column(Numeric)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False, default="baler")
    base_geom: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    capacity_t_per_day: Mapped[float | None] = mapped_column(Numeric)
    rate_per_tonne_inr: Mapped[float | None] = mapped_column(Numeric)
    available_from: Mapped[date | None] = mapped_column(Date)


class Truck(Base):
    __tablename__ = "trucks"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    base_geom: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    capacity_t: Mapped[float | None] = mapped_column(Numeric)
    rate_per_km_inr: Mapped[float | None] = mapped_column(Numeric)
    available_from: Mapped[date | None] = mapped_column(Date)


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint("status IN ('PROPOSED','CONFIRMED','COMPLETED','CANCELLED')"),
        Index("idx_matches_village", "village_id"),
        Index("idx_matches_status", "status"),
    )

    match_id: Mapped[str] = mapped_column(Text, primary_key=True)
    village_id: Mapped[str] = mapped_column(ForeignKey("villages.id"), nullable=False)
    buyer_id: Mapped[str] = mapped_column(ForeignKey("buyers.id"), nullable=False)
    baler_id: Mapped[str | None] = mapped_column(ForeignKey("machines.id"))
    truck_id: Mapped[str | None] = mapped_column(ForeignKey("trucks.id"))
    tonnes: Mapped[float] = mapped_column(Numeric, nullable=False)
    pickup_date: Mapped[date] = mapped_column(Date, nullable=False)
    price_per_tonne_inr: Mapped[float] = mapped_column(Numeric, nullable=False)
    net_to_farmers_inr: Mapped[float | None] = mapped_column(Numeric)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="PROPOSED")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('officer','farmer','buyer')"),
        CheckConstraint("language IN ('en','hi','pa')"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str | None] = mapped_column(Text, unique=True)
    email: Mapped[str | None] = mapped_column(Text, unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    village_id: Mapped[str | None] = mapped_column(ForeignKey("villages.id"))
    buyer_id: Mapped[str | None] = mapped_column(ForeignKey("buyers.id"))
    language: Mapped[str] = mapped_column(Text, nullable=False, default="en")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    match_id: Mapped[str | None] = mapped_column(ForeignKey("matches.match_id"))
    channel: Mapped[str] = mapped_column(Text, nullable=False, default="log")
    language: Mapped[str] = mapped_column(Text, nullable=False, default="en")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    provider_id: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(Text, nullable=False)
    entity: Mapped[str | None] = mapped_column(Text)
    entity_id: Mapped[str | None] = mapped_column(Text)
    details: Mapped[Any] = mapped_column(JSONB)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
