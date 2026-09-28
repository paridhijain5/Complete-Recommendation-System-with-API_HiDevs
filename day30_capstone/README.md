# Day 30 Recommendation System

A small learning-content recommendation service built with Python, Flask,
SQLAlchemy, and SQLite. It combines collaborative, skill-based, popularity, and
cold-start interest signals, and includes offline ranking evaluation and a
threaded API load-test script.

## Setup

Run these commands from the repository root. Python 3.10 or newer is
recommended.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r day30_capstone/requirements.txt
export DATABASE_URL="sqlite:///day30_capstone/recommendation.db"
python day30_capstone/scripts/seed_data.py
```

The seed script is safe to rerun. It creates sample learners, learning content,
skills, and interactions in the configured SQLite database.

Start the API:

```sh
flask --app day30_capstone.api.app:app run --host 127.0.0.1 --port 5000
```

Check that it is responding:

```sh
curl http://127.0.0.1:5000/health
```

Run tests and generate an evaluation report:

```sh
python -m unittest discover -s day30_capstone/tests -v
python day30_capstone/scripts/evaluate.py
```

Evaluation artifacts are saved in `day30_capstone/reports/`. To run the load
test, keep the API running in another terminal:

```sh
python day30_capstone/scripts/load_test.py \
	--base-url http://127.0.0.1:5000 \
	--requests-per-user 5
```

By default, the load test starts 10 threads (one per simulated user) and sends
five requests from each thread. The user IDs and request count can be changed
with `--user-ids` and `--requests-per-user`.

## Web Interface

Open `http://127.0.0.1:5000/` to use the recommendation dashboard. Enter a user
ID, choose a result count, and load recommendations. Save or complete a
recommendation to send feedback; the list refreshes after the feedback is
recorded. Health and API metrics are shown in the dashboard.

## API

The API endpoints return JSON. The dashboard at `/` returns HTML. Every response
includes a unique `X-Request-ID` header. API error responses use an `error`
field; malformed inputs return `400`, and unknown users or content return
`404`.

### `GET /health`

Returns a basic process health response.

```sh
curl -i http://127.0.0.1:5000/health
```

Example response:

```json
{"status":"ok"}
```

### `GET /recommend/<user_id>`

Returns ranked recommendations, with a score and brief reason for each item.
The optional `limit` query parameter defaults to 10 and must be a positive
integer. New users without interaction history receive popularity- and
interest-based recommendations.

```sh
curl -i "http://127.0.0.1:5000/recommend/1?limit=5"
```

Example response:

```json
{
	"user_id": 1,
	"recommendations": [
		{
			"id": 12,
			"title": "Joining Relational Tables",
			"category": "SQL",
			"difficulty": "beginner",
			"popularity": 84.0,
			"score": 0.82,
			"explanation": "Matches your interests: SQL, Data Analytics"
		}
	]
}
```

### `POST /feedback`

Records an interaction and invalidates cached recommendations. `user_id`,
`content_id`, and non-empty `type` are required. `rating` is optional and, when
provided, must be between 1 and 5.

```sh
curl -i -X POST http://127.0.0.1:5000/feedback \
	-H 'Content-Type: application/json' \
	-d '{"user_id":1,"content_id":12,"type":"complete","rating":5}'
```

Successful requests return `201 Created` with the recorded interaction.

### `GET /metrics`

Returns process-local `request_count`, `average_latency_ms`, and
`cache_hit_rate`. The cache hit rate is a fraction from 0 to 1 and covers
recommendation requests. Metrics endpoint scrapes are excluded from the request
count and latency average.

```sh
curl http://127.0.0.1:5000/metrics
```

## Architecture

- `data/` contains SQLAlchemy models, SQLite session configuration, and table
	repositories.
- `engine/` provides cosine similarity, collaborative/content/popularity
	candidate generation, score combination, ranking metrics, and the
	recommendation orchestrator.
- `api/` exposes recommendations, feedback, health, and process-local metrics
	through Flask.
- `scripts/seed_data.py` creates repeatable sample data.
- `scripts/evaluate.py` holds out interactions per user, evaluates against a
	training-only in-memory database, and writes a CSV table and PNG chart.
- `scripts/load_test.py` sends synchronized HTTP requests from concurrent
	threads.
- `tests/` contains unit and API tests.

The recommendation flow is: API request -> orchestrator -> candidate
strategies -> weighted ranking -> content records with explanations. Feedback
is persisted as an interaction and clears the API's in-memory recommendation
cache. The SQLite database is selected with the `DATABASE_URL` environment
variable; the default when running from the repository root is
`recommendation.db` in the current working directory.

## Evaluation Results

The checked-in sample report was generated from the seeded SQLite data using a
deterministic 80/20 per-user interaction split (seed 42). Scores are macro
averages across 20 users:

| Metric | Result |
| --- | ---: |
| Precision@5 | 0.0400 |
| Recall@5 | 0.0667 |
| NDCG@5 | 0.0437 |

Detailed per-user values and the mean row are in
[`reports/evaluation_results.csv`](reports/evaluation_results.csv); the chart
is [`reports/evaluation_metrics.png`](reports/evaluation_metrics.png). Rerun
`python day30_capstone/scripts/evaluate.py` to regenerate them from the current
database.

## Docker

Build and run from the repository root:

```sh
docker build -f day30_capstone/Dockerfile -t day30-capstone .
docker run --rm -p 5000:5000 \
	-v recommendation-data:/data \
	day30-capstone
```

The container uses `/data/recommendation.db` in the named volume, seeds that
database on startup, and serves the API on port 5000. The image uses one Gunicorn
worker with multiple threads so its in-memory cache and metrics are shared among
requests handled by that process. The included sample API is intended for a
capstone/demo deployment; production deployments should add environment-specific
configuration, monitoring, and operational security controls.
