"""Cosine similarity helpers for users and content items."""

from collections.abc import Hashable, Mapping


def cosine_similarity(
	vector_a: Mapping[Hashable, float],
	vector_b: Mapping[Hashable, float],
) -> float:
	"""Return cosine similarity for two sparse feature vectors."""
	magnitude_a = sum(value * value for value in vector_a.values()) ** 0.5
	magnitude_b = sum(value * value for value in vector_b.values()) ** 0.5
	if magnitude_a == 0 or magnitude_b == 0:
		return 0.0

	dot_product = sum(
		value * vector_b.get(feature, 0.0)
		for feature, value in vector_a.items()
	)
	return dot_product / (magnitude_a * magnitude_b)


def user_similarity(
	user_id: int,
	other_user_id: int,
	user_vectors: Mapping[int, Mapping[int, float]],
) -> float:
	"""Return cosine similarity between two users' item vectors."""
	return cosine_similarity(
		user_vectors.get(user_id, {}), user_vectors.get(other_user_id, {})
	)


def content_similarity(
	content_id: int,
	other_content_id: int,
	content_vectors: Mapping[int, Mapping[int, float]],
) -> float:
	"""Return cosine similarity between two content feature vectors."""
	return cosine_similarity(
		content_vectors.get(content_id, {}),
		content_vectors.get(other_content_id, {}),
	)
