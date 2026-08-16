#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${project_root}"

legacy_build_and_start() {
  echo "Compose Buildx execution failed; using the legacy image builder."
  DOCKER_BUILDKIT=0 docker build \
    -f docker/db-migration/Dockerfile \
    -t openg2p-catalogue-migrate:local .
  DOCKER_BUILDKIT=0 docker build \
    -f docker/db-seed/Dockerfile.sql \
    -t openg2p-catalogue-seed:local .
  DOCKER_BUILDKIT=0 docker build \
    -f docker/catalogue-api/Dockerfile \
    -t openg2p-catalogue-api:local .
  docker compose up --no-build --wait
}

if [[ "${CATALOGUE_LEGACY_BUILD:-}" == "true" ]]; then
  legacy_build_and_start
elif ! docker compose up --build --wait; then
  legacy_build_and_start
fi

"${project_root}/scripts/local-smoke-test.sh"
