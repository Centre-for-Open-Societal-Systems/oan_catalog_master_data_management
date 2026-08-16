# OpenG2P Catalogue Helm chart

Deploys the Catalogue API, provisions its PostgreSQL database through
`postgres-init`, applies versioned schema migrations with a dedicated Job, and
publishes the versioned SQL sources with a post hook Job. Database provisioning
and migration Jobs can start together: the migration runner retries until the
database exists. Its revision-specific name avoids immutable Kubernetes Job
updates on Helm upgrades.

API and seed pods run the migration image in verification mode before starting,
checking both version `schemaMigration.expectedVersion` and every applied file
checksum. This makes the API wait for the migration Job without creating a Helm
`--wait`/post-hook deadlock. The scheduled reconciliation CronJob is checksum-aware and uses
`concurrencyPolicy: Forbid`; unchanged releases are recorded as skipped.

```bash
helm dependency update deployments/charts/openg2p-catalogue
helm install catalogue deployments/charts/openg2p-catalogue
```

## Platform service discovery

The chart publishes a stable `catalogue-api` Kubernetes Service in addition to
the Helm release-scoped API Service. Platform resolvers should register the
logical service name `catalogue` with this base URL:

```text
http://catalogue-api.<catalogue-namespace>.svc.cluster.local
```

When the resolver runs in the same namespace, `http://catalogue-api` is
sufficient. The alias can be renamed or disabled through
`catalogueAPI.service.discovery`. If NetworkPolicy is enabled and the resolver
runs in another namespace, add that namespace to
`networkPolicy.ingressNamespaces`. Verify discovery from a platform pod with:

```bash
curl --fail http://catalogue-api.<catalogue-namespace>.svc.cluster.local/health/ready
```

The platform's logical `catalogue-values` operation should call:

```text
GET http://catalogue-api.<catalogue-namespace>.svc.cluster.local/v1/catalogue-values
```

The operation is implemented by the Catalogue API itself and requires the
existing `catalogue.read` permission. Its `options` array exposes `code` and
`display_name` for widget value/label binding; catalogue rows are not copied
into the master-data or registry databases.

The older country-pack publisher remains available behind
`catalogueSeed.enabled`, but is disabled by default.

All registry routes are protected by explicit IAM permissions and authorization
is default-deny. Workloads run as non-root with restricted container security
contexts. NetworkPolicies are enabled by default; review ingress namespaces and
external HTTPS requirements for the target cluster before installation. See
[`docs/security.md`](../../../docs/security.md) for the permission model.

Dependency-aware readiness and dependency-free liveness probes are enabled by
default. Optional Prometheus Operator `ServiceMonitor` and `PrometheusRule`
resources are configured under `monitoring`; they remain disabled until the
cluster has the corresponding CRDs. See
[`docs/operations.md`](../../../docs/operations.md) for metrics and runbooks.
Add the Prometheus namespace to `networkPolicy.ingressNamespaces` when its
scraper pods are not in the Catalogue namespace.
