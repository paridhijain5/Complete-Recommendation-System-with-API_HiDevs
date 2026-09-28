"""Coordinate candidate generation, ranking, explanations, and feedback."""

from collections import defaultdict
from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from day30_capstone.data.models import Content, ContentSkill, Interaction, Skill, User
from day30_capstone.data.repositories import InteractionRepository
from day30_capstone.engine.candidate_gen import (
	generate_collaborative_candidates,
	generate_content_based_candidates,
	generate_popularity_candidates,
)
from day30_capstone.engine.scorer import DEFAULT_WEIGHTS, combine_scores


class RecommendationOrchestrator:
	"""Generate, explain, cache, and update recommendations."""

	def __init__(
		self,
		session: Session,
		weights: Mapping[str, float] | None = None,
	):
		"""Create an orchestrator using a database session and optional weights."""
		self.session = session
		self.weights = dict(DEFAULT_WEIGHTS if weights is None else weights)
		self._cache: dict[tuple[int, int], list[dict]] = {}

	def get_recommendations(self, user_id: int, limit: int = 10) -> list[dict]:
		"""Return ranked content records with a score and short explanation."""
		if limit <= 0:
			return []

		cache_key = (user_id, limit)
		if cache_key in self._cache:
			return [dict(recommendation) for recommendation in self._cache[cache_key]]

		user = self.session.get(User, user_id)
		history = InteractionRepository(self.session).get_user_history(user_id)
		if history:
			strategy_scores = self._get_warm_user_scores(user_id, limit)
			weights = self.weights
		else:
			strategy_scores = self._get_cold_start_scores(user, user_id)
			weights = self._cold_start_weights()

		ranked_scores = combine_scores(strategy_scores, weights)
		content_by_id = {
			content.id: content
			for content in self.session.scalars(
				select(Content).where(Content.id.in_(ranked_scores))
			).all()
		}

		recommendations = []
		for content_id, score in ranked_scores.items():
			content = content_by_id.get(content_id)
			if content is None:
				continue
			recommendations.append(
				{
					"content": content,
					"score": score,
					"explanation": self._explain(
						content_id, strategy_scores, user
					),
				}
			)
			if len(recommendations) == limit:
				break

		self._cache[cache_key] = recommendations
		return [dict(recommendation) for recommendation in recommendations]

	def record_feedback(
		self,
		user_id: int,
		content_id: int,
		type: str,
		rating: float | None = None,
	) -> Interaction:
		"""Persist user feedback and invalidate cached recommendations."""
		interaction = InteractionRepository(self.session).record_interaction(
			user_id=user_id,
			content_id=content_id,
			interaction_type=type,
			rating=rating,
		)
		self._cache.clear()
		return interaction

	def _get_warm_user_scores(
		self, user_id: int, limit: int
	) -> dict[str, dict[int, float]]:
		"""Collect candidate scores for users with interaction history."""
		candidate_limit = max(limit * 3, limit)
		return {
			"collaborative": generate_collaborative_candidates(
				self.session, user_id, candidate_limit
			),
			"content": generate_content_based_candidates(
				self.session, user_id, candidate_limit
			),
			"popularity": generate_popularity_candidates(
				self.session, user_id, candidate_limit
			),
		}

	def _get_cold_start_scores(
		self, user: User | None, user_id: int
	) -> dict[str, dict[int, float]]:
		"""Combine popularity and interest matches for a user without history."""
		popularity = generate_popularity_candidates(
			self.session, user_id, limit=self._content_count()
		)
		interests = {
			interest.strip().casefold()
			for interest in (user.interests or [])
			if isinstance(interest, str) and interest.strip()
		} if user is not None else set()
		interest_scores: dict[int, float] = {}
		if interests:
			content_terms: dict[int, set[str]] = defaultdict(set)
			for content_id, title, category in self.session.execute(
				select(Content.id, Content.title, Content.category)
			):
				content_terms[content_id].update(
					(term.casefold() for term in (title, category) if term)
				)
			for content_id, skill_name in self.session.execute(
				select(ContentSkill.content_id, Skill.name)
				.join(Skill, Skill.id == ContentSkill.skill_id)
			):
				content_terms[content_id].add(skill_name.casefold())

			for content_id, terms in content_terms.items():
				matches = sum(
					1
					for interest in interests
					if any(interest in term or term in interest for term in terms)
				)
				interest_scores[content_id] = matches / len(interests)

		return {"popularity": popularity, "interest": interest_scores}

	def _cold_start_weights(self) -> dict[str, float]:
		"""Return configured popularity and interest weights for new users."""
		popularity_weight = self.weights.get("popularity", 0.2)
		interest_weight = self.weights.get("interest", 0.5)
		return {"popularity": popularity_weight, "interest": interest_weight}

	def _content_count(self) -> int:
		"""Return the number of content records available for cold-start ranking."""
		return self.session.query(Content).count()

	@staticmethod
	def _explain(
		content_id: int,
		strategy_scores: Mapping[str, Mapping[int, float]],
		user: User | None,
	) -> str:
		"""Describe the strongest signal contributing to a recommendation."""
		reasons = {
			"collaborative": "Learners with similar activity liked this",
			"content": "Matches skills in your profile",
			"popularity": "Popular with learners",
		}
		for strategy in ("interest", "collaborative", "content", "popularity"):
			if strategy_scores.get(strategy, {}).get(content_id, 0) <= 0:
				continue
			if strategy == "interest" and user is not None:
				return f"Matches your interests: {', '.join(user.interests or [])}"
			return reasons.get(strategy, "Recommended based on your activity")
		return "Recommended based on your activity"
