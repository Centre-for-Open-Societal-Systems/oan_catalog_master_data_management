# Security model

## Authentication and authorization

All `/v1` routes require a validated IAM access token and an explicit
permission. Authorization is default-deny: adding an undecorated route does not
make it public. `/ping`, `/health/live`, `/health/ready`, and `/metrics` are the
explicit unauthenticated operational routes. NetworkPolicy limits pod ingress,
and the Istio VirtualService blocks `/metrics` on the registry-facing hostname.

| Permission | Data exposed |
| --- | --- |
| `catalogue.read` | Releases, catalogue definitions and catalogue values |
| `geography.read` | Geography levels and administrative units |
| `statistics.read` | Livestock and seed-demand statistics |
| `snapshot.read` | Complete cross-domain registry snapshot |

The IAM client configured by `global.authClientId` must define these
permissions and map them to registry roles. IAM resolves the token's client
roles into permissions; possessing a valid token alone is insufficient.

## Registry service accounts

Registry integrations should use OAuth 2.0 client credentials with a dedicated
confidential client—not a human user token or a shared client secret. Assign
only the permissions needed by that registry. A registry consuming the full
snapshot normally needs only `snapshot.read`; one consuming paged endpoints
needs the corresponding domain permissions.

Store client secrets in the platform secret manager and project them into the
registry workload. Do not commit them to catalogue manifests or Helm values.
Rotate credentials independently per registry and use short-lived access
tokens. The Catalogue Service validates the bearer token through the existing
IAM middleware and never accepts API keys or database credentials from a
registry.

## Workload security

The API, migration and seed images run as UID/GID `10001`. Helm workloads use a
read-only root filesystem, drop all Linux capabilities, disable privilege
escalation and service-account-token mounting, and request the RuntimeDefault
seccomp profile.

NetworkPolicies allow:

- API ingress from the same namespace and configured ingress namespaces;
- DNS resolution;
- PostgreSQL and IAM traffic inside the namespace;
- optional outbound HTTPS for external identity-provider/JWKS access; and
- PostgreSQL-only egress for migration and seed Jobs.

If PostgreSQL or IAM runs in another namespace, adapt the policy selectors to
that cluster topology before enabling the chart. `allowExternalHttpsEgress`
can be disabled when all identity services are internal.
