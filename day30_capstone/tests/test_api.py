"""Tests for the Flask recommendation API."""

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from day30_capstone.api.app import create_app
from day30_capstone.data.database import Base
from day30_capstone.data.models import Content, Interaction, User


class RecommendationApiTests(unittest.TestCase):
	"""Exercise API routes against an isolated in-memory database."""

	def setUp(self):
		self.engine = create_engine("sqlite:///:memory:")
		Base.metadata.create_all(self.engine)
		with Session(self.engine) as session:
			session.add_all(
				[
					User(id=1, name="Ada", interests=["Python"]),
					Content(
						id=10,
					title="Python Foundations",
						category="Programming",
						difficulty="beginner",
						popularity=8,
					),
					Content(
						id=11,
						title="SQL Joins",
						category="Databases",
						difficulty="beginner",
						popularity=10,
					),
				]
			)
			session.commit()

		self.app = create_app(lambda: Session(self.engine, expire_on_commit=False))
		self.app.config["TESTING"] = True
		self.client = self.app.test_client()

	def tearDown(self):
		self.engine.dispose()

	def test_recommendation_response_is_json_with_request_id(self):
		response = self.client.get("/recommend/1?limit=1")

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.is_json)
		self.assertEqual(response.json["user_id"], 1)
		self.assertEqual(len(response.json["recommendations"]), 1)
		self.assertIn("explanation", response.json["recommendations"][0])
		self.assertTrue(response.headers["X-Request-ID"])

	def test_root_renders_recommendation_dashboard(self):
		response = self.client.get("/")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.mimetype, "text/html")
		self.assertIn(b"Learning recommendations", response.data)
		self.assertTrue(response.headers["X-Request-ID"])

	def test_recommendation_returns_404_for_unknown_user(self):
		response = self.client.get("/recommend/999")

		self.assertEqual(response.status_code, 404)
		self.assertEqual(response.json["error"], "User not found")
		self.assertTrue(response.headers["X-Request-ID"])

	def test_recommendation_rejects_bad_limit(self):
		for limit in ("zero", "0", "-1"):
			with self.subTest(limit=limit):
				response = self.client.get(f"/recommend/1?limit={limit}")
				self.assertEqual(response.status_code, 400)
				self.assertTrue(response.is_json)

	def test_feedback_validates_and_persists(self):
		bad_response = self.client.post(
			"/feedback", json={"user_id": 1, "content_id": 10}
		)
		self.assertEqual(bad_response.status_code, 400)

		response = self.client.post(
			"/feedback",
			json={"user_id": 1, "content_id": 10, "type": "rate", "rating": 4.5},
		)
		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.json["status"], "recorded")
		self.assertTrue(response.headers["X-Request-ID"])
		with Session(self.engine) as session:
			interaction = session.scalar(select(Interaction))
			self.assertEqual(interaction.type, "rate")
			self.assertEqual(interaction.rating, 4.5)

	def test_feedback_returns_404_for_unknown_user(self):
		response = self.client.post(
			"/feedback",
			json={"user_id": 999, "content_id": 10, "type": "view"},
		)
		self.assertEqual(response.status_code, 404)
		self.assertEqual(response.json["error"], "User not found")

	def test_feedback_invalidates_recommendation_cache(self):
		first = self.client.get("/recommend/1").json["recommendations"]
		self.assertIn(10, [item["id"] for item in first])

		response = self.client.post(
			"/feedback",
			json={"user_id": 1, "content_id": 10, "type": "view"},
		)
		self.assertEqual(response.status_code, 201)

		after_feedback = self.client.get("/recommend/1").json["recommendations"]
		self.assertNotIn(10, [item["id"] for item in after_feedback])

	def test_health_and_metrics(self):
		health_response = self.client.get("/health")
		self.assertEqual(health_response.json, {"status": "ok"})
		self.client.get("/recommend/1")
		self.client.get("/recommend/1")
		metrics_response = self.client.get("/metrics")

		self.assertEqual(metrics_response.status_code, 200)
		self.assertEqual(metrics_response.json["request_count"], 3)
		self.assertGreater(metrics_response.json["average_latency_ms"], 0)
		self.assertEqual(metrics_response.json["cache_hit_rate"], 0.5)
		self.assertTrue(metrics_response.headers["X-Request-ID"])

	def test_every_request_gets_a_distinct_request_id(self):
		first = self.client.get("/health").headers["X-Request-ID"]
		second = self.client.get("/health").headers["X-Request-ID"]
		self.assertNotEqual(first, second)


if __name__ == "__main__":
	unittest.main()
