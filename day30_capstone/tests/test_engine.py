"""Unit tests for recommendation engine components."""

import math
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from day30_capstone.data.database import Base
from day30_capstone.data.models import (
	Content,
	ContentSkill,
	Interaction,
	Skill,
	User,
	UserSkill,
)
from day30_capstone.engine.candidate_gen import (
	generate_collaborative_candidates,
	generate_content_based_candidates,
	generate_popularity_candidates,
)
from day30_capstone.engine.evaluator import (
	ndcg_at_k,
	precision_at_k,
	recall_at_k,
)
from day30_capstone.engine.orchestrator import RecommendationOrchestrator
from day30_capstone.engine.scorer import combine_scores
from day30_capstone.engine.similarity import (
	content_similarity,
	cosine_similarity,
	user_similarity,
)


class SimilarityTests(unittest.TestCase):
	"""Tests for sparse-vector cosine similarity."""

	def test_cosine_similarity_handles_matching_and_empty_vectors(self):
		self.assertAlmostEqual(cosine_similarity({1: 1, 2: 1}, {1: 1, 2: 1}), 1)
		self.assertEqual(cosine_similarity({1: 1}, {2: 1}), 0)
		self.assertEqual(cosine_similarity({}, {1: 1}), 0)

	def test_user_and_content_similarity_use_their_vectors(self):
		user_vectors = {1: {10: 1, 11: 1}, 2: {10: 1}}
		content_vectors = {10: {1: 1, 2: 1}, 11: {1: 1}}
		self.assertAlmostEqual(user_similarity(1, 2, user_vectors), 1 / math.sqrt(2))
		self.assertAlmostEqual(
			content_similarity(10, 11, content_vectors), 1 / math.sqrt(2)
		)


class EngineDatabaseTests(unittest.TestCase):
	"""Tests candidate generation against a small isolated database."""

	def setUp(self):
		self.engine = create_engine("sqlite:///:memory:")
		Base.metadata.create_all(self.engine)
		self.session = Session(self.engine)
		self.session.add_all(
			[
				User(id=1, name="Alex", interests=["Python"]),
				User(id=2, name="Sam", interests=["Python"]),
				User(id=3, name="Lee", interests=["SQL"]),
				Skill(id=1, name="Python"),
				Skill(id=2, name="SQL"),
				Content(
					id=1,
					title="Python Basics",
					category="Programming",
					difficulty="beginner",
					popularity=10,
				),
				Content(
					id=2,
					title="Python Practice",
					category="Programming",
					difficulty="intermediate",
					popularity=5,
				),
				Content(
					id=3,
					title="SQL Basics",
					category="Databases",
					difficulty="beginner",
					popularity=9,
				),
				Content(
					id=4,
					title="Advanced SQL",
					category="Databases",
					difficulty="advanced",
					popularity=12,
				),
				UserSkill(user_id=1, skill_id=1, proficiency=0.9),
				UserSkill(user_id=2, skill_id=1, proficiency=0.8),
				UserSkill(user_id=3, skill_id=2, proficiency=0.7),
				ContentSkill(content_id=1, skill_id=1),
				ContentSkill(content_id=2, skill_id=1),
				ContentSkill(content_id=3, skill_id=2),
				ContentSkill(content_id=4, skill_id=2),
				Interaction(user_id=1, content_id=1, type="complete", rating=None),
				Interaction(user_id=2, content_id=1, type="complete", rating=None),
				Interaction(user_id=2, content_id=2, type="rate", rating=5),
				Interaction(user_id=3, content_id=3, type="complete", rating=None),
			]
		)
		self.session.commit()

	def tearDown(self):
		self.session.close()
		self.engine.dispose()

	def test_collaborative_candidates_use_similar_users(self):
		candidates = generate_collaborative_candidates(self.session, 1)
		self.assertEqual(list(candidates), [2])
		self.assertGreater(candidates[2], 0)

	def test_content_candidates_match_user_skills(self):
		candidates = generate_content_based_candidates(self.session, 1)
		self.assertEqual(list(candidates), [2])
		self.assertEqual(candidates[2], 1.0)

	def test_popularity_candidates_exclude_seen_content(self):
		candidates = generate_popularity_candidates(self.session, 1, limit=3)
		self.assertEqual(list(candidates), [4, 3, 2])
		self.assertNotIn(1, candidates)
		self.assertEqual(candidates[4], 1.0)


class ScorerTests(unittest.TestCase):
	"""Tests for weighted strategy score combination."""

	def test_combine_scores_uses_configurable_weights(self):
		scores = {
			"collaborative": {1: 0.8, 2: 0.4},
			"content": {1: 0.2, 3: 1.0},
		}
		combined = combine_scores(
			scores, weights={"collaborative": 3, "content": 1}
		)
		self.assertEqual(list(combined), [3, 1, 2])
		self.assertAlmostEqual(combined[1], 0.65)
		self.assertAlmostEqual(combined[2], 0.4)

	def test_combine_scores_rejects_negative_weights(self):
		with self.assertRaises(ValueError):
			combine_scores({"content": {1: 1}}, weights={"content": -1})


class EvaluatorTests(unittest.TestCase):
	"""Tests for top-k recommendation metrics."""

	def test_precision_recall_and_ndcg_at_k(self):
		recommendations = [1, 2, 3]
		relevant = {2, 3, 4}
		self.assertEqual(precision_at_k(recommendations, relevant, 2), 0.5)
		self.assertAlmostEqual(recall_at_k(recommendations, relevant, 2), 1 / 3)
		expected_ndcg = (1 / math.log2(3)) / (1 + 1 / math.log2(3))
		self.assertAlmostEqual(ndcg_at_k(recommendations, relevant, 2), expected_ndcg)

	def test_metrics_handle_no_relevant_items(self):
		self.assertEqual(recall_at_k([1, 2], set(), 2), 0)
		self.assertEqual(ndcg_at_k([1, 2], set(), 2), 0)

	def test_metrics_reject_non_positive_k(self):
		with self.assertRaises(ValueError):
			precision_at_k([1], {1}, 0)


class OrchestratorTests(unittest.TestCase):
	"""Tests for end-to-end recommendation orchestration."""

	def setUp(self):
		self.engine = create_engine("sqlite:///:memory:")
		Base.metadata.create_all(self.engine)
		self.session = Session(self.engine)
		self.session.add_all(
			[
				User(id=1, name="New learner", interests=["Python"]),
				User(id=2, name="No interests", interests=[]),
				Skill(id=10, name="Python"),
				Content(
					id=10,
					title="Python Fundamentals",
					category="Programming",
					difficulty="beginner",
					popularity=10,
				),
				Content(
					id=11,
					title="SQL Joins",
					category="Databases",
					difficulty="beginner",
					popularity=100,
				),
				Content(
					id=12,
					title="Study Planning",
					category="Productivity",
					difficulty="beginner",
					popularity=50,
				),
				ContentSkill(content_id=10, skill_id=10),
			]
		)
		self.session.commit()
		self.orchestrator = RecommendationOrchestrator(self.session)

	def tearDown(self):
		self.session.close()
		self.engine.dispose()

	def test_cold_start_includes_interest_explanation(self):
		recommendations = self.orchestrator.get_recommendations(1, limit=3)
		self.assertEqual(recommendations[0]["content"].id, 10)
		self.assertIn("Python", recommendations[0]["explanation"])
		self.assertTrue(all(item["explanation"] for item in recommendations))

	def test_cold_start_without_interests_uses_popularity(self):
		recommendations = self.orchestrator.get_recommendations(2, limit=1)
		self.assertEqual(recommendations[0]["content"].id, 11)
		self.assertEqual(recommendations[0]["explanation"], "Popular with learners")

	def test_record_feedback_persists_and_invalidates_cache(self):
		before = self.orchestrator.get_recommendations(1, limit=3)
		self.assertIn(10, [item["content"].id for item in before])

		interaction = self.orchestrator.record_feedback(1, 10, "rate", 4.5)

		self.assertEqual(interaction.user_id, 1)
		self.assertEqual(interaction.content_id, 10)
		self.assertEqual(interaction.type, "rate")
		self.assertEqual(interaction.rating, 4.5)
		after = self.orchestrator.get_recommendations(1, limit=3)
		self.assertNotIn(10, [item["content"].id for item in after])
