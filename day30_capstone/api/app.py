"""Flask API for recommendations, feedback, health, and service metrics."""

import logging
import math
import threading
import time
import uuid

from flask import Flask, g, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from day30_capstone.data.database import SessionLocal
from day30_capstone.data.models import Content, User
from day30_capstone.engine.orchestrator import RecommendationOrchestrator


def create_app(session_factory=SessionLocal):
	"""Create the recommendation API application.

	The session factory can be replaced with an isolated database factory in
	tests. Recommendation results are cached in memory for the lifetime of the
	application instance.
	"""
	app = Flask(__name__)
	app.extensions["recommendation_session_factory"] = session_factory
	app.extensions["recommendation_cache"] = {}
	app.extensions["api_metrics"] = {
		"request_count": 0,
		"total_latency_ms": 0.0,
		"recommendation_request_count": 0,
		"cache_hit_count": 0,
	}
	app.extensions["api_metrics_lock"] = threading.Lock()

	@app.before_request
	def start_request():
		"""Assign a unique request ID and start request timing."""
		g.request_id = uuid.uuid4().hex
		g.request_started = time.perf_counter()
		g.cache_hit = False

	@app.after_request
	def finish_request(response):
		"""Attach request metadata, log latency, and update service metrics."""
		elapsed_ms = (time.perf_counter() - g.request_started) * 1000
		response.headers["X-Request-ID"] = g.request_id
		app.logger.info(
			"%s %s %s request_id=%s latency_ms=%.2f",
			request.method,
			request.path,
			response.status_code,
			g.request_id,
			elapsed_ms,
		)

		if request.endpoint != "metrics":
			metrics = app.extensions["api_metrics"]
			with app.extensions["api_metrics_lock"]:
				metrics["request_count"] += 1
				metrics["total_latency_ms"] += elapsed_ms
				if request.endpoint == "recommend":
					metrics["recommendation_request_count"] += 1
					metrics["cache_hit_count"] += int(g.cache_hit)
		return response

	@app.errorhandler(HTTPException)
	def handle_http_error(error):
		"""Return HTTP errors as JSON instead of Flask's HTML pages."""
		return jsonify({"error": error.description}), error.code

	@app.errorhandler(Exception)
	def handle_unexpected_error(error):
		"""Log unexpected failures and return a generic JSON error."""
		app.logger.exception("Unhandled API error: %s", error)
		return jsonify({"error": "Internal server error"}), 500

	@app.get("/health")
	def health():
		"""Report that the API process is responding."""
		return jsonify({"status": "ok"})

	@app.get("/")
	def index():
		"""Render the recommendation dashboard."""
		return render_template("index.html")

	@app.get("/recommend/<int:user_id>")
	def recommend(user_id):
		"""Return ranked recommendations for an existing user."""
		limit_value = request.args.get("limit", default="10")
		try:
			limit = int(limit_value)
		except (TypeError, ValueError):
			return jsonify({"error": "limit must be a positive integer"}), 400
		if limit <= 0:
			return jsonify({"error": "limit must be a positive integer"}), 400

		with session_factory() as session:
			user = session.get(User, user_id)
			if user is None:
				return jsonify({"error": "User not found"}), 404

			cache = app.extensions["recommendation_cache"]
			cache_key = (user_id, limit)
			g.cache_hit = cache_key in cache
			orchestrator = RecommendationOrchestrator(session)
			orchestrator._cache = cache
			recommendations = orchestrator.get_recommendations(user_id, limit)
			response_items = [
				{
					"id": item["content"].id,
					"title": item["content"].title,
					"category": item["content"].category,
					"difficulty": item["content"].difficulty,
					"popularity": item["content"].popularity,
					"score": item["score"],
					"explanation": item["explanation"],
				}
				for item in recommendations
			]
		return jsonify({"user_id": user_id, "recommendations": response_items})

	@app.post("/feedback")
	def feedback():
		"""Validate and record user feedback for a content item."""
		payload = request.get_json(silent=True)
		if not isinstance(payload, dict):
			return jsonify({"error": "Request body must be a JSON object"}), 400

		user_id = payload.get("user_id")
		content_id = payload.get("content_id")
		interaction_type = payload.get("type")
		rating = payload.get("rating")
		if (
			isinstance(user_id, bool)
			or not isinstance(user_id, int)
			or user_id <= 0
			or isinstance(content_id, bool)
			or not isinstance(content_id, int)
			or content_id <= 0
			or not isinstance(interaction_type, str)
			or not interaction_type.strip()
			or len(interaction_type) > 50
		):
			return jsonify(
				{
					"error": "user_id, content_id, and a valid type are required"
				}
			), 400
		if rating is not None and (
			isinstance(rating, bool)
			or not isinstance(rating, (int, float))
			or not math.isfinite(rating)
			or not 1 <= rating <= 5
		):
			return jsonify({"error": "rating must be a number from 1 to 5"}), 400

		with session_factory() as session:
			if session.get(User, user_id) is None:
				return jsonify({"error": "User not found"}), 404
			if session.get(Content, content_id) is None:
				return jsonify({"error": "Content not found"}), 404

			orchestrator = RecommendationOrchestrator(session)
			orchestrator._cache = app.extensions["recommendation_cache"]
			interaction = orchestrator.record_feedback(
				user_id=user_id,
				content_id=content_id,
				type=interaction_type.strip(),
				rating=rating,
			)
		return jsonify(
			{
				"status": "recorded",
				"user_id": interaction.user_id,
				"content_id": interaction.content_id,
				"type": interaction.type,
				"rating": interaction.rating,
			}
		), 201

	@app.get("/metrics")
	def metrics():
		"""Return request count, average latency, and recommendation cache rate."""
		values = app.extensions["api_metrics"]
		with app.extensions["api_metrics_lock"]:
			request_count = values["request_count"]
			recommendation_count = values["recommendation_request_count"]
			cache_hit_count = values["cache_hit_count"]
			average_latency_ms = (
				values["total_latency_ms"] / request_count if request_count else 0.0
			)
			cache_hit_rate = (
				cache_hit_count / recommendation_count
				if recommendation_count
				else 0.0
			)
		return jsonify(
			{
				"request_count": request_count,
				"average_latency_ms": average_latency_ms,
				"cache_hit_rate": cache_hit_rate,
			}
		)

	return app


app = create_app()
