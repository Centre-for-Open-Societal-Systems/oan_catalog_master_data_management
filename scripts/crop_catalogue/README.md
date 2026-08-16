# Crop catalogue reconciliation

The five SQL files in `crop_catalog_scripts/` are the source contract for the
legacy crop catalogue. The workbook supplies a finer crop taxonomy, but it is
not allowed to silently overwrite a category supplied by those SQL files.

Regenerate the review artifacts with:

```bash
PYTHONPATH=. python scripts/crop_catalogue/review_crop_categories.py \
  crop_catalog_scripts crop_catalog_variety_included.xlsx \
  --output-dir scripts/crop_catalogue/review
```

`crop_category_review.csv` contains one row per source crop. `ALIGNED` means
the two sources agree, `CATEGORY_MISSING` means the source SQL category is
NULL, `DIVERGENT` requires a reviewed decision, and `SOURCE_CATEGORY_ONLY`
means that no reviewed workbook crop-type match exists. The JSON report also
checks category text carried by all 902 crop-variety rows.

The enrichment generator adds workbook fields to the SQL crop contract and
regenerates the deployable staging SQL:

```bash
PYTHONPATH=. python scripts/crop_catalogue/enrich_crop_catalog.py \
  crop_catalog_scripts crop_catalog_variety_included.xlsx \
  --source-output crop_catalog_scripts/04_insert_crop_catalog.sql \
  --seed-output scripts/seed_db_sql/import_crop_catalog.sql
```

It retains all 129 SQL crops, adds 21 workbook-only crop types, and stores the
reviewed match code and provenance. Existing SQL categories are never
overwritten; missing categories are filled through the reviewed taxonomy map
and `category_source` distinguishes both cases. `varieties_count` is never copied from the
workbook summary field. For original SQL crops it is counted from the 902 SQL
`crop_variety` rows. For workbook additions it is counted from normalized
workbook variety concepts. `varieties_count_source` identifies which child
dataset was counted.
