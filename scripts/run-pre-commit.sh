#!/usr/bin/env bash
set -euo pipefail

pre-commit run --config .pre-commit-config.yaml --all-files
pre-commit run --config docker/.pre-commit-config.yaml --all-files
pre-commit run --config deployments/.pre-commit-config.yaml --all-files

