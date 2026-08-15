# Integration tests

The integration suite recreates a disposable PostgreSQL `public` schema,
publishes the SQL sources, and verifies both publication and the registry read
API. It also verifies incremental migrations, advisory locks, rollback and
checksum failures, ORM/schema parity, OpenAPI parameters, release upgrades,
historical release pinning, and failed-publication recovery. Never point
`CATALOGUE_TEST_DB_DSN` at a persistent database.

```bash
CATALOGUE_TEST_DB_DSN=postgresql://postgres:password@localhost:55432/catalogue_test \
  .venv/bin/python -m pytest -q tests/integration
```

The suite is intentionally sequential because its tests recreate the same
schema. CI waits up to 60 seconds for PostgreSQL and applies a 60-second timeout
to every test so infrastructure failures cannot leave a job hanging forever.

The SQL publication test requires a disposable PostgreSQL database. It drops
and recreates that database's `public` schema.

```bash
CATALOGUE_TEST_DB_DSN=postgresql://catalogue:password@localhost/catalogue_test \
  pytest -q tests/integration/test_sql_seed_publication.py
```
