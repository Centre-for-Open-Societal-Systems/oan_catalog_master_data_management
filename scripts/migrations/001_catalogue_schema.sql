BEGIN;

CREATE TABLE IF NOT EXISTS catalogue_releases (
    release_id       VARCHAR PRIMARY KEY,
    country_code     VARCHAR(3) NOT NULL,
    version          VARCHAR NOT NULL,
    schema_version   VARCHAR NOT NULL DEFAULT '1.0',
    checksum         VARCHAR NOT NULL,
    source           VARCHAR,
    status           VARCHAR NOT NULL DEFAULT 'STAGED',
    manifest         JSONB,
    created_at       TIMESTAMPTZ NOT NULL,
    activated_at     TIMESTAMPTZ,
    CONSTRAINT uq_catalogue_release_country_version UNIQUE (country_code, version)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_catalogue_active_country
    ON catalogue_releases (country_code)
    WHERE status = 'ACTIVE';

CREATE TABLE IF NOT EXISTS catalogues (
    catalogue_id       VARCHAR PRIMARY KEY,
    release_id         VARCHAR NOT NULL REFERENCES catalogue_releases(release_id) ON DELETE CASCADE,
    code               VARCHAR NOT NULL,
    domain             VARCHAR,
    display_name       VARCHAR NOT NULL,
    display_name_i18n  JSONB,
    is_hierarchical    BOOLEAN NOT NULL DEFAULT FALSE,
    status             VARCHAR NOT NULL DEFAULT 'ACTIVE',
    CONSTRAINT uq_catalogue_release_code UNIQUE (release_id, code)
);

CREATE INDEX IF NOT EXISTS ix_catalogues_release ON catalogues (release_id);
CREATE INDEX IF NOT EXISTS ix_catalogues_domain ON catalogues (domain);

CREATE TABLE IF NOT EXISTS catalogue_values (
    catalogue_value_id VARCHAR PRIMARY KEY,
    catalogue_id       VARCHAR NOT NULL REFERENCES catalogues(catalogue_id) ON DELETE CASCADE,
    code               VARCHAR NOT NULL,
    parent_value_id    VARCHAR REFERENCES catalogue_values(catalogue_value_id),
    display_name       VARCHAR NOT NULL,
    display_name_i18n  JSONB,
    semantic_roles     JSONB,
    sort_order         INTEGER,
    valid_from         DATE,
    valid_to           DATE,
    status             VARCHAR NOT NULL DEFAULT 'ACTIVE',
    metadata           JSONB,
    CONSTRAINT uq_catalogue_value_code UNIQUE (catalogue_id, code),
    CONSTRAINT ck_catalogue_value_dates CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)
);

CREATE INDEX IF NOT EXISTS ix_catalogue_values_catalogue ON catalogue_values (catalogue_id);
CREATE INDEX IF NOT EXISTS ix_catalogue_values_parent ON catalogue_values (parent_value_id);

CREATE TABLE IF NOT EXISTS catalogue_seed_runs (
    seed_run_id  VARCHAR PRIMARY KEY,
    release_id  VARCHAR REFERENCES catalogue_releases(release_id),
    status      VARCHAR NOT NULL,
    started_at  TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    error       VARCHAR
);

COMMIT;
