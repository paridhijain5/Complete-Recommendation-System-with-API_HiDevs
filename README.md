# Complete Recommendation System with API

A learning-content recommendation capstone built with Python, Flask,
SQLAlchemy, and SQLite. The system combines collaborative filtering,
skill-based matching, popularity, and cold-start interests, with a responsive
web dashboard and JSON API.

## Run with Docker

```sh
docker build -f day30_capstone/Dockerfile -t day30-capstone .
docker run --rm -p 5000:5000 -v recommendation-data:/data day30-capstone
```

Open [http://localhost:5000](http://localhost:5000) for the dashboard. The
container seeds the database on startup and persists it in the named Docker
volume. The health endpoint is available at
[http://localhost:5000/health](http://localhost:5000/health).

## Run Locally

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r day30_capstone/requirements.txt
export DATABASE_URL="sqlite:///day30_capstone/recommendation.db"
python day30_capstone/scripts/seed_data.py
flask --app day30_capstone.api.app:app run --host 127.0.0.1 --port 5000
```

Run the tests with:

```sh
python -m unittest discover -s day30_capstone/tests -v
```

## Project Guide

See the [capstone README](day30_capstone/README.md) for API documentation and
curl examples, architecture, evaluation instructions and results, and the
threaded load-test command.

Sample evaluation outputs:

- [Results table](day30_capstone/reports/evaluation_results.csv)
- [Metrics chart](day30_capstone/reports/evaluation_metrics.png)
