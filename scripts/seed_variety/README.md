# Ethio-Seed variety adapter

The authoritative archived SQL in `crop_catalog_scripts`
uses standalone table names and destructive DDL. The adapter preserves the 902
variety tuples but targets the migration-owned staging schema with an
idempotent upsert:

```bash
python3 scripts/seed_variety/generate_seed_sql.py \
  crop_catalog_scripts/05_insert_crop_variety.sql \
  scripts/seed_db_sql/import_seed_variety.sql
```

Use `--check` in review or CI to detect source/generated drift. The adapter
does not infer crop-variety matches; Phase 3 owns that separate, auditable step.

Generate the conservative crop-scoped match decisions and review artifacts:

```bash
python3 scripts/seed_variety/match_seed_varieties.py \
  crop_catalog_scripts/05_insert_crop_variety.sql \
  crop_catalog_variety_included.xlsx \
  scripts/seed_db_sql/import_seed_variety_matches.sql \
  scripts/seed_variety/review/seed_variety_match_review.csv \
  scripts/seed_variety/review/seed_variety_match_report.json
```

Numeric IDs from the archived list and workbook are not assumed to share an
identity namespace. A source-ID match is accepted only when the crop type and
normalized variety name also agree. Add `--check` to verify all three outputs.
