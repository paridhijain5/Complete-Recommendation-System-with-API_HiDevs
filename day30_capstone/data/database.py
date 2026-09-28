"""Database engine and session configuration."""

import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """Base class for all database models."""


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///recommendation.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
)


if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(connection, _connection_record):
        """Enable foreign-key enforcement for each SQLite connection."""
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def create_tables():
    """Create all tables registered on the declarative base."""
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)