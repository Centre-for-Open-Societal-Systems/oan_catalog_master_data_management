#!/usr/bin/env bash
set -euo pipefail

if [[ "${CONFIRM_CATALOGUE_RESTORE:-}" != "RESTORE" ]]; then
  echo "Set CONFIRM_CATALOGUE_RESTORE=RESTORE to acknowledge replacement of database objects" >&2
  exit 2
fi

backup_file="${BACKUP_FILE:?BACKUP_FILE is required}"
test -f "${backup_file}"
pg_restore --list "${backup_file}" >/dev/null
pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  --exit-on-error \
  --dbname="${CATALOGUE_DATABASE_URL:?CATALOGUE_DATABASE_URL is required}" \
  "${backup_file}"

echo "Catalogue database restored from ${backup_file}; run migration verification before starting the API"
