# Releasing and production readiness

## Version contract

One semantic version identifies the API package, registry client, Helm chart,
and all three images. Before tagging, update:

- `catalogue-api/src/openg2p_catalogue_service/__init__.py`;
- `catalogue-client/pyproject.toml`;
- Helm `version` and `appVersion`; and
- `CHANGELOG.md`.

Validate alignment with:

```bash
python scripts/check-release-version.py --expected 0.2.0
```

Before tagging, build and validate the standalone client artifact and run the
containerized consumer acceptance check:

```bash
python -m build catalogue-client --outdir dist/client
twine check dist/client/*
docker compose --profile smoke up --build --abort-on-container-exit \
  --exit-code-from consumer-smoke consumer-smoke
```

A `vX.Y.Z` GitHub tag runs tests, publishes versioned images to GHCR, builds
and publishes the Python client to PyPI, pushes the Helm chart as OCI, generates
SPDX SBOMs, scans images for high/critical vulnerabilities, and creates the
GitHub release. Configure a PyPI trusted publisher for this repository before
the first tag. Protected environments may be added to require approval.

The published `catalogue-db-seed` artifact uses `Dockerfile.sql`, matching the
SQL publisher used by the local and consumer Compose profiles. Its entry point
is `run_sql_seeds.py`, so Docker Compose supplies only publisher arguments.

The root `Dockerfile` is the unified consumer artifact. It contains the API,
ordered migrations, seed runner, manifest, and complete SQL release. Consumer
Compose starts that image with explicit migration, seed, and API commands.
PostgreSQL is deliberately not embedded in the image.
The unified and API Dockerfiles pin their external Git dependencies to exact
commits; update those pins deliberately as part of a future version review.

Build the unified image locally without publishing it:

```bash
scripts/publish-unified-image.sh \
  --image docker.io/rediet03/mdm \
  --version 0.2.0
```

After `docker login`, build and push the immutable Docker Hub tag in one
command by adding `--push`. Add `--latest` only when deliberately promoting
this release as the default pull target. Consumers should pin `0.2.0` in
`.env.consumer`; production deployment should pin an image digest.

## Promotion

Promote immutable versions through development, staging, and production by
changing only image/chart versions and environment values. Never deploy branch
tags such as `develop` to production. Record chart version, image digests,
country release, schema version, and backup identifier in the change ticket.

## Upgrade checklist

1. Review migrations and confirm they are forward-compatible with the currently running API.
2. Back up PostgreSQL and verify the custom archive with `pg_restore --list`.
3. Deploy to staging using production-sized data and run API/client acceptance tests.
4. Run the load test and confirm latency, error rate, memory, and connection-pool limits.
5. Confirm IAM permissions, NetworkPolicies, probes, alerts, and dashboards.
6. Deploy the immutable Helm chart; migrations run before API readiness and SQL publication is atomic.
7. Confirm schema `014`, active release, registry syncs, and monitoring before closing the change.

## Rollback

Application images may be rolled back only when the older application supports
the already-applied database schema. SQL migrations are forward-only and are
not automatically reversed. Catalogue releases themselves are immutable; a
corrected source must use a new version rather than modifying an existing one.

If an upgrade introduced an incompatible schema, stop publishers and API
traffic, restore the pre-upgrade backup into a replacement database, verify its
migration history, point the prior Helm release to that database, and then
resume traffic. Practice this procedure outside production.

## Backup and restore

Use platform-managed encrypted PostgreSQL backups in production. The helper
scripts provide a portable manual procedure:

```bash
CATALOGUE_DATABASE_URL='postgresql://user:pass@host/catalogue' \
BACKUP_FILE=/secure/catalogue-0.2.0.dump \
scripts/backup-database.sh
```

Restore is intentionally confirmation-gated and replaces database objects:

```bash
CATALOGUE_DATABASE_URL='postgresql://user:pass@replacement/catalogue' \
BACKUP_FILE=/secure/catalogue-0.2.0.dump \
CONFIRM_CATALOGUE_RESTORE=RESTORE \
scripts/restore-database.sh
```

After restore, run the migration runner in `--verify-only` mode and compare the
active release checksum before directing API traffic to the database.

## Performance acceptance

Run `tests/load/snapshot.js` with k6 against the development entry point or a
real IAM token in shared environments:

```bash
k6 run -e CATALOGUE_URL=http://localhost:8000 -e VUS=10 -e DURATION=60s \
  tests/load/snapshot.js
```

The default gate requires fewer than 1% failed requests and snapshot polling
p95 below one second. Tune API replicas, worker count, memory, and PostgreSQL
pool capacity together; do not scale workers without accounting for database
connections.
