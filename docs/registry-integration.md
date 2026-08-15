# Registry integration

Registry services consume Catalogue Service over HTTP. They must not share its
PostgreSQL database. The recommended integration is scheduled pull using the
complete immutable snapshot and its ETag.

Scheduled synchronization is explicit and registry-owned; installing Catalogue
Service does not copy values into any registry. UI dropdowns should use the live
`/v1/catalogue-values` operation described in
[`widget-integration.md`](widget-integration.md). Create a local copy only when
a registry has a documented offline, foreign-key, or local-audit requirement.

## Consumer package

`catalogue-client/` is a standalone Python package intended to be installed by
a registry service:

```bash
pip install ./catalogue-client
```

It supplies:

- OAuth 2.0 client-credentials token acquisition and token reuse;
- typed validation for the full snapshot contract;
- `If-None-Match` polling and `304 Not Modified` handling;
- bounded exponential retries for transport errors, `429`, and transient `5xx` responses;
- one forced token refresh following `401`; and
- response integrity checks across the ETag, release header, and payload.

For a record-level lookup, `fetch_crop_variety_detail(variety_code)` returns
typed category, crop type, source-record, range, unit, and characteristic data.
It accepts `release_version` for reproducible historical reads and `etag` for
conditional requests. A missing variety is surfaced as
`CatalogueResponseError` with status code `404`.

Seed-variety consumers can call `fetch_seed_varieties(...)` for typed,
server-filtered pages and `fetch_seed_variety_detail(seed_variety_code)` for a
single source listing. Both operations validate the release header and ETag,
support immutable `release_version` pinning, and accept an ETag for conditional
reads. The list exposes seed-crop links for every record and reviewed crop
taxonomy links only where `match_status` is `MATCHED`.

Livestock consumers can call `fetch_livestock_species(...)`,
`fetch_livestock_breeds(...)`, `fetch_livestock_reference_data()`,
`fetch_livestock_registry_entries(...)`, and
`fetch_livestock_registry_validation(...)`. These
operations expose typed species metadata, resolved breed-to-species links,
production-type applicability, ecological-zone links, and the supporting
gender, body-condition, and record-status values. They support release pinning
and conditional ETags; the two list operations also support pagination.

Each registry gets its own IAM confidential client with `snapshot.read` for
snapshot synchronization and `catalogue.read` for typed catalogue reads.
Keep its secret in the workload secret manager. Configuration values are shown in
[`examples/registry_snapshot_sync.py`](../examples/registry_snapshot_sync.py).

## Registry persistence contract

The consumer owns a small sync-state record:

| Field | Purpose |
| --- | --- |
| `country_code` | Prevents applying one country's state to another consumer |
| `release_version` | Audits the locally active release |
| `etag` | Enables inexpensive conditional polling |

Run synchronization from one scheduler replica, or take a registry-local
advisory/distributed lock. On a changed snapshot:

1. validate the typed response and any registry-specific invariants;
2. stage all values in the registry database;
3. atomically activate the staged release;
4. commit the database transaction; and
5. persist the returned `SyncState`.

`sync_snapshot` invokes the supplied async apply callback before returning the
new state. If validation or persistence fails, it propagates the exception and
does not return a newer ETag. The next scheduled run therefore retries the same
release while the registry continues serving its previously committed data.

Do not update the ETag before committing local data. Do not partially apply a
snapshot, and do not combine pages from different unpinned releases.

## Scheduling and failure policy

A five- to fifteen-minute polling interval is normally sufficient because
unchanged polls return `304` without a response body. Add scheduler jitter when
many registries poll the service. Alert after repeated failures, but keep the
last locally validated release available.

The client retries only failures likely to be transient. Other `4xx` responses
are terminal and should be investigated as configuration, permission, or
contract errors. Network timeouts are bounded by `timeout_seconds`; retry count
is bounded by `max_attempts`.

## Why polling instead of webhooks

Release activation is immutable and already represented by a stable checksum.
Conditional polling is idempotent, tolerates consumer downtime, and introduces
no webhook registration, signing, delivery, or replay state. Webhooks or an
event broker can be added later as a latency optimization; consumers should
still use the release endpoint or snapshot ETag as the source of truth.
