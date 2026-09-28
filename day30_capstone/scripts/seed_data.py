"""Populate the recommendation database with sample learning data."""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = PROJECT_DIR.parent
sys.path.insert(0, str(WORKSPACE_DIR))
os.environ.setdefault(
	"DATABASE_URL",
	f"sqlite:///{(PROJECT_DIR / 'recommendation.db').as_posix()}",
)

from sqlalchemy import func, select

from day30_capstone.data.database import SessionLocal, create_tables
from day30_capstone.data.models import (
	Content,
	ContentSkill,
	Interaction,
	Skill,
	User,
	UserSkill,
)


SKILL_NAMES = [
	"Python",
	"SQL",
	"Pandas",
	"NumPy",
	"Data Visualization",
	"Statistics",
	"Machine Learning",
	"Deep Learning",
	"Natural Language Processing",
	"Data Cleaning",
	"Feature Engineering",
	"Regression",
	"Classification",
	"Model Evaluation",
	"Clustering",
	"Flask",
	"REST APIs",
	"Git",
]


CONTENT_DATA = [
	("Python: Getting Started", "Python", "Programming", "beginner", 88,
	 ("Python", "Git")),
	("Python Variables and Types", "Python", "Programming", "beginner", 82,
	 ("Python",)),
	("Control Flow with Python", "Python", "Programming", "beginner", 76,
	 ("Python",)),
	("Functions and Modules", "Python", "Programming", "beginner", 72,
	 ("Python", "Git")),
	("Object-Oriented Python", "Python", "Programming", "intermediate", 64,
	 ("Python",)),
	("Working with Files and Data", "Python", "Programming", "intermediate", 69,
	 ("Python", "Pandas", "Data Cleaning")),
	("Building APIs with Flask", "Python", "Web Development", "intermediate",
	 58, ("Python", "Flask", "REST APIs")),
	("Python Testing Essentials", "Python", "Programming", "intermediate", 55,
	 ("Python", "Git")),
	("SQL Queries from Scratch", "SQL", "Databases", "beginner", 91,
	 ("SQL",)),
	("Filtering and Sorting Data", "SQL", "Databases", "beginner", 79,
	 ("SQL",)),
	("Joining Relational Tables", "SQL", "Databases", "beginner", 84,
	 ("SQL",)),
	("Aggregations and Grouping", "SQL", "Databases", "intermediate", 77,
	 ("SQL",)),
	("Subqueries and Common Tables", "SQL", "Databases", "intermediate", 61,
	 ("SQL",)),
	("Designing a Relational Schema", "SQL", "Databases", "intermediate", 57,
	 ("SQL",)),
	("Window Functions in Practice", "SQL", "Databases", "advanced", 48,
	 ("SQL",)),
	("Query Performance Basics", "SQL", "Databases", "advanced", 43,
	 ("SQL",)),
	("Machine Learning Overview", "Machine Learning", "Machine Learning",
	 "beginner", 87, ("Machine Learning", "Statistics")),
	("Preparing Data for Models", "Machine Learning", "Machine Learning",
	 "beginner", 73, ("Data Cleaning", "Pandas")),
	("Linear Regression", "Machine Learning", "Machine Learning",
	 "beginner", 78, ("Regression", "Statistics")),
	("Classification with Decision Trees", "Machine Learning",
	 "Machine Learning", "intermediate", 68,
	 ("Classification", "Machine Learning")),
	("Feature Engineering Workshop", "Machine Learning", "Machine Learning",
	 "intermediate", 65, ("Feature Engineering", "Pandas")),
	("Evaluating Model Performance", "Machine Learning", "Machine Learning",
	 "intermediate", 62, ("Model Evaluation", "Statistics")),
	("Clustering Customer Data", "Machine Learning", "Machine Learning",
	 "intermediate", 51, ("Clustering", "Machine Learning")),
	("Neural Networks: First Steps", "Machine Learning", "Machine Learning",
	 "advanced", 46, ("Deep Learning", "Machine Learning")),
	("Exploring Data with Pandas", "Data Analytics", "Data Analytics",
	 "beginner", 86, ("Pandas", "Data Cleaning")),
	("NumPy for Everyday Analysis", "Data Analytics", "Data Analytics",
	 "beginner", 66, ("NumPy", "Python")),
	("Descriptive Statistics", "Data Analytics", "Data Analytics", "beginner",
	 74, ("Statistics",)),
	("Creating Clear Data Visuals", "Data Analytics", "Data Analytics",
	 "beginner", 71, ("Data Visualization", "Pandas")),
	("Cleaning Messy Datasets", "Data Analytics", "Data Analytics",
	 "intermediate", 63, ("Data Cleaning", "Pandas")),
	("SQL for Business Analysis", "Data Analytics", "Data Analytics",
	 "intermediate", 81, ("SQL", "Data Visualization")),
	("Communicating Analytical Results", "Data Analytics", "Data Analytics",
	 "intermediate", 52, ("Data Visualization", "Statistics")),
	("Text Data and NLP Basics", "Data Analytics", "Data Analytics", "advanced",
	 44, ("Natural Language Processing", "Python")),
]


USER_GROUPS = [
	("Python", "Data Analytics"),
	("SQL", "Data Analytics"),
	("Machine Learning", "Python"),
	("SQL", "Machine Learning"),
]

USER_NAMES = [
	"Avery Chen",
	"Jordan Patel",
	"Maya Thompson",
	"Ethan Rivera",
	"Sofia Kim",
	"Noah Williams",
	"Leila Hassan",
	"Lucas Martin",
	"Amara Okafor",
	"Oliver Brown",
	"Priya Shah",
	"Mateo Garcia",
	"Zoe Anderson",
	"Arjun Mehta",
	"Nina Costa",
	"Theo Nguyen",
	"Fatima Ali",
	"Caleb Johnson",
	"Elena Petrova",
	"Kai Robinson",
]


def _get_or_create_by_name(session, model, names):
	"""Return records by name, creating any that are missing."""
	existing = session.scalars(select(model)).all()
	records = {record.name: record for record in existing}
	for name in names:
		if name not in records:
			record = model(name=name)
			session.add(record)
			records[name] = record
	session.flush()
	return records


def seed_data():
	"""Insert repeatable users, learning content, skills, and interactions."""
	create_tables()

	with SessionLocal() as session:
		try:
			users = _get_or_create_by_name(session, User, USER_NAMES)
			skills = _get_or_create_by_name(session, Skill, SKILL_NAMES)

			existing_content = session.scalars(select(Content)).all()
			content_by_title = {
				content.title: content for content in existing_content
			}
			for title, track, category, difficulty, popularity, _ in CONTENT_DATA:
				content = content_by_title.get(title)
				if content is None:
					content = Content(
						title=title,
						category=category,
						difficulty=difficulty,
						popularity=popularity,
					)
					session.add(content)
					content_by_title[title] = content
			session.flush()

			user_skill_keys = {
				(association.user_id, association.skill_id)
				for association in session.scalars(select(UserSkill)).all()
			}
			content_skill_keys = {
				(association.content_id, association.skill_id)
				for association in session.scalars(select(ContentSkill)).all()
			}

			skill_names_by_track = {
				"Python": {"Python", "Git", "Flask", "REST APIs"},
				"SQL": {"SQL"},
				"Machine Learning": {
					"Machine Learning",
					"Deep Learning",
					"Natural Language Processing",
					"Statistics",
					"Regression",
					"Classification",
					"Model Evaluation",
					"Clustering",
					"Feature Engineering",
				},
				"Data Analytics": {
					"Pandas",
					"NumPy",
					"Data Visualization",
					"Statistics",
					"Data Cleaning",
					"SQL",
				},
			}

			for user_index, user_name in enumerate(USER_NAMES):
				tracks = USER_GROUPS[user_index % len(USER_GROUPS)]
				user = users[user_name]
				if user.interests != list(tracks):
					user.interests = list(tracks)
				for skill_name in set().union(
					*(skill_names_by_track[track] for track in tracks)
				):
					skill_id = skills[skill_name].id
					key = (user.id, skill_id)
					if key not in user_skill_keys:
						session.add(
							UserSkill(
								user_id=user.id,
								skill_id=skill_id,
								proficiency=round(
									0.45 + ((user_index + skill_id) % 6) * 0.1,
									2,
								),
							)
						)
						user_skill_keys.add(key)

			for title, _, _, _, _, content_skill_names in CONTENT_DATA:
				content_id = content_by_title[title].id
				for skill_name in content_skill_names:
					skill_id = skills[skill_name].id
					key = (content_id, skill_id)
					if key not in content_skill_keys:
						session.add(
							ContentSkill(content_id=content_id, skill_id=skill_id)
						)
						content_skill_keys.add(key)

			session.flush()
			existing_interaction_keys = {
				(
					interaction.user_id,
					interaction.content_id,
					interaction.created_at.replace(tzinfo=timezone.utc),
				)
				for interaction in session.scalars(select(Interaction)).all()
			}
			topic_by_title = {
				title: track for title, track, *_ in CONTENT_DATA
			}
			base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
			for user_index, user_name in enumerate(USER_NAMES):
				tracks = USER_GROUPS[user_index % len(USER_GROUPS)]
				user = users[user_name]
				for content_index, (title, track, *_rest) in enumerate(CONTENT_DATA):
					if topic_by_title[title] not in tracks:
						continue
					content = content_by_title[title]
					created_at = base_time + timedelta(
						minutes=user_index * len(CONTENT_DATA) + content_index
					)
					key = (user.id, content.id, created_at)
					if key in existing_interaction_keys:
						continue

					interaction_type = ("view", "complete", "bookmark", "rate")
					kind = interaction_type[(user_index + content_index) % 4]
					session.add(
						Interaction(
							user_id=user.id,
							content_id=content.id,
							type=kind,
							rating=round(3.0 + ((user_index + content_index) % 3), 1)
							if kind == "rate"
							else None,
							created_at=created_at,
						)
					)
					existing_interaction_keys.add(key)

			session.commit()
		except Exception:
			session.rollback()
			raise

	with SessionLocal() as session:
		counts = {
			model.__tablename__: session.scalar(
				select(func.count()).select_from(model)
			)
			for model in (User, Content, Skill, UserSkill, ContentSkill, Interaction)
		}
	for table, count in counts.items():
		print(f"{table}: {count}")
	return counts


if __name__ == "__main__":
	seed_data()
