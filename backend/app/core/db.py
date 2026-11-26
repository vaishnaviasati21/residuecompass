"""
Database engine + session factory.
Uses psycopg3 (psycopg) driver via SQLAlchemy 2.x.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# psycopg3 async-compatible sync driver
_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(
    _url,
    pool_pre_ping=True,     # drops dead connections before use
    pool_size=10,
    max_overflow=20,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """All SQLAlchemy ORM models inherit from this."""
    pass


def get_db():
    """FastAPI dependency – yields a session and closes it on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
