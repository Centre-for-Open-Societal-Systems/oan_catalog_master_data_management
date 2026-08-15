FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install --no-cache-dir psycopg2-binary PyYAML

COPY docker/db-seed/run_sql_seeds.py /seed/run_sql_seeds.py
COPY scripts/seed_db_sql /seed/sql
RUN chmod +x /seed/run_sql_seeds.py

WORKDIR /seed
USER 10001:10001
ENTRYPOINT ["python", "/seed/run_sql_seeds.py"]
