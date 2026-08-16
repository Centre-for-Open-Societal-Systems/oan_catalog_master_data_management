# OpenG2P Catalogue Service

Standalone service for publishing versioned catalogue/reference values to
OpenG2P registries and other platform services.

This repository follows the same monorepo layout as `master-data-service`:

| Area | Purpose |
| --- | --- |
| `catalogue-api/` | Python/FastAPI application |
| `catalogue-client/` | Standalone async client for registry services |
| `docker/catalogue-api/` | API container image |
| `docker/db-seed/` | Catalogue-pack validation and publication image |
| `deployments/charts/openg2p-catalogue/` | Helm chart |
| `scripts/migrations/` | PostgreSQL migrations |
| `examples/` | Consumer integration examples |
| `tests/` | Unit and integration tests |

## Runtime components

The deployment owns one PostgreSQL database and runs three components:

1. A dedicated, advisory-locked migration Job applies ordered SQL migrations.
2. A seed Job validates and atomically publishes an immutable catalogue release.
3. The API serves the active release to registries.

Registries must consume the API; they must not connect directly to this
service's database.

See [the data-model guide](docs/data-model.md) for the canonical, staging, and
import-audit boundaries used by SQL seeding.

The service uses default-deny IAM authorization and hardened Kubernetes
workloads. Registry service-account setup, permissions and network controls are
documented in [the security guide](docs/security.md).

Production health checks, Prometheus metrics, alert rules, structured request
context, and incident procedures are documented in the
[operations guide](docs/operations.md).

Schema migration is not performed by API replicas. Applied versions and
checksums are recorded in `catalogue_schema_migrations`; API and publisher pods
verify the expected schema before starting. See the
[migration guide](scripts/migrations/README.md) for the upgrade contract.

## SQL publication

The SQL runner reads `scripts/seed_db_sql/manifest.yaml`, locks against
concurrent imports, refreshes staging tables, validates the datasets, and
publishes one immutable release in the same transaction. Re-running unchanged
content records a skipped import instead of rewriting the active release.

```bash
python docker/db-seed/run_sql_seeds.py \
  --manifest scripts/seed_db_sql/manifest.yaml \
  --expected-country ETH \
  --validate-only
```

Helm runs this publisher after installation and upgrades. A checksum-aware
CronJob also reconciles it daily by default.

Registry services can retrieve a complete, release-consistent projection from:

```http
GET /v1/snapshots/current
```

The read API also offers filtered, paginated catalogue, geography, livestock,
and seed-demand endpoints. Consumers can pin `release_version` and use the
release checksum as an `If-None-Match` ETag for inexpensive scheduled polling.
Crop values include typed relations to independently queryable
`crop_category` and `ecological_zone` catalogues.
See [the registry read API](docs/read-api.md) for the endpoint contract and
recommended synchronization behavior.

Platform forms can use the compact `GET /v1/catalogue-values` operation for
live category → crop → variety dropdowns. See the
[widget integration guide](docs/widget-integration.md) for service discovery,
IAM, cascading parameters, caching, and the opt-in-only synchronization rule.

Frontend teams should use the
[frontend catalogue and API guide](docs/frontend-catalogue-guide.md) for the
complete endpoint and field inventory, recommended table columns, detail-page
layouts, status/error handling, and UI implementation order.

A standalone async consumer package is available under `catalogue-client/`.
It implements client-credentials authentication, typed snapshot validation,
conditional polling, and bounded retries. See the
[registry integration guide](docs/registry-integration.md) for the safe local
commit and sync-state contract.

## Local package

## Run locally with Docker Compose

The local profile starts PostgreSQL, applies migrations, publishes all five SQL
sources, and starts the API:

```bash
cp .env.example .env
scripts/local-up.sh
```

The launcher uses Compose/Buildx when available and automatically falls back to
Docker's legacy builder on older or minimal Engine installations.

Useful URLs:

- API documentation: <http://localhost:8000/docs>
- readiness: <http://localhost:8000/health/ready>
- current release: <http://localhost:8000/v1/releases/current?country_code=ETH>
- full snapshot: <http://localhost:8000/v1/snapshots/current?country_code=ETH>

Compose intentionally runs `openg2p_catalogue_service.dev_main`, which is
unauthenticated and refuses to start without `CATALOGUE_API_DEV_MODE=true`.
Never deploy that entry point. Kubernetes and the production image default use
the IAM-protected `main` entry point.

Stop containers while retaining PostgreSQL data with `docker compose down`.
For a clean local rebuild, explicitly remove the project volumes:

```bash
docker compose down --volumes
```

## Run the prebuilt unified release image

The development `compose.yaml` builds the separate lifecycle images from source.
For simple distribution, the root `Dockerfile` packages the API, migrations,
and complete SQL seed release into one image. Compose runs that same image as
three containers with different commands while PostgreSQL remains separate.
After publishing the unified image, consumers can run it without cloning the
build toolchain by using `compose.consumer.yaml`:

```bash
cp .env.consumer.example .env.consumer
# Set CATALOGUE_IMAGE and CATALOGUE_IMAGE_TAG to the published Docker image.
docker compose --env-file .env.consumer -f compose.consumer.yaml pull
docker compose --env-file .env.consumer -f compose.consumer.yaml up -d
```

Build and publish the unified Docker Hub image from the repository root:

```bash
scripts/publish-unified-image.sh \
  --image docker.io/rediet03/mdm \
  --version 0.2.0 \
  --push
```

Add `--latest` only when this release should also become
`docker.io/rediet03/mdm:latest`. The script checks that the API package,
client, and Helm chart all use the requested version before building. It
pushes the immutable `0.2.0` tag first and never updates `latest` implicitly.

This starts PostgreSQL, runs schema migration `014`, publishes the SQL release,
and exposes Swagger on <http://localhost:8000/docs>. This consumer profile uses
the deliberately unauthenticated development entry point for local evaluation.
Production environments must use the Helm chart and IAM-protected entry point.

Stop it while retaining its database with:

```bash
docker compose --env-file .env.consumer -f compose.consumer.yaml down
```

## Local Python package

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e catalogue-api
```

Configuration uses the `CATALOGUE_API_` environment-variable prefix.

## Validate the crop taxonomy workbook

Generate reviewable relational CSVs without changing the database:

```bash
python3 scripts/crop_taxonomy/transform_workbook.py \
  crop_catalog_variety_included.xlsx \
  --output-dir /tmp/crop-taxonomy
```

The command fails on structural errors. Add `--strict` when source-quality
warnings should also produce a non-zero exit status. Loading and canonical API
publication are handled by the SQL seed runner.

After publication, Swagger can query the consolidated hierarchy through the generic
`GET /v1/catalogues/{catalogue_code}/values` operation using catalogue codes
`crop_category`, `crop`, and `crop_variety`. Relation filters select crops by
SQL category and varieties directly by crop. The workbook-only
`crop_taxonomy_category` and compatibility `crop_type` catalogues remain
available for taxonomy-specific consumers.

The dedicated `GET /v1/crop-varieties/{variety_code}` operation returns the
crop type, category, source records, common typed ranges, and complete
relational characteristic values for one variety.

Seed varieties are available in Swagger through `GET /v1/seed-varieties` and
`GET /v1/seed-varieties/{seed_variety_code}`. The list supports seed-crop,
crop-variety, crop-type, taxonomy-category, match-status, release-year, and
text-search filters while retaining unresolved source listings.

Run the independently packaged client against the complete local Docker stack:

```bash
docker compose --profile smoke up --build --abort-on-container-exit \
  --exit-code-from consumer-smoke consumer-smoke
```

The smoke container acquires a development token, reads Melkassa 1Q and seed
varieties through the typed client, validates matched and unresolved taxonomy
behavior, and confirms ETag-based `304` reads for both detail APIs. The mock IAM
service is profile-scoped and must never be used outside local or CI
verification.

## Production installation

Copy and edit
[`values-production.example.yaml`](deployments/charts/openg2p-catalogue/values-production.example.yaml),
then install a tagged OCI chart:

```bash
helm upgrade --install catalogue \
  oci://ghcr.io/YOUR_ORGANIZATION/charts/openg2p-catalogue \
  --version 0.2.0 \
  --namespace catalogue \
  --create-namespace \
  --values values-production.yaml
```

See [the release and production-readiness guide](docs/releasing.md) for
artifact publication, promotion, backup, restore, rollback, and performance
acceptance.
