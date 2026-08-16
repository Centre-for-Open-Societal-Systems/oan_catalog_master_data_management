FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install --no-cache-dir psycopg2-binary

COPY docker/db-migration/migrate_database.py /migration/migrate_database.py
COPY scripts/migrations /migration/sql
RUN chmod +x /migration/migrate_database.py

WORKDIR /migration
USER 10001:10001
ENTRYPOINT ["python", "/migration/migrate_database.py"]
