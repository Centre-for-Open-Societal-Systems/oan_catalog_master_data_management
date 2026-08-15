#!/usr/bin/env bash
set -euo pipefail

RELEASE="catalogue"
NAMESPACE=""
DROP_DATABASE=false

usage() {
  echo "Usage: $0 --namespace <namespace> [--release <release>] [--drop-database]"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --namespace|-n) NAMESPACE="$2"; shift 2 ;;
    --release) RELEASE="$2"; shift 2 ;;
    --drop-database) DROP_DATABASE=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1"; usage; exit 1 ;;
  esac
done

if [[ -z "$NAMESPACE" ]]; then
  echo "--namespace is required"
  exit 1
fi

helm uninstall "$RELEASE" --namespace "$NAMESPACE"

if [[ "$DROP_DATABASE" == true ]]; then
  echo "The Helm release was removed. Drop the catalogue database and role through the platform's"
  echo "PostgreSQL administration process; this script does not infer destructive database targets."
fi
