"""Evaluate recommendation quality using a deterministic interaction split."""

import argparse
import csv
import os
import random
import sys
from collections import defaultdict
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = PROJECT_DIR.parent
sys.path.insert(0, str(WORKSPACE_DIR))
os.environ.setdefault(
	"DATABASE_URL",
	f"sqlite:///{(PROJECT_DIR / 'recommendation.db').as_posix()}",
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from day30_capstone.data.database import Base, SessionLocal
from day30_capstone.data.models import (
	Content,
	ContentSkill,
	Interaction,
	Skill,
	User,
	UserSkill,
)
from day30_capstone.engine.evaluator import (
	ndcg_at_k,
	precision_at_k,
	recall_at_k,
)
from day30_capstone.engine.orchestrator import RecommendationOrchestrator


K = 5
COPY_MODELS = (User, Content, Skill, UserSkill, ContentSkill)
METRIC_COLUMNS = ("precision@5", "recall@5", "ndcg@5")


def _clone_row(model, row):
	"""Copy mapped column values into a detached model instance."""
	values = {
		column.key: getattr(row, column.key)
		for column in model.__table__.columns
	}
	return model(**values)


def _split_interactions(interactions, test_fraction, seed):
	"""Split interactions per user while retaining history for evaluation."""
	if not 0 < test_fraction < 1:
		raise ValueError("test_fraction must be between 0 and 1")

	by_user = defaultdict(list)
	for interaction in interactions:
		by_user[interaction.user_id].append(interaction)

	randomizer = random.Random(seed)
	training = []
	testing = defaultdict(set)
	for user_id, user_interactions in by_user.items():
		if len(user_interactions) < 2:
			training.extend(user_interactions)
			continue

		test_count = min(
			len(user_interactions) - 1,
			max(1, round(len(user_interactions) * test_fraction)),
		)
		held_out = randomizer.sample(user_interactions, test_count)
		held_out_ids = {interaction.content_id for interaction in held_out}
		testing[user_id].update(held_out_ids)
		training.extend(
			interaction
			for interaction in user_interactions
			if interaction.content_id not in held_out_ids
		)
	return training, testing


def _evaluate_split(training, testing):
	"""Evaluate users on a temporary database containing training rows only."""
	temporary_engine = create_engine("sqlite://")
	Base.metadata.create_all(temporary_engine)
	try:
		with SessionLocal() as source_session, Session(temporary_engine) as train_session:
			for model in COPY_MODELS:
				rows = source_session.scalars(select(model)).all()
				train_session.add_all(_clone_row(model, row) for row in rows)
			train_session.add_all(
				_clone_row(Interaction, row) for row in training
			)
			train_session.commit()

			orchestrator = RecommendationOrchestrator(train_session)
			per_user = []
			for user_id, relevant_items in sorted(testing.items()):
				if not relevant_items:
					continue
				recommendations = orchestrator.get_recommendations(user_id, limit=K)
				recommended_ids = [
					item["content"].id for item in recommendations
				]
				per_user.append(
					{
						"user_id": user_id,
						"precision@5": precision_at_k(
							recommended_ids, relevant_items, K
						),
						"recall@5": recall_at_k(
							recommended_ids, relevant_items, K
						),
						"ndcg@5": ndcg_at_k(
							recommended_ids, relevant_items, K
						),
					}
				)
		return per_user
	finally:
		temporary_engine.dispose()


def evaluate(test_fraction=0.2, seed=42, reports_dir=None):
	"""Run the evaluation, save a CSV table and a metric bar chart."""
	with SessionLocal() as session:
		interactions = session.scalars(
			select(Interaction).order_by(Interaction.user_id, Interaction.created_at)
		).all()
	training, testing = _split_interactions(interactions, test_fraction, seed)

	if not testing:
		raise ValueError("Not enough interactions for a per-user train/test split")
	rows = _evaluate_split(training, testing)
	if not rows:
		raise ValueError("No users have held-out interactions to evaluate")

	means = {
		metric: sum(row[metric] for row in rows) / len(rows)
		for metric in METRIC_COLUMNS
	}
	output_dir = Path(reports_dir) if reports_dir else PROJECT_DIR / "reports"
	output_dir.mkdir(parents=True, exist_ok=True)
	csv_path = output_dir / "evaluation_results.csv"
	chart_path = output_dir / "evaluation_metrics.png"

	with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
		writer = csv.DictWriter(
			csv_file,
			fieldnames=("user_id", *METRIC_COLUMNS),
			lineterminator="\n",
		)
		writer.writeheader()
		writer.writerows(rows)
		writer.writerow({"user_id": "MEAN", **means})

	figure, axis = plt.subplots(figsize=(7, 4))
	axis.bar(list(means), list(means.values()), color="#3979a8")
	axis.set_ylim(0, 1)
	axis.set_ylabel("Score")
	axis.set_title(f"Recommendation quality at k={K}")
	axis.grid(axis="y", alpha=0.25)
	figure.tight_layout()
	figure.savefig(chart_path, dpi=150)
	plt.close(figure)

	print(f"Evaluated users: {len(rows)}")
	for metric, value in means.items():
		print(f"Mean {metric}: {value:.4f}")
	print(f"Results table: {csv_path}")
	print(f"Metric chart: {chart_path}")
	return {"users": len(rows), **means, "csv_path": csv_path, "chart_path": chart_path}


def main():
	"""Parse command-line options and run the evaluation."""
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--test-fraction", type=float, default=0.2)
	parser.add_argument("--seed", type=int, default=42)
	parser.add_argument("--reports-dir", type=Path)
	args = parser.parse_args()
	evaluate(args.test_fraction, args.seed, args.reports_dir)


if __name__ == "__main__":
	main()
