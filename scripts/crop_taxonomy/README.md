# Crop taxonomy workbook transformer

Phase 2 converts the source workbook into deterministic relational datasets. It
does not connect to PostgreSQL, execute the workbook's `Sheet1` SQL, or publish a
catalogue release.

```bash
python3 scripts/crop_taxonomy/transform_workbook.py \
  crop_catalog_variety_included.xlsx \
  --output-dir /tmp/crop-taxonomy
```

The output directory contains CSV files corresponding to the six crop taxonomy
staging tables from migration `007`, plus `validation_report.json`. Common range
attributes are projected into typed source-record columns. Their original text,
and every other populated workbook attribute, are retained in the relational
characteristic files.

The command exits non-zero for structural errors. `--strict` also treats source
quality warnings as failures. Generated files are intermediate review artifacts;
Phase 3 will load them transactionally and publish the API catalogues.
