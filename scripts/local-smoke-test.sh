#!/usr/bin/env bash
set -euo pipefail

base_url="${CATALOGUE_URL:-http://localhost:8000}"

ready=false
for _attempt in $(seq 1 30); do
  if curl --fail --silent "${base_url}/health/ready" >/dev/null; then
    ready=true
    break
  fi
  sleep 1
done
if [[ "${ready}" != "true" ]]; then
  echo "Catalogue Service did not become ready at ${base_url}" >&2
  exit 1
fi

curl --fail --silent --show-error "${base_url}/health/live" >/dev/null
curl --fail --silent --show-error "${base_url}/v1/releases/current?country_code=ETH" >/dev/null
curl --fail --silent --show-error "${base_url}/v1/catalogues?country_code=ETH" >/dev/null
curl --fail --silent --show-error "${base_url}/v1/snapshots/current?country_code=ETH" >/dev/null

echo "Catalogue Service local smoke test passed: ${base_url}"
