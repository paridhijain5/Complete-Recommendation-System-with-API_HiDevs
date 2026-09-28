"""Generate recommendation candidates from several simple strategies."""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from day30_capstone.data.models import (
	Content,
	ContentSkill,
	Interaction,
	UserSkill,
)
from day30_capstone.engine.similarity import cosine_similarity, user_similarity


_EVENT_STRENGTHS = {"view": 1.0, "bookmark": 3.0, "complete": 4.0}


def _interaction_strength(interaction: Interaction) -> float:
	"""Convert an interaction into an implicit rating from zero to five."""
	if interaction.rating is not None:
		return min(max(interaction.rating, 0.0), 5.0)
	return _EVENT_STRENGTHS.get(interaction.type.lower(), 1.0)


def _rank(scores: dict[int, float], limit: int) -> dict[int, float]:
	"""Return scores ordered by score descending, then content ID."""
	if limit <= 0:
		return {}
	ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
	return dict(ranked[:limit])


def generate_collaborative_candidates(
	session: Session,
	user_id: int,
	limit: int = 10,
) -> dict[int, float]:
	"""Recommend unseen content liked by users with similar histories."""
	interactions = session.scalars(select(Interaction)).all()
	user_vectors: dict[int, dict[int, float]] = defaultdict(dict)
	for interaction in interactions:
		strength = _interaction_strength(interaction)
		previous = user_vectors[interaction.user_id].get(interaction.content_id, 0.0)
		user_vectors[interaction.user_id][interaction.content_id] = max(
			previous, strength
		)

	target_vector = user_vectors.get(user_id, {})
	if not target_vector:
		return {}

	numerators: dict[int, float] = defaultdict(float)
	denominators: dict[int, float] = defaultdict(float)
	for other_user_id, item_vector in user_vectors.items():
		if other_user_id == user_id:
			continue
		similarity = user_similarity(user_id, other_user_id, user_vectors)
		if similarity <= 0:
			continue

		for content_id, strength in item_vector.items():
			if content_id in target_vector:
				continue
			numerators[content_id] += similarity * strength
			denominators[content_id] += similarity

	scores = {
		content_id: numerator / denominators[content_id] / 5.0
		for content_id, numerator in numerators.items()
		if denominators[content_id] > 0
	}
	return _rank(scores, limit)


def generate_content_based_candidates(
	session: Session,
	user_id: int,
	limit: int = 10,
) -> dict[int, float]:
	"""Recommend unseen content whose skills match the user's skill profile."""
	profile = {
		row.skill_id: row.proficiency
		for row in session.scalars(
			select(UserSkill).where(UserSkill.user_id == user_id)
		).all()
	}
	if not profile:
		return {}

	seen_content_ids = set(
		session.scalars(
			select(Interaction.content_id).where(Interaction.user_id == user_id)
		).all()
	)
	content_skills: dict[int, dict[int, float]] = defaultdict(dict)
	for content_id, skill_id in session.execute(
		select(ContentSkill.content_id, ContentSkill.skill_id)
	):
		content_skills[content_id][skill_id] = 1.0

	scores = {}
	for content_id, skill_vector in content_skills.items():
		if content_id in seen_content_ids:
			continue
		score = cosine_similarity(profile, skill_vector)
		if score > 0:
			scores[content_id] = score
	return _rank(scores, limit)


def generate_popularity_candidates(
	session: Session,
	user_id: int,
	limit: int = 10,
) -> dict[int, float]:
	"""Recommend unseen content ordered by normalized popularity."""
	seen_content_ids = set(
		session.scalars(
			select(Interaction.content_id).where(Interaction.user_id == user_id)
		).all()
	)
	content_items = session.scalars(select(Content)).all()
	max_popularity = max(
		(content.popularity for content in content_items), default=0.0
	)
	scores = {
		content.id: content.popularity / max_popularity
		if max_popularity > 0
		else 0.0
		for content in content_items
		if content.id not in seen_content_ids
	}
	return _rank(scores, limit)
