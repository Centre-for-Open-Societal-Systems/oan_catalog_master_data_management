# Frontend catalogue and API guide

This document is the implementation contract for web, mobile, registry, and
widget consumers of Catalogue Service. It describes the available datasets,
API fields, filters, relationships, and recommended table and detail-page
layouts.

## 1. Product boundary

Catalogue Service publishes immutable, versioned reference-data releases. The
public `/v1` API is read-only. Data changes originate in reviewed SQL sources,
are validated by the seed pipeline, and become visible when a new release is
activated.

Frontend implications:

- Do not present **New**, **Edit**, **Delete**, or **Upload** as working actions
  unless a separate administration/import API is implemented.
- Do not write catalogue values into registry attribute tables just to populate
  dropdowns. Use the live `/v1/catalogue-values` operation.
- Use `code` as the durable identifier. Names are labels and can change or be
  translated.
- Never infer relationships from names, numeric source IDs, or metadata. Use
  `parent_code` or typed `relations`.
- Display the active release version somewhere unobtrusive, such as the page
  footer or data-toolbar menu.

The current frontend's `/new` and `/upload` routes should therefore be hidden,
disabled with a clear explanation, or connected to a real release-publication
workflow. They must not imply that the read API supports mutations.

## 2. Connection, authentication, and caching

### Addresses

| Environment | Base URL |
| --- | --- |
| Local unified image | `http://localhost:8000` |
| Same Kubernetes namespace | `http://catalogue-api` |
| Cross namespace | `http://catalogue-api.<namespace>.svc.cluster.local` |

The web application uses `CATALOGUE_API_BASE_URL`; configure it to the relevant
base URL. The production API requires an IAM Bearer token. Server-side frontend
requests must forward the user's token or use a dedicated confidential client.
The local `dev_main` entry point is intentionally unauthenticated and must not
be deployed.

### Permissions

| Permission | APIs |
| --- | --- |
| `catalogue.read` | catalogues, crop details, seed varieties, livestock reference and registry views |
| `geography.read` | geography levels and units |
| `statistics.read` | livestock-population and seed-demand statistics |
| `snapshot.read` | complete release snapshot |

### Release and cache headers

Successful release-backed reads return:

- `ETag: "<release-checksum>"`
- `X-Catalogue-Release: <release-version>`
- `Cache-Control: public, max-age=<seconds>`

Cache by the complete request URL, including filters and page number. Send the
stored ETag as `If-None-Match`; reuse cached data when the API returns `304 Not
Modified`. Do not call `response.json()` on a `304` response.

### Shared query rules

- `country_code`: defaults to the configured country, normally `ETH`.
- `release_version`: omit for the active release; provide it for historical or
  reproducible reads.
- `page`: one-based, minimum `1`.
- `page_size`: `1`–`1000`.
- `search`: omit when empty; the API rejects an empty string.
- `status`: catalogue values normally use `ACTIVE` or `RETIRED`.

## 3. Common response contracts

### Release

| Field | Type | UI treatment |
| --- | --- | --- |
| `country_code` | string | Country badge or hidden context |
| `version` | string | Release badge/tool-tip |
| `schema_version` | string | Diagnostics only |
| `checksum` | string | Diagnostics/cache integrity; truncate visually |
| `source` | string/null | Provenance section |
| `status` | string | `ACTIVE`/`RETIRED` badge |
| `activated_at` | datetime/null | Localized date/time |

### Catalogue definition

| Field | Type | Meaning |
| --- | --- | --- |
| `code` | string | Stable catalogue identifier |
| `domain` | string/null | Functional grouping such as crop or livestock |
| `display_name` | string | Default label |
| `display_name_i18n` | object/null | Language-code-to-label map |
| `is_hierarchical` | boolean | Whether `parent_code` is meaningful inside this catalogue |
| `status` | string | Catalogue availability |

### Generic catalogue value

| Field | Type | UI treatment |
| --- | --- | --- |
| `code` | string | Primary identifier; monospace in details, not oversized in tables |
| `display_name` | string | Primary table/detail label |
| `display_name_i18n` | object/null | Localized-name section, not raw JSON |
| `parent_code` | string/null | Parent link only for same-catalogue hierarchies |
| `semantic_roles` | string[] | Chips; hide section when empty |
| `sort_order` | integer/null | Usually hidden; useful in diagnostics |
| `valid_from`, `valid_to` | date/null | Validity section; show `—` for open bounds |
| `status` | string | Consistent status badge |
| `metadata` | object | Render through a field map; never dump raw JSON in the primary UI |
| `relations` | array | Related-record links |

Each relation has `type`, `target_catalogue_code`, `target_code`, and
`target_display_name`. Link to
`/catalogues/{target_catalogue_code}/{target_code}` where that detail page is
available.

### Compact widget option

`GET /v1/catalogue-values` returns an `options` array:

```json
{
  "options": [
    {"code": "1", "display_name": "Cereal Crops"}
  ],
  "total": 7,
  "page": 1,
  "page_size": 100
}
```

Bind `code` to the submitted form value and `display_name` to the visible
label. See [`widget-integration.md`](widget-integration.md) for complete
category → crop → variety configurations.

## 4. Catalogue inventory

The active Ethiopia release currently publishes these generic catalogues:

| Code | Purpose | Preferred frontend |
| --- | --- | --- |
| `crop_category` | SQL crop categories | Category table and first crop selector |
| `crop` | Consolidated crops | Crop table/detail and second selector |
| `crop_variety` | Consolidated SQL + workbook varieties | Variety table/detail and third selector |
| `crop_taxonomy_category` | Workbook taxonomy categories | Compatibility/taxonomy views |
| `crop_type` | Workbook crop types | Compatibility/taxonomy views |
| `ecological_zone` | Agro-ecological zones | Small reference table |
| `seed_crop` | Seed-system crop references | Seed-variety filtering |
| `seed_variety` | Generic seed-variety projection | Prefer the typed seed-variety API |
| `livestock_type` | Species/type reference | Species selectors |
| `livestock_breed` | Breed reference | Prefer typed breed API |
| `livestock_gender` | Gender reference | Small reference table/select |
| `livestock_location_type` | ET-LITS land/location type | Prefer typed reference-data API |
| `livestock_body_condition` | Body-condition score | Prefer typed reference-data API |
| `livestock_production_type` | Production purpose | Prefer typed reference-data API |
| `etlits_livestock_record_status` | Registry workflow states | Prefer typed reference-data API |

Compatibility catalogues are intentionally retained. For new crop forms use
`crop_category → crop → crop_variety`, not
`crop_taxonomy_category → crop_type`, unless the workflow explicitly uses the
workbook taxonomy.

### Supported relationship filters

| Source catalogue | Relation | Target catalogue | Use |
| --- | --- | --- | --- |
| `crop` | `category` | `crop_category` | Crops in a selected SQL category |
| `crop` | `preferred_ecological_zone` | `ecological_zone` | Crop's preferred zone |
| `crop_variety` | `crop` | `crop` | Varieties belonging to a crop |
| `crop_variety` | `crop_type` | `crop_type` | Compatibility taxonomy mapping |
| `crop_type` | `category` | `crop_taxonomy_category` | Workbook types in a taxonomy category |
| `livestock_breed` | `species` | `livestock_type` | Breeds valid for a species |
| `livestock_location_type` | `ecological_zone` | `ecological_zone` | Location-to-zone mapping |
| `livestock_production_type` | `valid_for_species` | `livestock_type` | Purposes valid for a species |

Generic relation query:

```http
GET /v1/catalogues/{source}/values
  ?relation_type={type}
  &related_catalogue_code={target_catalogue}
  &related_value_code={target_code}
```

## 5. API endpoint reference

### Catalogue and crop APIs (`catalogue.read`)

| Endpoint | Collection | Filters/use |
| --- | --- | --- |
| `GET /v1/releases/current` | release | `country_code`, `release_version` |
| `GET /v1/catalogues` | `catalogues` | `country_code`, `domain`, `release_version` |
| `GET /v1/catalogues/{code}/values` | `values` | status, parent, relation, search, paging |
| `GET /v1/catalogue-values` | `options` | widget-ready equivalent using `catalogue_code` |
| `GET /v1/crop-varieties/{variety_code}` | `variety` | Full agronomic variety detail |
| `GET /v1/snapshots/current` | complete snapshot | Registry sync, not ordinary pages |

Do not load every value and then find a detail client-side. Use the dedicated
crop-variety detail route for varieties. For generic values without a dedicated
detail endpoint, a list lookup is currently the only read contract; keep the
requested page bounded and add a backend detail route before relying on very
large catalogues.

### Seed-variety APIs (`catalogue.read`)

| Endpoint | Filters |
| --- | --- |
| `GET /v1/seed-varieties` | `seed_crop_code`, `crop_variety_code`, `crop_type_code`, `category_code`, `match_status`, `release_year`, `search`, paging |
| `GET /v1/seed-varieties/{seed_variety_code}` | `country_code`, `release_version` |

`match_status` is `MATCHED`, `UNRESOLVED`, or `CONFLICT`.

### Geography APIs (`geography.read`)

| Endpoint | Filters |
| --- | --- |
| `GET /v1/geography/levels` | country/release |
| `GET /v1/geography/units` | `level_code`, `parent_code`, `status`, `search`, paging |
| `GET /v1/geography/units/{unit_code}` | optional `level_code` disambiguator |

Use `parent_code` for Region → Zone → Woreda → Kebele cascading. Geography is
not served through the generic catalogue widget endpoint.

### Livestock APIs (`catalogue.read`)

| Endpoint | Filters |
| --- | --- |
| `GET /v1/livestock/species` | `search`, paging |
| `GET /v1/livestock/breeds` | `species_code`, `breed_type`, `in_national_standard`, `in_etlits_registry`, `search`, paging |
| `GET /v1/livestock/reference-data` | country/release; complete small reference sets |
| `GET /v1/livestock/registry-entries` | `species_code`, `status`, `breed_id`, `search`, paging |
| `GET /v1/livestock/registry-validation` | `species_code`, `status`, `has_issues`, paging |

`livestock_registry_validation` is a database view exposed through the final
endpoint; it is not an editable table.

### Statistics APIs (`statistics.read`)

| Endpoint | Filters |
| --- | --- |
| `GET /v1/statistics/livestock-population` | `species_code`, `census_year`, paging |
| `GET /v1/statistics/seed-demand/summary` | `budget_year`, paging |
| `GET /v1/statistics/seed-demand/trends` | `budget_year`, `seed_class`, paging |
| `GET /v1/statistics/seed-demand/by-crop` | `crop_code`, `budget_year`, `seed_class`, paging |

## 6. Typed field reference

### Crop-variety detail

Top level: `code`, `display_name`, `display_name_i18n`, `status`, `crop_type`,
`category`, and `source_records`.

Each source record contains:

- provenance: `source_record_code`, `source_row_number`, `centre`,
  `source_url`;
- release: `release_year_raw`, `release_year`;
- adaptation: altitude and rainfall minimum/maximum;
- agronomy: maturity, research/farmer yield ranges, seed rate, adaptation area,
  planting date, pest reaction; and
- `characteristics`, whose typed values may be text, numeric, boolean, or a
  minimum/maximum range with `unit_code`.

Display numeric ranges as one value, for example `1,500–2,200 m`, and preserve
the original `raw_value` in a tooltip or provenance view.

### Seed variety

| Field group | Fields |
| --- | --- |
| Identity | `code`, `display_name`, `status`, `source_variety_id` |
| Source taxonomy | `seed_crop`, `crop_name_raw`, `common_name_raw`, `category_raw` |
| Resolved taxonomy | `matched_crop_variety`, `crop_type`, `category` |
| Release | `release_year`, `release_date`, `release_raw` |
| Provenance | `maintainer`, `source_classification`, `details_url` |
| Reconciliation | `match_method`, `match_status`, `review_note` |

Null resolved taxonomy is expected for unresolved records. Do not display it as
an application error.

### Geography unit

Fields: `code`, `level_code`, `parent_code`, `display_name`,
`display_name_amh`, `display_name_i18n`, `latitude`, `longitude`, `valid_from`,
`valid_to`, `status`, `aliases`, and `metadata`.

Prefer `display_name_amh` for an Amharic secondary-name column. Build hierarchy
breadcrumbs from parent records rather than concatenating or parsing codes.

### Livestock species and breed

Species fields include identity/status plus `description`, `icon_url`,
`dataset_id`, `scientific_name`, `subfamily`, `species_type_code`,
`chart_color`, `ear_tag_range`, `in_lis_population`, and
`in_etlits_registry`.

Breed fields include `species`, `source_id`, `breed_code`, `abbreviation`,
`breed_type` (`Indigenous`, `Exotic`, `Cross`), standard/ET-LITS flags, and
`source`.

### Livestock reference bundle

- Gender: `code`, `display_name`, `description`, `in_etlits_registry`.
- Location type: zone/altitude descriptions and resolved `ecological_zone`.
- Body condition: `bcs_score`, condition/fatness/ET-LITS labels, description.
- Production type: standard purpose, standard/ET-LITS flags, description,
  resolved `valid_species`.
- Record status: `sort_order`, `is_live_master_data`, description.

### Livestock registry entry and validation

Registry entry fields: `id`, species/breed references, gender, location, body
condition, production type, workflow `status`, timestamps, and embedded
`validation`.

Validation booleans:

- `breed_unrecognised`
- `breed_outside_national_standard`
- `breed_species_mismatch`
- `production_type_species_mismatch`

Show a single issue count in the table and the individual flags on the detail
page. A row with no flags is **Valid** or **Clean**, not merely “Active”.

### Statistics

- Livestock population: species, census year, total, source-record count,
  source.
- Seed-demand summary: year, entry count, total/average quantity, total/average
  estimated land.
- Seed-demand trend: year, seed class, quantity.
- Seed demand by crop: crop code/name, year, seed class, quantity.

Format counts as localized integers and decimal quantities consistently. Put
units in column headers when the API field or domain supplies them; do not
invent a unit when none is declared.

## 7. Recommended table designs

All tables should use the same shell:

1. page title, one-sentence description, and release badge;
2. one toolbar row with search, meaningful filters, result count, and optional
   column controls;
3. a table with a sticky header and server-side pagination;
4. a resource-specific empty state; and
5. an error state that distinguishes authorization, not-found, and service
   availability failures.

Do not show every API field as a column. Keep the primary table to roughly five
to seven useful columns and move secondary information to the detail page.

| Page | Recommended columns |
| --- | --- |
| Catalogue index | Name, code, domain, hierarchical, status |
| Generic values | Name, code, relation/parent, validity, status |
| Crop categories | Name, code, crop count |
| Crops | Name, code, scientific name, category, centre, variety count, status |
| Crop varieties | Name, code, crop, crop type, status |
| Seed varieties | Variety, seed crop, match status, matched variety, release year, maintainer |
| Geography | Name, Amharic name, code, level, parent, status |
| Species | Name, code, scientific name, LIS, ET-LITS, status |
| Breeds | Name, code, species, breed type, national standard, ET-LITS |
| Registry entries | ID, species, breed, production type, status, issue count, updated date |
| Population | Species, census year, population, source |
| Seed-demand summary | Budget year, entries, total quantity, estimated land |

Avoid one request per row for counts or labels. The existing crop/category pages
perform row-level count requests; this is an N+1 pattern. Until the API provides
batch counts, either omit those columns, calculate them once from an already
loaded dataset, or fetch with a bounded parallel strategy and cache by release.

### Responsive behavior

- Keep name and status visible at all widths.
- At tablet widths hide provenance and secondary flags first.
- On small screens switch each row to a labelled summary card rather than
  forcing a nine-column horizontal scroll.
- Truncate long codes visually but expose the complete value through copy and
  title/tooltip actions.

## 8. Recommended detail-page designs

Use a consistent maximum-width content column. The header should contain a
breadcrumb, display name, code, status, and release context. Organize the body
into cards in this order:

1. **Identity** — code, name, translated names, status.
2. **Relationships** — clickable parent and related values.
3. **Domain details** — resource-specific fields.
4. **Validity** — effective dates and lifecycle state.
5. **Provenance** — source, source IDs/URLs, centre, release.
6. **Technical metadata** — collapsed by default and visible only when useful.

Resource-specific layouts:

- Crop: identity; category/ecological zone; scientific name and centre;
  varieties link; provenance.
- Crop variety: taxonomy summary; agronomic range cards; one collapsible card
  per source record; characteristic table.
- Seed variety: source identity; reconciliation status; resolved taxonomy;
  release/provenance. Use warning styling only for unresolved/conflict states.
- Geography: identity and localized names; hierarchy breadcrumb; coordinates;
  aliases/validity; metadata.
- Species/breed: identity; classification; interoperability flags;
  description/provenance.
- Livestock registry entry: identity/status; resolved reference values;
  validation panel; timestamps. Provide a dedicated detail route before making
  IDs look clickable.

Never render `metadata` with `JSON.stringify` as the main detail UI. Use a field
definition map with readable labels and formatters, and put unknown keys in a
collapsed “Additional metadata” definition list.

## 9. Visual and interaction rules

- Use one badge vocabulary: green for active/valid/matched, amber for unresolved
  or review, red for conflict/invalid, grey for retired/inactive.
- Do not rely on color alone; every badge must have text.
- Use sentence-case labels in the interface while preserving API codes in
  monospace.
- Render null/empty scalar values as `—`; render an empty collection as a clear
  “No …” message.
- Show booleans as Yes/No or labelled icons, not raw `true`/`false`.
- Localize dates and numbers at render time; keep API values unchanged.
- Preserve filters in pagination links and reset `page` to `1` when a filter
  changes.
- Debounce text search and do not send an empty `search` parameter.
- Clear dependent crop and variety selections when an ancestor changes.
- Use skeletons for initial loading and retain prior table data during page or
  filter transitions where possible.

## 10. Error and empty states

| HTTP/result | Frontend behavior |
| --- | --- |
| `401` | Start or refresh authentication; do not show “not found” |
| `403` | Show missing-permission message and required permission |
| `404` | Resource-specific not-found page |
| `422` | Correct invalid filters; log validation detail for developers |
| `304` | Reuse cached response body |
| `5xx`/network | Retry affordance; keep last cached release visible if available |
| Empty page | Explain that no records match the current filters and offer reset |

The current frontend converts several API failures into `notFound()`. Replace
that broad handling so connectivity and authorization problems do not appear as
missing catalogue records.

## 11. Suggested frontend implementation order

1. Centralize API errors, authorization forwarding, release headers, and ETag
   caching in `web/src/lib/api.ts`.
2. Create reusable `DataTable`, `FilterToolbar`, `StatusBadge`, `DefinitionList`,
   `RelationLink`, `EmptyState`, and `ErrorState` components.
3. Remove or disable unsupported New/Upload actions.
4. Replace raw/generic tables with the recommended resource-specific columns.
5. Standardize detail pages using the section order above.
6. Remove N+1 row-count requests or add a batch-count backend operation.
7. Add responsive table/card behavior and accessibility checks.
8. Add component and browser tests for loading, empty, error, filtered, and
   cached states.

## 12. Source-of-truth files

- API routes: `catalogue-api/src/openg2p_catalogue_service/controllers/`
- API response fields: `catalogue-api/src/openg2p_catalogue_service/schemas/`
- Frontend API wrapper: `web/src/lib/api.ts`
- Frontend TypeScript fields: `web/src/lib/types.ts`
- Existing pages: `web/src/app/`
- Widget-only configuration: [`widget-integration.md`](widget-integration.md)
- Security: [`security.md`](security.md)
- Release and caching behavior: [`read-api.md`](read-api.md)

When this document and OpenAPI disagree, OpenAPI is authoritative for the wire
contract. Update this guide in the same change whenever an endpoint or field is
added, removed, or renamed.
