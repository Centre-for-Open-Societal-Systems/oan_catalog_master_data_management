# Widget integration

Widgets should read catalogue options live from Catalogue Service. They should
not copy crop categories, crops, or crop varieties into registry attribute
tables merely to populate dropdowns.

## Platform service mapping

Register the logical platform operation with the Catalogue API's stable
Kubernetes service:

```yaml
service: catalogue
endpoint: catalogue-values
method: GET
base_url: http://catalogue-api.<catalogue-namespace>.svc.cluster.local
path: /v1/catalogue-values
permission: catalogue.read
```

The exact service-map syntax belongs to the consuming platform repository; the
values above are the required contract. When both workloads share a namespace,
the short base URL `http://catalogue-api` is sufficient. For cross-namespace
traffic, add the platform namespace to the chart's
`networkPolicy.ingressNamespaces`.

Production callers must send an IAM Bearer token whose role resolves to
`catalogue.read`. The local Docker Compose development entry point deliberately
disables IAM and must not be deployed.

## Dropdown configuration

Bind `code` as the stored value and `display_name` as the visible label. The
resolver response collection is named `options`.

### Crop category

```yaml
service: catalogue
endpoint: catalogue-values
params:
  catalogue_code: crop_category
  country_code: ETH
  status: ACTIVE
option_value: code
option_label: display_name
```

### Crop filtered by category

```yaml
service: catalogue
endpoint: catalogue-values
params:
  catalogue_code: crop
  country_code: ETH
  status: ACTIVE
  relation_type: category
  related_catalogue_code: crop_category
  related_value_code: "${cropCategory.code}"
option_value: code
option_label: display_name
```

Clear the selected crop whenever the category changes.

### Crop variety filtered by crop

```yaml
service: catalogue
endpoint: catalogue-values
params:
  catalogue_code: crop_variety
  country_code: ETH
  status: ACTIVE
  relation_type: crop
  related_catalogue_code: crop
  related_value_code: "${crop.code}"
  page_size: 1000
option_value: code
option_label: display_name
```

Clear the selected variety whenever its crop or crop category changes. Use
server-side `search` and paging if a deployment does not want to load as many
as 1000 options at once.

## Response and caching

```json
{
  "release": {"country_code": "ETH", "version": "ETH-catalogue-v9"},
  "catalogue": {"code": "crop", "display_name": "Crop"},
  "options": [
    {"code": "1", "display_name": "Maize"}
  ],
  "total": 1,
  "page": 1,
  "page_size": 100
}
```

Cache each complete request URL separately, including its relation and paging
parameters. Retain the returned `ETag` and send it as `If-None-Match`; on `304
Not Modified`, reuse the cached options. `X-Catalogue-Release` identifies the
release that supplied the values.

## When local synchronization is appropriate

Attribute synchronization is not part of the default widget path. Enable a
registry-owned synchronization job only when that registry explicitly needs a
local copy for offline operation, database foreign keys, or an audited local
snapshot. Such a job must use a dedicated IAM client, retain release and ETag
state, stage and validate the whole update, and activate it atomically.

Catalogue Service never connects to or writes a registry database. A registry
that opts into synchronization owns its copied rows, scheduling, failure
handling, and retirement policy. Registries without those requirements should
continue using the live `catalogue-values` operation.
