FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/recommendation.db

WORKDIR /app

COPY day30_capstone/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip install --no-cache-dir 'gunicorn>=22,<24'

COPY day30_capstone/api ./day30_capstone/api
COPY day30_capstone/data ./day30_capstone/data
COPY day30_capstone/engine ./day30_capstone/engine
COPY day30_capstone/scripts ./day30_capstone/scripts

RUN mkdir -p /data \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app /data

USER appuser

VOLUME ["/data"]
EXPOSE 5000

CMD ["sh", "-c", "python -m day30_capstone.scripts.seed_data && exec gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 8 day30_capstone.api.app:app"]