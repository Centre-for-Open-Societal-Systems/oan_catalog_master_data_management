# SQL seed sources

These files are versioned input data, not database migrations. They populate a
compatibility staging schema whose table names match the inherited SQL. A later
publication step validates and copies that data into release-specific canonical
tables used by the Catalogue API.

The execution contract is declared in `manifest.yaml`. File order must never be
inferred alphabetically.

## Dataset ownership

| Source | Staged data | Canonical output |
| --- | --- | --- |
| `import_catalog_related.sql` | Crop categories and ecological zones | Supporting catalogues and typed crop relations |
| `import_crop_catalog.sql` | Crop details | `crop` catalogue |
| `import_crop_taxonomy.sql` | Categories, crop types, variety concepts, source records and relational characteristics | `crop_taxonomy_category`, `crop_type`, and `crop_variety` catalogues with typed relations |
| `import_livestock_data.sql` | Generated complete livestock species, population, breed, gender, location, body-condition, production, and status staging data | Expanded livestock catalogues, typed relations, and population statistics |
| `import_location_data.sql` | Regions, zones and woredas | Geography levels and units |
| `import_kebele_data.sql` | Reviewed supplemental zones and woredas, plus kebele source rows and parent-match decisions | Matched kebeles under canonical woredas; unresolved rows remain in staging for review |
| `import_seed_data.sql` | Seed types and demand facts | `seed_crop` catalogue and seed statistics |
| `import_seed_variety.sql` and `import_seed_variety_matches.sql` | 902 explicit Ethio-Seed variety listings and reviewed taxonomy matches | `seed_variety` catalogue, typed seed/crop relations, and canonical source records |

Do not run these files against a registry database. Do not expose the staging
tables through the public API. Database migrations must run first.

The SQL comes from an Odoo-shaped source but is executed only inside the
runner-owned transaction. The manifest orders supporting crop catalogues before
the crops that reference them. Unknown category or ecological-zone IDs fail
validation and preserve the previously active release.

The location source currently references three zone codes for which it carries
no zone rows. They are listed explicitly in the manifest. Those woredas are
published without a parent and with `metadata.data_quality=MISSING_PARENT`;
any additional orphan fails validation.

Region, zone, and woreda inserts may populate the nullable
`display_name_amh` column. Existing location SQL does not need to specify it;
the publisher exposes a null value until an Amharic name is provided.

## Regenerate the kebele SQL

`import_kebele_data.sql` is deterministically generated from `KebeleList.csv`,
cross-checked against `woreda_data.csv`, and must not be edited by hand:

```bash
python3 scripts/kebele/generate_seed_sql.py \
  KebeleList.csv \
  woreda_data.csv \
  scripts/seed_db_sql/import_location_data.sql \
  scripts/seed_db_sql/import_kebele_data.sql \
  --review-output scripts/kebele/review/kebele_parent_matches.csv

python3 scripts/kebele/generate_seed_sql.py \
  KebeleList.csv \
  woreda_data.csv \
  scripts/seed_db_sql/import_location_data.sql \
  scripts/seed_db_sql/import_kebele_data.sql \
  --review-output scripts/kebele/review/kebele_parent_matches.csv \
  --check
```

Woreda codes are normalized to `ET` plus six digits. Exact existing parents are
preferred. Missing parents are imported from the reference only when both the
normalized woreda code and source zone agree. The reviewed `woreda=e` anomaly
resolves to `ET041405`, and Doyogena resolves to the existing `ET070306` parent.
The generated review CSV records every decision. Only rows with a `MATCHED`
status are published; unresolved kebeles remain in `g2p_kebele` for correction
without creating unsafe hierarchy links.

## Regenerate the crop taxonomy SQL

`import_crop_taxonomy.sql` is generated from the reviewed workbook and must not
be edited by hand:

```bash
python3 scripts/crop_taxonomy/generate_seed_sql.py \
  crop_catalog_variety_included.xlsx \
  scripts/seed_db_sql/import_crop_taxonomy.sql
```

CI or reviewers can verify that the checked-in SQL matches the workbook:

```bash
python3 scripts/crop_taxonomy/generate_seed_sql.py \
  crop_catalog_variety_included.xlsx \
  scripts/seed_db_sql/import_crop_taxonomy.sql \
  --check
```

The manifest requires exact row counts for all six taxonomy tables and allows
only the reviewed `fine-bush` crop type to have no source `cropTypeId`.

## Regenerate the Ethio-Seed variety SQL

`import_seed_variety.sql` is adapted from the reviewed archived SQL without
executing its destructive table-creation script:

```bash
python3 scripts/seed_variety/generate_seed_sql.py \
  crop_catalog_scripts/05_insert_crop_variety.sql \
  scripts/seed_db_sql/import_seed_variety.sql
```

Add `--check` to verify that the committed generated SQL is current. Matching
is applied by the separately generated `import_seed_variety_matches.sql`.
Only crop-scoped exact names are accepted automatically; unresolved rows and
source-ID disagreements are retained in the review artifacts under
`scripts/seed_variety/review/`.

Publication creates one stable `seed_variety` value for every source listing.
All 902 values relate to their `seed_crop`; the 309 reviewed matches also relate
to the canonical `crop_variety`, `crop_type`, and `crop_taxonomy_category`.
Unresolved listings remain available without an inferred crop-taxonomy link.

## Regenerate the complete livestock SQL

`import_livestock_data.sql` is generated from the reviewed data-only SQL in
`livestock_catalog/`. The destructive table-creation source and `run_all.sql`
are never executed by the Catalogue Service:

```bash
python3 scripts/livestock/generate_seed_sql.py \
  livestock_catalog \
  scripts/seed_db_sql/import_livestock_data.sql \
  --review-output scripts/livestock/review/livestock_registry_validation.csv \
  --report-output scripts/livestock/review/livestock_transform_report.json
```

Add `--check` to fail if any generated artifact has drifted. The 12 ET-LITS
registry rows are written only to the validation review; they are operational
source records and are not inserted as catalogue values. The manifest enforces
exact table counts and reviewed exceptions before canonical publication.
