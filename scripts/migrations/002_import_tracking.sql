BEGIN;

CREATE TABLE IF NOT EXISTS catalogue_import_runs (
    import_run_id      VARCHAR PRIMARY KEY,
    release_id         VARCHAR REFERENCES catalogue_releases(release_id),
    country_code       VARCHAR(3) NOT NULL,
    source_version     VARCHAR NOT NULL,
    manifest_checksum VARCHAR NOT NULL,
    status             VARCHAR NOT NULL DEFAULT 'PENDING',
    trigger            VARCHAR NOT NULL DEFAULT 'MANUAL',
    started_at         TIMESTAMPTZ NOT NULL,
    finished_at        TIMESTAMPTZ,
    error_summary      VARCHAR,
    metadata           JSONB
);

CREATE INDEX IF NOT EXISTS ix_catalogue_import_runs_release
    ON catalogue_import_runs (release_id);
CREATE INDEX IF NOT EXISTS ix_catalogue_import_runs_country
    ON catalogue_import_runs (country_code);
CREATE INDEX IF NOT EXISTS ix_catalogue_import_runs_version
    ON catalogue_import_runs (source_version);
CREATE INDEX IF NOT EXISTS ix_catalogue_import_runs_checksum
    ON catalogue_import_runs (manifest_checksum);
CREATE INDEX IF NOT EXISTS ix_catalogue_import_runs_status
    ON catalogue_import_runs (status);

CREATE TABLE IF NOT EXISTS catalogue_import_scripts (
    import_script_id VARCHAR PRIMARY KEY,
    import_run_id    VARCHAR NOT NULL
                     REFERENCES catalogue_import_runs(import_run_id) ON DELETE CASCADE,
    script_id        VARCHAR NOT NULL,
    filename         VARCHAR NOT NULL,
    checksum         VARCHAR NOT NULL,
    execution_order  INTEGER NOT NULL,
    dataset_kind     VARCHAR NOT NULL,
    status           VARCHAR NOT NULL DEFAULT 'PENDING',
    started_at       TIMESTAMPTZ,
    finished_at      TIMESTAMPTZ,
    affected_rows    JSONB,
    error            VARCHAR,
    CONSTRAINT uq_import_run_script UNIQUE (import_run_id, script_id)
);

CREATE INDEX IF NOT EXISTS ix_catalogue_import_scripts_run
    ON catalogue_import_scripts (import_run_id);
CREATE INDEX IF NOT EXISTS ix_catalogue_import_scripts_status
    ON catalogue_import_scripts (status);

COMMIT;

