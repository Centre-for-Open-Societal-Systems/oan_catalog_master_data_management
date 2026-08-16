#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
image=""
version=""
push_image="false"
push_latest="false"

usage() {
  cat <<'EOF'
Usage: scripts/publish-unified-image.sh --image REPOSITORY --version X.Y.Z [--push] [--latest]

Builds the unified API, migration, and SQL seed image. --push publishes the
immutable version tag. --latest additionally publishes the latest tag and is
valid only together with --push.
EOF
}

while (($#)); do
  case "$1" in
    --image)
      image="${2:-}"
      shift 2
      ;;
    --version)
      version="${2:-}"
      shift 2
      ;;
    --push)
      push_image="true"
      shift
      ;;
    --latest)
      push_latest="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${image}" || -z "${version}" ]]; then
  usage >&2
  exit 2
fi
if [[ ! "${version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]]; then
  echo "Invalid semantic version: ${version}" >&2
  exit 2
fi
if [[ "${image}" == *:* ]]; then
  echo "--image must not include a tag: ${image}" >&2
  exit 2
fi
if [[ "${push_latest}" == "true" && "${push_image}" != "true" ]]; then
  echo "--latest requires --push" >&2
  exit 2
fi

cd "${project_root}"
python_command="python3"
if [[ -x "${project_root}/.venv/bin/python" ]]; then
  python_command="${project_root}/.venv/bin/python"
fi
"${python_command}" scripts/check-release-version.py --expected "${version}"

versioned_image="${image}:${version}"
vcs_ref="$(git rev-parse --verify HEAD 2>/dev/null || printf 'unknown')"
build_args=(
  --build-arg "CATALOGUE_VERSION=${version}"
  --build-arg "VCS_REF=${vcs_ref}"
  --tag "${versioned_image}"
  .
)

if docker buildx version >/dev/null 2>&1; then
  docker build "${build_args[@]}"
else
  echo "Docker Buildx is unavailable; using the legacy builder."
  DOCKER_BUILDKIT=0 docker build "${build_args[@]}"
fi

docker image inspect "${versioned_image}" >/dev/null
echo "Built ${versioned_image}"

if [[ "${push_image}" == "true" ]]; then
  docker push "${versioned_image}"
  echo "Pushed ${versioned_image}"
fi
if [[ "${push_latest}" == "true" ]]; then
  latest_image="${image}:latest"
  docker tag "${versioned_image}" "${latest_image}"
  docker push "${latest_image}"
  echo "Pushed ${latest_image}"
fi
