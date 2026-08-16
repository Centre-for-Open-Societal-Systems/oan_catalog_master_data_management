# Database migrations

This directory is the only source of truth for the Catalogue Service database
schema. The API models describe the schema to SQLAlchemy but do not create or
alter tables at runtime.

## Adding a migration

1. Add the next ordered file using `NNN_short_description.sql`.
2. Wrap the file in one outer `BEGIN;` and `COMMIT;`. The runner removes that
   wrapper and owns the actual transaction so the schema change and history
   record commit together.
3. Make forward changes only. Never edit, rename, or delete an applied file.
4. Update `schemaMigration.expectedVersion` in the Helm values.
5. Test both a clean installation and an upgrade from the previous version.

Migration `007` creates the relational staging contract for crop categories,
types, varieties, source records, and typed characteristics. It does not load
the workbook or alter the current canonical crop release.

Migration `008` adds release-scoped canonical source records, characteristic
definitions, and characteristic values for the crop-variety detail API.

Migration `009` adds Ethio-Seed variety source records, optional normalized
crop-variety matches, and their release-scoped canonical publication contract.

Migration `010` adds kebele staging records, normalized woreda parent links,
explicit match provenance, and unresolved-row review state.

Migration `011` extends livestock species staging and adds relational staging
contracts for breeds, genders, location types, body conditions, production
types and their valid species, and ET-LITS record statuses.

Migration `012` adds the source ET-LITS registry snapshot, its validation view,
and the release-scoped canonical registry table and view used by the read API.

Migration `013` enriches the consolidated SQL crop catalogue with typed
workbook provenance and a crop-variety count computed from SQL source rows.

Migration `014` adds explicit SQL crop foreign keys to variety source records,
release-scoped consolidated crop and variety references, and crop category
provenance used by the SQL-first category-to-crop-to-variety hierarchy.

Each successful migration is recorded in `catalogue_schema_migrations` with
its filename, SHA-256 checksum, application timestamp, duration, and runner
version. A checksum or ordering mismatch stops deployment.

The runner uses a PostgreSQL advisory lock, so only one migration process can
operate on a database at a time. Every file has its own transaction: earlier
successful versions remain committed if a later version fails, while all work
from the failing file is rolled back.

## Local commands

```bash
python docker/db-migration/migrate_database.py \
  --migrations scripts/migrations \
  --expected-version 014

python docker/db-migration/migrate_database.py \
  --migrations scripts/migrations \
  --expected-version 014 \
  --verify-only
```

Connection settings use standard `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`,
and `PGPASSWORD` variables. `CATALOGUE_DB` remains accepted as a database-name
fallback for consistency with the seed image.
