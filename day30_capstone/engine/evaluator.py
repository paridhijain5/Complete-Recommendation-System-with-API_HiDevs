"""Ranking metrics for evaluating recommendation results."""

import math
from collections.abc import Sequence, Set


def _validate_k(k: int) -> None:
	"""Raise an error when a metric is given an invalid cutoff."""
	if k <= 0:
		raise ValueError("k must be greater than zero")


def precision_at_k(
	recommended_items: Sequence[int],
	relevant_items: Set[int],
	k: int,
) -> float:
	"""Return the fraction of the first k recommendations that are relevant."""
	_validate_k(k)
	return sum(item in relevant_items for item in recommended_items[:k]) / k


def recall_at_k(
	recommended_items: Sequence[int],
	relevant_items: Set[int],
	k: int,
) -> float:
	"""Return the fraction of relevant items found in the first k results."""
	_validate_k(k)
	if not relevant_items:
		return 0.0
	hits = sum(item in relevant_items for item in recommended_items[:k])
	return hits / len(relevant_items)


def ndcg_at_k(
	recommended_items: Sequence[int],
	relevant_items: Set[int],
	k: int,
) -> float:
	"""Return binary-relevance normalized discounted cumulative gain at k."""
	_validate_k(k)
	discounts = (
		1.0 / math.log2(rank + 2)
		for rank, item in enumerate(recommended_items[:k])
		if item in relevant_items
	)
	dcg = sum(discounts)
	ideal_hits = min(len(relevant_items), k)
	if ideal_hits == 0:
		return 0.0
	ideal_dcg = sum(1.0 / math.log2(rank + 2) for rank in range(ideal_hits))
	return dcg / ideal_dcg
