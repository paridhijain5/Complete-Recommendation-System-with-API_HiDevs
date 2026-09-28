"""Repository classes for database access."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Content, ContentSkill, Interaction, Skill, User, UserSkill


class UserRepository:
    """Queries and writes users."""

    def __init__(self, session: Session):
        """Create a repository using an existing database session."""
        self.session = session

    def add(self, user: User) -> User:
        """Add and persist a user."""
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_by_id(self, user_id: int) -> User | None:
        """Return a user by primary key, if present."""
        return self.session.get(User, user_id)


class ContentRepository:
    """Queries and writes recommendable content."""

    def __init__(self, session: Session):
        """Create a repository using an existing database session."""
        self.session = session

    def add(self, content: Content) -> Content:
        """Add and persist a content item."""
        self.session.add(content)
        self.session.commit()
        self.session.refresh(content)
        return content

    def get_by_id(self, content_id: int) -> Content | None:
        """Return content by primary key, if present."""
        return self.session.get(Content, content_id)

    def get_content_by_skills(self, skill_ids: list[int]) -> list[Content]:
        """Return content tagged with any of the supplied skill IDs."""
        if not skill_ids:
            return []

        statement = (
            select(Content)
            .join(ContentSkill, ContentSkill.content_id == Content.id)
            .where(ContentSkill.skill_id.in_(skill_ids))
            .distinct()
            .order_by(Content.id)
        )
        return list(self.session.scalars(statement))


class SkillRepository:
    """Queries and writes skills."""

    def __init__(self, session: Session):
        """Create a repository using an existing database session."""
        self.session = session

    def add(self, skill: Skill) -> Skill:
        """Add and persist a skill."""
        self.session.add(skill)
        self.session.commit()
        self.session.refresh(skill)
        return skill

    def get_by_id(self, skill_id: int) -> Skill | None:
        """Return a skill by primary key, if present."""
        return self.session.get(Skill, skill_id)


class UserSkillRepository:
    """Queries and writes user skill proficiencies."""

    def __init__(self, session: Session):
        """Create a repository using an existing database session."""
        self.session = session

    def add(self, user_skill: UserSkill) -> UserSkill:
        """Add and persist a user skill association."""
        self.session.add(user_skill)
        self.session.commit()
        self.session.refresh(user_skill)
        return user_skill

    def get_by_user_id(self, user_id: int) -> list[UserSkill]:
        """Return all skill proficiencies for a user."""
        statement = select(UserSkill).where(UserSkill.user_id == user_id)
        return list(self.session.scalars(statement))


class ContentSkillRepository:
    """Queries and writes content skill associations."""

    def __init__(self, session: Session):
        """Create a repository using an existing database session."""
        self.session = session

    def add(self, content_skill: ContentSkill) -> ContentSkill:
        """Add and persist a content skill association."""
        self.session.add(content_skill)
        self.session.commit()
        self.session.refresh(content_skill)
        return content_skill

    def get_by_content_id(self, content_id: int) -> list[ContentSkill]:
        """Return all skill associations for a content item."""
        statement = select(ContentSkill).where(
            ContentSkill.content_id == content_id
        )
        return list(self.session.scalars(statement))


class InteractionRepository:
    """Queries and writes user interactions."""

    def __init__(self, session: Session):
        """Create a repository using an existing database session."""
        self.session = session

    def record_interaction(
        self,
        user_id: int,
        content_id: int,
        interaction_type: str,
        rating: float | None = None,
        created_at: datetime | None = None,
    ) -> Interaction:
        """Record and persist one interaction."""
        interaction = Interaction(
            user_id=user_id,
            content_id=content_id,
            type=interaction_type,
            rating=rating,
            created_at=created_at,
        )
        self.session.add(interaction)
        self.session.commit()
        self.session.refresh(interaction)
        return interaction

    def get_user_history(self, user_id: int) -> list[Interaction]:
        """Return a user's interactions from newest to oldest."""
        statement = (
            select(Interaction)
            .where(Interaction.user_id == user_id)
            .order_by(Interaction.created_at.desc())
        )
        return list(self.session.scalars(statement))