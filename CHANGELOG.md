# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) and
this project uses semantic versioning.

## [Unreleased]

### Added

- Migration `012`, release-scoped publication of all 12 ET-LITS registry rows,
  the SQL-compatible registry-validation view, typed read APIs, and client methods.
- Migration `013` and deterministic crop enrichment: typed scientific name,
  centre, image, Amharic display name, taxonomy provenance, computed variety
  counts, and 21 workbook-only crop types without removing SQL-only fields.
- Migration `014` and the consolidated crop hierarchy: SQL categories link to
  enriched crops, all 902 SQL variety rows link directly to their crops, 309
  reviewed SQL/Excel identities are reused, and 593 unmatched SQL varieties
  extend the 1,359 Excel concepts into a 1,952-value union.

## [0.2.0] - 2026-08-15

### Added

- Migration `011` and ORM contracts for typed livestock species metadata,
  breeds, genders, location types, body conditions, production types and valid
  species, and ET-LITS record statuses.
- Deterministic complete-livestock SQL generation with source checksums and
  exact dataset validation.
- Canonical livestock breed, gender, location-type, body-condition,
  production-type, and ET-LITS status catalogues with 131 typed relations and
  livestock-specific publication integrity gates.
- Swagger-documented typed livestock species, breed, and reference-data APIs
  with registry-oriented filters, resolved relations, and conditional ETags.
- Typed Python registry-client methods and container smoke coverage for
  livestock species, breed filters, reference sets, release pinning, and ETags.
- Migration `010`, deterministic kebele SQL generation, reviewed woreda
  crosswalks, and level-four publication of 19,535 safely matched kebeles while
  retaining 35 unresolved source rows for review.
- Relational crop category, type, variety, source-record, and characteristic staging schema in migration `007`.
- Dependency-free crop workbook transformer with stable codes, localized-name
  extraction, relational characteristic mapping, typed range projections, CSV
  review artifacts, and deterministic source-quality reporting.
- Generated full crop-taxonomy SQL seed, immutable workbook/SQL drift check,
  exact table-count validation, and relational completeness checks in the
  transactional seed runner.
- Canonical crop taxonomy category, crop type, and crop variety publication
  with filterable category-to-type and type-to-variety relations.
- Release-scoped canonical crop source records and characteristics, plus a
  Swagger-documented crop-variety detail endpoint.
- Typed registry-client support for crop-variety detail reads, release pinning,
  conditional ETags, and response-integrity validation.
- Containerized registry-consumer acceptance profile and client wheel checks in
  the GitHub and GitLab release pipelines.
- Migration `009` and ORM contracts for Ethio-Seed variety source records,
  explicit match states, and optional normalized crop-variety relationships.
- Deterministic, drift-checked adaptation of 902 archived Ethio-Seed variety
  rows into idempotent staging SQL without executing destructive source DDL.
- Conservative seed-variety matching with 309 crop-scoped exact links and
  deterministic SQL, CSV, and JSON review artifacts for 593 unresolved rows.
- Nullable Amharic display names for region, zone, and woreda records and API responses.
- Typed cross-catalogue value relations and relation-based API filtering.
- Crop category and ecological-zone catalogues sourced from the related catalogue SQL import.
- Schema migration `005` and immutable Ethiopia SQL release `ETH-legacy-sql-v2`.

## [0.1.0] - 2026-08-13

### Added

- Versioned catalogue, geography, and agriculture-statistics data model.
- Ordered schema migration and atomic SQL publication runners.
- IAM-protected read and snapshot APIs with conditional ETag synchronization.
- Standalone registry client, Kubernetes security, and observability resources.
- Local Compose environment and production release automation.
