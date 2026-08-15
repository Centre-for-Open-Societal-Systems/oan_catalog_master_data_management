FROM python:3.12-slim

ARG CATALOGUE_DATA_REPO=https://github.com/OpenG2P/openg2p-data.git
ARG CATALOGUE_DATA_REF=develop

ENV CATALOGUE_DATA_DIR=/catalogue-data \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir psycopg2-binary PyYAML

RUN mkdir -p ${CATALOGUE_DATA_DIR} \
    && cd ${CATALOGUE_DATA_DIR} \
    && git init -q \
    && git remote add origin ${CATALOGUE_DATA_REPO} \
    && git fetch -q --depth 1 origin ${CATALOGUE_DATA_REF} \
    && git checkout -q FETCH_HEAD \
    && rm -rf ${CATALOGUE_DATA_DIR}/.git

COPY docker/db-seed/seed_catalogue_pack.py /seed/seed_catalogue_pack.py
COPY docker/db-seed/run_sql_seeds.py /seed/run_sql_seeds.py
COPY scripts/seed_db_sql /seed/sql
RUN chmod +x /seed/seed_catalogue_pack.py /seed/run_sql_seeds.py
WORKDIR /seed
USER 10001:10001
