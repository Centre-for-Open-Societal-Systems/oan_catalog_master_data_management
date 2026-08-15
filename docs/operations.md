# Operations and observability

## Health endpoints

| Endpoint | Purpose | Dependency behavior |
| --- | --- | --- |
| `GET /health/live` | Process liveness | Does not contact PostgreSQL or IAM |
| `GET /health/ready` | Traffic readiness | Checks PostgreSQL and applied schema version |
| `GET /metrics` | Prometheus scrape | In-cluster only; blocked by the external VirtualService |

Readiness returns `503` when PostgreSQL is unavailable, the check times out, or
the highest applied migration does not equal `schemaMigration.expectedVersion`.
Error responses deliberately omit database exception and credential details.

## Logs

The common application framework emits JSON logs. Catalogue request completion
records add:

- `request_id` (accepted from a sanitized `X-Request-ID`, otherwise generated);
- HTTP method, templated route, status, and duration;
- requested country and pinned release; and
- resolved `catalogue_release_version` when returned by the API.

The templated route—not the raw URL—is used as the metric label, preventing
catalogue or geography codes from creating unbounded Prometheus series. Never
put access tokens, client secrets, database URLs, or response bodies in logs.

## Metrics

| Metric | Operational use |
| --- | --- |
| `catalogue_http_requests_total` | Request volume and error rate by method/route/status |
| `catalogue_http_request_duration_seconds` | API latency percentiles |
| `catalogue_readiness_checks_total` | Ready/not-ready transitions |
| `catalogue_readiness_check_duration_seconds` | Database readiness latency |
| `catalogue_active_release_timestamp_seconds` | Age of the active country release |
| `catalogue_last_successful_import_timestamp_seconds` | Age of the latest published/skipped SQL reconciliation |

The release/import gauges refresh during readiness checks. Gunicorn workers use
Prometheus multiprocess mode backed by the pod-local `/tmp/prometheus`
`emptyDir`.

Enable Prometheus Operator resources only when their CRDs exist:

```yaml
monitoring:
  serviceMonitor:
    enabled: true
    labels:
      release: kube-prometheus-stack
  prometheusRule:
    enabled: true
    labels:
      release: kube-prometheus-stack
```

If Prometheus runs outside the Catalogue namespace, add its namespace to
`networkPolicy.ingressNamespaces`; otherwise the ServiceMonitor will discover
the Service but its scraper pods will be denied by the default NetworkPolicy.

Recommended dashboard panels are request rate, 5xx percentage, p50/p95/p99
latency, ready replicas, active release age, latest import age, CronJob history,
and PostgreSQL connection/error rate.

## Alerts

The optional `PrometheusRule` includes:

- elevated Catalogue API 5xx rate;
- failed readiness checks;
- stale active releases;
- stale SQL reconciliation; and
- failed SQL seed Jobs through kube-state-metrics.

Tune release and seed freshness thresholds to the actual publication schedule.
Migration Job failures should also be alerted from kube-state-metrics in the
platform-level Job alert policy because migration job names are revisioned.

## Runbook

### API is not ready

1. Inspect `/health/ready` to distinguish database-down from schema-mismatch.
2. Check the PostgreSQL Service, Secret keys, NetworkPolicy, and database logs.
3. For schema mismatch, inspect the revisioned migration Job and
   `catalogue_schema_migrations`; do not bypass readiness or run ORM schema creation.
4. Correct the migration failure and redeploy. Liveness restarts are not useful
   for an unavailable dependency, which is why liveness remains dependency-free.

### SQL seed Job failed or reconciliation is stale

1. Inspect the latest Job/CronJob pod logs and `catalogue_import_runs` failure summary.
2. Verify the manifest country/version/checksum and database connectivity.
3. Correct the source or configuration, then create a one-off Job from the
   CronJob or redeploy the hook. Advisory locking and immutable checksums make
   retries safe.
4. Confirm a `PUBLISHED` or `SKIPPED` run and that the freshness gauge advances.

### API errors or latency increased

1. Split the request metrics by templated route and status code.
2. Correlate a failing request using `X-Request-ID` across ingress and API logs.
3. Check PostgreSQL saturation and slow queries before increasing replicas;
   every replica adds a connection pool.
4. Keep the previously active release available while investigating publisher issues.
