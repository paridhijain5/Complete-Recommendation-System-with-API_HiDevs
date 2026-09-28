"""SQLAlchemy models for recommendation data."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utc_now():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class User(Base):
    """A user and their declared interests."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    interests: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class Content(Base):
    """A piece of recommendable content."""

    __tablename__ = "content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(50), nullable=False)
    popularity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class Skill(Base):
    """A skill associated with users or content."""

    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class UserSkill(Base):
    """A user's proficiency in a skill."""

    __tablename__ = "user_skills"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    proficiency: Mapped[float] = mapped_column(Float, nullable=False)


class ContentSkill(Base):
    """A skill required or taught by a piece of content."""

    __tablename__ = "content_skills"

    content_id: Mapped[int] = mapped_column(
        ForeignKey("content.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )


class Interaction(Base):
    """A recorded user interaction with content."""

    __tablename__ = "interactions"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    content_id: Mapped[int] = mapped_column(
        ForeignKey("content.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, default=utc_now
    )
    type: Mapped[str] = mapped_column("type", String(50), nullable=False)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)