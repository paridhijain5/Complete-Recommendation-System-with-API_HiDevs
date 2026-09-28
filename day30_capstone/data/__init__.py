"""Data layer for the recommendation system."""

from .database import Base, SessionLocal, create_tables, engine
from .models import Content, ContentSkill, Interaction, Skill, User, UserSkill
from .repositories import (
    ContentRepository,
    ContentSkillRepository,
    InteractionRepository,
    SkillRepository,
    UserRepository,
    UserSkillRepository,
)

__all__ = [
    "Base",
    "Content",
    "ContentRepository",
    "ContentSkill",
    "ContentSkillRepository",
    "Interaction",
    "InteractionRepository",
    "SessionLocal",
    "Skill",
    "SkillRepository",
    "User",
    "UserRepository",
    "UserSkill",
    "UserSkillRepository",
    "create_tables",
    "engine",
]