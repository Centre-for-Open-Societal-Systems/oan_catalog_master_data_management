#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${BACKUP_FILE:-}" ]]; then
  echo "BACKUP_FILE must be an explicit output path" >&2
  exit 2
fi

umask 077
pg_dump \
  --format=custom \
  --no-owner \
  --no-acl \
  --file="${BACKUP_FILE}" \
  "${CATALOGUE_DATABASE_URL:?CATALOGUE_DATABASE_URL is required}"

pg_restore --list "${BACKUP_FILE}" >/dev/null
echo "Verified catalogue backup written to ${BACKUP_FILE}"
