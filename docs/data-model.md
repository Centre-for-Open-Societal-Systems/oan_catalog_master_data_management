# Catalogue Service data model

The database has three data layers and one operational schema-history table.

## Schema history

`catalogue_schema_migrations` records the immutable ordered SQL files applied by
the dedicated migration Job. The API has an ORM representation for schema
introspection, but it never creates or modifies this table or other schema
objects at startup.

## Canonical publication layer

- `catalogue_releases` defines immutable country releases.
- `catalogues` and `catalogue_values` hold registry-facing reference values.
- `catalogue_value_relations` links values across catalogues with a typed,
  release-scoped reference. It is distinct from `parent_value_id`, which is
  reserved for hierarchy within a catalogue.
- `geography_levels` and `geography_units` hold the administrative hierarchy.
  Units expose the required `display_name` and a nullable `display_name_amh`
  reserved for an Amharic name.
- `*_statistics` tables hold measured facts that must not be represented as
  selectable catalogue values.

Every canonical row belongs, directly or through its parent, to a release. Only
an active, fully validated release is visible through the service API.

Crop categories and ecological zones are independent catalogues. Crop values
use `category` and `preferred_ecological_zone` relations to their values;
source staging IDs never become database foreign keys in the public contract.

## SQL compatibility staging layer

The legacy `g2p_*` tables match the five inherited SQL files under
`scripts/seed_db_sql`. They exist so source data can be loaded without making
the inherited Odoo table shapes the public API contract.

The `g2p_region`, `g2p_zone`, and `g2p_woreda` staging tables also have a
nullable `display_name_amh`. The publisher copies it to the canonical unit;
current source rows leave it null until translated names are supplied.

Migration `007` adds a separate relational ingestion boundary for the new crop
taxonomy workbook:

- `g2p_crop_taxonomy_category` and `g2p_crop_taxonomy_type` hold the first two
  taxonomy levels without changing the legacy `g2p_crop*` tables.
- `g2p_crop_variety` identifies a variety concept, while
  `g2p_crop_variety_source_record` preserves individual workbook records and
  their typed common measurements.
- `g2p_crop_characteristic_definition` defines uncommon crop-specific traits,
  and `g2p_crop_variety_characteristic` stores their typed relational values.

Common ranges such as altitude, rainfall, maturity days, yield, and seed rate
are columns on the source-record table. The characteristic tables handle the
remaining sparse traits; variety characteristics are not stored as JSONB.
`display_name_i18n` remains JSONB only for the service-wide localization
contract.

Phase 2 adds `scripts/crop_taxonomy/transform_workbook.py`. It reads the XLSX
source directly, resolves category/type/variety relationships, groups repeated
records under one variety concept, and produces six reviewable relational CSV
files plus a deterministic validation report. The source's raw values are
retained even when a year or range is too ambiguous to normalize safely.

The transformer does not connect to PostgreSQL or execute SQL embedded in the
workbook. Phase 3 generates `scripts/seed_db_sql/import_crop_taxonomy.sql` from
that transformer. The normal seed runner loads all six tables in its existing
atomic transaction, verifies exact row counts, checks the reviewed missing type
ID, and rejects variety concepts without source records. Source records with no
optional characteristic cells remain valid because their identity, centre,
year, and URL fields are stored directly on the source record.

Phase 4 publishes the taxonomy identities as the canonical
`crop_taxonomy_category`, `crop_type`, and `crop_variety` catalogues. Every crop
type retains its workbook-category relation and also resolves to the reviewed
SQL `crop_category`. Every Excel variety retains its `crop_type` relation and
also has a direct `crop` relation.

Agronomic characteristic values remain in relational tables and are not copied
into generic JSON metadata. Migration `008` adds release-scoped canonical
`crop_variety_source_records`, `crop_characteristic_definitions`, and
`crop_variety_characteristics` tables. They preserve both active and retired
release details for the dedicated variety-detail API.

Migration `009` adds `g2p_seed_variety_source_record` for the original
Ethio-Seed listing identity and metadata. A source row may remain unresolved or
link to `g2p_crop_variety` using a constrained match method. Its canonical
counterpart, `seed_variety_source_records`, is release-scoped and relates the
published seed variety and seed crop to the normalized crop variety when a
verified match exists.

Migration `014` makes the original SQL `crop_id` relationship explicit and
publishes a consolidated `crop_variety` catalogue. The 309 reviewed SQL/Excel
matches reuse their Excel variety identities; the 593 unmatched SQL rows are
added with deterministic `ethioseed-{id}` codes. Together with the 1,359 Excel
concepts this produces 1,952 values without dropping source metadata. Each of
the 902 SQL source records retains its seed-crop reference, direct SQL crop
reference, consolidated variety reference, and optional reviewed Excel match.

Migration `010` adds `g2p_kebele` as an auditable staging layer for the kebele
register. Each row retains its raw region, zone, and woreda values together with
the normalized parent decision, match method, status, and review note. Matched
rows publish as level-four `geography_units` beneath canonical woredas.
Unresolved rows stay queryable in staging for data-quality review and are not
exposed as incorrectly parented geography units.

Migration `011` extends `g2p_livestock_type` with typed scientific, national
coding, presentation, ear-tag, and source-coverage fields. It also adds
relational staging tables for livestock breeds, genders, location types, body
conditions, production types and valid species, and ET-LITS workflow statuses.
These tables are the ingestion boundary and are validated before publication.

The `ETH-catalogue-v9` publisher exposes `livestock_breed`,
`livestock_gender`, `livestock_location_type`, `livestock_body_condition`,
`livestock_production_type`, and `etlits_livestock_record_status` alongside the
backward-compatible `livestock_type` catalogue. Breed values relate to their
species, production types relate to every valid species, and location types
relate to the existing ecological-zone catalogue. Operational ET-LITS registry
records publish separately as immutable rows in `livestock_registry_entries`.

Migration `012` adds `g2p_livestock_registry_entry` and the source-compatible
`g2p_livestock_registry_validation` view. Publication resolves breed and
production-type relationships into release-scoped rows. The canonical
`livestock_registry_validation` view retains the four SQL quality flags:
unrecognised breed, breed outside the national standard, species mismatch, and
invalid production-type/species combination.

Staging data is never served directly. The publisher validates and copies it
into the release-scoped canonical layer before activating a release.

Migration `013` consolidates workbook crop-type information into `g2p_crop`.
The original 129 SQL crop rows retain their identifiers and SQL-only fields;
21 workbook-only types receive deterministic integer identifiers. Scientific
name, centre, image, localized name, and taxonomy provenance remain typed
columns in staging and are exposed as crop catalogue metadata. The published
`varieties_count` is computed from child rows, with its source recorded in
`varieties_count_source`; the workbook's reported summary count is not copied.
Null SQL category assignments are filled through the reviewed workbook-to-SQL
category map without replacing categories present in the source. The
`category_source` field records which path supplied each assignment.

## Import audit layer

- `catalogue_import_runs` records one complete import attempt.
- `catalogue_import_scripts` records checksum, order and outcome per SQL file.

This layer will let the scheduled runner skip unchanged sources, reject a
changed file under an existing version, prevent overlapping runs, and diagnose
partial failures without publishing them.
