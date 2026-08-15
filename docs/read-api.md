# Registry read API

The `/v1` API exposes only canonical, immutable release data. SQL staging tables
are an internal publication detail and are never part of the consumer contract.

## Release selection

Every endpoint accepts:

| Query parameter | Meaning |
| --- | --- |
| `country_code` | ISO alpha-3 catalogue owner; defaults to the configured country |
| `release_version` | Pin an `ACTIVE` or `RETIRED` release; omit it to follow `ACTIVE` |

Every response includes the resolved `release`. This makes a registry import
auditable and prevents it from accidentally combining data from different
publication runs.

## Endpoints

| Endpoint | Important filters |
| --- | --- |
| `GET /v1/releases/current` | `release_version` |
| `GET /v1/catalogues` | `domain` |
| `GET /v1/catalogues/{code}/values` | `status`, `parent_code`, relation filters, `search`, pagination |
| `GET /v1/catalogue-values` | Widget options by `catalogue_code`; `status`, `parent_code`, relation filters, `search`, pagination |
| `GET /v1/crop-varieties/{code}` | `release_version`; complete relational variety details |
| `GET /v1/geography/levels` | — |
| `GET /v1/geography/units` | `level_code`, `parent_code`, `status`, `search`, pagination |
| `GET /v1/geography/units/{code}` | optional `level_code` disambiguator |
| `GET /v1/livestock/species` | `search`, pagination |
| `GET /v1/livestock/breeds` | `species_code`, `breed_type`, national/ET-LITS flags, `search`, pagination |
| `GET /v1/livestock/reference-data` | complete gender, location, body-condition, production-type, and record-status sets |
| `GET /v1/livestock/registry-entries` | `species_code`, `status`, `breed_id`, `search`, pagination |
| `GET /v1/livestock/registry-validation` | `species_code`, `status`, `has_issues`, pagination |
| `GET /v1/statistics/livestock-population` | `species_code`, `census_year`, pagination |
| `GET /v1/statistics/seed-demand/summary` | `budget_year`, pagination |
| `GET /v1/statistics/seed-demand/trends` | `budget_year`, `seed_class`, pagination |
| `GET /v1/statistics/seed-demand/by-crop` | `crop_code`, `budget_year`, `seed_class`, pagination |
| `GET /v1/snapshots/current` | complete registry projection |

Paged endpoints use one-based `page` and a `page_size` from 1 to 1000. They
return `total`, `page`, and `page_size` with the result collection.

Geography units return both `display_name` and nullable `display_name_amh`.
The `search` filter matches the unit code, default display name, or Amharic
display name.

Catalogue values expose typed cross-catalogue `relations`. Relation targets
contain the target catalogue code, value code, and display name. Consumers must
use these references rather than interpreting source IDs in metadata.

Widgets can use the compact catalogue operation without copying catalogue data
into registry attributes:

```http
GET /v1/catalogue-values?catalogue_code=crop_category
```

Its `options` array contains only `code` and `display_name`. Configure widgets
to submit `code` and show `display_name`. The full response retains release,
catalogue, and pagination context. This operation requires `catalogue.read`,
like the full catalogue-values endpoint. It also returns `ETag`,
`X-Catalogue-Release`, and `Cache-Control`; widgets or their resolver can send
`If-None-Match` and reuse cached options when the service responds `304`.

For cascading crop widgets, use the selected parent option's `code` as
`related_value_code`:

```http
GET /v1/catalogue-values?catalogue_code=crop_category
GET /v1/catalogue-values?catalogue_code=crop&relation_type=category&related_catalogue_code=crop_category&related_value_code=1
GET /v1/catalogue-values?catalogue_code=crop_variety&relation_type=crop&related_catalogue_code=crop&related_value_code=1
```

For example, request all cereal crops with:

```http
GET /v1/catalogues/crop/values?relation_type=category&related_catalogue_code=crop_category&related_value_code=1
```

The consolidated SQL-first crop hierarchy is queried directly with:

```http
GET /v1/catalogues/crop_category/values
GET /v1/catalogues/crop/values?relation_type=category&related_catalogue_code=crop_category&related_value_code=1
GET /v1/catalogues/crop_variety/values?relation_type=crop&related_catalogue_code=crop&related_value_code=1
```

The public `crop_variety` catalogue is the deduplicated union of the 1,359 Excel
concepts and 902 SQL source rows: 309 reviewed matches reuse an Excel identity,
while 593 unmatched SQL records remain available as independent values. The
compatibility `crop_type` relation remains available for taxonomy filtering.

Retrieve one variety's typed ranges, individual source records, and all
populated characteristics with:

```http
GET /v1/crop-varieties/maize-melkassa-1-q
```

The response also resolves its crop type and taxonomy category. Multiple source
records remain separate, including their original release years and raw values.

Seed varieties have dedicated list and detail operations:

```http
GET /v1/seed-varieties?match_status=MATCHED&crop_type_code=maize
GET /v1/seed-varieties/ethioseed-20
```

The list can be filtered by seed crop, matched crop variety, crop type,
taxonomy category, match status, release year, and search text. Every item
contains its original Ethio-Seed fields and seed-crop reference. Confirmed
matches also contain resolved crop-variety, crop-type, and category references;
those references are null for unresolved listings.

`parent_code` remains reserved for hierarchical values inside one catalogue;
it does not represent crop-to-category relationships.

Livestock registries can use the typed endpoints without interpreting generic
metadata or relation objects:

```http
GET /v1/livestock/species
GET /v1/livestock/breeds?species_code=cattle&breed_type=Indigenous
GET /v1/livestock/reference-data
GET /v1/livestock/registry-entries?species_code=cattle
GET /v1/livestock/registry-validation?has_issues=true
```

Every breed contains its resolved species. Production types contain their
resolved `valid_species` collection, while location types contain their
resolved ecological zone. The national-standard and ET-LITS flags remain
separate so a consumer can select the applicable interoperability profile.

The complete snapshot contains catalogue values, geography levels and units,
and all agriculture statistics. It is resolved to one release before its
sections are read, so an activation during the request cannot mix versions.

## Conditional synchronization

All successful reads return:

- `ETag: "<release-checksum>"`
- `X-Catalogue-Release: <release-version>`
- `Cache-Control: public, max-age=<configured-seconds>`

A registry should retain the ETag and send it on its next poll:

```http
GET /v1/snapshots/current?country_code=ETH HTTP/1.1
If-None-Match: "f65c..."
```

The service responds with `304 Not Modified` and no response body while that
release remains current. On a `200`, the registry should validate and commit
the entire snapshot locally before replacing its prior version.

## Recommended consumption patterns

- Use the snapshot endpoint for an initial load or a small registry-local cache.
- Use filtered, paged endpoints when a registry needs only one domain.
- Record `country_code`, `version`, and `checksum` with each completed sync.
- Pin `release_version` when retrying a partially completed paged import.
- Keep serving the previous locally validated release if a fetch or validation fails.
