"""Combine recommendation scores from candidate-generation strategies."""

from collections import defaultdict
from collections.abc import Mapping


DEFAULT_WEIGHTS = {
	"collaborative": 0.4,
	"content": 0.4,
	"popularity": 0.2,
}


def combine_scores(
	strategy_scores: Mapping[str, Mapping[int, float]],
	weights: Mapping[str, float] | None = None,
) -> dict[int, float]:
	"""Return weighted-average scores for all supplied content candidates.

	A candidate is averaged over strategies that returned a score for it.
	"""
	active_weights = DEFAULT_WEIGHTS if weights is None else weights
	if any(weight < 0 for weight in active_weights.values()):
		raise ValueError("Strategy weights must be non-negative")

	totals: dict[int, float] = defaultdict(float)
	weight_totals: dict[int, float] = defaultdict(float)
	for strategy, scores in strategy_scores.items():
		weight = active_weights.get(strategy, 0.0)
		if weight == 0:
			continue
		for content_id, score in scores.items():
			totals[content_id] += score * weight
			weight_totals[content_id] += weight

	combined = {
		content_id: totals[content_id] / weight_totals[content_id]
		for content_id in totals
		if weight_totals[content_id] > 0
	}
	return dict(sorted(combined.items(), key=lambda item: (-item[1], item[0])))
